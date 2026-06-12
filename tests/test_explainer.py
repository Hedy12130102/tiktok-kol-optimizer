import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.scoring.explainer import generate_reasons, get_tier
from engine.models import KOL


def test_generate_reasons_returns_at_least_three():
    kol = KOL(
        id=1, name="Test Beauty Influencer", country="MY", category="beauty",
        followers=1_000_000, engagement_rate=0.08, fit_score=0.85,
        commission_rate=0.15, cost=1200,
        avg_views=120_000, avg_likes=11_000, gender_ratio=0.45, age_group="18-24",
    )
    reasons = generate_reasons(kol, [kol])
    assert len(reasons) >= 3


def test_get_tier_delegates_to_property():
    kol = KOL(
        id=1, name="Test", country="MY", category="beauty",
        followers=1_200_000, engagement_rate=0.08, fit_score=0.7,
        commission_rate=0.15, cost=1000,
    )
    assert get_tier(kol) == "Mega"


def test_all_countries_have_display_names():
    from engine.scoring.explainer import _COUNTRY_NAME
    for country in ["MY", "ID", "TH", "PH", "SG", "VN"]:
        assert country in _COUNTRY_NAME, f"Missing country: {country}"


def test_all_categories_have_display_names():
    from engine.scoring.explainer import _CATEGORY_NAME
    for cat in ["beauty", "fashion", "home", "fmcg"]:
        assert cat in _CATEGORY_NAME, f"Missing category: {cat}"
