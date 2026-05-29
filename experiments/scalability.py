import sys
import os

# 1. Path auto-injector to find root project folders smoothly
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import time
import csv
import numpy as np
from data.generator import generate_kols
from engine.models import KOL

from engine.optimization.hill_climber import hill_climber
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.random_search import random_search

def load_kols_from_list(kol_dicts):
    return [KOL(**item) for item in kol_dicts]

def run_scalability_experiment():
    sizes = [50, 100, 200, 500]
    iterations = 10
    
    output_dir = "experiments/plots"
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "scalability_results.csv")
    
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "N", "Algorithm", 
            "Mean_Time_Sec", "Std_Time_Sec", 
            "Mean_GMV", "Std_GMV"
        ])
        
        for N in sizes:
            print(f"--- Running experiments for N = {N} ---")
            results = {
                "Hill_Climber": {"times": [], "gmvs": []},
                "Simulated_Annealing": {"times": [], "gmvs": []},
                "Random_Search": {"times": [], "gmvs": []}
            }
            
            for seed in range(42, 42 + iterations):
                kol_dicts = generate_kols(
                    num=N, 
                    json_output_path=f"data/temp_kols_{N}.json", 
                    csv_output_path=f"data/temp_kols_{N}.csv", 
                    seed=seed
                )
                kols_pool = load_kols_from_list(kol_dicts)
                campaign_budget = 5000.0
                
                # ---- Test Hill Climber ----
                start_time = time.time()
                # These functions typically return (best_state, best_fitness/GMV)
                _, hc_gmv = hill_climber(kols_pool, budget=campaign_budget, seed=seed)
                results["Hill_Climber"]["times"].append(time.time() - start_time)
                # If your fitness function returns negative cost, convert it to GMV by taking absolute value
                results["Hill_Climber"]["gmvs"].append(abs(hc_gmv))
                
                # ---- Test Simulated Annealing ----
                start_time = time.time()
                _, sa_gmv = simulated_annealing(kols_pool, budget=campaign_budget, seed=seed)
                results["Simulated_Annealing"]["times"].append(time.time() - start_time)
                results["Simulated_Annealing"]["gmvs"].append(abs(sa_gmv))
                
                # ---- Test Random Search ----
                start_time = time.time()
                _, rs_gmv = random_search(kols_pool, budget=campaign_budget, seed=seed)
                results["Random_Search"]["times"].append(time.time() - start_time)
                results["Random_Search"]["gmvs"].append(abs(rs_gmv))
            
            for algo_name, metrics in results.items():
                mean_time = np.mean(metrics["times"])
                std_time = np.std(metrics["times"])
                mean_gmv = np.mean(metrics["gmvs"])
                std_gmv = np.std(metrics["gmvs"])
                
                writer.writerow([N, algo_name, mean_time, std_time, mean_gmv, std_gmv])
                print(f"[{algo_name}] Time: {mean_time:.4f}s, GMV: {mean_gmv:.2f}")
                
            if os.path.exists(f"data/temp_kols_{N}.json"):
                os.remove(f"data/temp_kols_{N}.json")
                os.remove(f"data/temp_kols_{N}.csv")

    print(f"\nSuccess! Metrics cleanly written to: {csv_path}")

if __name__ == "__main__":
    run_scalability_experiment()
