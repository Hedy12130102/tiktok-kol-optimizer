import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.scoring.creator_score import compute_creator_score


def test_creator_score_returns_correct_count():
    """CreatorScore should return one score per KOL."""
    kols = [
        KOL(id=1, name="A", country="MY", category="beauty",
            followers=1_000_000, engagement_rate=0.08, fit_score=0.85,
            commission_rate=0.15, cost=1200),
        KOL(id=2, name="B", country="MY", category="fashion",
            followers=95_000, engagement_rate=0.13, fit_score=0.88,
            commission_rate=0.15, cost=750),
    ]
    scores = compute_creator_score(kols)
    assert len(scores) == 2


def test_creator_score_in_range():
    """All scores must lie in [0, 1]."""
    kols = [
        KOL(id=1, name="A", country="MY", category="beauty",
            followers=1_000_000, engagement_rate=0.08, fit_score=0.85,
            commission_rate=0.15, cost=1200),
        KOL(id=2, name="B", country="MY", category="fashion",
            followers=95_000, engagement_rate=0.13, fit_score=0.88,
            commission_rate=0.15, cost=750),
        KOL(id=3, name="C", country="TH", category="fashion",
            followers=12_000, engagement_rate=0.05, fit_score=0.68,
            commission_rate=0.20, cost=420),
    ]
    scores = compute_creator_score(kols)
    for s in scores:
        assert 0.0 <= s <= 1.0


def test_creator_score_higher_for_better_kol():
    """A KOL with higher followers, engagement, fit, and cost-effectiveness scores higher."""
    kols = [
        KOL(id=1, name="Weak", country="MY", category="beauty",
            followers=5_000, engagement_rate=0.03, fit_score=0.4,
            commission_rate=0.30, cost=100),
        KOL(id=2, name="Strong", country="MY", category="beauty",
            followers=500_000, engagement_rate=0.12, fit_score=0.9,
            commission_rate=0.10, cost=1000),
    ]
    scores = compute_creator_score(kols)
    assert scores[1] > scores[0], f"Strong KOL ({scores[1]:.3f}) should outscore Weak KOL ({scores[0]:.3f})"
