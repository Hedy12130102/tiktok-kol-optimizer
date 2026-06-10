# engine/optimization/tabu_search.py
"""
Tabu Search for KOL portfolio optimization.

Why Tabu Search works well here:
  The KOL selection problem has many shallow local optima — sets of KOLs
  with very similar quality that differ by only one or two members.
  Hill Climber gets trapped immediately. SA escapes via random acceptance.
  Tabu Search escapes *systematically* by maintaining a short-term memory
  (tabu list) of recently flipped indices, forbidding re-visiting them
  for `tabu_tenure` iterations.

  Aspiration criterion: if a tabu move produces a new global best, it is
  accepted regardless — the memory overrides are rare but crucial.

  Starting from a greedy solution (near-optimal initialisation) means
  Tabu Search begins close to the optimum and refines from there, making
  it fast and reliable on small-to-medium pools (10–100 KOLs).

Algorithm:
  1. Greedy initialisation (sort by GMV/cost, fill to budget)
  2. At each iteration: evaluate ALL n single-flip neighbours
  3. Choose best non-tabu neighbour (or any if aspiration criterion met)
  4. Add the flipped index to tabu list for `tabu_tenure` steps
  5. Repeat until max_iter

Complexity per iteration: O(n × fitness) where fitness is O(n²) for
overlap penalty — fast for typical filtered pools of 10–30 KOLs.
"""
import copy
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def _greedy_init(kols: List[KOL], budget: float) -> List[int]:
    """Sort by GMV/cost ratio and greedily fill to budget."""
    n = len(kols)
    order = sorted(
        range(n),
        key=lambda i: kols[i].expected_gmv() / kols[i].cost if kols[i].cost > 0 else 0,
        reverse=True,
    )
    state = [0] * n
    total_cost = 0.0
    for i in order:
        if total_cost + kols[i].cost <= budget:
            state[i] = 1
            total_cost += kols[i].cost
    return state


def tabu_search(
    kols: List[KOL],
    budget: float,
    max_iter: int = 2000,
    tabu_tenure: int = 8,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Tabu Search with greedy initialisation and aspiration criterion.

    Args:
        kols:         List of KOL candidates.
        budget:       Maximum total hiring cost (USD).
        max_iter:     Total number of improvement iterations.
        tabu_tenure:  How many iterations a flipped index stays forbidden.
        seed:         Random seed (used only for tie-breaking via jitter).

    Returns:
        (best_state, best_cost, history)
    """
    rng = random.Random(seed)
    n = len(kols)

    # Strong starting point from greedy init
    current = _greedy_init(kols, budget)
    current_cost = fitness(current, kols, budget)
    best = copy.copy(current)
    best_cost = current_cost

    # tabu[i] = iteration number after which index i is no longer tabu
    tabu: dict = {}
    history: List[float] = []

    for iter_num in range(max_iter):
        best_nb: Optional[List[int]] = None
        best_nb_cost = float("inf")
        best_nb_idx = -1

        # ── Evaluate all n single-flip neighbours ───────────────────
        for i in range(n):
            nb = copy.copy(current)
            nb[i] ^= 1
            nb_cost = fitness(nb, kols, budget)

            # Skip if tabu, unless aspiration criterion met (beats global best)
            is_tabu = tabu.get(i, 0) > iter_num
            if is_tabu and nb_cost >= best_cost:
                continue

            # Tie-break with tiny random jitter to avoid cycling in flat regions
            if nb_cost < best_nb_cost or (
                nb_cost == best_nb_cost and rng.random() < 0.3
            ):
                best_nb_cost = nb_cost
                best_nb = nb
                best_nb_idx = i

        if best_nb is None:
            # All moves are tabu — expire oldest entry to unblock
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

        history.append(-best_cost)

    return best, best_cost, history
