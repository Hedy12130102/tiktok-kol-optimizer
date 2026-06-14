import csv, json, random, os, math


# ════════════════════════════════════════════════════════════════
#  Market-data tables (mirrored from engine/models.py so the
#  generator stays self-contained — no engine import needed)
# ════════════════════════════════════════════════════════════════

_CTR = {
    "beauty":  {"MY": 0.035, "ID": 0.032, "TH": 0.040, "PH": 0.030, "SG": 0.038, "VN": 0.038},
    "fashion": {"MY": 0.033, "ID": 0.030, "TH": 0.036, "PH": 0.028, "SG": 0.036, "VN": 0.034},
    "home":    {"MY": 0.028, "ID": 0.025, "TH": 0.030, "PH": 0.023, "SG": 0.030, "VN": 0.027},
    "fmcg":    {"MY": 0.040, "ID": 0.037, "TH": 0.044, "PH": 0.035, "SG": 0.042, "VN": 0.041},
}

_CVR = {
    "beauty":  {"MY": 0.085, "ID": 0.075, "TH": 0.090, "PH": 0.070, "SG": 0.095, "VN": 0.072},
    "fashion": {"MY": 0.075, "ID": 0.065, "TH": 0.080, "PH": 0.060, "SG": 0.085, "VN": 0.062},
    "home":    {"MY": 0.060, "ID": 0.050, "TH": 0.065, "PH": 0.045, "SG": 0.068, "VN": 0.046},
    "fmcg":    {"MY": 0.095, "ID": 0.085, "TH": 0.105, "PH": 0.078, "SG": 0.108, "VN": 0.082},
}

_AOV = {
    "beauty":  {"MY": 42,  "ID": 35,  "TH": 38,  "PH": 32,  "SG": 60,  "VN": 28},
    "fashion": {"MY": 55,  "ID": 45,  "TH": 50,  "PH": 40,  "SG": 72,  "VN": 34},
    "home":    {"MY": 45,  "ID": 38,  "TH": 42,  "PH": 32,  "SG": 65,  "VN": 28},
    "fmcg":    {"MY": 22,  "ID": 18,  "TH": 20,  "PH": 16,  "SG": 32,  "VN": 11},
}

_PURCHASING_POWER = {
    "MY": 1.0,
    "TH": 0.9,
    "ID": 0.7,
    "PH": 0.6,
    "SG": 1.3,
    "VN": 0.55,
}

_SCALE = 200
_ENG_BASE = 0.132
_FIT_BASE = 0.650


def _approx_expected_gmv(country: str, category: str, followers: int,
                          engagement_rate: float, fit_score: float) -> float:
    """Approximate GMV — same formula as KOL.expected_gmv() in engine/models.py."""
    cat = category if category in _CTR else "beauty"
    cty = country  if country  in _PURCHASING_POWER else "MY"

    ctr = _CTR.get(cat, {}).get(cty, 0.030)
    cvr = _CVR.get(cat, {}).get(cty, 0.060)
    aov = _AOV.get(cat, {}).get(cty, 50)
    pp  = _PURCHASING_POWER.get(cty, 1.0)

    traction    = math.sqrt(max(1, followers))
    funnel_rate = ctr * cvr

    engagement_factor = math.sqrt(max(1e-4, engagement_rate) / _ENG_BASE)
    fit_factor        = math.sqrt(max(1e-4, fit_score)        / _FIT_BASE)

    return round(
        traction * funnel_rate * aov * pp * engagement_factor * fit_factor * _SCALE,
        2
    )


_COUNTRIES  = ["MY", "ID", "TH", "PH", "SG", "VN"]
_CATEGORIES = ["beauty", "fashion", "home", "fmcg"]

# Handle-like name fragments per category, for synthetic creators that need to
# read as plausible TikTok accounts rather than "KOL_123".
_NAME_PARTS = {
    "beauty":  ["glowlab", "skinsense", "beautybox", "makeupdaily", "luxederma", "radiant", "glossy"],
    "fashion": ["styledby", "wardrobe", "trendthreads", "ootd", "fitcheck", "couture", "streetfit"],
    "home":    ["homestyle", "cozyliving", "nestit", "decorhub", "kitchenly", "casamood", "tidyhome"],
    "fmcg":    ["dailypick", "snackbox", "freshmart", "pantrygo", "tastybites", "grocerly", "sip.daily"],
}


def _slice_name(category, country, n, rng):
    base = rng.choice(_NAME_PARTS.get(category, ["creator"]))
    return f"{base}.{country.lower()}{n:02d}"


