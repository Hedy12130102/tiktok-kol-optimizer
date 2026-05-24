import copy, random
from typing import List, Tuple
from .models import KOL
from .fitness import fitness

def hill_climber(
    kols: List[KOL], budget: float, max_iter: int = 5000
) -> Tuple[List[int], float, List[float]]:
    n = len(kols)
    current = [random.randint(0, 1) for _ in range(n)]
    current_cost = fitness(current, kols, budget)
    history = []

    for _ in range(max_iter):
        idx = random.randint(0, n - 1)
        neighbour = copy.copy(current)
        neighbour[idx] = 1 - neighbour[idx]
        new_cost = fitness(neighbour, kols, budget)
        if new_cost < current_cost:        # 只接受更好的解
            current, current_cost = neighbour, new_cost
        history.append(-current_cost)

    return current, current_cost, history
