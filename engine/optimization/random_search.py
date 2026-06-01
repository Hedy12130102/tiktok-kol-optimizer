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

    Each iteration samples a completely random binary state.
    Included to demonstrate that unstructured random sampling is
    significantly worse than local search on this problem.

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
    best = [0] * n
    best_cost = fitness(best, kols, budget)
    history: List[float] = []

    for _ in range(max_iter):
        current = [rng.randint(0, 1) for _ in range(n)]
        current_cost = fitness(current, kols, budget)
        if current_cost < best_cost:
            best = copy.copy(current)
            best_cost = current_cost
        history.append(-best_cost)

    return best, best_cost, history