def _make_kol(idx, country, category, rng, name=None, source=None):
    """Build one realistic synthetic creator record for a fixed market+category.

    `rng` may be the `random` module or a `random.Random` instance (both expose
    randint/uniform/choice), so callers control reproducibility.
    """
    tier_roll = rng.uniform(0, 100)
    if tier_roll < 40.0:
        followers = rng.randint(1000, 9999)
    elif tier_roll < 75.0:
        followers = rng.randint(10000, 100000)
    elif tier_roll < 95.0:
        followers = rng.randint(100001, 1000000)
    else:
        followers = rng.randint(1000001, 5000000)

    # Engagement rate: tier-specific, calibrated to real TikTok benchmarks
    # Source: Brandwatch / TTS Vibes 2025
    #   Nano  (<10K):     avg 17-18%, range 10-30%
    #   Micro (10K-100K): avg 6-8%,   range 4-15%
    #   Macro (100K-1M):  avg 5-7%,   range 3-10%
    #   Mega  (>1M):      avg 4-6%,   range 2-8%
    if followers < 10_000:
        base = rng.uniform(0.10, 0.30)
    elif followers < 100_000:
        base = rng.uniform(0.04, 0.15)
    elif followers < 1_000_000:
        base = rng.uniform(0.03, 0.10)
    else:
        base = rng.uniform(0.02, 0.08)
    engagement_rate = round(max(0.001, min(0.30, base * rng.uniform(0.85, 1.15))), 4)

    fit_score = rng.uniform(0.3, 1.0)

    # ── Commission rate (replaces flat-fee cost) ──────────────────
    # Sources: TikTok Shop Affiliate Commission Benchmarks 2025-2026
    # Higher-tier KOLs negotiate lower commission rates because they
    # deliver higher absolute volume.
    #   Nano  (<10K):     25-35%  — low reach, high rate
    #   Micro (10K-100K): 18-28%
    #   Macro (100K-1M):  12-22%
    #   Mega  (>1M):       5-15%  — high volume, low rate
    if followers >= 1_000_000:
        commission_rate = round(rng.uniform(0.05, 0.15), 4)
    elif followers >= 100_000:
        commission_rate = round(rng.uniform(0.12, 0.22), 4)
    elif followers >= 10_000:
        commission_rate = round(rng.uniform(0.18, 0.28), 4)
    else:
        commission_rate = round(rng.uniform(0.25, 0.35), 4)

    # ── Cost = commission_rate × expected_gmv ────────────────────
    approx_gmv = _approx_expected_gmv(country, category, followers,
                                       engagement_rate, fit_score)
    cost = round(commission_rate * approx_gmv, 2)

    noise    = rng.randint(-int(followers * 0.05), int(followers * 0.05))
    avg_views = max(0, int(followers * 0.3 + noise))
    avg_likes = int(avg_views * engagement_rate)

    record = {
        "id": idx, "name": name or f"KOL_{idx}",
        "country": country,
        "category": category,
        "followers": followers,
        "engagement_rate": engagement_rate,
        "fit_score": round(fit_score, 4),
        "commission_rate": commission_rate,
        "cost": cost,
        "avg_views": avg_views,
        "avg_likes": avg_likes,
        "gender_ratio": round(rng.uniform(0.0, 1.0), 2),
        "age_group": rng.choice(["18-24", "25-34", "35+"]),
    }
    if source:
        record["source"] = source
    return record


def generate_for_slices(targets: dict, start_id: int = 1, seed: int = 42,
                        source: str = "synthetic") -> list:
    """Generate creators for specific (country, category) slices.

    `targets` maps (country, category) -> how many creators to create.
    Returns a list of records with sequential ids starting at `start_id`,
    each tagged with the given `source`.
    """
    rng = random.Random(seed)
    out, idx = [], start_id
    for (country, category), count in sorted(targets.items()):
        for n in range(1, int(count) + 1):
            name = _slice_name(category, country, n, rng)
            rec = _make_kol(idx, country, category, rng, name=name, source=source)
            rec["cost_estimated"] = True   # demo price, not a negotiated quote
            out.append(rec)
            idx += 1
    return out


def generate_kols(num=2000, json_output_path="data/sample_kols.json",
                  csv_output_path=None, seed=42):
    """Generate a synthetic KOL pool.

    Writes JSON to `json_output_path`. A CSV mirror is written only if
    `csv_output_path` is given (optional — nothing in the app reads it).
    """
    if num < 1:
        raise ValueError("num must be a positive integer")
    random.seed(seed)
    for p in [json_output_path, csv_output_path]:
        if p and os.path.dirname(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)

    kols = []
    for i in range(1, num + 1):
        country  = random.choice(_COUNTRIES)
        category = random.choice(_CATEGORIES)
        kols.append(_make_kol(i, country, category, random))

    if json_output_path:
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(kols, f, indent=4, ensure_ascii=False)
    if csv_output_path:
        with open(csv_output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=kols[0].keys())
            writer.writeheader()
            writer.writerows(kols)
    print(f"Generated {num} KOLs -> {json_output_path}")
    return kols


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a synthetic KOL dataset.")
    parser.add_argument("--num", type=int, default=300,
                        help="Number of KOLs to generate (default: 300).")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42).")
    args = parser.parse_args()

    if args.num < 1:
        parser.error("--num must be a positive integer")

    generate_kols(num=args.num, seed=args.seed)
