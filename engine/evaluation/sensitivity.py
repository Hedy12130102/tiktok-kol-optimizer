import json
import numpy as np
import matplotlib.pyplot as plt
from typing import List
from tqdm import tqdm

from engine.models import KOL
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.sa_improved import simulated_annealing_improved
from engine.fitness import summarize_state

# ---------------------- Parameter Configuration (Official Requirement) ----------------------
T0_LIST = [1000, 10000, 50000, 100000]
ALPHA_LIST = [0.90, 0.95, 0.99]
REPEAT_TIMES = 5
BUDGET = 5000
SEED = 42
SAVE_FIG_PATH = "docs/figures/sensitivity_heatmap.png"

# ---------------------- Load Filtered Dataset ----------------------
def load_malaysia_beauty_kols() -> List[KOL]:
    """Load and filter Malaysia beauty category KOL data"""
    with open("data/sample_kols.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    kols = [KOL(**item) for item in raw_data]
    filtered_kols = [k for k in kols if k.country == "MY" and k.category == "beauty"]
    return filtered_kols

# ---------------------- Parameter Sensitivity Experiment ----------------------
def run_sensitivity_experiment():
    kols = load_malaysia_beauty_kols()
    result_matrix = np.zeros((len(T0_LIST), len(ALPHA_LIST)))

    for t_idx, t0 in enumerate(tqdm(T0_LIST, desc="Traverse Initial Temperature")):
        for a_idx, alpha in enumerate(tqdm(ALPHA_LIST, desc="Traverse Cooling Factor", leave=False)):
            gmv_total = 0.0
            for _ in range(REPEAT_TIMES):
                state, _, _ = simulated_annealing_improved(
                    kols=kols,
                    budget=BUDGET,
                    T0=t0,
                    alpha=alpha,
                    seed=SEED
                )
                res = summarize_state(state, kols)
                gmv_total += res["total_gmv"]
            # Calculate average GMV
            avg_gmv = gmv_total / REPEAT_TIMES
            result_matrix[t_idx][a_idx] = avg_gmv

    # ---------------------- Draw Heatmap ----------------------
    plt.rcParams["font.sans-serif"] = ["SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(result_matrix, cmap="Blues", aspect="auto")

    ax.set_xticks(np.arange(len(ALPHA_LIST)))
    ax.set_yticks(np.arange(len(T0_LIST)))
    ax.set_xticklabels(ALPHA_LIST)
    ax.set_yticklabels(T0_LIST)

    plt.colorbar(im, ax=ax, label="Average Total GMV")
    plt.xlabel("Cooling Coefficient Alpha")
    plt.ylabel("Initial Temperature T0")
    plt.title("Parameter Sensitivity Analysis of Improved SA Algorithm")

    # Save figure to appointed path
    plt.tight_layout()
    plt.savefig(SAVE_FIG_PATH, dpi=300)
    plt.close()
    print(f"Heatmap saved successfully at: {SAVE_FIG_PATH}")
    print("All sensitivity analysis experiments finished")

    return result_matrix

if __name__ == "__main__":
    run_sensitivity_experiment()
