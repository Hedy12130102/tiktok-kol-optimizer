from engine.models import KOL
from engine.scoring.creator_score import compute_creator_score

def test_creator_score():
    """Test the CreatorScore calculation with sample KOL data."""
    # Sample Malaysian KOL data for testing
    kol1 = KOL(
        id=1,
        name="Beauty Influencer",
        country="MY",
        category="beauty",
        followers=1000000,
        engagement_rate=0.08,
        fit_score=0.85,
        cost=1200,
        avg_views=120000,
        avg_likes=11000,
        gender_ratio=0.45,
        age_group="18-24"
    )

    kol2 = KOL(
        id=2,
        name="Fashion Influencer",
        country="MY",
        category="fashion",
        followers=95000,
        engagement_rate=0.13,
        fit_score=0.88,
        cost=750,
        avg_views=28000,
        avg_likes=3200,
        gender_ratio=0.62,
        age_group="25-30"
    )

    kol_list = [kol1, kol2]
    scores = compute_creator_score(kol_list)
    print("Creator scores:", scores)

if __name__ == "__main__":
    test_creator_score()
