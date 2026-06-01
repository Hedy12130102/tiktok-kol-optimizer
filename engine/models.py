from dataclasses import dataclass

@dataclass
class KOL:
    id: int
    name: str
    country: str          # MY, ID, TH, PH
    category: str         # beauty, tech, fashion
    followers: int
    engagement_rate: float   # 0~1, historical conversion rate
    fit_score: float         # 0~1, cultural fit score
    cost: float              # Cost in USD
    
    # ─── ADD THESE 4 NEW FIELDS BELOW ───
    avg_views: int = 0
    avg_likes: int = 0
    gender_ratio: float = 0.0
    age_group: str = ""

    def expected_gmv(self) -> float:
        """Expected GMV for a single KOL"""
        return self.followers * self.engagement_rate * self.fit_score