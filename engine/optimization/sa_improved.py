# engine/optimization/sa_improved.py
"""
Improved Simulated Annealing with Swap neighbourhood.

Difference from the standard version (simulated_annealing.py):
  - Adds a SWAP move: pick one selected KOL and one unselected KOL,
    swap their states.  This keeps the portfolio size roughly constant
    while exploring budget-equivalent alternatives.
  - Each iteration randomly chooses between BIT-FLIP and SWAP (50/50),
    giving the search both size-changing and size-preserving moves.

This variant is used to demonstrate algorithm improvement (CLO3).
Compare its convergence curve against the standard SA to show that
the hybrid neighbourhood finds higher GMV on the same budget.
"""
import copy
import math
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def _bitflip(state: List[int], rng: random.Random) -> List[int]:
    """Flip one random bit."""
    nb = copy.copy(state)
    nb[rng.randint(0, len(state) - 1)] ^= 1
    return nb


def _swap(state: List[int], rng: random.Random) -> List[int]:
    """
    Swap one selected KOL with one unselected KOL.
    Falls back to bit-flip if all KOLs are selected or none are selected.
    """
    selected   = [i for i, x in enumerate(state) if x == 1]
    unselected = [i for i, x in enumerate(state) if x == 0]

    if not selected or not unselected:
        return _bitflip(state, rng)

    nb = copy.copy(state)
    nb[rng.choice(selected)]   = 0
    nb[rng.choice(unselected)] = 1
    return nb


def simulated_annealing_improved(
    kols: List[KOL],
    budget: float,
    T0: float = 50000.0,
    T_min: float = 1.0,
    alpha: float = 0.95,
    max_iter: int = 500,
    swap_prob: float = 0.5,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Improved SA with hybrid bit-flip / swap neighbourhood.

    Args:
        kols:       List of KOL candidates.
        budget:     Maximum total hiring cost (USD).
        T0:         Initial temperature.
        T_min:      Stopping temperature.
        alpha:      Cooling rate.
        max_iter:   Neighbour evaluations per temperature level.
        swap_prob:  Probability of using SWAP instead of BIT-FLIP (0–1).
        seed:       Random seed for reproducibility.

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
            # Choose neighbourhood strategy
            if rng.random() < swap_prob:
                neighbour = _swap(current, rng)
            else:
                neighbour = _bitflip(current, rng)

            delta = fitness(neighbour, kols, budget) - current_cost

            if delta < 0 or rng.random() < math.exp(-delta / T):
                current = neighbour
                current_cost = fitness(neighbour, kols, budget)

            if current_cost < best_cost:
                best = copy.copy(current)
                best_cost = current_cost

            history.append(-best_cost)

        T *= alpha

    return best, best_cost, history