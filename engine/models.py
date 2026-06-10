from dataclasses import dataclass
import math

# ================================================================
#  Market data tables -- country & category specific metrics
# ================================================================
# Sources:
#   TikTok Shop SEA Partner Reports H1 2024, Cube Asia Social Commerce 2024
#   e-Conomy SEA 2024 (Google/Temasek/Bain), IMF WEO Oct 2024
#   Statista TikTok Shop Singapore/Vietnam 2024, Marketing LTB TikTok Stats 2024
#   AsiaKOL Vietnam Influencer Marketing Guide 2024
#   Kantar FMCG Social Commerce SEA 2024, Nielsen IQ TikTok Shop FMCG Report 2024
#   World Bank GDP per capita data 2024

# Click-through rate: % of viewers who click through to product page
# FMCG: high CTR driven by impulse purchases (personal care, household, snacks)
# SG: tech-savvy, high intent shoppers
# VN: very active TikTok base, high video engagement
_CTR = {
    "beauty":  {"MY": 0.035, "ID": 0.032, "TH": 0.040, "PH": 0.030, "SG": 0.038, "VN": 0.038},
    "fashion": {"MY": 0.033, "ID": 0.030, "TH": 0.036, "PH": 0.028, "SG": 0.036, "VN": 0.034},
    "home":    {"MY": 0.028, "ID": 0.025, "TH": 0.030, "PH": 0.023, "SG": 0.030, "VN": 0.027},
    "fmcg":    {"MY": 0.040, "ID": 0.037, "TH": 0.044, "PH": 0.035, "SG": 0.042, "VN": 0.041},
}

# Conversion rate: % of clicks that convert to a purchase
# FMCG: high CVR due to everyday necessity + low price friction
# SG: high purchasing power, low price friction -> highest CVR
# VN: price-conscious but volume-driven -> lower-mid CVR
_CVR = {
    "beauty":  {"MY": 0.085, "ID": 0.075, "TH": 0.090, "PH": 0.070, "SG": 0.095, "VN": 0.072},
    "fashion": {"MY": 0.075, "ID": 0.065, "TH": 0.080, "PH": 0.060, "SG": 0.085, "VN": 0.062},
    "home":    {"MY": 0.060, "ID": 0.050, "TH": 0.065, "PH": 0.045, "SG": 0.068, "VN": 0.046},
    "fmcg":    {"MY": 0.095, "ID": 0.085, "TH": 0.105, "PH": 0.078, "SG": 0.108, "VN": 0.082},
}

# Average order value by category x country (USD)
# FMCG: blend of food (~$12-22), personal care (~$20-35), household (~$15-28)
# SG: premium market; VN: price-sensitive, low-ticket
_AOV = {
    "beauty":  {"MY": 42,  "ID": 35,  "TH": 38,  "PH": 32,  "SG": 60,  "VN": 28},
    "fashion": {"MY": 55,  "ID": 45,  "TH": 50,  "PH": 40,  "SG": 72,  "VN": 34},
    "home":    {"MY": 45,  "ID": 38,  "TH": 42,  "PH": 32,  "SG": 65,  "VN": 28},
    "fmcg":    {"MY": 22,  "ID": 18,  "TH": 20,  "PH": 16,  "SG": 32,  "VN": 11},
}

# Purchasing power parity -- residual behavioral multiplier (beyond AOV)
# Reflects checkout completion rate, payment success, return behavior
# Sources: IMF World Economic Outlook Oct 2024, World Bank 2024
_PURCHASING_POWER = {
    "MY": 1.0,   # baseline -- GDP/cap ~$13,490
    "TH": 0.9,   # ~$7,810
    "ID": 0.7,   # ~$5,270
    "PH": 0.6,   # ~$4,130
    "SG": 1.3,   # ~$90,674 -- highest GDP/cap in SEA; premium market
    "VN": 0.55,  # ~$4,717  -- fast-growing, high volume but low-ticket
}


@dataclass
class KOL:
    id: int
    name: str
    country: str          # MY, ID, TH, PH, SG, VN
    category: str         # beauty, fashion, home, fmcg
    followers: int
    engagement_rate: float   # 0~1, historical engagement rate
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
        Enhanced GMV formula (v2):

          GMV = sqrt(followers)
                x CTR(category, country) x CVR(category, country)
                x AOV(category, country)
                x purchasing_power(country)
                x engagement_factor
                x fit_factor
                x SCALE

        Quality multipliers (diminishing returns, normalised to dataset mean):
          engagement_factor = sqrt(engagement_rate / ENG_BASE)   ENG_BASE=0.132
          fit_factor        = sqrt(fit_score / FIT_BASE)          FIT_BASE=0.650

        Countries:  MY, ID, TH, PH, SG, VN
        Categories: beauty, fashion, home, fmcg
        """
        cat = self.category if self.category in _CTR else "beauty"
        cty = self.country  if self.country  in _PURCHASING_POWER else "MY"

        ctr = _CTR.get(cat, {}).get(cty, 0.030)
        cvr = _CVR.get(cat, {}).get(cty, 0.060)
        aov = _AOV.get(cat, {}).get(cty, 50)
        pp  = _PURCHASING_POWER.get(cty, 1.0)

        traction    = math.sqrt(max(1, self.followers))
        funnel_rate = ctr * cvr

        _ENG_BASE = 0.132
        _FIT_BASE = 0.650

        engagement_factor = math.sqrt(max(1e-4, self.engagement_rate) / _ENG_BASE)
        fit_factor        = math.sqrt(max(1e-4, self.fit_score)        / _FIT_BASE)

        SCALE = 200

        return round(
            traction * funnel_rate * aov * pp * engagement_factor * fit_factor * SCALE,
            2
        )
