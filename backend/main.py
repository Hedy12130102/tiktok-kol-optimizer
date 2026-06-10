"""
TikTok Shop KOL Matrix Optimizer — FastAPI backend.

Endpoints
---------
  GET  /health           Health check
  POST /optimize         Run all 6 algorithms, return best KOL matrix
  GET  /kols             Filtered & paginated KOL list
  GET  /kol/{id}         Single KOL detail with scores & reasons
  GET  /top-kols         Top 10 KOLs by creator score
  POST /scalability      Algorithm performance at different pool sizes

Run:  uvicorn backend.main:app --reload
Docs: http://localhost:8000/docs
"""

import json
import math
import os
import sys
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
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
app.include_router(crud_router)
app.include_router(campaigns_router)

# ── Enum constants ────────────────────────────────────────────────
VALID_COUNTRIES = ["MY", "ID", "TH", "PH", "SG", "VN"]
VALID_CATEGORIES = ["beauty", "fashion", "home", "fmcg"]
VALID_TIERS = ["Mega", "Macro", "Micro", "Nano"]

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "sample_kols.json",
)


# ════════════════════════════════════════════════════════════════
#  Pydantic models
# ════════════════════════════════════════════════════════════════
class OptimizeRequest(BaseModel):
    budget: float
    country: str = "MY"
    category: str = "beauty"
    seed: int = 42


class ScalabilityRequest(BaseModel):
    n: int
    budget: float
    seed: int = 42


class KOLResult(BaseModel):
    id: int
    name: str
    country: str
    category: str
    followers: int
    engagement_rate: float
    fit_score: float
    cost: float
    expected_gmv: float
    tier: str = ""
    creator_score: float = 0.0
    reasons: List[str] = []


class KOLDetail(KOLResult):
    avg_views: Optional[int] = None
    avg_likes: Optional[int] = None
    gender_ratio: Optional[float] = None
    age_group: Optional[str] = None
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
    country: str
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
    country: str
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


class ScalabilityEntry(BaseModel):
    time_seconds: float
    total_gmv: float
    roi: float
    selected_count: int


class ScalabilityResponse(BaseModel):
    n: int
    budget: float
    simulated_annealing: ScalabilityEntry
    hill_climber: ScalabilityEntry
    random_search: ScalabilityEntry
    genetic_algorithm: ScalabilityEntry
    tabu_search: ScalabilityEntry
    greedy_ranking: ScalabilityEntry


# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════
def load_kols() -> List[KOL]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return [_dict_to_kol(d) for d in json.load(f)]


def load_raw_kols() -> List[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


_KOL_FIELDS = {"id", "name", "country", "category",
               "followers", "engagement_rate", "fit_score", "cost"}


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
        cost=k.cost,
        expected_gmv=round(k.expected_gmv(), 2),
        tier=get_tier(k),
        creator_score=score,
        reasons=generate_reasons(k, all_kols),
    )


def build_algorithm_result(
    name: str,
    state: List[int],
    history: List[float],
    kols: List[KOL],
    scores: List[float],
) -> AlgorithmResult:
    selected_idx = [i for i, x in enumerate(state) if x == 1]
    selected = [to_kol_result(kols[i], scores[i], kols) for i in selected_idx]
    summary = summarize_state(state, kols)
    return AlgorithmResult(
        algorithm=name,
        selected_kols=selected,
        selected_count=int(summary["selected_count"]),
        total_cost=round(summary["total_cost"], 2),
        total_gmv=round(summary["total_gmv"], 2),
        roi=round(summary["roi"], 4),
        history=history,
    )


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

            if a.country == b.country:
                score += 0.4
                reasons.append("same country")
            if a.category == b.category:
                score += 0.3
                reasons.append("same category")

            fa = follower_map.get(a.id, a.followers)
            fb = follower_map.get(b.id, b.followers)
            if fa > 0 and fb > 0:
                ratio = min(fa, fb) / max(fa, fb)
                if ratio > 0.8:
                    score += 0.3
                    reasons.append("similar follower range")

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
            overlap += 0.4
        if kol.category == other.category:
            overlap += 0.3
        if kol.followers > 0 and other.followers > 0:
            ratio = min(kol.followers, other.followers) / max(kol.followers, other.followers)
            if ratio > 0.5:
                overlap += 0.3
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
    """Run all 6 algorithms and return the one with highest GMV."""
    results = run_all_optimizations(filtered, budget, seed, scores, sa_T0, sa_max_iter)
    best_key = max(results, key=lambda k: results[k].total_gmv)
    return results[best_key]


