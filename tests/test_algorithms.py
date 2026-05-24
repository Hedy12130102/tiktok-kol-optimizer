import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.hill_climber import hill_climber
from engine.simulated_annealing import simulated_annealing
from engine.random_search import random_search

def test_algorithms():
    kols = [
        KOL(i, f"KOL_{i}", "MY", "beauty", 10000 * i, 0.1, 0.8, 500 * i)
        for i in range(1, 10)
    ]
    budget = 2000
    
    best_hc, cost_hc, _ = hill_climber(kols, budget, max_iter=100)
    assert len(best_hc) == len(kols)
    
    best_sa, cost_sa, _ = simulated_annealing(kols, budget, max_iter=10)
    assert len(best_sa) == len(kols)
    
    best_rs, cost_rs, _ = random_search(kols, budget, max_iter=100)
    assert len(best_rs) == len(kols)
