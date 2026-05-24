import math, random, copy
from typing import List, Optional, Tuple
from .models import KOL
from .fitness import fitness

def get_neighbour(state: List[int], rng: random.Random) -> List[int]:
    """Generate neighborhood by single point flip"""
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
    Returns: (best state, best fitness, history of best fitness per step)
    """
    rng = random.Random(seed)
    n = len(kols)
    current = [0] * n
    current_cost = fitness(current, kols, budget)
    best = copy.copy(current)
    best_cost = current_cost
    history = []  # Used to plot convergence curve

    T = T0
    while T > T_min:
        for _ in range(max_iter):
            neighbour = get_neighbour(current, rng)
            delta = fitness(neighbour, kols, budget) - current_cost
            if delta < 0 or rng.random() < math.exp(-delta / T):
                current = neighbour
                current_cost = fitness(neighbour, kols, budget)
            if current_cost < best_cost:
                best = copy.copy(current)
                best_cost = current_cost
            history.append(-best_cost)  # Record GMV (positive)
        T *= alpha

    return best, best_cost, history
