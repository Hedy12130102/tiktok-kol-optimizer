"""
TikTok Shop KOL Matrix Optimizer — FastAPI backend.

Endpoints
---------
  GET  /health           Health check
  POST /optimize         Run all 6 algorithms, return best KOL matrix
  GET  /kols             Filtered & paginated KOL list
  GET  /kol/{id}         Single KOL detail with scores & reasons
  GET  /top-kols         Top 10 KOLs by creator score
  POST /simulate-scale   Synthetic pool-size simulator (achievable GMV vs creator count)

Run:  uvicorn backend.main:app --reload
Docs: http://localhost:8000/docs
"""

import json
import math
import os
import sys
import contextvars
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Make project root importable ──────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.fitness import summarize_state
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.hill_climber import hill_climber
from engine.optimization.random_search import random_search
from engine.optimization.genetic_algorithm import genetic_algorithm
from engine.optimization.tabu_search import tabu_search
from engine.optimization.greedy_ranking import greedy_ranking
from engine.scoring.creator_score import compute_creator_score
from engine.scoring.explainer import generate_reasons, get_tier
from backend import tenancy
from backend import calibration
from backend.auth import router as auth_router, require_tenant
from backend.crud import router as crud_router
from backend.campaigns import router as campaigns_router

app = FastAPI(
    title="TikTok Shop KOL Matrix Optimizer API",
    description="Local search optimizer for selecting a KOL portfolio under a marketing budget.",
    version="2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(crud_router)
app.include_router(campaigns_router)

# ── Enum constants ────────────────────────────────────────────────
VALID_COUNTRIES = ["MY", "ID", "TH", "PH", "SG", "VN"]
VALID_CATEGORIES = ["beauty", "fashion", "home", "fmcg"]
VALID_TIERS = ["Mega", "Macro", "Micro", "Nano"]

# The active KOL library is resolved per-tenant at call time (backend/tenancy.py),
# so every request reads only the current merchant's isolated library.


# ════════════════════════════════════════════════════════════════
#  Pydantic models
# ════════════════════════════════════════════════════════════════
class OptimizeRequest(BaseModel):
    budget: float
    countries: List[str] = []
    category: str = "beauty"
    seed: int = 42


class SimulateScaleRequest(BaseModel):
    """Inputs for the synthetic Creator-Pool-Size simulator."""
    budget: float
    seed: int = 42
    sizes: List[int] = []                 # pool sizes to sweep; empty = default sweep
    target_gmv: Optional[float] = None     # optional GMV goal → server returns needed_n


class KOLResult(BaseModel):
    id: int
    name: str
    country: str
    category: str
    followers: int
    engagement_rate: float
    fit_score: float
    commission_rate: float = 0.15
    cost: float
    expected_gmv: float
    tier: str = ""
    creator_score: float = 0.0
    reasons: List[str] = []
    age_group: str = ""
    gender_ratio: float = 0.5
    source: str = "fastmoss"          # "fastmoss" (real import) | "synthetic" (demo fill)
    cost_estimated: bool = False      # True when cost was inferred, not a real quote


class KOLDetail(KOLResult):
    avg_views: Optional[int] = None
    avg_likes: Optional[int] = None
    predicted_gmv_solo: float = 0.0
    audience_overlap_risk: float = 0.0
    cost_effectiveness_rank: int = 0


class AlgorithmResult(BaseModel):
    algorithm: str
    selected_kols: List[KOLResult]
    selected_count: int
    total_cost: float
    total_gmv: float
    roi: float
    # GMV net of the audience-overlap penalty — the true objective the solvers
    # optimise. Algorithms are RANKED by this, while total_gmv stays the headline
    # display number. (See summarize_state in engine/fitness.py.)
    objective: float
    history: List[float]


class OverlapWarning(BaseModel):
    kol_id_1: int
    kol_name_1: str
    kol_id_2: int
    kol_name_2: str
    overlap_score: float
    reason: str


class TierBreakdown(BaseModel):
    Mega: int = 0
    Macro: int = 0
    Micro: int = 0
    Nano: int = 0


class OptimizeResponse(BaseModel):
    budget: float
    countries: List[str]
    category: str
    candidates: int
    best_algorithm: str
    selected_kols: List[KOLResult]
    total_cost: float
    total_gmv: float
    roi: float
    results: Dict[str, AlgorithmResult]
    tier_breakdown: TierBreakdown = TierBreakdown()
    overlap_warnings: List[OverlapWarning] = []


class PlanResult(BaseModel):
    plan_name: str
    description: str
    budget_limit: float
    selected_kols: List[KOLResult]
    total_cost: float
    total_gmv: float
    roi: float
    tier_breakdown: TierBreakdown = TierBreakdown()
    overlap_warnings: List[OverlapWarning] = []


class OptimizePlansResponse(BaseModel):
    budget: float
    countries: List[str]
    category: str
    candidates: int
    plans: List[PlanResult]


class KOLListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    kols: List[KOLResult]


class TopKOLResponse(BaseModel):
    country: Optional[str]
    category: Optional[str]
    top_kols: List[KOLResult]


class ScalePoint(BaseModel):
    n: int                  # pool size (number of synthetic creators)
    gmv: float              # best achievable GMV at this size (optimized)
    baseline_gmv: float     # random-search baseline at this size (for contrast)
    roi: float
    selected_count: int


class SimulateScaleResponse(BaseModel):
    budget: float
    seed: int
    target_gmv: Optional[float] = None
    needed_n: Optional[int] = None   # smallest swept size whose GMV ≥ target (None = not reached)
    points: List[ScalePoint]


# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════
# Presentation-only metadata (source, cost_estimated) that the engine KOL
# dataclass deliberately doesn't carry. Held in a request-scoped contextvar so
# concurrent tenants never share each other's badge metadata.
_KOL_META_VAR: contextvars.ContextVar = contextvars.ContextVar("kol_meta", default=None)


def _refresh_meta(raw_list: List[dict]):
    _KOL_META_VAR.set({
        d["id"]: {
            "source": d.get("source", "fastmoss"),
            "cost_estimated": bool(d.get("cost_estimated", False)),
        }
        for d in raw_list
    })


def _kol_meta() -> dict:
    return _KOL_META_VAR.get() or {}


def load_kols() -> List[KOL]:
    try:
        with open(tenancy.data_path(), encoding="utf-8") as f:
            raw = json.load(f)
        _refresh_meta(raw)
        return [_dict_to_kol(d) for d in raw]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500, detail=f"Data file error: {e}")


