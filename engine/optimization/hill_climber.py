# engine/optimization/hill_climber.py
import copy
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def hill_climber(
    kols: List[KOL],
    budget: float,
    max_iter: int = 5000,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Hill Climber (greedy local search).

    Only accepts a neighbour if it strictly improves the cost function (minimization).
    """
    rng = random.Random(seed)
    n = len(kols)
    current = [0] * n
    current_cost = fitness(current, kols, budget)
    history: List[float] = []

    for _ in range(max_iter):
        idx = rng.randint(0, n - 1)
        neighbour = copy.copy(current)
        neighbour[idx] = 1 - neighbour[idx]
        new_cost = fitness(neighbour, kols, budget)

        # Minimization check: lower cost is better
        if new_cost < current_cost:
            current, current_cost = neighbour, new_cost

        history.append(-current_cost)

    return current, current_cost, history