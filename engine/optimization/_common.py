"""
Shared building blocks for the KOL portfolio optimizers.

The portfolio problem is a 0-1 knapsack: maximise total GMV (net of the
audience-overlap penalty) subject to a budget cap. Two pieces are reused by
the constructive / memory-based solvers (Greedy Ranking, GA, Tabu Search):

  - greedy_init  : a strong starting portfolio. CRUCIAL detail — it does NOT
                   order by GMV/cost ratio alone. Ratio-greedy maximises ROI,
                   not GMV, so on skewed real pools it piles up many cheap,
                   mutually-overlapping creators and underperforms badly (it can
                   score below even a random baseline). We therefore build BOTH
                   a GMV-descending and a ratio-descending fill and keep whichever
                   scores better — the classic knapsack guard of taking
                   max(by-value, by-ratio).
  - local_improve: hill-climbing polish (2-OPT swap + budget-fill ADD + DROP)
                   that turns any portfolio into a local optimum. Used by Greedy
                   Ranking as its 2-opt phase.

Note: the trajectory controls (Simulated Annealing, Hill Climber) deliberately
do NOT use these — they start from an empty portfolio so the benchmark can
measure the value of a warm greedy start against a cold one.
"""
from typing import List

from engine.models import KOL
from engine.fitness import fitness


def _greedy_fill(kols: List[KOL], budget: float, order: List[int]) -> List[int]:
    """Add KOLs in the given priority order, skipping any that would bust budget."""
    state = [0] * len(kols)
    total_cost = 0.0
    for i in order:
        if total_cost + kols[i].cost <= budget:
            state[i] = 1
            total_cost += kols[i].cost
    return state


def greedy_init(kols: List[KOL], budget: float) -> List[int]:
    """
    Strong starting portfolio: the better (by fitness) of a GMV-descending and a
    GMV/cost-ratio-descending greedy fill. Returns the binary selection state.

    Trying both orderings is what fixes the ratio-greedy trap — on pools where
    a few big-GMV creators dominate, the ratio ordering wastes the budget on many
    small overlapping creators while the GMV ordering captures the big winners.
    """
    n = len(kols)
    if n == 0:
        return []

    by_gmv = sorted(range(n), key=lambda i: kols[i].expected_gmv(), reverse=True)
    by_ratio = sorted(
        range(n),
        key=lambda i: kols[i].expected_gmv() / kols[i].cost if kols[i].cost > 0 else 0,
        reverse=True,
    )

    candidates = [
        _greedy_fill(kols, budget, by_gmv),
        _greedy_fill(kols, budget, by_ratio),
    ]
    # Lower fitness = better (minimisation).
    return min(candidates, key=lambda s: fitness(s, kols, budget))


def local_improve(state: List[int], kols: List[KOL], budget: float,
                  max_swap_passes: int = 20) -> List[int]:
    """
    Hill-climb a portfolio to a local optimum under the fitness objective,
    always staying within budget. Three move types, applied first-improvement:

      1. 2-OPT swap — drop one selected KOL, add one unselected KOL.
      2. ADD        — spend leftover budget on any KOL that improves fitness.
      3. DROP       — remove any KOL whose absence improves fitness (e.g. one
                      that adds more overlap penalty than its GMV is worth).
    """
    current = list(state)
    current_cost = fitness(current, kols, budget)
    total_cost = sum(kols[i].cost for i, x in enumerate(current) if x == 1)

    # ── 1. 2-OPT swap ────────────────────────────────────────────────
    for _ in range(max_swap_passes):
        improved = False
        selected = [i for i, x in enumerate(current) if x == 1]
        unselected = [i for i, x in enumerate(current) if x == 0]
        for drop in selected:
            for add in unselected:
                new_total = total_cost - kols[drop].cost + kols[add].cost
                if new_total > budget:
                    continue
                nb = list(current)
                nb[drop] = 0
                nb[add] = 1
                nb_cost = fitness(nb, kols, budget)
                if nb_cost < current_cost:
                    current, current_cost, total_cost = nb, nb_cost, new_total
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break

    # ── 2. ADD (fill remaining budget) ───────────────────────────────
    improved = True
    while improved:
        improved = False
        for add in [i for i, x in enumerate(current) if x == 0]:
            if total_cost + kols[add].cost > budget:
                continue
            nb = list(current)
            nb[add] = 1
            nb_cost = fitness(nb, kols, budget)
            if nb_cost < current_cost:
                current, current_cost = nb, nb_cost
                total_cost += kols[add].cost
                improved = True
                break

    # ── 3. DROP ──────────────────────────────────────────────────────
    improved = True
    while improved:
        improved = False
        for drop in [i for i, x in enumerate(current) if x == 1]:
            nb = list(current)
            nb[drop] = 0
            nb_cost = fitness(nb, kols, budget)
            if nb_cost < current_cost:
                current, current_cost = nb, nb_cost
                total_cost -= kols[drop].cost
                improved = True
                break

    return current