def load_raw_kols() -> List[dict]:
    with open(tenancy.data_path(), encoding="utf-8") as f:
        raw = json.load(f)
    _refresh_meta(raw)
    return raw


_KOL_FIELDS = {"id", "name", "country", "category",
               "followers", "engagement_rate", "fit_score",
               "commission_rate", "cost",
               "avg_views", "avg_likes", "gender_ratio", "age_group"}


def _dict_to_kol(d: dict) -> KOL:
    return KOL(**{k: v for k, v in d.items() if k in _KOL_FIELDS})


def to_kol_result(k: KOL, score: float, all_kols: List[KOL]) -> KOLResult:
    return KOLResult(
        id=k.id,
        name=k.name,
        country=k.country,
        category=k.category,
        followers=k.followers,
        engagement_rate=k.engagement_rate,
        fit_score=k.fit_score,
        commission_rate=k.commission_rate,
        cost=k.cost,
        # Calibrated by past actual-vs-predicted outcomes — this creator's own
        # track record, falling back to its (category, country) segment, then
        # global (factor = 1.0 until the tenant has completed campaigns).
        expected_gmv=round(k.expected_gmv() * calibration.factor(k.category, k.country, k.id), 2),
        tier=get_tier(k),
        age_group=k.age_group,
        gender_ratio=k.gender_ratio,
        creator_score=score,
        reasons=generate_reasons(k, all_kols),
        source=_kol_meta().get(k.id, {}).get("source", "fastmoss"),
        cost_estimated=_kol_meta().get(k.id, {}).get("cost_estimated", False),
    )


def build_algorithm_result(
    name: str,
    state: List[int],
    history: List[float],
    kols: List[KOL],
    scores: List[float],
) -> AlgorithmResult:
    # Displayed GMV/ROI are summed from the per-creator *calibrated* predictions
    # (to_kol_result applies the calibration factor), so the cards always reconcile
    # with the total. The solver's `objective` (its ranking metric) stays raw, so
    # which creators/algorithm win is unaffected. No calibration history → factor
    # 1.0 → numbers match the raw model.
    selected_idx = [i for i, x in enumerate(state) if x == 1]
    selected = [to_kol_result(kols[i], scores[i], kols) for i in selected_idx]
    summary = summarize_state(state, kols)
    total_cost = round(summary["total_cost"], 2)
    total_gmv = round(sum(s.expected_gmv for s in selected), 2)
    return AlgorithmResult(
        algorithm=name,
        selected_kols=selected,
        selected_count=int(summary["selected_count"]),
        total_cost=total_cost,
        total_gmv=total_gmv,
        roi=round(total_gmv / total_cost, 4) if total_cost > 0 else 0.0,
        objective=round(summary["objective"], 2),
        history=history,
    )


