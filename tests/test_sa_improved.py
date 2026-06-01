"""
ALG-07: Unit tests for the improved Simulated Annealing algorithm
Tests include:
1. Valid output format
2. Budget compliance
3. Performance improvement over Hill-Climber
"""
import pytest
import json
from engine.models import KOL
from engine.optimization.sa_improved import simulated_annealing_improved
from engine.optimization.hill_climber import hill_climber
from engine.fitness import summarize_state

# Load and prepare test data
with open("data/sample_kols.json") as f:
    kols_data = json.load(f)
kols = [KOL(**item) for item in kols_data]
kols_my = [k for k in kols if k.country == "MY" and k.category == "beauty"]
BUDGET_LIMIT = 5000


def test_sai_state_format():
    """Test that simulated_annealing_improved returns a valid binary state."""
    state, _, _ = simulated_annealing_improved(
        kols_my, budget=BUDGET_LIMIT, seed=42
    )
    # State length must match number of KOLs
    assert len(state) == len(kols_my)
    # State must only contain 0 or 1 (unselected/selected)
    assert all(selected in (0, 1) for selected in state)


def test_sai_budget_compliance():
    """Test that the solution does not exceed the budget limit."""
    state, _, _ = simulated_annealing_improved(
        kols_my, budget=BUDGET_LIMIT, seed=42
    )
    total_cost = sum(
        kols_my[i].cost for i, selected in enumerate(state) if selected
    )
    assert total_cost <= BUDGET_LIMIT, f"Cost {total_cost} exceeds budget {BUDGET_LIMIT}"


def test_sai_outperforms_hill_climber():
    """Test that SAI's average GMV is at least as good as Hill-Climber over multiple seeds."""
    seeds = [42, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    sai_gmvs = []
    hc_gmvs = []

    for seed in seeds:
        sai_state, _, _ = simulated_annealing_improved(
            kols_my, budget=BUDGET_LIMIT, seed=seed
        )
        hc_state, _, _ = hill_climber(
            kols_my, budget=BUDGET_LIMIT, seed=seed
        )
        sai_gmvs.append(summarize_state(sai_state, kols_my)["total_gmv"])
        hc_gmvs.append(summarize_state(hc_state, kols_my)["total_gmv"])

    avg_sai = sum(sai_gmvs) / len(sai_gmvs)
    avg_hc = sum(hc_gmvs) / len(hc_gmvs)

    assert avg_sai >= avg_hc, (
        f"SAI average GMV ({avg_sai:.2f}) is worse than Hill-Climber ({avg_hc:.2f})"
    )
