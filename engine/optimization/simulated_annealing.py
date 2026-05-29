# engine/optimization/simulated_annealing.py
import copy
import math
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def get_neighbour_bitflip(state: List[int], rng: random.Random) -> List[int]:
    """Flip one random bit (add or remove one KOL)."""
    neighbour = copy.copy(state)
    idx = rng.randint(0, len(state) - 1)
    neighbour[idx] = 1 - neighbour[idx]
    return neighbour


def simulated_annealing(
    kols: List[KOL],
    budget: float,
    T0: float = 50000.0,
    T_min: float = 1.0,
    alpha: float = 0.95,
    max_iter: int = 500,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Simulated Annealing with bit-flip neighbourhood.

    Accepts worse neighbours with probability exp(-delta / T), which
    allows the search to escape local optima that trap Hill Climber.
    Temperature decreases geometrically: T = T * alpha each round.

    Args:
        kols:      List of KOL candidates.
        budget:    Maximum total hiring cost (USD).
        T0:        Initial temperature (controls early exploration).
        T_min:     Stopping temperature.
        alpha:     Cooling rate (0 < alpha < 1, typically 0.90–0.99).
        max_iter:  Neighbour evaluations per temperature level.
        seed:      Random seed for reproducibility.

    Returns:
        (best_state, best_cost, history)
    """
    rng = random.Random(seed)
    n = len(kols)
    current = [0] * n
    current_cost = fitness(current, kols, budget)
    best = copy.copy(current)
    best_cost = current_cost
    history: List[float] = []

    T = T0
    while T > T_min:
        for _ in range(max_iter):
            neighbour = get_neighbour_bitflip(current, rng)
            delta = fitness(neighbour, kols, budget) - current_cost

            # Accept if better, or with Metropolis probability if worse
            if delta < 0 or rng.random() < math.exp(-delta / T):
                current = neighbour
                current_cost = fitness(neighbour, kols, budget)

            if current_cost < best_cost:
                best = copy.copy(current)
                best_cost = current_cost

            history.append(-best_cost)       # record best GMV seen so far

        T *= alpha

    return best, best_cost, history
