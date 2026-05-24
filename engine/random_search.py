import copy, random
from typing import List, Optional, Tuple
from .models import KOL
from .fitness import fitness

def random_search(
    kols: List[KOL],
    budget: float,
    max_iter: int = 5000,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    rng = random.Random(seed)
    n = len(kols)
    best = [0] * n
    best_cost = fitness(best, kols, budget)
    history = []

    for _ in range(max_iter):
        current = [rng.randint(0, 1) for _ in range(n)]
        current_cost = fitness(current, kols, budget)
        if current_cost < best_cost:
            best = copy.copy(current)
            best_cost = current_cost
        history.append(-best_cost)

    return best, best_cost, history
