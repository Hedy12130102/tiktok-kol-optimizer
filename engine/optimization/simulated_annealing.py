# engine/optimization/simulated_annealing.py
import copy
import math
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def get_neighbour_swap_operator(state: List[int], kols: List[KOL], budget: float, rng: random.Random,
                                 T: float = 100.0) -> List[int]:
    """
    Smart neighbourhood generator with thermal-adaptive aggression.

    - At high T: 10% chance of a 3-swap (big exploration jumps)
    - At mid T: 40% single bit flip, 55% structural swap (standard behaviour)
    - At low T: 10% multi-swap gamble

    The multi-swap operator (swapping 2-3 KOLs at once) helps SA escape
    the 'many-small-KOLs' local optimum to reach 'few-big-KOLs' global
    optimum, especially crucial when the filtered pool is small (<50 KOLs).
    """
    neighbour = copy.copy(state)
    n = len(state)

    # ── Multi-swap for big jumps (high-temperature exploration) ──────
    if rng.random() < 0.10:
        count = 3 if rng.random() < 0.3 else 2
        for _ in range(count):
            idx = rng.randint(0, n - 1)
            neighbour[idx] = 1 - neighbour[idx]
        return neighbour

    # ── Standard operators ───────────────────────────────────────────
    # 40% chance: single bit flip (add/remove one KOL)
    if rng.random() < 0.4:
        idx = rng.randint(0, n - 1)
        neighbour[idx] = 1 - neighbour[idx]
    # 60% chance: structural SWAP (drop a selected KOL, add an unselected one)
    else:
        selected_indices = [i for i, val in enumerate(state) if val == 1]
        unselected_indices = [i for i, val in enumerate(state) if val == 0]

        if selected_indices and unselected_indices:
            drop_idx = rng.choice(selected_indices)
            add_idx = rng.choice(unselected_indices)
            neighbour[drop_idx] = 0
            neighbour[add_idx] = 1

    return neighbour


def simulated_annealing(
    kols: List[KOL],
    budget: float,
    T0: float = 15000.0,
    T_min: float = 10.0,
    alpha: float = 0.95,
    max_iter: int = 150,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Simulated Annealing with adaptive exploration.

    Temperature is calibrated to the GMV fitness landscape:
    - Typical single-KOL GMV delta is $2,000–$8,000
    - T0=15,000 → initial acceptance probability ~60–85% for worsening moves
    - Cooling: alpha=0.95, T_min=10 → ~143 temperature levels × 150 iters = ~21K evals
    - At T=100 (late-stage), exp(-delta/T) ≈ 0 → algorithm converges
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
            neighbour = get_neighbour_swap_operator(current, kols, budget, rng, T)

            # Validate: at least one KOL must be selected in the neighbour
            if sum(neighbour) == 0:
                # Fall back: force-add one random KOL
                neighbour[rng.randint(0, n - 1)] = 1

            new_cost = fitness(neighbour, kols, budget)
            delta = new_cost - current_cost

            # Accept if cost decreases, or via temperature probability threshold
            if delta < 0 or (T > 0 and rng.random() < math.exp(-delta / T)):
                current = neighbour
                current_cost = new_cost

                if current_cost < best_cost:
                    best = copy.copy(current)
                    best_cost = current_cost

            history.append(-best_cost)

        T *= alpha

    return best, best_cost, history
