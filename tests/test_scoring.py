import pytest
from engine.models import KOL
from engine.scoring.creator_score import compute_creator_score, add_scores_to_kols
from engine.scoring.explainer import generate_reasons, get_tier
from engine.fitness import summarize_state


@pytest.fixture
def sample_kols() -> list[KOL]:
    """
    Fixture: Initialize KOL objects covering all 4 tiers and a mix of categories.
    """
    return [
        KOL(
            id=1,
            name="Influencer_A",
            country="MY",
            category="beauty",
            followers=1200000,
            engagement_rate=0.09,
            fit_score=0.86,
            cost=1300.0
        ),
        KOL(
            id=2,
            name="Influencer_B",
            country="TH",
            category="fashion",
            followers=450000,
            engagement_rate=0.065,
            fit_score=0.72,
            cost=780.0
        ),
        KOL(
            id=3,
            name="Influencer_C",
            country="ID",
            category="fashion",
            followers=12000,
            engagement_rate=0.048,
            fit_score=0.68,
            cost=420.0
        ),
        KOL(
            id=4,
            name="Influencer_D",
            country="PH",
            category="beauty",
            followers=3200,
            engagement_rate=0.035,
            fit_score=0.61,
            cost=260.0
        ),
        KOL(
            id=5,
            name="Influencer_E",
            country="MY",
            category="fmcg",
            followers=75000,
            engagement_rate=0.12,
            fit_score=0.78,
            cost=600.0
        ),
        KOL(
            id=6,
            name="Influencer_F",
            country="TH",
            category="home",
            followers=280000,
            engagement_rate=0.07,
            fit_score=0.82,
            cost=2100.0
        ),
    ]


def test_creator_score_range(sample_kols):
    """
    ALG-06 Test 1: Scores must be strictly within the range [0, 1].
    """
    scores = compute_creator_score(sample_kols)
    assert len(scores) == len(sample_kols)
    for s in scores:
        assert 0.0 <= s <= 1.0


def test_add_scores_dict_format(sample_kols):
    """
    ALG-06 Test 2: Verify correct dictionary format for API responses.
    """
    res_list = add_scores_to_kols(sample_kols)
    assert isinstance(res_list, list)
    assert "creator_score" in res_list[0]
    assert "expected_gmv" in res_list[0]


def test_kol_tier_division(sample_kols):
    """
    ALG-06 Test 3: Verify follower tier classification logic.
    """
    assert get_tier(sample_kols[0]) == "Mega"
    assert get_tier(sample_kols[1]) == "Macro"
    assert get_tier(sample_kols[2]) == "Micro"
    assert get_tier(sample_kols[3]) == "Nano"


def test_recommendation_reasons(sample_kols):
    """
    ALG-06 Test 4: Recommendation must generate at least 3 reasons.
    """
    reasons = generate_reasons(sample_kols[0], sample_kols)
    assert isinstance(reasons, list)
    assert len(reasons) >= 3


def test_state_roi_calculate(sample_kols):
    """
    ALG-06 Test 5: Verify ROI calculation for a selected state.
    """
    test_state = [1, 0, 1, 0, 0, 0]
    summary = summarize_state(test_state, sample_kols)
    assert isinstance(summary["total_gmv"], float)
    assert isinstance(summary["roi"], float)
    assert summary["roi"] >= 0


def test_new_categories_have_positive_gmv():
    """All 4 categories must produce positive GMV."""
    for cat in ["beauty", "fashion", "home", "fmcg"]:
        k = KOL(id=1, name="T", country="MY", category=cat,
                followers=100000, engagement_rate=0.08, fit_score=0.7, cost=1000)
        gmv = k.expected_gmv()
        assert gmv > 0, f"Category {cat} produced non-positive GMV: {gmv}"


def test_creator_score_includes_new_category_kols(sample_kols):
    """Creator scores should be computed for all 6 KOLs including fmcg and home."""
    scores = compute_creator_score(sample_kols)
    assert len(scores) == 6
    for i, s in enumerate(scores):
        assert 0.0 <= s <= 1.0, f"Score {i} out of range: {s}"