# Key of the reference baseline in the results dict. Random Search is a
# yardstick the real optimisers are measured against — never a recommendation.
BASELINE_ALGORITHM = "random_search"


def pick_recommended_key(results: Dict[str, AlgorithmResult]) -> str:
    """Choose the recommended algorithm: the highest objective (GMV net of the
    audience-overlap penalty) AMONG the real optimisers, excluding the Random
    Search baseline. Falls back to all results only if no optimiser ran."""
    solvers = [k for k in results if k != BASELINE_ALGORITHM]
    pool = solvers or list(results)
    return max(pool, key=lambda k: results[k].objective)


def compute_tier_breakdown(kols: List[KOLResult]) -> TierBreakdown:
    counts = {"Mega": 0, "Macro": 0, "Micro": 0, "Nano": 0}
    for k in kols:
        t = k.tier or get_tier_from_followers(k.followers)
        if t in counts:
            counts[t] += 1
    return TierBreakdown(**counts)


def get_tier_from_followers(followers: int) -> str:
    if followers >= 1_000_000:
        return "Mega"
    if followers >= 100_000:
        return "Macro"
    if followers >= 10_000:
        return "Micro"
    return "Nano"


def detect_audience_overlap(selected_kols: List[KOLResult], all_kols: List[KOL]) -> List[OverlapWarning]:
    """Warn when two selected KOLs target demographically near-identical audiences.

    IMPORTANT: /optimize already filters by country + category, so we skip
    those dimensions (every pair would trigger). Instead we check follower
    range, age group, and gender skew — the same dimensions used by the
    fitness overlap penalty.
    """
    warnings: List[OverlapWarning] = []
    n = len(selected_kols)
    if n < 2:
        return warnings

    follower_map = {k.id: k.followers for k in all_kols}

    for i in range(n):
        for j in range(i + 1, n):
            a = selected_kols[i]
            b = selected_kols[j]
            score = 0.0
            reasons: List[str] = []

            fa = follower_map.get(a.id, a.followers)
            fb = follower_map.get(b.id, b.followers)
            if fa > 0 and fb > 0:
                ratio = min(fa, fb) / max(fa, fb)
                if ratio > 0.5:
                    score += 0.5
                    reasons.append("similar follower range")

            if hasattr(a, 'age_group') and hasattr(b, 'age_group') and a.age_group and b.age_group and a.age_group == b.age_group:
                score += 0.3
                reasons.append("same age group")

            if hasattr(a, 'gender_ratio') and hasattr(b, 'gender_ratio'):
                if a.gender_ratio >= 0.7 and b.gender_ratio >= 0.7:
                    score += 0.2
                    reasons.append("both heavily female")
                elif a.gender_ratio <= 0.3 and b.gender_ratio <= 0.3:
                    score += 0.2
                    reasons.append("both heavily male")

            if score > 0.5:
                warnings.append(OverlapWarning(
                    kol_id_1=a.id,
                    kol_name_1=a.name,
                    kol_id_2=b.id,
                    kol_name_2=b.name,
                    overlap_score=round(score, 2),
                    reason=", ".join(reasons),
                ))

    warnings.sort(key=lambda w: w.overlap_score, reverse=True)
    return warnings


