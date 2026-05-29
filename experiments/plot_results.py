import sys
import os

# Ensure root directory is in python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import matplotlib.pyplot as plt
import json

def generate_charts():
    # Make sure output directory exists
    os.makedirs("docs/figures", exist_ok=True)
    
    # Load the CSV data we just generated
    csv_path = "experiments/plots/scalability_results.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Wait for scalability.py to finish!")
        return
        
    df = pd.read_csv(csv_path)
    
    # ----------------------------------------------------
    # Chart 1: Scalability Time (scalability_time.png)
    # ----------------------------------------------------
    plt.figure(figsize=(8, 5))
    for algo in df['Algorithm'].unique():
        algo_df = df[df['Algorithm'] == algo]
        plt.errorbar(
            algo_df['N'], algo_df['Mean_Time_Sec'], yerr=algo_df['Std_Time_Sec'],
            marker='o', capsize=5, label=algo.replace('_', ' ')
        )
    plt.title("Algorithm Execution Time vs. Pool Size (N)")
    plt.xlabel("Pool Size (N)")
    plt.ylabel("Execution Time (Seconds)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.savefig("docs/figures/scalability_time.png", dpi=300)
    plt.close()
    print("Saved docs/figures/scalability_time.png")

    # ----------------------------------------------------
    # Chart 2: Scalability GMV (scalability_gmv.png)
    # ----------------------------------------------------
    plt.figure(figsize=(8, 5))
    for algo in df['Algorithm'].unique():
        algo_df = df[df['Algorithm'] == algo]
        plt.errorbar(
            algo_df['N'], algo_df['Mean_GMV'], yerr=algo_df['Std_GMV'],
            marker='s', capsize=5, label=algo.replace('_', ' ')
        )
    plt.title("Optimized Portfolio Value vs. Pool Size (N)")
    plt.xlabel("Pool Size (N)")
    plt.ylabel("Portfolio Value (Fitness Score)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.savefig("docs/figures/scalability_gmv.png", dpi=300)
    plt.close()
    print("Saved docs/figures/scalability_gmv.png")

    # ----------------------------------------------------
    # Chart 3: Tier Distribution Pie Chart (tier_distribution.png)
    # ----------------------------------------------------
    # Read our core 300 KOL data file to see our final market split
    try:
        with open("data/sample_kols.json", "r", encoding="utf-8") as f:
            kols = json.load(f)
        
        # Count the frequency of each generated age group or follower tier
        # (Since we explicitly tiered followers, let's categorize them for the pie chart)
        tiers = {"Nano (<10k)": 0, "Micro (10k-100k)": 0, "Macro (100k-1M)": 0, "Mega (>1M)": 0}
        for k in kols:
            f_count = k['followers']
            if f_count < 10000: tiers["Nano (<10k)"] += 1
            elif f_count <= 100000: tiers["Micro (10k-100k)"] += 1
            elif f_count <= 1000000: tiers["Macro (100k-1M)"] += 1
            else: tiers["Mega (>1M)"] += 1

        plt.figure(figsize=(6, 6))
        plt.pie(
            tiers.values(), labels=tiers.keys(), 
            autopct='%1.1f%%', startangle=140, 
            colors=['#ff9999','#66b3ff','#99ff99','#ffcc99']
        )
        plt.title("KOL Tier Distribution (Target Market Ratios)")
        plt.savefig("docs/figures/tier_distribution.png", dpi=300)
        plt.close()
        print("Saved docs/figures/tier_distribution.png")
    except Exception as e:
        print(f"Skipping Pie Chart: Ensure data/sample_kols.json is generated! ({e})")

if __name__ == "__main__":
    generate_charts()