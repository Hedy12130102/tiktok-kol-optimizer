import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.fitness import fitness, summarize_state


def test_fitness():
    kols = [
        KOL(id=1, name="A", country="MY", category="beauty",
            followers=100000, engagement_rate=0.1, fit_score=0.8, cost=1000),
        KOL(id=2, name="B", country="MY", category="tech",
            followers=50000, engagement_rate=0.2, fit_score=0.9, cost=800),
    ]
    budget = 1500

    # New GMV formula: sqrt(f) × ctr × cvr × aov × pp × 200
    # A (MY/beauty, 100K): GMV ≈ $7,902.53
    # B (MY/tech, 50K):    GMV ≈ $7,137.53
    # Total GMV ≈ $15,040.06
    # Overlap: both MY → 0.4 score → 0.4 × 5000 = 2000 penalty
    # Total cost = 1800 > 1500 → budget penalty = (1800-1500)×1e6 = 300,000,000
    # Fitness = -15040.06 + 300000000 + 2000 = 299986959.94

    expected_fitness = 299986959.94
    val = fitness([1, 1], kols, budget)
    assert val == expected_fitness, f"Expected {expected_fitness}, got {val}"

    # A only: fitness = -7902.53 (just -GMV, no penalties)
    val2 = fitness([1, 0], kols, budget)
    assert abs(val2 - (-7902.53)) < 0.1, f"Expected ~-7902.53, got {val2}"


def test_summarize_state_with_overlap():
    """Verify overlap penalty is computed for same country+category KOLs."""
    kols = [
        KOL(id=1, name="X", country="MY", category="beauty",
            followers=50000, engagement_rate=0.1, fit_score=0.5, cost=500),
        KOL(id=2, name="Y", country="MY", category="beauty",
            followers=48000, engagement_rate=0.1, fit_score=0.5, cost=500),
    ]
    summary = summarize_state([1, 1], kols)
    # Same country (0.4) + same category (0.3) + similar followers (48K/50K=0.96>0.8 → 0.3)
    # Full overlap score = 1.0 → penalty = 1.0 × 5000 = 5000
    assert summary["overlap_penalty"] == 5000, \
        f"Expected overlap penalty 5000, got {summary['overlap_penalty']}"


def test_summarize_state_no_overlap():
    """No overlap penalty for different country+category KOLs."""
    kols = [
        KOL(id=1, name="X", country="MY", category="beauty",
            followers=50000, engagement_rate=0.1, fit_score=0.5, cost=500),
        KOL(id=2, name="Y", country="TH", category="tech",
            followers=500000, engagement_rate=0.1, fit_score=0.5, cost=500),
    ]
    summary = summarize_state([1, 1], kols)
    # Different country (0) + different category (0) + follower ratio 0.1 (not>0.8 → 0)
    assert summary["overlap_penalty"] == 0, \
        f"Expected 0 overlap penalty, got {summary['overlap_penalty']}"