def compute_audience_overlap_risk(kol: KOL, all_kols: List[KOL]) -> float:
    if len(all_kols) <= 1:
        return 0.0

    sorted_by_followers = sorted(all_kols, key=lambda k: k.followers, reverse=True)
    top_n = max(1, len(all_kols) // 5)
    top_kols = sorted_by_followers[:top_n]

    total_overlap = 0.0
    count = 0
    for other in top_kols:
        if other.id == kol.id:
            continue
        overlap = 0.0
        if kol.country == other.country:
            overlap += 0.3
        if kol.category == other.category:
            overlap += 0.2
        if kol.followers > 0 and other.followers > 0:
            ratio = min(kol.followers, other.followers) / max(kol.followers, other.followers)
            if ratio > 0.5:
                overlap += 0.3
        if kol.age_group and other.age_group and kol.age_group == other.age_group:
            overlap += 0.1
        if kol.gender_ratio >= 0.7 and other.gender_ratio >= 0.7:
            overlap += 0.05
        elif kol.gender_ratio <= 0.3 and other.gender_ratio <= 0.3:
            overlap += 0.05
        total_overlap += overlap
        count += 1

    if count == 0:
        return 0.0
    return round(min(total_overlap / count, 1.0), 2)


def compute_cost_effectiveness_rank(kol: KOL, all_kols: List[KOL]) -> int:
    if kol.cost <= 0:
        return len(all_kols)

    target_ratio = kol.expected_gmv() / kol.cost
    better_count = sum(
        1 for k in all_kols
        if k.cost > 0 and (k.expected_gmv() / k.cost) > target_ratio
    )
    return better_count + 1


def _downsample(history: List[float], target: int = 400) -> List[float]:
    """Downsample history to at most `target` evenly-spaced points."""
    n = len(history)
    if n <= target:
        return history
    step = n / target
    return [history[min(int(i * step), n - 1)] for i in range(target)]


def run_all_optimizations(
    filtered: List[KOL],
    budget: float,
    seed: int,
    scores: List[float],
    sa_T0: float = 15000.0,
    sa_max_iter: int = 150,
) -> Dict[str, AlgorithmResult]:
    """Run all 6 algorithms and return the full results dict."""
    sa_state, _, sa_hist = simulated_annealing(filtered, budget, seed=seed, T0=sa_T0, max_iter=sa_max_iter)
    hc_state, _, hc_hist = hill_climber(filtered, budget, seed=seed)
    rs_state, _, rs_hist = random_search(filtered, budget, seed=seed)
    ga_state, _, ga_hist = genetic_algorithm(filtered, budget, seed=seed)
    ts_state, _, ts_hist = tabu_search(filtered, budget, seed=seed)
    gr_state, _, gr_hist = greedy_ranking(filtered, budget, seed=seed)

    return {
        "simulated_annealing": build_algorithm_result("Simulated Annealing", sa_state, _downsample(sa_hist), filtered, scores),
        "hill_climber":        build_algorithm_result("Hill Climber",        hc_state, _downsample(hc_hist), filtered, scores),
        "random_search":       build_algorithm_result("Random Search",       rs_state, _downsample(rs_hist), filtered, scores),
        "genetic_algorithm":   build_algorithm_result("Genetic Algorithm",   ga_state, _downsample(ga_hist), filtered, scores),
        "tabu_search":         build_algorithm_result("Tabu Search",         ts_state, _downsample(ts_hist), filtered, scores),
        "greedy_ranking":      build_algorithm_result("Greedy Ranking",      gr_state, _downsample(gr_hist), filtered, scores),
    }


def run_single_optimization(
    filtered: List[KOL],
    budget: float,
    seed: int,
    scores: List[float],
    sa_T0: float = 15000.0,
    sa_max_iter: int = 150,
) -> AlgorithmResult:
    """Run all 6 algorithms and return the recommended optimiser — the highest
    true objective (GMV net of audience-overlap penalty) among the real solvers,
    excluding the Random Search baseline."""
    results = run_all_optimizations(filtered, budget, seed, scores, sa_T0, sa_max_iter)
    return results[pick_recommended_key(results)]


def run_greedy_only(filtered: List[KOL], budget: float, seed: int, scores: List[float]) -> AlgorithmResult:
    """Greedy Ranking only — used by the Safe plan, which always picks Greedy.

    Running all six algorithms just to discard five of them is wasted work that
    grows with pool size and budget, so the Safe plan calls this directly.
    """
    gr_state, _, gr_hist = greedy_ranking(filtered, budget, seed=seed)
    return build_algorithm_result("Greedy Ranking", gr_state, _downsample(gr_hist), filtered, scores)


def run_plan_optimizers(
    filtered: List[KOL],
    budget: float,
    seed: int,
    scores: List[float],
    sa_T0: float = 15000.0,
    sa_max_iter: int = 150,
) -> Dict[str, AlgorithmResult]:
    """Run only the consistently strong solvers (SA, GA, Greedy) for the plans.

    The Aggressive/Balanced plans just need the best portfolio under a criterion;
    the weak baselines (Random Search, Hill Climber) never win, and Tabu Search's
    O(N^2) cost dominates runtime — so they're skipped here. The full six-way
    comparison still runs in /optimize for the Technical benchmark view.
    """
    sa_state, _, sa_hist = simulated_annealing(filtered, budget, seed=seed, T0=sa_T0, max_iter=sa_max_iter)
    ga_state, _, ga_hist = genetic_algorithm(filtered, budget, seed=seed)
    gr_state, _, gr_hist = greedy_ranking(filtered, budget, seed=seed)
    return {
        "simulated_annealing": build_algorithm_result("Simulated Annealing", sa_state, _downsample(sa_hist), filtered, scores),
        "genetic_algorithm":   build_algorithm_result("Genetic Algorithm",   ga_state, _downsample(ga_hist), filtered, scores),
        "greedy_ranking":      build_algorithm_result("Greedy Ranking",       gr_state, _downsample(gr_hist), filtered, scores),
    }


# ════════════════════════════════════════════════════════════════
#  Endpoints
# ════════════════════════════════════════════════════════════════
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/calibration")
def get_calibration(_t: str = Depends(require_tenant)):
    """How much past actual-vs-predicted outcomes are nudging this tenant's GMV
    predictions (1.0 = no adjustment yet)."""
    return calibration.summary()



# ── API Connections (commercial expansion stubs) ──────────────────
# Phase 1 (current): manual import only
# Phase 2 (planned): TikTok Creator Marketplace, TikTok Shop Partner API
# Phase 3 (planned): Third-party analytics (AsiaKOL, Cube Asia, Nox)

class ApiConnectionRequest(BaseModel):
    integration_type: str
    credentials: Dict[str, str]

class ApiInterestRequest(BaseModel):
    email: str
    integration_type: str

@app.get("/api/connections")
def list_connections():
    """Return status of all available data source integrations."""
    return {
        "connections": [
            {"id": "manual", "name": "Manual Import", "status": "active",
             "description": "CSV upload and manual KOL entry"},
            {"id": "tiktok_creator", "name": "TikTok Creator Marketplace API", "status": "coming_soon",
             "description": "Auto-sync KOL profiles and audience demographics"},
            {"id": "tiktok_shop", "name": "TikTok Shop Partner API", "status": "coming_soon",
             "description": "Real GMV and commission data from affiliate campaigns"},
            {"id": "third_party", "name": "Third-Party Analytics Platforms", "status": "coming_soon",
             "description": "AsiaKOL, Cube Asia, Nox Influencer and similar"},
        ]
    }

@app.post("/api/connections/interest")
def register_interest(req: ApiInterestRequest):
    """Register merchant interest in a coming-soon integration."""
    import re as _re
    if not _re.match(r"[^@]+@[^@]+\.[^@]+", req.email):
        raise HTTPException(status_code=422, detail="Invalid email address")
    valid_types = {"tiktok_creator", "tiktok_shop", "third_party"}
    if req.integration_type not in valid_types:
        raise HTTPException(status_code=422, detail=f"Unknown integration type: {req.integration_type}")
    return {"status": "registered", "email": req.email, "integration_type": req.integration_type}

@app.post("/api/connections/connect")
def connect_integration(req: ApiConnectionRequest):
    """Stub — integrations not yet live."""
    return {
        "status": "coming_soon",
        "message": f"Integration '{req.integration_type}' is not yet available."
    }

# Cap how many candidates the metaheuristics actually search over. A large
# connected creator library can hold hundreds of creators in a single
# market+category slice; running six algorithms (and ×3 for the plan variants)
# over all of them is slow and unnecessary. We pre-screen to the top-K by
# CreatorScore — a realistic shortlisting step that keeps /optimize responsive
# no matter how big the library grows, while leaving the search space large
# enough that the algorithms still produce meaningfully different solutions.
CANDIDATE_CAP = 80


def shortlist_candidates(kols: List[KOL], scores: List[float], cap: int = CANDIDATE_CAP):
    """Return the top-`cap` creators by CreatorScore, with their aligned scores."""
    if len(kols) <= cap:
        return kols, scores
    top = sorted(range(len(kols)), key=lambda i: scores[i], reverse=True)[:cap]
    top.sort()
    return [kols[i] for i in top], [scores[i] for i in top]


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest, _t: str = Depends(require_tenant)):
    """Run all six algorithms and return the best KOL matrix."""
    if req.budget <= 0:
        raise HTTPException(status_code=422, detail="budget must be a positive number")
    invalid_countries = [c for c in req.countries if c not in VALID_COUNTRIES]
    if invalid_countries:
        raise HTTPException(status_code=422, detail=f"invalid countries: {invalid_countries}")
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, fashion, home, fmcg")

    active_countries = set(req.countries) if req.countries else set(VALID_COUNTRIES)
    all_kols = load_kols()
    filtered = [k for k in all_kols
                if k.country in active_countries and k.category == req.category]

    if not filtered:
        return OptimizeResponse(
            budget=req.budget,
            countries=list(active_countries),
            category=req.category,
            candidates=0,
            best_algorithm="none",
            selected_kols=[],
            total_cost=0.0,
            total_gmv=0.0,
            roi=0.0,
            results={},
        )

    scores = compute_creator_score(filtered)
    filtered, scores = shortlist_candidates(filtered, scores)

    sa_state, _, sa_hist = simulated_annealing(filtered, req.budget, seed=req.seed)
    hc_state, _, hc_hist = hill_climber(filtered, req.budget, seed=req.seed)
    rs_state, _, rs_hist = random_search(filtered, req.budget, seed=req.seed)
    ga_state, _, ga_hist = genetic_algorithm(filtered, req.budget, seed=req.seed)
    ts_state, _, ts_hist = tabu_search(filtered, req.budget, seed=req.seed)
    gr_state, _, gr_hist = greedy_ranking(filtered, req.budget, seed=req.seed)

    results = {
        "simulated_annealing": build_algorithm_result("Simulated Annealing", sa_state, _downsample(sa_hist), filtered, scores),
        "hill_climber":        build_algorithm_result("Hill Climber",        hc_state, _downsample(hc_hist), filtered, scores),
        "random_search":       build_algorithm_result("Random Search",       rs_state, _downsample(rs_hist), filtered, scores),
        "genetic_algorithm":   build_algorithm_result("Genetic Algorithm",   ga_state, _downsample(ga_hist), filtered, scores),
        "tabu_search":         build_algorithm_result("Tabu Search",         ts_state, _downsample(ts_hist), filtered, scores),
        "greedy_ranking":      build_algorithm_result("Greedy Ranking",      gr_state, _downsample(gr_hist), filtered, scores),
    }

    # Recommend the best real optimiser by true objective (GMV net of overlap),
    # excluding the Random Search baseline.
    best_key = pick_recommended_key(results)
    best = results[best_key]

    tier_bd = compute_tier_breakdown(best.selected_kols)
    overlap_warnings = detect_audience_overlap(best.selected_kols, filtered)

    return OptimizeResponse(
        budget=req.budget,
        countries=list(active_countries),
        category=req.category,
        candidates=len(filtered),
        best_algorithm=best.algorithm,
        selected_kols=best.selected_kols,
        total_cost=best.total_cost,
        total_gmv=best.total_gmv,
        roi=best.roi,
        results=results,
        tier_breakdown=tier_bd,
        overlap_warnings=overlap_warnings,
    )


