from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import json
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.simulated_annealing import simulated_annealing
from engine.hill_climber import hill_climber
from engine.random_search import random_search
from engine.fitness import summarize_state

app = FastAPI(
    title="TikTok Shop KOL Matrix Optimizer API",
    description="Local search optimizer for selecting a KOL portfolio under a marketing budget.",
)

class OptimizeRequest(BaseModel):
    budget: float
    country: str = "MY"
    category: str = "beauty"
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

def load_kols() -> List[KOL]:
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "sample_kols.json",
    )
    with open(data_path, encoding="utf-8") as f:
        return [KOL(**d) for d in json.load(f)]

def to_kol_result(k: KOL) -> KOLResult:
    return KOLResult(
        id=k.id,
        name=k.name,
        country=k.country,
        category=k.category,
        followers=k.followers,
        engagement_rate=k.engagement_rate,
        fit_score=k.fit_score,
        cost=k.cost,
        expected_gmv=k.expected_gmv(),
    )

def build_algorithm_result(name: str, state: List[int], history: List[float], kols: List[KOL]) -> AlgorithmResult:
    selected = [kols[i] for i, x in enumerate(state) if x == 1]
    summary = summarize_state(state, kols)
    return AlgorithmResult(
        algorithm=name,
        selected_kols=[to_kol_result(k) for k in selected],
        selected_count=int(summary["selected_count"]),
        total_cost=summary["total_cost"],
        total_gmv=summary["total_gmv"],
        roi=summary["roi"],
        history=history,
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest):
    all_kols = load_kols()
    # Filter by country and category
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

    sa_state, _, sa_hist = simulated_annealing(filtered, req.budget, seed=req.seed)
    hc_state, _, hc_hist = hill_climber(filtered, req.budget, seed=req.seed)
    rs_state, _, rs_hist = random_search(filtered, req.budget, seed=req.seed)

    results = {
        "simulated_annealing": build_algorithm_result("Simulated Annealing", sa_state, sa_hist, filtered),
        "hill_climber": build_algorithm_result("Hill Climber", hc_state, hc_hist, filtered),
        "random_search": build_algorithm_result("Random Search", rs_state, rs_hist, filtered),
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
