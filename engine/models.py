from dataclasses import dataclass

@dataclass
class KOL:
    id: int
    name: str
    country: str          # MY, ID, TH, PH
    category: str         # beauty, tech, fashion
    followers: int
    engagement_rate: float   # 0~1，历史转化率
    fit_score: float         # 0~1，文化契合度
    cost: float              # 坑位费 USD

    def expected_gmv(self) -> float:
        """单达人预期 GMV"""
        return self.followers * self.engagement_rate * self.fit_score
