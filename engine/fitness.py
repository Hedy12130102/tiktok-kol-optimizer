from typing import Dict, List
import math
from .models import KOL

# Penalty weight for audience overlap — higher = stronger discouragement
# of near-duplicate creators in the same portfolio
_OVERLAP_PENALTY_WEIGHT = 5000  # dollars of effective GMV penalty per full-overlap pair


def fitness(state: List[int], kols: List[KOL], budget: float) -> float:
    """
    state: binary list, 1=selected, 0=not.
    Returns negative value (minimization): cost = -GMV + budget_penalty + overlap_penalty.
    """
    summary = summarize_state(state, kols)
    total_cost = summary["total_cost"]
    total_gmv = summary["total_gmv"]
    overlap_penalty = summary.get("overlap_penalty", 0)

    # Severe penalty for exceeding budget
    budget_violation = max(0, total_cost - budget) * 1e6

    return -total_gmv + budget_violation + overlap_penalty


def get_total_cost(state: List[int], kols: List[KOL]) -> float:
    return sum(kols[i].cost for i, x in enumerate(state) if x == 1)


def summarize_state(state: List[int], kols: List[KOL]) -> Dict[str, float]:
    selected = [kols[i] for i, x in enumerate(state) if x == 1]
    total_cost = sum(k.cost for k in selected)
    total_gmv = sum(k.expected_gmv() for k in selected)
    roi = total_gmv / total_cost if total_cost else 0.0

    # ── Audience overlap penalty ──────────────────────────────────
    # If two selected KOLs share country+category+similar follower
    # range, apply a penalty to discourage near-duplicates.
    overlap_penalty = _compute_overlap_penalty(selected)

    return {
        "selected_count": len(selected),
        "total_cost": total_cost,
        "total_gmv": total_gmv,
        "roi": roi,
        "overlap_penalty": overlap_penalty,
    }


def _compute_overlap_penalty(selected: List[KOL]) -> float:
    """
    Compute audience overlap penalty for a portfolio.

    Two KOLs are considered overlapping when they share:
    - same country + same category → 0.4
    - similar follower range (within 20%) → 0.3 each

    Full match (same country + same category + similar followers) = 1.0 score.
    The penalty discourages selecting near-duplicate creators.
    """
    n = len(selected)
    if n < 2:
        return 0.0

    total_overlap = 0.0

    for i in range(n):
        for j in range(i + 1, n):
            a, b = selected[i], selected[j]
            score = 0.0

            # Same country → +0.4
            if a.country == b.country:
                score += 0.4
            # Same category → +0.3
            if a.category == b.category:
                score += 0.3
            # Similar follower range (within 20%)
            if a.followers > 0 and b.followers > 0:
                ratio = min(a.followers, b.followers) / max(a.followers, b.followers)
                if ratio > 0.8:
                    score += 0.3

            total_overlap += score * _OVERLAP_PENALTY_WEIGHT

    return round(total_overlap, 2)
