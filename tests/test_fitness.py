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

    # GMV: A ≈ $7,902.53, B ≈ $7,137.53, total ≈ $15,040.06
    # Overlap: same age_group "18-24" → 0.3 × 1500 = 450
    # Budget: cost 1800 > 1500 → penalty = (1800-1500)×1e6 = 300,000,000
    # Fitness = -15040.06 + 300000000 + 450 = 299985409.94

    expected_fitness = 299985409.94
    val = fitness([1, 1], kols, budget)
    assert val == expected_fitness, f"Expected {expected_fitness}, got {val}"

    # A only: fitness = -7902.53 (just -GMV, no penalties)
    val2 = fitness([1, 0], kols, budget)
    assert abs(val2 - (-7902.53)) < 0.1, f"Expected ~-7902.53, got {val2}"


def test_summarize_state_with_overlap():
    """Verify overlap penalty is computed for similar follower range + age KOLs."""
    kols = [
        KOL(id=1, name="X", country="MY", category="beauty",
            followers=50000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="25-34", gender_ratio=0.5),
        KOL(id=2, name="Y", country="MY", category="beauty",
            followers=48000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="25-34", gender_ratio=0.5),
    ]
    summary = summarize_state([1, 1], kols)
    # follower ratio 48K/50K=0.96 > 0.5 → 0.5
    # age_group: both default "18-24" → 0.3
    # gender: 0.5 not extreme
    # Total score = 0.8 → penalty = 0.8 × 1500 = 1200
    assert summary["overlap_penalty"] == 1200, \
        f"Expected overlap penalty 1200, got {summary['overlap_penalty']}"


def test_summarize_state_no_overlap():
    """No overlap penalty for different country+category KOLs."""
    kols = [
        KOL(id=1, name="X", country="MY", category="beauty",
            followers=50000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="18-24", gender_ratio=0.5),
        KOL(id=2, name="Y", country="TH", category="tech",
            followers=500000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="35+", gender_ratio=0.5),
    ]
    summary = summarize_state([1, 1], kols)
    # Different followers (ratio 0.1 < 0.5), different age, no gender extreme → 0
    assert summary["overlap_penalty"] == 0, \
        f"Expected 0 overlap penalty, got {summary['overlap_penalty']}"
