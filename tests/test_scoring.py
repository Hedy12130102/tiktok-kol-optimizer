import pytest
from engine.models import KOL
from engine.scoring.creator_score import compute_creator_score
from engine.scoring.explainer import generate_reasons
from engine.fitness import summarize_state

# ---------------------- Fixtures ----------------------
@pytest.fixture
def test_kols():
    """Fixture: Create KOL objects for testing"""
    return [
        KOL(id=1, name="Test1", country="MY", category="beauty", followers=2_000_000, engagement=0.08, fit=0.85, cost=1200),  # Mega
        KOL(id=2, name="Test2", country="MY", category="beauty", followers=500_000, engagement=0.06, fit=0.75, cost=800),    # Macro
        KOL(id=3, name="Test3", country="MY", category="beauty", followers=50_000, engagement=0.05, fit=0.70, cost=500),    # Micro
        KOL(id=4, name="Test4", country="MY", category="beauty", followers=5_000, engagement=0.04, fit=0.65, cost=300),     # Nano
    ]

# ---------------------- ALG-06 Test Cases ----------------------
def test_compute_creator_score_range(test_kols):
    """Test case 1: Scores should be in [0, 1] range"""
    scores = compute_creator_score(test_kols)
    assert all(0 <= s <= 1 for s in scores), "Score out of [0,1] range"

def test_compute_creator_score_length(test_kols):
    """Test case 2: Output length should match input count"""
    scores = compute_creator_score(test_kols)
    assert len(scores) == len(test_kols), "Score count mismatch with KOL count"

def test_generate_reasons_quantity(test_kols):
    """Test case 3: Should return at least 3 reasons"""
    reasons = generate_reasons(test_kols[0], test_kols)
    assert len(reasons) >= 3, "Less than 3 reasons generated"

def test_tier_classification():
    """Test case 4: Tier classification logic"""
    kol_mega = KOL(1, "Mega", "MY", "beauty", 1_500_000, 0.08, 0.85, 1200)
    kol_macro = KOL(2, "Macro", "MY", "beauty", 500_000, 0.06, 0.75, 800)
    kol_micro = KOL(3, "Micro", "MY", "beauty", 50_000, 0.05, 0.70, 500)
    kol_nano = KOL(4, "Nano", "MY", "beauty", 5_000, 0.04, 0.65, 300)

    assert kol_mega.tier == "Mega"
    assert kol_macro.tier == "Macro"
    assert kol_micro.tier == "Micro"
    assert kol_nano.tier == "Nano"

def test_roi_calculation_from_state(test_kols):
    """Test case 5: ROI calculation using summarize_state"""
    # Select the first two KOLs
    state = [1, 1, 0, 0]
    summary = summarize_state(state, test_kols)
    
    assert "roi" in summary, "ROI key missing in summary"
    roi = summary["roi"]
    assert isinstance(roi, (int, float)), "ROI should be a numeric value"
    assert roi > 0, "ROI should be positive for valid selection"
