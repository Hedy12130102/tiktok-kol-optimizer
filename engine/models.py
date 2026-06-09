from dataclasses import dataclass
import math

# ════════════════════════════════════════════════════════════════
#  Market data tables — country & category specific metrics
# ════════════════════════════════════════════════════════════════

# Click-through rate: % of viewers who click through to product page
# Varies by category (vertical strength) × country (platform maturity)
_CTR = {
    "beauty":  {"MY": 0.035, "ID": 0.032, "TH": 0.040, "PH": 0.030},
    "tech":   {"MY": 0.028, "ID": 0.025, "TH": 0.030, "PH": 0.022},
    "fashion":{"MY": 0.033, "ID": 0.030, "TH": 0.036, "PH": 0.028},
}

# Conversion rate: % of clicks that convert to a purchase
# Varies by category (purchase intent) × country (purchasing behavior)
_CVR = {
    "beauty":  {"MY": 0.085, "ID": 0.075, "TH": 0.090, "PH": 0.070},
    "tech":   {"MY": 0.060, "ID": 0.050, "TH": 0.065, "PH": 0.045},
    "fashion":{"MY": 0.075, "ID": 0.065, "TH": 0.080, "PH": 0.060},
}

# Average order value by category × country (USD)
# Scaled to produce reasonable GMV values in the optimizer
_AOV = {
    "beauty":  {"MY": 42, "ID": 35, "TH": 38, "PH": 32},
    "tech":   {"MY": 95, "ID": 80, "TH": 85, "PH": 70},
    "fashion":{"MY": 55, "ID": 45, "TH": 50, "PH": 40},
}

# Purchasing power parity — final GMV multiplier per country
_PURCHASING_POWER = {"MY": 1.0, "ID": 0.7, "TH": 0.9, "PH": 0.6}


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
    avg_views:    int   = 0
    avg_likes:    int   = 0
    gender_ratio: float = 0.5
    age_group:    str   = "18-24"

    @property
    def tier(self) -> str:
       if self.followers >= 1_000_000:
          return "Mega"
       if self.followers >= 100_000:
          return "Macro"
       if self.followers >= 10_000:
          return "Micro"
       return "Nano"

    def expected_gmv(self) -> float:
        """
        Upgraded GMV formula:

          GMV = sqrt(followers) × CTR_cat,ctry × CVR_cat,ctry × AOV_cat,ctry
                × purchasing_power × scale

        Diminishing returns: sqrt(f) means 100× followers → 10× GMV growth.
        This prevents the algorithm from always favouring mega KOLs —
        mixed-tier portfolios (Mega + Micro + Nano) naturally emerge.

        Market factors vary by category + country to reflect real e-commerce
        differences in click-through, conversion, and order value.
        """
        import math

        # Market parameters — default to beauty/MY for safety
        cat = self.category if self.category in _CTR else "beauty"
        cty = self.country  if self.country  in _PURCHASING_POWER else "MY"

        ctr = _CTR.get(cat, {}).get(cty, 0.030)
        cvr = _CVR.get(cat, {}).get(cty, 0.060)
        aov = _AOV.get(cat, {}).get(cty, 50)
        pp  = _PURCHASING_POWER.get(cty, 1.0)

        # Diminishing-returns traction
        traction = math.sqrt(max(1, self.followers))

        # Funnel: views → clicks → purchases → revenue
        funnel_rate = ctr * cvr  # combined click + conversion probability

        # Normalisation constant so a 100K-follower beauty/MY KOL ≈ $7,900 GMV
        SCALE = 200

        gmv = traction * funnel_rate * aov * pp * SCALE

        return round(gmv, 2)
