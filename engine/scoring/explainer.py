# engine/scoring/explainer.py
"""
Explainer — generates human-readable recommendation reasons for each KOL.

This is the "Explainable AI" feature that makes the system more
trustworthy: instead of showing a black-box score, the frontend
displays concrete, data-driven sentences explaining WHY a KOL was
recommended.

Each KOL receives ≥ 3 reasons, selected from the checks below.
"""
from typing import List

from engine.models import KOL

# ── Tier thresholds ────────────────────────────────────────────────
_TIER_MAP = {
    "Mega":  1_000_000,
    "Macro":   100_000,
    "Micro":    10_000,
    "Nano":          0,
}

# ── Country display names ──────────────────────────────────────────
_COUNTRY_NAME = {
    "MY": "Malaysia",
    "ID": "Indonesia",
    "TH": "Thailand",
    "PH": "Philippines",
    "SG": "Singapore",
    "VN": "Vietnam",
}

# ── Category display names ─────────────────────────────────────────
_CATEGORY_NAME = {
    "beauty":  "beauty & personal care",
    "fashion": "fashion & lifestyle",
    "home":    "home & living",
    "fmcg":    "FMCG",
}


def get_tier(kol: KOL) -> str:
    """Return tier string — delegates to KOL.tier property."""
    return kol.tier


def generate_reasons(kol: KOL, all_kols: List[KOL]) -> List[str]:
    """
    Generate a list of recommendation reasons for a single KOL.

    Args:
        kol:      The KOL to explain.
        all_kols: Full candidate pool, used to compute relative benchmarks.

    Returns:
        List of ≥ 3 human-readable reason strings.
    """
    reasons: List[str] = []
    country  = _COUNTRY_NAME.get(kol.country, kol.country)
    category = _CATEGORY_NAME.get(kol.category, kol.category)
    tier     = get_tier(kol)

    # ── 1. Audience market fit ────────────────────────────────────
    fit_pct = int(kol.fit_score * 100)
    if kol.fit_score >= 0.80:
        reasons.append(
            f"{country} audience match is {fit_pct}%, well above the 80% threshold"
        )
    elif kol.fit_score >= 0.60:
        reasons.append(
            f"Solid {country} audience fit at {fit_pct}%"
        )
    else:
        reasons.append(
            f"Audience fit score is {fit_pct}% for {country} market"
        )

    # ── 2. Engagement rate ────────────────────────────────────────
    eng_pct = round(kol.engagement_rate * 100, 1)
    avg_eng = sum(k.engagement_rate for k in all_kols) / len(all_kols) if all_kols else 0
    if kol.engagement_rate >= avg_eng * 1.2:
        reasons.append(
            f"Engagement rate {eng_pct}% is {round((kol.engagement_rate/avg_eng - 1)*100)}% "
            f"above the candidate-pool average"
        )
    else:
        reasons.append(
            f"Engagement rate of {eng_pct}% in {category} content"
        )

    # ── 3. Tier & reach ───────────────────────────────────────────
    followers_fmt = (
        f"{kol.followers / 1_000_000:.1f}M"
        if kol.followers >= 1_000_000
        else f"{kol.followers // 1_000}K"
    )
    reasons.append(
        f"{tier} KOL with {followers_fmt} followers — "
        + {
            "Mega":  "maximum brand awareness reach",
            "Macro": "broad coverage with strong credibility",
            "Micro": "high conversion rate and precise audience targeting",
            "Nano":  "highly engaged niche community",
        }[tier]
    )

    # ── 4. Cost-effectiveness (conditional) ──────────────────────
    gmv = kol.expected_gmv()
    cost_eff = gmv / kol.cost if kol.cost > 0 else 0
    positive_cost_kols = [k for k in all_kols if k.cost > 0]
    avg_ce = (
        sum(k.expected_gmv() / k.cost for k in positive_cost_kols)
        / len(positive_cost_kols)
        if positive_cost_kols
        else 0
    )
    if cost_eff > 0 and avg_ce > 0 and cost_eff >= avg_ce * 1.15:
        reasons.append(
            f"Predicted ROI is {round((cost_eff / avg_ce - 1) * 100)}% "
            f"above the pool average — high cost-effectiveness"
        )

    # ── 5. High absolute GMV (conditional) ───────────────────────
    avg_gmv = sum(k.expected_gmv() for k in all_kols) / len(all_kols) if all_kols else 0
    if gmv >= avg_gmv * 1.3:
        reasons.append(
            f"Predicted GMV of ${gmv:,.0f} is among the top performers in this pool"
        )

    # Guarantee at least 3 reasons
    while len(reasons) < 3:
        reasons.append(f"Recommended for {category} campaigns in {country}")

    return reasons