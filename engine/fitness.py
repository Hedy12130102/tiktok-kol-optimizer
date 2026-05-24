from typing import List
from .models import KOL

def fitness(state: List[int], kols: List[KOL], budget: float) -> float:
    """
    state: binary list, 1=selected, 0=not
    Returns negative value (minimization problem): cost = -GMV + penalty
    """
    selected = [kols[i] for i, x in enumerate(state) if x == 1]
    total_cost = sum(k.cost for k in selected)
    total_gmv  = sum(k.expected_gmv() for k in selected)

    penalty = max(0, total_cost - budget) * 1e6  # Penalty for over budget
    return -total_gmv + penalty

def get_total_cost(state: List[int], kols: List[KOL]) -> float:
    return sum(kols[i].cost for i, x in enumerate(state) if x == 1)
