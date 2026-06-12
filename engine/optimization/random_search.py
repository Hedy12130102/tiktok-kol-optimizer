# engine/optimization/random_search.py
import copy
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def random_search(
    kols: List[KOL],
    budget: float,
    max_iter: int = 5000,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Random Search baseline.

    Each iteration samples a random binary state that is bounded
    closer to the realistic budget selection constraints.

    Args:
        kols:      List of KOL candidates.
        budget:    Maximum total hiring cost (USD).
        max_iter:  Number of random states to evaluate.
        seed:      Random seed for reproducibility.

    Returns:
        (best_state, best_cost, history)
    """
    rng = random.Random(seed)
    n = len(kols)
    
    # Start with the empty baseline selection
    best = [0] * n
    best_cost = fitness(best, kols, budget)
    history: List[float] = []

    # Calculate an approximate safe selection ratio so random sampling 
    # doesn't instantly blow the budget on large pools (e.g., N=500)
    avg_cost = sum(k.cost for k in kols) / n if n > 0 else 1.0
    safe_sample_count = max(1, min(n, int(budget / avg_cost))) if avg_cost > 0 else 1
    prob_of_inclusion = safe_sample_count / n

    for _ in range(max_iter):
        # Sample a smart random state based on realistic inclusion probability
        current = [1 if rng.random() < prob_of_inclusion else 0 for _ in range(n)]
        current_cost = fitness(current, kols, budget)
        
        # In a minimization context, lower (more negative) is better
        if current_cost < best_cost:
            best = copy.copy(current)
            best_cost = current_cost
            
        history.append(-best_cost)

    return best, best_cost, history