import csv, json, random, os, math

def generate_kols(num=300, json_output_path="data/sample_kols.json",
                  csv_output_path="data/influencers_mock.csv", seed=42):
    random.seed(seed)
    for p in [json_output_path, csv_output_path]:
        if p and os.path.dirname(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)

    countries  = ["MY", "ID", "TH", "PH", "SG", "VN"]
    categories = ["beauty", "fashion", "home", "fmcg"]
    kols = []

    for i in range(1, num + 1):
        tier_roll = random.uniform(0, 100)
        if tier_roll < 40.0:
            followers = random.randint(1000, 9999)
        elif tier_roll < 75.0:
            followers = random.randint(10000, 100000)
        elif tier_roll < 95.0:
            followers = random.randint(100001, 1000000)
        else:
            followers = random.randint(1000001, 5000000)

        # Engagement rate: tier-specific, calibrated to real TikTok benchmarks
        # Source: Brandwatch / TTS Vibes 2025
        #   Nano  (<10K):     avg 17-18%, range 10-30%
        #   Micro (10K-100K): avg 6-8%,   range 4-15%
        #   Macro (100K-1M):  avg 5-7%,   range 3-10%
        #   Mega  (>1M):      avg 4-6%,   range 2-8%
        if followers < 10_000:
            base = random.uniform(0.10, 0.30)
        elif followers < 100_000:
            base = random.uniform(0.04, 0.15)
        elif followers < 1_000_000:
            base = random.uniform(0.03, 0.10)
        else:
            base = random.uniform(0.02, 0.08)
        engagement_rate = round(max(0.001, min(0.30, base * random.uniform(0.85, 1.15))), 4)

        fit_score = random.uniform(0.3, 1.0)

        # Cost: calibrated to SEA influencer market rates
        # Sources: InfluenceFlow 2026, ContentGrip 2026
        #   Nano:  $50-$200  |  Micro: $250-$1,000
        #   Macro: $1,500-$5,000  |  Mega: $5,000-$20,000
        if followers >= 1_000_000:
            cost = round(random.uniform(5000, 20000), 2)
        elif followers >= 100_000:
            cost = round(random.uniform(1500, 5000), 2)
        elif followers >= 10_000:
            cost = round(random.uniform(250, 1000), 2)
        else:
            cost = round(random.uniform(50, 200), 2)

        noise    = random.randint(-int(followers * 0.05), int(followers * 0.05))
        avg_views = max(0, int(followers * 0.3 + noise))
        avg_likes = int(avg_views * engagement_rate)

        kols.append({
            "id": i, "name": f"KOL_{i}",
            "country": random.choice(countries),
            "category": random.choice(categories),
            "followers": followers,
            "engagement_rate": engagement_rate,
            "fit_score": round(fit_score, 4),
            "cost": cost,
            "avg_views": avg_views,
            "avg_likes": avg_likes,
            "gender_ratio": round(random.uniform(0.0, 1.0), 2),
            "age_group": random.choice(["18-24", "25-34", "35+"])
        })

    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(kols, f, indent=4, ensure_ascii=False)
    with open(csv_output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=kols[0].keys())
        writer.writeheader()
        writer.writerows(kols)
    print(f"Generated {num} KOLs -> {json_output_path}")
    return kols

generate_kols(300)
