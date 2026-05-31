from engine.models import KOL
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.sa_improved import simulated_annealing_improved
from engine.fitness import summarize_state
import json

# Step 1: Load the sample KOL dataset
with open("data/sample_kols.json") as f:
    kols = [KOL(**d) for d in json.load(f)]

# Step 2: Filter for Malaysian beauty category KOLs
kols_my = [k for k in kols if k.country == "MY" and k.category == "beauty"]

print(f"Loaded {len(kols_my)} Malaysian beauty KOLs\n")

# Step 3: Run the standard Simulated Annealing algorithm
print("Running Standard Simulated Annealing...")
sa_state, _, sa_hist = simulated_annealing(kols_my, iterations=5000, seed=42)

# Step 4: Run the improved Simulated Annealing algorithm
print("Running Improved Simulated Annealing...")
sai_state, _, sai_hist = simulated_annealing_improved(kols_my, iterations=5000, seed=42)

# Step 5: Calculate and compare GMV results
sa_result = summarize_state(sa_state, kols_my)
sai_result = summarize_state(sai_state, kols_my)

print("\n===== SA vs SA-Improved Comparison =====")
print(f"Standard SA      Total GMV: {sa_result['total_gmv']:.2f}")
print(f"Improved SA      Total GMV: {sai_result['total_gmv']:.2f}")

improvement_percent = ((sai_result['total_gmv'] - sa_result['total_gmv']) / sa_result['total_gmv'] * 100)
print(f"GMV Improvement: {improvement_percent:.2f}%")
