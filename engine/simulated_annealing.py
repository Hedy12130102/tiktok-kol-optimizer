import math, random, copy
from typing import List, Tuple
from .models import KOL
from .fitness import fitness

def get_neighbour(state: List[int]) -> List[int]:
    """Generate neighborhood by single point flip"""
    neighbour = copy.copy(state)
    idx = random.randint(0, len(state) - 1)
    neighbour[idx] = 1 - neighbour[idx]
    return neighbour

def simulated_annealing(
    kols: List[KOL],
    budget: float,
    T0: float = 1000.0,
    T_min: float = 1.0,
    alpha: float = 0.95,
    max_iter: int = 500,
) -> Tuple[List[int], float, List[float]]:
    """
    Returns: (best state, best fitness, history of best fitness per step)
    """
    n = len(kols)
    current = [random.randint(0, 1) for _ in range(n)]
    current_cost = fitness(current, kols, budget)
    best = copy.copy(current)
    best_cost = current_cost
    history = []  # Used to plot convergence curve

    T = T0
    while T > T_min:
        for _ in range(max_iter):
            neighbour = get_neighbour(current)
            delta = fitness(neighbour, kols, budget) - current_cost
            if delta < 0 or random.random() < math.exp(-delta / T):
                current = neighbour
                current_cost = fitness(neighbour, kols, budget)
            if current_cost < best_cost:
                best = copy.copy(current)
                best_cost = current_cost
            history.append(-best_cost)  # Record GMV (positive)
        T *= alpha

    return best, best_cost, history
