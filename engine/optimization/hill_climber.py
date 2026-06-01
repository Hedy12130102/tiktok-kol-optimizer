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

    Only accepts a neighbour if it strictly improves the cost function.
    Fast to converge but prone to getting trapped in local optima —
    e.g. after selecting expensive macro KOLs the budget is exhausted
    and no single-bit flip can improve the solution further.

    Args:
        kols:      List of KOL candidates.
        budget:    Maximum total hiring cost (USD).
        max_iter:  Number of neighbour evaluations.
        seed:      Random seed for reproducibility.

    Returns:
        (best_state, best_cost, history)
        best_state  — binary list, 1 = KOL selected.
        best_cost   — final cost function value (negative GMV).
        history     — best GMV at each iteration step (for convergence plot).
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

        if new_cost < current_cost:          # accept only improvements
            current, current_cost = neighbour, new_cost

        history.append(-current_cost)        # record GMV (positive)

    return current, current_cost, history