@app.post("/optimize-plans", response_model=OptimizePlansResponse)
def optimize_plans(req: OptimizeRequest, _t: str = Depends(require_tenant)):
    """Return 3 plans with genuinely different selection objectives.

    Aggressive  — 120% budget, winner = algorithm with highest total GMV.
                  "Spend more, maximise reach."

    Balanced    — 100% budget, winner = algorithm with highest sqrt(GMV × ROI).
                  Geometric mean penalises both low-GMV and low-ROI extremes.
                  "Best trade-off between scale and efficiency."

    Safe        — 80% budget, winner = Greedy Ranking.
                  Greedy picks by GMV/cost ratio, guaranteeing the best
                  cost-effectiveness in the pool.
                  "Protect budget, maximise ROI."
    """
    if req.budget <= 0:
        raise HTTPException(status_code=422, detail="budget must be a positive number")
    invalid_countries = [c for c in req.countries if c not in VALID_COUNTRIES]
    if invalid_countries:
        raise HTTPException(status_code=422, detail=f"invalid countries: {invalid_countries}")
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, fashion, home, fmcg")

    active_countries = set(req.countries) if req.countries else set(VALID_COUNTRIES)
    all_kols = load_kols()
    filtered = [k for k in all_kols
                if k.country in active_countries and k.category == req.category]

    if not filtered:
        return OptimizePlansResponse(
            budget=req.budget,
            countries=list(active_countries),
            category=req.category,
            candidates=0,
            plans=[],
        )

    scores = compute_creator_score(filtered)
    filtered, scores = shortlist_candidates(filtered, scores)

    # ── Aggressive: 120% budget → pick algorithm with max GMV ──────────────
    aggressive_budget = req.budget * 1.2
    agg_results = run_plan_optimizers(filtered, aggressive_budget, req.seed, scores,
                                      sa_T0=20000.0, sa_max_iter=200)
    agg_key = max(agg_results, key=lambda k: agg_results[k].total_gmv)
    agg_result = agg_results[agg_key]
    agg_tier = compute_tier_breakdown(agg_result.selected_kols)
    agg_overlap = detect_audience_overlap(agg_result.selected_kols, filtered)

    # ── Balanced: 100% budget → pick algorithm with max sqrt(GMV × ROI) ────
    #    Geometric mean of GMV and ROI rewards both scale and efficiency;
    #    it differs from Aggressive whenever ROI varies meaningfully across algos.
    bal_results = run_plan_optimizers(filtered, req.budget, req.seed + 1, scores,
                                      sa_T0=15000.0, sa_max_iter=150)
    bal_key = max(bal_results,
                  key=lambda k: math.sqrt(bal_results[k].total_gmv * max(bal_results[k].roi, 0.01)))
    bal_result = bal_results[bal_key]
    bal_tier = compute_tier_breakdown(bal_result.selected_kols)
    bal_overlap = detect_audience_overlap(bal_result.selected_kols, filtered)

    # ── Safe: 80% budget → always use Greedy Ranking ───────────────────────
    #    Greedy sorts by GMV/cost and greedily fills the budget, giving the
    #    provably best cost-effectiveness ratio in the pool.
    safe_budget = req.budget * 0.8
    safe_result = run_greedy_only(filtered, safe_budget, req.seed + 2, scores)   # always best ROI
    safe_tier = compute_tier_breakdown(safe_result.selected_kols)
    safe_overlap = detect_audience_overlap(safe_result.selected_kols, filtered)

    return OptimizePlansResponse(
        budget=req.budget,
        countries=list(active_countries),
        category=req.category,
        candidates=len(filtered),
        plans=[
            PlanResult(
                plan_name="Aggressive",
                description="Maximize GMV with up to 120% budget. Best for growth campaigns.",
                budget_limit=aggressive_budget,
                selected_kols=agg_result.selected_kols,
                total_cost=agg_result.total_cost,
                total_gmv=agg_result.total_gmv,
                roi=agg_result.roi,
                tier_breakdown=agg_tier,
                overlap_warnings=agg_overlap,
            ),
            PlanResult(
                plan_name="Balanced",
                description="Optimal GMV–ROI trade-off within budget. Recommended default.",
                budget_limit=req.budget,
                selected_kols=bal_result.selected_kols,
                total_cost=bal_result.total_cost,
                total_gmv=bal_result.total_gmv,
                roi=bal_result.roi,
                tier_breakdown=bal_tier,
                overlap_warnings=bal_overlap,
            ),
            PlanResult(
                plan_name="Safe",
                description="80% budget cap, Greedy selection — highest cost-effectiveness guaranteed.",
                budget_limit=safe_budget,
                selected_kols=safe_result.selected_kols,
                total_cost=safe_result.total_cost,
                total_gmv=safe_result.total_gmv,
                roi=safe_result.roi,
                tier_breakdown=safe_tier,
                overlap_warnings=safe_overlap,
            ),
        ],
    )


