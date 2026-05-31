from engine.scoring.explainer import generate_reasons
from engine.models import KOL

kol = KOL(
    id=1,
    name="Test Beauty Influencer",
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

reasons = generate_reasons(kol, [kol])
for idx, text in enumerate(reasons,1):
    print(f"reasons{idx}: {text}")
