import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.fitness import fitness, summarize_state


def test_fitness_budget_overflow():
    """Exceeding budget triggers a massive penalty."""
    kols = [
        KOL(id=1, name="A", country="MY", category="beauty",
            followers=100000, engagement_rate=0.1, fit_score=0.8, cost=1000),
        KOL(id=2, name="B", country="MY", category="fmcg",
            followers=50000, engagement_rate=0.2, fit_score=0.9, cost=800),
    ]
    budget = 1500  # total cost = 1800, exceeds budget by 300

    gmv_a = kols[0].expected_gmv()
    gmv_b = kols[1].expected_gmv()
    total_gmv = round(gmv_a + gmv_b, 2)

    # Overlap analysis:
    #   follower ratio = 50000/100000 = 0.5 — NOT > 0.5, so no follower overlap
    #   age_group both "18-24" (default) → +0.3 → penalty = 0.3 × 1500 = 450
    #   gender_ratio 0.5 (default) → no gender skew
    expected_overlap = 450.0
    expected_budget_penalty = (1800 - 1500) * 1e6  # = 300_000_000
    expected_fitness = -total_gmv + expected_budget_penalty + expected_overlap

    val = fitness([1, 1], kols, budget)
    assert abs(val - expected_fitness) < 0.1, f"Expected {expected_fitness:.2f}, got {val}"


def test_fitness_single_kol_no_penalty():
    """Selecting one KOL within budget: fitness = -GMV (no penalties)."""
    kols = [
        KOL(id=1, name="A", country="MY", category="beauty",
            followers=100000, engagement_rate=0.1, fit_score=0.8, cost=1000),
        KOL(id=2, name="B", country="MY", category="fmcg",
            followers=50000, engagement_rate=0.2, fit_score=0.9, cost=800),
    ]
    budget = 1500

    gmv_a = kols[0].expected_gmv()
    val = fitness([1, 0], kols, budget)
    assert abs(val - (-gmv_a)) < 0.01, f"Expected {-gmv_a}, got {val}"


def test_fitness_new_categories():
    """All categories (beauty, fashion, home, fmcg) should produce valid GMV."""
    for cat in ["beauty", "fashion", "home", "fmcg"]:
        k = KOL(id=1, name="T", country="MY", category=cat,
                followers=100000, engagement_rate=0.1, fit_score=0.7, cost=1000)
        gmv = k.expected_gmv()
        assert gmv > 0, f"Category {cat} produced non-positive GMV: {gmv}"
        val = fitness([1], [k], 2000)
        assert val == -gmv, f"fitness([1]) should equal -GMV for {cat}"


def test_summarize_state_with_overlap():
    """Verify overlap penalty is computed for similar follower range + same age KOLs."""
    kols = [
        KOL(id=1, name="X", country="MY", category="beauty",
            followers=50000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="25-34", gender_ratio=0.5),
        KOL(id=2, name="Y", country="MY", category="beauty",
            followers=48000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="25-34", gender_ratio=0.5),
    ]
    summary = summarize_state([1, 1], kols)
    # follower ratio 48K/50K = 0.96 > 0.5 → +0.5
    # age_group "25-34" == "25-34" → +0.3
    # gender_ratio 0.5 — not extreme → 0
    # Total score = 0.8 → penalty = 0.8 × 1500 = 1200
    assert summary["overlap_penalty"] == 1200, \
        f"Expected overlap penalty 1200, got {summary['overlap_penalty']}"


def test_summarize_state_no_overlap():
    """No overlap penalty for KOLs with different age group and very different follower counts."""
    kols = [
        KOL(id=1, name="X", country="MY", category="beauty",
            followers=50000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="18-24", gender_ratio=0.5),
        KOL(id=2, name="Y", country="TH", category="home",
            followers=500000, engagement_rate=0.1, fit_score=0.5, cost=500,
            age_group="35+", gender_ratio=0.5),
    ]
    summary = summarize_state([1, 1], kols)
    # follower ratio 50K/500K = 0.1, NOT > 0.5 → no follower overlap
    # different age groups → no age overlap
    # gender_ratio 0.5 → no gender skew
    assert summary["overlap_penalty"] == 0, \
        f"Expected 0 overlap penalty, got {summary['overlap_penalty']}"


def test_gmv_differs_by_category():
    """Different categories must produce different GMV for identical KOL metrics."""
    baseline = KOL(id=1, name="T", country="MY", category="beauty",
                   followers=100000, engagement_rate=0.1, fit_score=0.7, cost=1000)
    gmv_values = set()
    for cat in ["beauty", "fashion", "home", "fmcg"]:
        k = KOL(id=1, name="T", country="MY", category=cat,
                followers=100000, engagement_rate=0.1, fit_score=0.7, cost=1000)
        gmv_values.add(k.expected_gmv())
    # All 4 categories have distinct CTR×CVR×AOV products → 4 distinct GMV values
    assert len(gmv_values) == 4, f"Expected 4 distinct GMV values across categories, got: {gmv_values}"
