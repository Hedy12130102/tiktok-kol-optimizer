# engine/optimization/simulated_annealing.py
import copy
import math
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def get_neighbour_swap_operator(state: List[int], rng: random.Random) -> List[int]:
    """
    Smart neighborhood generator.
    Allows a standard 1-bit flip OR a 2-bit swap to prevent budget paralysis
    by replacing an expensive KOL with cheaper options seamlessly.
    """
    neighbour = copy.copy(state)
    n = len(state)
    
    # 40% chance: standard single bit flip (add/remove one KOL)
    if rng.random() < 0.4:
        idx = rng.randint(0, n - 1)
        neighbour[idx] = 1 - neighbour[idx]
    # 60% chance: Perform a structural SWAP (drop a selected KOL, add an unselected one)
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
    T0: float = 100.0,       # Initial temperature optimized for cost bounds
    T_min: float = 0.01,
    alpha: float = 0.98,     # Slower cooling to thoroughly search swap spaces
    max_iter: int = 150,     # Stable iteration limit
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Simulated Annealing utilizing a swap operator to bypass local optimum traps.
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
            neighbour = get_neighbour_swap_operator(current, rng)
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