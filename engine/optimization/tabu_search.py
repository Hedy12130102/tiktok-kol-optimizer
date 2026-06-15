# engine/optimization/tabu_search.py
"""
Tabu Search for KOL portfolio optimization.

Algorithm:
  1. Greedy initialisation (sort by GMV/cost, fill to budget)
  2. At each iteration: evaluate ALL n single-flip neighbours
  3. Choose best non-tabu neighbour (or any if aspiration criterion met)
  4. Add the flipped index to tabu list for `tabu_tenure` steps
  5. Stop at max_iter, or early once the global best stops improving.
"""
import copy
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness
from engine.optimization._common import greedy_init


def tabu_search(
    kols: List[KOL],
    budget: float,
    max_iter: int = 2000,
    tabu_tenure: int = 8,
    seed: Optional[int] = None,
    patience: int = 150,
) -> Tuple[List[int], float, List[float]]:
    """Tabu Search with greedy initialisation, aspiration criterion and
    no-improvement early stopping."""
    rng = random.Random(seed)
    n = len(kols)

    current = greedy_init(kols, budget)
    current_cost = fitness(current, kols, budget)
    best = copy.copy(current)
    best_cost = current_cost

    tabu: dict = {}
    history: List[float] = []
    no_improve = 0

    for iter_num in range(max_iter):
        best_nb: Optional[List[int]] = None
        best_nb_cost = float("inf")
        best_nb_idx = -1

        for i in range(n):
            nb = copy.copy(current)
            nb[i] ^= 1
            nb_cost = fitness(nb, kols, budget)

            is_tabu = tabu.get(i, 0) > iter_num
            if is_tabu and nb_cost >= best_cost:
                continue

            if nb_cost < best_nb_cost or (
                nb_cost == best_nb_cost and rng.random() < 0.3
            ):
                best_nb_cost = nb_cost
                best_nb = nb
                best_nb_idx = i

        if best_nb is None:
            if tabu:
                oldest = min(tabu, key=lambda k: tabu[k])
                del tabu[oldest]
            history.append(-best_cost)
            continue

        current = best_nb
        current_cost = best_nb_cost
        tabu[best_nb_idx] = iter_num + tabu_tenure

        if current_cost < best_cost:
            best = copy.copy(current)
            best_cost = current_cost
            no_improve = 0
        else:
            no_improve += 1

        history.append(-best_cost)

        if no_improve >= patience:
            break

    return best, best_cost, history
