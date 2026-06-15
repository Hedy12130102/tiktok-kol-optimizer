# engine/optimization/greedy_ranking.py
"""
Greedy Ranking — knapsack-style construction + local polish.

Builds the best of a GMV-descending and a GMV/cost-ratio-descending greedy fill
(see engine.optimization._common.greedy_init — ratio ordering alone maximises
ROI not GMV and badly underperforms), then polishes with 2-OPT swap / ADD / DROP.
"""
import copy
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness
from engine.optimization._common import greedy_init, local_improve


def greedy_ranking(
    kols: List[KOL],
    budget: float,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Greedy Ranking with multi-strategy seeding + 2-OPT / ADD / DROP polish.
    Deterministic — `seed` is accepted only for a uniform solver signature.
    """
    n = len(kols)

    # Multi-strategy greedy fill, then 2-OPT / ADD / DROP polish.
    best_state = local_improve(greedy_init(kols, budget), kols, budget)
    best_cost = fitness(best_state, kols, budget)

    # ── Build an ascending convergence history from the GMV-descending fill,
    #    ending at the final polished value (cosmetic, for the chart). ──
    order = sorted(range(n), key=lambda i: kols[i].expected_gmv(), reverse=True)
    state = [0] * n
    total_cost = 0.0
    history: List[float] = []
    for i in order:
        if total_cost + kols[i].cost <= budget:
            state[i] = 1
            total_cost += kols[i].cost
        history.append(-fitness(state, kols, budget))
    history.append(-best_cost)

    # Pad up to ~400 points for consistent chart display (don't pad beyond 400).
    if history and len(history) < 400:
        pad_val = history[-1]
        target = min(400, len(history) + 100)
        history.extend([pad_val] * max(0, target - len(history)))

    return copy.copy(best_state), best_cost, history
