import csv
import json
import random
import os

def generate_kols(
    num: int = 200,
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
        followers = random.randint(10000, 5000000)
        # Engagement rate is usually inversely proportional to followers, with some randomness
        base_engagement = max(0.01, 100000 / followers)
        engagement_rate = min(0.3, max(0.001, base_engagement * random.uniform(0.5, 1.5)))
        fit_score = random.uniform(0.3, 1.0)
        
        # Cost is usually positively correlated with followers and engagement rate
        base_cost = followers * engagement_rate * 0.05
        cost = max(50.0, min(100000.0, base_cost * random.uniform(0.8, 1.2)))
        
        kols.append({
            "id": i,
            "name": f"KOL_{i}",
            "country": random.choice(countries),
            "category": random.choice(categories),
            "followers": followers,
            "engagement_rate": round(engagement_rate, 4),
            "fit_score": round(fit_score, 4),
            "cost": round(cost, 2)
        })
        
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(kols, f, indent=4, ensure_ascii=False)

    with open(csv_output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=kols[0].keys())
        writer.writeheader()
        writer.writerows(kols)
    
    print(f"Successfully generated {num} KOLs to {json_output_path} and {csv_output_path}")

if __name__ == "__main__":
    generate_kols()
