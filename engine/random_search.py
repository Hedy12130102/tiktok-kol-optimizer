import copy, random
from typing import List, Tuple
from .models import KOL
from .fitness import fitness

def random_search(
    kols: List[KOL], budget: float, max_iter: int = 5000
) -> Tuple[List[int], float, List[float]]:
    n = len(kols)
    best = [random.randint(0, 1) for _ in range(n)]
    best_cost = fitness(best, kols, budget)
    history = []

    for _ in range(max_iter):
        current = [random.randint(0, 1) for _ in range(n)]
        current_cost = fitness(current, kols, budget)
        if current_cost < best_cost:
            best = copy.copy(current)
            best_cost = current_cost
        history.append(-best_cost)

    return best, best_cost, history