@app.get("/kols", response_model=KOLListResponse)
def get_kols(
    country: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _t: str = Depends(require_tenant),
):
    """Return a filtered, paginated list of KOLs."""
    if country is not None and country not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail="country must be one of: MY, ID, TH, PH, SG, VN")
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, fashion, home, fmcg")
    if tier is not None and tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail="tier must be one of: Mega, Macro, Micro, Nano")

    all_kols = load_kols()

    filtered = [
        k for k in all_kols
        if (country is None or k.country == country)
        and (category is None or k.category == category)
        and (tier is None or get_tier(k) == tier)
    ]

    scores = compute_creator_score(filtered)
    page = filtered[offset:offset + limit]
    page_scores = scores[offset:offset + limit]

    kols_out = [
        to_kol_result(k, s, filtered) for k, s in zip(page, page_scores)
    ]

    return KOLListResponse(
        total=len(filtered),
        limit=limit,
        offset=offset,
        kols=kols_out,
    )


@app.get("/kol/{kol_id}", response_model=KOLDetail)
def get_kol(kol_id: int, _t: str = Depends(require_tenant)):
    """Return full details for a single KOL, including extended fields."""
    raw_kols = load_raw_kols()
    raw = next((d for d in raw_kols if d["id"] == kol_id), None)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"KOL with id {kol_id} not found")

    all_kols = [_dict_to_kol(d) for d in raw_kols]
    target = _dict_to_kol(raw)

    scores = compute_creator_score(all_kols)
    idx = next(i for i, k in enumerate(all_kols) if k.id == kol_id)
    score = scores[idx]

    base = to_kol_result(target, score, all_kols)

    return KOLDetail(
        **base.model_dump(),
        avg_views=raw.get("avg_views"),
        avg_likes=raw.get("avg_likes"),
        predicted_gmv_solo=round(target.expected_gmv(), 2),
        audience_overlap_risk=compute_audience_overlap_risk(target, all_kols),
        cost_effectiveness_rank=compute_cost_effectiveness_rank(target, all_kols),
    )


