from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import json
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.simulated_annealing import simulated_annealing
from engine.fitness import get_total_cost

app = FastAPI(title="KOL Optimizer API")

class OptimizeRequest(BaseModel):
    budget: float
    country: str = "MY"
    category: str = "beauty"

class KOLResult(BaseModel):
    name: str
    followers: int
    cost: float
    expected_gmv: float

class OptimizeResponse(BaseModel):
    selected_kols: List[KOLResult]
    total_cost: float
    total_gmv: float

@app.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest):
    data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_kols.json")
    with open(data_path) as f:
        all_kols = [KOL(**d) for d in json.load(f)]
    # Filter by country and category
    filtered = [k for k in all_kols
                if k.country == req.country and k.category == req.category]
    
    if not filtered:
        return OptimizeResponse(selected_kols=[], total_cost=0.0, total_gmv=0.0)
        
    best_state, _, _ = simulated_annealing(filtered, req.budget)
    selected = [filtered[i] for i, x in enumerate(best_state) if x == 1]
    return OptimizeResponse(
        selected_kols=[KOLResult(
            name=k.name, followers=k.followers,
            cost=k.cost, expected_gmv=k.expected_gmv()
        ) for k in selected],
        total_cost=sum(k.cost for k in selected),
        total_gmv=sum(k.expected_gmv() for k in selected),
    )
