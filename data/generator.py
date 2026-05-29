import csv
import json
import random
import os

def generate_kols(
    num: int = 300,
    json_output_path: str = "data/sample_kols.json",
    csv_output_path: str = "data/influencers_mock.csv",
    seed: int = 42,
):
    random.seed(seed)
    os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
    countries = ["MY", "ID", "TH", "PH"]
    categories = ["beauty", "tech", "fashion"]
    kols = []
    
    for i in range(1, num + 1):
        tier_roll = random.uniform(0, 100)
        if tier_roll < 40.0:
            # Nano: < 10k (Let's say between 1,000 and 9,999)
            followers = random.randint(1000, 9999)
        elif tier_roll < 75.0:
            # Micro: 10k ~ 100k (40% + 35% = 75%)
            followers = random.randint(10000, 100000)
        elif tier_roll < 95.0:
            # Macro: 100k ~ 1python data/generator.pyM (75% + 20% = 95%)
            followers = random.randint(100001, 1000000)
        else:
            # Mega: > 1M (Remaining 5%)
            followers = random.randint(1000001, 5000000)
        # Engagement rate is usually inversely proportional to followers, with some randomness
        base_engagement = max(0.01, 100000 / followers)
        engagement_rate = min(0.3, max(0.001, base_engagement * random.uniform(0.5, 1.5)))
        fit_score = random.uniform(0.3, 1.0)
        
        # Cost is usually positively correlated with followers and engagement rate
        base_cost = followers * engagement_rate * 0.05
        cost = max(50.0, min(100000.0, base_cost * random.uniform(0.8, 1.2)))
       
        noise = random.randint(-int(followers * 0.05), int(followers * 0.05))
        avg_views = max(0, int(followers * 0.3 + noise))
        avg_likes = int(avg_views * engagement_rate)
        gender_ratio = round(random.uniform(0.0, 1.0), 2)
        age_group = random.choice(["18-24", "25-34", "35+"])
        
        kols.append({
            "id": i,
            "name": f"KOL_{i}",
            "country": random.choice(countries),
            "category": random.choice(categories),
            "followers": followers,
            "engagement_rate": round(engagement_rate, 4),
            "fit_score": round(fit_score, 4),
            "cost": round(cost, 2),
            "avg_views": avg_views,
            "avg_likes": avg_likes,
            "gender_ratio": gender_ratio,
            "age_group": age_group
        })
        
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(kols, f, indent=4, ensure_ascii=False)

    with open(csv_output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=kols[0].keys())
        writer.writeheader()
        writer.writerows(kols)
    return kols
    print(f"Successfully generated {num} KOLs to {json_output_path} and {csv_output_path}")

if __name__ == "__main__":
    import argparse  # We import this here so we don't disrupt the top of your file

    # 1. Set up the command-line argument parser
    parser = argparse.ArgumentParser(description="Generate mock TikTok KOL data.")

    # 2. Tell it to look out for a '--num' flag, defaulting to 300 if not specified
    parser.add_argument(
        "--num", 
        type=int, 
        default=300, 
        help="Number of KOLs to generate (default: 300)"
    )

    # 3. Read whatever the user typed in the terminal
    args = parser.parse_args()
    
    # 4. Call your function using that dynamic number!
    generate_kols(num=args.num)
