import json
import numpy as np
import matplotlib.pyplot as plt
from typing import List
from tqdm import tqdm

from engine.models import KOL
from engine.optimization.simulated_annealing import simulated_annealing
from engine.fitness import summarize_state

# ---------------------- Parameter Configuration ----------------------
T0_LIST = [500, 1000, 5000, 10000, 50000, 100000]
ALPHA_LIST = [0.90, 0.92, 0.95, 0.97, 0.99]
REPEAT_TIMES = 5
BUDGET = 2500
SEED = 42
SAVE_FIG_PATH = "docs/figures/_sensitivity_heatmap.png"

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
    # result_matrix: rows = alpha, cols = T0 (to match imshow with origin="lower")
    result_matrix = np.zeros((len(ALPHA_LIST), len(T0_LIST)))

    for a_idx, alpha in enumerate(tqdm(ALPHA_LIST, desc="Traverse Cooling Factor")):
        for t_idx, t0 in enumerate(tqdm(T0_LIST, desc="Traverse Initial Temperature", leave=False)):
            gmv_total = 0.0
            for _ in range(REPEAT_TIMES):
                state, _, _ = simulated_annealing(
                    kols=kols,
                    budget=BUDGET,
                    T0=t0,
                    alpha=alpha,
                    seed=SEED + _
                )
                res = summarize_state(state, kols)
                gmv_total += res["total_gmv"]
            # Calculate average GMV
            avg_gmv = round(gmv_total / REPEAT_TIMES, 2)
            result_matrix[a_idx][t_idx] = avg_gmv

    # ---------------------- Draw Heatmap ----------------------
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(result_matrix, cmap="YlGn", aspect="auto", origin="lower")

    ax.set_xticks(np.arange(len(T0_LIST)))
    ax.set_yticks(np.arange(len(ALPHA_LIST)))
    ax.set_xticklabels(T0_LIST)
    ax.set_yticklabels(ALPHA_LIST)

    cbar = plt.colorbar(im, ax=ax, label="Average Total GMV")
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    plt.xlabel("Initial Temperature T0", fontsize=12)
    plt.ylabel("Cooling Rate Alpha", fontsize=12)
    plt.title("SA Parameter Sensitivity — Best GMV (MY beauty, budget=$2,500)", fontsize=13)

    for i in range(len(ALPHA_LIST)):
        for j in range(len(T0_LIST)):
            ax.text(j, i, f"${result_matrix[i,j]:,.0f}", ha="center", va="center",
                    fontsize=7.5, color="white" if result_matrix[i,j] < result_matrix.max()*0.6 else "black")

    # Save figure to appointed path
    plt.tight_layout()
    plt.savefig(SAVE_FIG_PATH, dpi=300)
    plt.close()
    print(f"Heatmap saved successfully at: {SAVE_FIG_PATH}")
    print("All sensitivity analysis experiments finished")

    return result_matrix

if __name__ == "__main__":
    run_sensitivity_experiment()
