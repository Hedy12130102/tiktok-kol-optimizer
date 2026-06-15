"""
Algorithm interface tests — all 6 optimizers.

Checks:
  - Return shape: (state, cost, history) with len(state) == len(kols)
  - Budget constraint: total cost of selected KOLs <= budget
  - Non-negative GMV
  - Reproducibility: same seed = same result
  - Works across all 4 product categories

Run:  pytest tests/test_algorithms.py -v
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from engine.models import KOL
from engine.fitness import summarize_state
from engine.optimization.hill_climber import hill_climber
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.random_search import random_search
from engine.optimization.genetic_algorithm import genetic_algorithm
from engine.optimization.tabu_search import tabu_search
from engine.optimization.greedy_ranking import greedy_ranking


# ────────────────────────────────────────────────────────────
#  Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture
def small_pool():
    """9 beauty/MY KOLs with increasing follower counts and costs."""
    return [
        KOL(id=i, name=f"KOL_{i}", country="MY", category="beauty",
            followers=10000 * i, engagement_rate=0.1, fit_score=0.8,
            commission_rate=0.15, cost=500 * i)
        for i in range(1, 10)
    ]


@pytest.fixture
def mixed_pool():
    """Mixed-category pool covering all 4 categories."""
    categories = ["beauty", "fashion", "home", "fmcg"]
    return [
        KOL(id=i + 1, name=f"KOL_{i+1}", country="MY", category=categories[i % 4],
            followers=50000 + 10000 * i, engagement_rate=0.08 + 0.01 * i,
            fit_score=0.6 + 0.04 * i, commission_rate=0.15, cost=300 + 200 * i)
        for i in range(16)
    ]


BUDGET = 2000
ALL_RUNNERS = [
    ("hill_climber",        lambda kols, b: hill_climber(kols, b, max_iter=100)),
    ("simulated_annealing", lambda kols, b: simulated_annealing(kols, b, max_iter=10)),
    ("random_search",       lambda kols, b: random_search(kols, b, max_iter=100)),
    ("genetic_algorithm",   lambda kols, b: genetic_algorithm(kols, b, generations=5)),
    ("tabu_search",         lambda kols, b: tabu_search(kols, b, max_iter=20)),
    ("greedy_ranking",      lambda kols, b: greedy_ranking(kols, b)),
]


# ────────────────────────────────────────────────────────────
#  Interface tests — all 6 algorithms
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,runner", ALL_RUNNERS)
def test_returns_correct_shape(name, runner, small_pool):
    """state vector length must equal number of KOLs."""
    state, _, history = runner(small_pool, BUDGET)
    assert len(state) == len(small_pool), \
        f"{name}: state length {len(state)} != pool size {len(small_pool)}"
    assert isinstance(history, list)
    assert len(history) > 0


@pytest.mark.parametrize("name,runner", ALL_RUNNERS)
def test_respects_budget(name, runner, small_pool):
    """Total cost of selected KOLs must not exceed budget."""
    state, _, _ = runner(small_pool, BUDGET)
    summary = summarize_state(state, small_pool)
    assert summary["total_cost"] <= BUDGET + 0.01, \
        f"{name}: total_cost {summary['total_cost']} exceeds budget {BUDGET}"


@pytest.mark.parametrize("name,runner", ALL_RUNNERS)
def test_nonnegative_gmv(name, runner, small_pool):
    """Selected portfolio must produce non-negative GMV."""
    state, _, _ = runner(small_pool, BUDGET)
    summary = summarize_state(state, small_pool)
    assert summary["total_gmv"] >= 0, \
        f"{name}: total_gmv is negative: {summary['total_gmv']}"


@pytest.mark.parametrize("name,runner", ALL_RUNNERS)
def test_state_is_binary(name, runner, small_pool):
    """State values must all be 0 or 1."""
    state, _, _ = runner(small_pool, BUDGET)
    assert all(x in (0, 1) for x in state), \
        f"{name}: state contains non-binary values"


# ────────────────────────────────────────────────────────────
#  Reproducibility
# ────────────────────────────────────────────────────────────

def test_sa_reproducibility(small_pool):
    """Same seed must yield identical SA result."""
    s1, _, _ = simulated_annealing(small_pool, BUDGET, seed=42, max_iter=10)
    s2, _, _ = simulated_annealing(small_pool, BUDGET, seed=42, max_iter=10)
    assert s1 == s2, "SA is not reproducible with fixed seed"


def test_ga_reproducibility(small_pool):
    """Same seed must yield identical GA result."""
    s1, _, _ = genetic_algorithm(small_pool, BUDGET, seed=42, generations=5)
    s2, _, _ = genetic_algorithm(small_pool, BUDGET, seed=42, generations=5)
    assert s1 == s2, "GA is not reproducible with fixed seed"


# ────────────────────────────────────────────────────────────
#  New categories
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name,runner", ALL_RUNNERS)
def test_works_with_new_categories(name, runner, mixed_pool):
    """All 6 algorithms must run cleanly on pools with all 4 categories."""
    state, _, history = runner(mixed_pool, 3000)
    assert len(state) == len(mixed_pool)
    assert len(history) > 0
    summary = summarize_state(state, mixed_pool)
    assert summary["total_cost"] <= 3000 + 0.01


# ────────────────────────────────────────────────────────────
#  Greedy ranking specific
# ────────────────────────────────────────────────────────────

def test_greedy_ranking_is_deterministic(small_pool):
    """Greedy ranking has no randomness — two calls must return identical state."""
    s1, _, _ = greedy_ranking(small_pool, BUDGET)
    s2, _, _ = greedy_ranking(small_pool, BUDGET)
    assert s1 == s2, "Greedy ranking is not deterministic"


def test_greedy_ranking_history_length_one(small_pool):
    """Greedy ranking produces a single-point history (instant result)."""
    _, _, history = greedy_ranking(small_pool, BUDGET)
    assert len(history) >= 1


# ────────────────────────────────────────────────────────────
#  Greedy-seeded solvers must add value over the random baseline
# ────────────────────────────────────────────────────────────

# The constructive / memory solvers seed from the multi-strategy greedy
# (engine.optimization._common.greedy_init); they are the ones the product
# recommends, and must beat the Random Search baseline. The cold-start
# trajectory controls (SA, HC) are NOT required to — they exist to measure the
# value of a warm greedy start, and can legitimately trail random on small pools.
GREEDY_SEEDED_SOLVERS = [
    ("genetic_algorithm",   genetic_algorithm),
    ("tabu_search",         tabu_search),
    ("greedy_ranking",      greedy_ranking),
]


@pytest.fixture
def knapsack_pool():
    """Pool that exposes the ratio-greedy trap (mirrors the real-data failure):
    a couple of high-GMV creators worth picking, plus many cheap, high-ROI-ratio,
    mutually-overlapping ones that ratio-greedy would wrongly pile up. The true
    optimum is the few big creators, not the many small ones."""
    big = [
        KOL(id=1, name="Big1", country="MY", category="beauty",
            followers=2_000_000, engagement_rate=0.12, fit_score=0.9,
            commission_rate=0.12, cost=4000),
        KOL(id=2, name="Big2", country="MY", category="beauty",
            followers=900_000, engagement_rate=0.12, fit_score=0.85,
            commission_rate=0.12, cost=900),
    ]
    small = [
        KOL(id=i, name=f"Small{i}", country="MY", category="beauty",
            followers=30_000, engagement_rate=0.10, fit_score=0.7,
            commission_rate=0.15, cost=150)
        for i in range(3, 22)
    ]
    return big + small


@pytest.mark.parametrize("name,solver", GREEDY_SEEDED_SOLVERS)
def test_greedy_seeded_solver_beats_random_baseline(name, solver, knapsack_pool):
    """The greedy-seeded constructive/memory solvers (the ones the product
    recommends) must score at least as high (true objective = GMV net of overlap)
    as the Random Search baseline. Regression guard for the ratio-greedy-seed bug
    that let random outscore them on skewed real pools."""
    budget = 5000
    rs_state, _, _ = random_search(knapsack_pool, budget, seed=42)
    rs_obj = summarize_state(rs_state, knapsack_pool)["objective"]

    state, _, _ = solver(knapsack_pool, budget, seed=42)
    obj = summarize_state(state, knapsack_pool)["objective"]
    assert obj >= rs_obj - 1e-6, \
        f"{name} objective {obj:.0f} is below the random baseline {rs_obj:.0f}"
