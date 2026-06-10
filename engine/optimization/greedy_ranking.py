# engine/optimization/greedy_ranking.py
"""
Greedy Ranking Algorithm — LP relaxation approximation for KOL selection.

Phase 1: Sort by GMV/cost ratio, add greedily until budget exhausted.
Phase 2: 2-OPT swap — replace selected KOL with unselected if fitness improves.
Phase 3: Drop improvement — remove any KOL whose absence improves fitness
         (handles the case where all KOLs fit within budget but some cause
         excessive audience overlap penalty).
"""
import copy
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def greedy_ranking(
    kols: List[KOL],
    budget: float,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Greedy Ranking with 2-OPT swap + drop improvement.
    """
    n = len(kols)
    history: List[float] = []

    # ── Phase 1: Greedy build ────────────────────────────────────────
    order = sorted(
        range(n),
        key=lambda i: kols[i].expected_gmv() / kols[i].cost if kols[i].cost > 0 else 0,
        reverse=True,
    )
    current = [0] * n
    total_cost = 0.0

    for i in order:
        if total_cost + kols[i].cost <= budget:
            current[i] = 1
            total_cost += kols[i].cost
        history.append(-fitness(current, kols, budget))

    current_cost = fitness(current, kols, budget)

    # ── Phase 2: 2-OPT swap improvement ─────────────────────────────
    improved = True
    for _ in range(20):
        if not improved:
            break
        improved = False

        selected = [i for i, x in enumerate(current) if x == 1]
        unselected = [i for i, x in enumerate(current) if x == 0]

        for drop in selected:
            for add in unselected:
                new_total = total_cost - kols[drop].cost + kols[add].cost
                if new_total > budget:
                    continue
                nb = copy.copy(current)
                nb[drop] = 0
                nb[add] = 1
                nb_cost = fitness(nb, kols, budget)
                if nb_cost < current_cost:
                    current = nb
                    current_cost = nb_cost
                    total_cost = new_total
                    improved = True
                    history.append(-current_cost)
                    break
            if improved:
                break

    # ── Phase 3: Drop improvement ─────────────────────────────────
    # When all KOLs fit within budget, Phase 2 has no unselected KOLs
    # to swap in. This phase drops any KOL whose removal reduces the
    # audience overlap penalty more than it costs in GMV.
    drop_improved = True
    while drop_improved:
        drop_improved = False
        selected = [i for i, x in enumerate(current) if x == 1]
        for drop in selected:
            nb = copy.copy(current)
            nb[drop] = 0
            nb_cost = fitness(nb, kols, budget)
            if nb_cost < current_cost:
                current = nb
                current_cost = nb_cost
                total_cost -= kols[drop].cost
                drop_improved = True
                history.append(-current_cost)
                break

    # ── Pad history to ~400 points for consistent chart display ─────
    if history:
        pad_val = history[-1]
        target = max(400, len(history))
        history.extend([pad_val] * (target - len(history)))

    return copy.copy(current), current_cost, history
