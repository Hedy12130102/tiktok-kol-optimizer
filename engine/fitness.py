from typing import Dict, List
from .models import KOL

def fitness(state: List[int], kols: List[KOL], budget: float) -> float:
    """
    state: binary list, 1=selected, 0=not
    Returns negative value (minimization problem): cost = -GMV + penalty
    """
    summary = summarize_state(state, kols)
    total_cost = summary["total_cost"]
    total_gmv = summary["total_gmv"]

    penalty = max(0, total_cost - budget) * 1e6  # Penalty for over budget
    return -total_gmv + penalty

def get_total_cost(state: List[int], kols: List[KOL]) -> float:
    return sum(kols[i].cost for i, x in enumerate(state) if x == 1)

def summarize_state(state: List[int], kols: List[KOL]) -> Dict[str, float]:
    selected = [kols[i] for i, x in enumerate(state) if x == 1]
    total_cost = sum(k.cost for k in selected)
    total_gmv = sum(k.expected_gmv() for k in selected)
    roi = total_gmv / total_cost if total_cost else 0.0
    return {
        "selected_count": len(selected),
        "total_cost": total_cost,
        "total_gmv": total_gmv,
        "roi": roi,
    }