@app.get("/top-kols", response_model=TopKOLResponse)
def top_kols(
    country: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    _t: str = Depends(require_tenant),
):
    """Return the top 10 KOLs ranked by creator score."""
    if country is not None and country not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail="country must be one of: MY, ID, TH, PH, SG, VN")
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, fashion, home, fmcg")

    all_kols = load_kols()
    filtered = [
        k for k in all_kols
        if (country is None or k.country == country)
        and (category is None or k.category == category)
    ]

    if not filtered:
        return TopKOLResponse(country=country, category=category, top_kols=[])

    scores = compute_creator_score(filtered)
    paired = sorted(zip(filtered, scores), key=lambda p: p[1], reverse=True)[:10]
    top = [to_kol_result(k, s, filtered) for k, s in paired]

    return TopKOLResponse(country=country, category=category, top_kols=top)


_DEFAULT_SCALE_SIZES = [25, 50, 100, 200, 300, 500]


@app.post("/simulate-scale", response_model=SimulateScaleResponse)
def simulate_scale(req: SimulateScaleRequest):
    """
    Creator-Pool-Size simulator — answers "how big a creator library do I need
    to reach my target GMV?".

    Runs entirely on freshly generated **synthetic** creators (a generic mixed
    pool), independent of the user's real library. For each pool size it reports
    the achievable GMV (best of the strong solvers) plus a random-search baseline,
    so the frontend can plot achievable-GMV-vs-pool-size and read off the size
    needed to hit a target.
    """
    if req.budget <= 0:
        raise HTTPException(status_code=422, detail="budget must be a positive number")

    # Normalise the requested sweep: clamp to [10, 500], de-dup, cap count, sort.
    sizes = sorted({max(10, min(500, int(s))) for s in (req.sizes or _DEFAULT_SCALE_SIZES)})[:8]
    if not sizes:
        sizes = list(_DEFAULT_SCALE_SIZES)

    # Generate ONE synthetic pool at the largest size, then slice it for the
    # smaller sizes → a clean monotonic curve from a single generation pass.
    import tempfile
    from data.generator import generate_kols
    max_n = sizes[-1]
    with tempfile.TemporaryDirectory() as tmpdir:
        kol_dicts = generate_kols(
            num=max_n,
            json_output_path=os.path.join(tmpdir, f"scale_{max_n}_{req.seed}.json"),
            csv_output_path=os.path.join(tmpdir, f"scale_{max_n}_{req.seed}.csv"),
            seed=req.seed,
        )
    full_pool = [_dict_to_kol(d) for d in kol_dicts]

    points: List[ScalePoint] = []
    best_run = 0.0   # running max → monotonic achievable curve (pools are nested)
    base_run = 0.0
    for n in sizes:
        pool = full_pool[:n]
        # Achievable = best of the strong solvers AND the baseline (skip O(N^2) Tabu).
        ga = summarize_state(genetic_algorithm(pool, req.budget, seed=req.seed)[0], pool)
        gr = summarize_state(greedy_ranking(pool, req.budget, seed=req.seed)[0], pool)
        rs = summarize_state(random_search(pool, req.budget, seed=req.seed)[0], pool)
        cand = max((ga, gr, rs), key=lambda s: s["total_gmv"])
        best_run = max(best_run, cand["total_gmv"])
        base_run = max(base_run, rs["total_gmv"])
        points.append(ScalePoint(
            n=n,
            gmv=round(best_run, 2),
            baseline_gmv=round(base_run, 2),
            roi=round(cand["roi"], 4),
            selected_count=int(cand["selected_count"]),
        ))

    needed_n = None
    if req.target_gmv and req.target_gmv > 0:
        hit = next((p.n for p in points if p.gmv >= req.target_gmv), None)
        needed_n = hit

    return SimulateScaleResponse(
        budget=req.budget,
        seed=req.seed,
        target_gmv=req.target_gmv,
        needed_n=needed_n,
        points=points,
    )


# ── Serve frontend as static files (after all API routes) ──────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