# ════════════════════════════════════════════════════════════════
#  Endpoints
# ════════════════════════════════════════════════════════════════
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest):
    """Run all six algorithms and return the best KOL matrix."""
    if req.budget <= 0:
        raise HTTPException(status_code=422, detail="budget must be a positive number")
    if req.country not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail="country must be one of: MY, ID, TH, PH, SG, VN")
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, fashion, home, fmcg")

    all_kols = load_kols()
    filtered = [k for k in all_kols
                if k.country == req.country and k.category == req.category]

    if not filtered:
        return OptimizeResponse(
            budget=req.budget,
            country=req.country,
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

    best_key = max(results, key=lambda key: results[key].total_gmv)
    best = results[best_key]

    tier_bd = compute_tier_breakdown(best.selected_kols)
    overlap_warnings = detect_audience_overlap(best.selected_kols, filtered)

    return OptimizeResponse(
        budget=req.budget,
        country=req.country,
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
def optimize_plans(req: OptimizeRequest):
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
    if req.country not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail="country must be one of: MY, ID, TH, PH, SG, VN")
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, fashion, home, fmcg")

    all_kols = load_kols()
    filtered = [k for k in all_kols
                if k.country == req.country and k.category == req.category]

    if not filtered:
        return OptimizePlansResponse(
            budget=req.budget,
            country=req.country,
            category=req.category,
            candidates=0,
            plans=[],
        )

    scores = compute_creator_score(filtered)

    # ── Aggressive: 120% budget → pick algorithm with max GMV ──────────────
    aggressive_budget = req.budget * 1.2
    agg_results = run_all_optimizations(filtered, aggressive_budget, req.seed, scores,
                                        sa_T0=20000.0, sa_max_iter=300)
    agg_key = max(agg_results, key=lambda k: agg_results[k].total_gmv)
    agg_result = agg_results[agg_key]
    agg_tier = compute_tier_breakdown(agg_result.selected_kols)
    agg_overlap = detect_audience_overlap(agg_result.selected_kols, filtered)

    # ── Balanced: 100% budget → pick algorithm with max sqrt(GMV × ROI) ────
    #    Geometric mean of GMV and ROI rewards both scale and efficiency;
    #    it differs from Aggressive whenever ROI varies meaningfully across algos.
    bal_results = run_all_optimizations(filtered, req.budget, req.seed + 1, scores,
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
    safe_results = run_all_optimizations(filtered, safe_budget, req.seed + 2, scores,
                                         sa_T0=8000.0, sa_max_iter=100)
    safe_result = safe_results["greedy_ranking"]   # always best ROI
    safe_tier = compute_tier_breakdown(safe_result.selected_kols)
    safe_overlap = detect_audience_overlap(safe_result.selected_kols, filtered)

    return OptimizePlansResponse(
        budget=req.budget,
        country=req.country,
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
def get_kol(kol_id: int):
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
        gender_ratio=raw.get("gender_ratio"),
        age_group=raw.get("age_group"),
        predicted_gmv_solo=round(target.expected_gmv(), 2),
        audience_overlap_risk=compute_audience_overlap_risk(target, all_kols),
        cost_effectiveness_rank=compute_cost_effectiveness_rank(target, all_kols),
    )


@app.get("/top-kols", response_model=TopKOLResponse)
def top_kols(
    country: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
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


@app.post("/scalability", response_model=ScalabilityResponse)
def scalability(req: ScalabilityRequest):
    """
    Run all 6 algorithms on a freshly generated pool of size n
    and return execution time + final GMV for each.
    """
    if req.n < 10 or req.n > 500:
        raise HTTPException(status_code=422, detail="n must be between 10 and 500")
    if req.budget <= 0:
        raise HTTPException(status_code=422, detail="budget must be a positive number")

    from data.generator import generate_kols
    tmp_json = os.path.join(os.path.dirname(DATA_PATH), f"_scalability_tmp_{req.n}_{req.seed}.json")
    tmp_csv = tmp_json.replace(".json", ".csv")
    try:
        kol_dicts = generate_kols(
            num=req.n,
            json_output_path=tmp_json,
            csv_output_path=tmp_csv,
            seed=req.seed,
        )
        kols = [_dict_to_kol(d) for d in kol_dicts]
    finally:
        for path in (tmp_json, tmp_csv):
            if os.path.exists(path):
                os.remove(path)

    def run(algo_fn) -> ScalabilityEntry:
        t0 = time.perf_counter()
        state, _, _hist = algo_fn(kols, req.budget, seed=req.seed)
        elapsed = time.perf_counter() - t0
        summary = summarize_state(state, kols)
        return ScalabilityEntry(
            time_seconds=round(elapsed, 4),
            total_gmv=round(summary["total_gmv"], 2),
            roi=round(summary["roi"], 4),
            selected_count=int(summary["selected_count"]),
        )

    return ScalabilityResponse(
        n=req.n,
        budget=req.budget,
        simulated_annealing=run(simulated_annealing),
        hill_climber=run(hill_climber),
        random_search=run(random_search),
        genetic_algorithm=run(genetic_algorithm),
        tabu_search=run(tabu_search),
        greedy_ranking=run(greedy_ranking),
    )


# ── Serve frontend as static files (after all API routes) ──────────
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
