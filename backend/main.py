"""
TikTok Shop KOL Matrix Optimizer — FastAPI backend.
 
Endpoints
---------
  GET  /health           Health check
  POST /optimize         Run all 3 algorithms, return best KOL matrix
  GET  /kols             Filtered & paginated KOL list
  GET  /kol/{id}         Single KOL detail with scores & reasons
  GET  /top-kols         Top 10 KOLs by creator score
  POST /scalability      Algorithm performance at different pool sizes
 
Run:  uvicorn backend.main:app --reload
Docs: http://localhost:8000/docs
"""

import json
import os
import sys
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
 
# ── Make project root importable ──────────────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
from engine.models import KOL
from engine.fitness import summarize_state
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.hill_climber import hill_climber
from engine.optimization.random_search import random_search
from engine.scoring.creator_score import compute_creator_score
from engine.scoring.explainer import generate_reasons, get_tier
 
app = FastAPI(
    title="TikTok Shop KOL Matrix Optimizer API",
    description="Local search optimizer for selecting a KOL portfolio under a marketing budget.",
    version="1.0",
)
 
# ── Enum constants ────────────────────────────────────────────────
VALID_COUNTRIES = ["MY", "ID", "TH", "PH"]
VALID_CATEGORIES = ["beauty", "tech", "fashion"]
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
 
 
class AlgorithmResult(BaseModel):
    algorithm: str
    selected_kols: List[KOLResult]
    selected_count: int
    total_cost: float
    total_gmv: float
    roi: float
    history: List[float]
 
 
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
 
 
# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════
def load_kols() -> List[KOL]:
    """
    Load KOLs from the JSON data file.
 
    The data file may contain extra fields (avg_views, avg_likes,
    gender_ratio, age_group) that the KOL dataclass does not accept,
    so we only pass the fields KOL knows about, and keep the raw dict
    for endpoints that need the extra fields.
    """
    with open(DATA_PATH, encoding="utf-8") as f:
        return [_dict_to_kol(d) for d in json.load(f)]
 
 
def load_raw_kols() -> List[dict]:
    """Load the raw dicts (including extra fields) for detail endpoints."""
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)
 
 
# Only these keys are passed into the KOL dataclass constructor.
_KOL_FIELDS = {"id", "name", "country", "category",
               "followers", "engagement_rate", "fit_score", "cost"}
 
 
def _dict_to_kol(d: dict) -> KOL:
    """Build a KOL from a dict, ignoring any extra fields."""
    return KOL(**{k: v for k, v in d.items() if k in _KOL_FIELDS})
 
 
def to_kol_result(k: KOL, score: float, all_kols: List[KOL]) -> KOLResult:
    """Convert a KOL into a KOLResult, enriched with tier, score and reasons."""
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
    """Build an AlgorithmResult from an algorithm's output state."""
    selected_idx = [i for i, x in enumerate(state) if x == 1]
    selected = [
        to_kol_result(kols[i], scores[i], kols) for i in selected_idx
    ]
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
 
 
# ════════════════════════════════════════════════════════════════
#  Endpoints
# ════════════════════════════════════════════════════════════════
@app.get("/health")
def health():
    """Health check — call this first to confirm the backend is running."""
    return {"status": "ok"}
 
 
@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest):
    """Run all three algorithms and return the best KOL matrix."""
    # ── Input validation ──────────────────────────────────────────
    if req.budget <= 0:
        raise HTTPException(status_code=422, detail="budget must be a positive number")
    if req.country not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail="country must be one of: MY, ID, TH, PH")
    if req.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, tech, fashion")
 
    all_kols = load_kols()
    filtered = [k for k in all_kols
                if k.country == req.country and k.category == req.category]
 
    # ── Empty pool → return empty result (not an error) ──────────
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
 
    # Compute creator scores once for the whole filtered pool
    scores = compute_creator_score(filtered)
 
    # ── Run all three algorithms ──────────────────────────────────
    sa_state, _, sa_hist = simulated_annealing(filtered, req.budget, seed=req.seed)
    hc_state, _, hc_hist = hill_climber(filtered, req.budget, seed=req.seed)
    rs_state, _, rs_hist = random_search(filtered, req.budget, seed=req.seed)
 
    # Truncate all histories to the same length for the convergence chart
    min_len = min(len(sa_hist), len(hc_hist), len(rs_hist))
    sa_hist, hc_hist, rs_hist = sa_hist[:min_len], hc_hist[:min_len], rs_hist[:min_len]
 
    results = {
        "simulated_annealing": build_algorithm_result("Simulated Annealing", sa_state, sa_hist, filtered, scores),
        "hill_climber":        build_algorithm_result("Hill Climber",        hc_state, hc_hist, filtered, scores),
        "random_search":       build_algorithm_result("Random Search",       rs_state, rs_hist, filtered, scores),
    }
 
    best_key = max(results, key=lambda key: results[key].total_gmv)
    best = results[best_key]
 
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
        raise HTTPException(status_code=422, detail="country must be one of: MY, ID, TH, PH")
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, tech, fashion")
    if tier is not None and tier not in VALID_TIERS:
        raise HTTPException(status_code=422, detail="tier must be one of: Mega, Macro, Micro, Nano")
 
    all_kols = load_kols()
 
    filtered = [
        k for k in all_kols
        if (country is None or k.country == country)
        and (category is None or k.category == category)
        and (tier is None or get_tier(k) == tier)
    ]
 
    # Score the filtered pool, then paginate
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
 
    # Build a KOL object and compute its score relative to all KOLs
    all_kols = [_dict_to_kol(d) for d in raw_kols]
    target = _dict_to_kol(raw)
 
    # Find target's score within the full pool
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
    )
 
 
@app.get("/top-kols", response_model=TopKOLResponse)
def top_kols(
    country: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    """Return the top 10 KOLs ranked by creator score."""
    if country is not None and country not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail="country must be one of: MY, ID, TH, PH")
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail="category must be one of: beauty, tech, fashion")
 
    all_kols = load_kols()
    filtered = [
        k for k in all_kols
        if (country is None or k.country == country)
        and (category is None or k.category == category)
    ]
 
    if not filtered:
        return TopKOLResponse(country=country, category=category, top_kols=[])
 
    scores = compute_creator_score(filtered)
    # Pair each KOL with its score, sort by score descending, take top 10
    paired = sorted(zip(filtered, scores), key=lambda p: p[1], reverse=True)[:10]
    top = [to_kol_result(k, s, filtered) for k, s in paired]
 
    return TopKOLResponse(country=country, category=category, top_kols=top)
 
 
@app.post("/scalability", response_model=ScalabilityResponse)
def scalability(req: ScalabilityRequest):
    """
    Run all three algorithms on a freshly generated pool of size n
    and return execution time + final GMV for each.
    """
    if req.n < 10 or req.n > 500:
        raise HTTPException(status_code=422, detail="n must be between 10 and 500")
    if req.budget <= 0:
        raise HTTPException(status_code=422, detail="budget must be a positive number")
 
    # Generate a temporary pool of size n
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
    )
