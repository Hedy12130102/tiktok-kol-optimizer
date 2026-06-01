# experiments/scalability.py
"""
Scalability Analysis Experiment
================================
Tests how each algorithm performs as the KOL pool size grows.

For each pool size N in [50, 100, 200, 500]:
  - Runs Hill Climber, Simulated Annealing, and Random Search
  - Repeats 10 times with different seeds
  - Records mean ± std of execution time and final GMV

Outputs
-------
  experiments/plots/scalability_results.csv
  docs/figures/scalability_time.png
  docs/figures/scalability_gmv.png
"""

import csv
import os
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

# ── Make sure project root is on the path ─────────────────────────
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from data.generator import generate_kols
from engine.fitness import summarize_state
from engine.models import KOL
from engine.optimization.hill_climber import hill_climber
from engine.optimization.random_search import random_search
from engine.optimization.simulated_annealing import simulated_annealing

# ── Experiment configuration ──────────────────────────────────────
POOL_SIZES     = [50, 100, 200, 500]
REPEAT         = 10          # number of seeds per pool size
BUDGET         = 5000.0
BASE_SEED      = 42          # seeds will be BASE_SEED, BASE_SEED+1, ..., BASE_SEED+REPEAT-1

ALGO_CONFIGS = {
    "Simulated Annealing": {"color": "#1D9E75", "marker": "o"},
    "Hill Climber":        {"color": "#D85A30", "marker": "s"},
    "Random Search":       {"color": "#888780", "marker": "^"},
}


# ── Helper ────────────────────────────────────────────────────────
def dicts_to_kols(kol_dicts: list) -> list:
    """Convert list of dicts (from generator) to list of KOL objects."""
    return [KOL(**d) for d in kol_dicts]


def run_one(algo_fn, kols, budget, seed, **kwargs):
    """
    Run one algorithm and return (elapsed_seconds, total_gmv).
    All three algorithms return (state, cost, history).
    """
    t0 = time.perf_counter()
    state, _, _hist = algo_fn(kols, budget, seed=seed, **kwargs)
    elapsed = time.perf_counter() - t0
    gmv = summarize_state(state, kols)["total_gmv"]
    return elapsed, gmv


# ── Main experiment ───────────────────────────────────────────────
def run_scalability_experiment():
    os.makedirs("experiments/plots", exist_ok=True)
    os.makedirs("docs/figures", exist_ok=True)

    # Storage: results[algo_name][N] = {"times": [...], "gmvs": [...]}
    results = {name: {N: {"times": [], "gmvs": []} for N in POOL_SIZES}
               for name in ALGO_CONFIGS}

    for N in POOL_SIZES:
        print(f"\n{'─'*50}")
        print(f"  Pool size N = {N}")
        print(f"{'─'*50}")

        for i in range(REPEAT):
            seed = BASE_SEED + i

            # Generate a fresh KOL pool for this seed
            kol_dicts = generate_kols(
                num=N,
                json_output_path=f"data/temp_kols_{N}_{seed}.json",
                csv_output_path=f"data/temp_kols_{N}_{seed}.csv",
                seed=seed,
            )
            kols = dicts_to_kols(kol_dicts)

            # Run all three algorithms on the same pool
            t_sa, gmv_sa = run_one(simulated_annealing, kols, BUDGET, seed)
            t_hc, gmv_hc = run_one(hill_climber,        kols, BUDGET, seed)
            t_rs, gmv_rs = run_one(random_search,        kols, BUDGET, seed)

            results["Simulated Annealing"][N]["times"].append(t_sa)
            results["Simulated Annealing"][N]["gmvs"].append(gmv_sa)
            results["Hill Climber"][N]["times"].append(t_hc)
            results["Hill Climber"][N]["gmvs"].append(gmv_hc)
            results["Random Search"][N]["times"].append(t_rs)
            results["Random Search"][N]["gmvs"].append(gmv_rs)

            print(f"  seed={seed}  SA={gmv_sa:>10,.0f}  HC={gmv_hc:>10,.0f}  RS={gmv_rs:>10,.0f}")

            # Clean up temp files
            for ext in [".json", ".csv"]:
                tmp = f"data/temp_kols_{N}_{seed}{ext}"
                if os.path.exists(tmp):
                    os.remove(tmp)

    # ── Write CSV ─────────────────────────────────────────────────
    csv_path = "experiments/plots/scalability_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "N", "Algorithm",
            "Mean_Time_Sec", "Std_Time_Sec",
            "Mean_GMV",      "Std_GMV",
        ])
        for algo_name in ALGO_CONFIGS:
            for N in POOL_SIZES:
                times = results[algo_name][N]["times"]
                gmvs  = results[algo_name][N]["gmvs"]
                writer.writerow([
                    N, algo_name,
                    round(np.mean(times), 4), round(np.std(times), 4),
                    round(np.mean(gmvs),  2),  round(np.std(gmvs),  2),
                ])
    print(f"\n✅  CSV saved → {csv_path}")

    # ── Compute summary arrays for plotting ───────────────────────
    summary = {}
    for algo_name in ALGO_CONFIGS:
        summary[algo_name] = {
            "mean_times": [np.mean(results[algo_name][N]["times"]) for N in POOL_SIZES],
            "std_times":  [np.std( results[algo_name][N]["times"]) for N in POOL_SIZES],
            "mean_gmvs":  [np.mean(results[algo_name][N]["gmvs"])  for N in POOL_SIZES],
            "std_gmvs":   [np.std( results[algo_name][N]["gmvs"])  for N in POOL_SIZES],
        }

    # ── Plot 1: Execution Time ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    for algo_name, cfg in ALGO_CONFIGS.items():
        s = summary[algo_name]
        ax.errorbar(
            POOL_SIZES,
            s["mean_times"],
            yerr=s["std_times"],
            label=algo_name,
            color=cfg["color"],
            marker=cfg["marker"],
            linewidth=2,
            markersize=7,
            capsize=4,
        )
    ax.set_xlabel("KOL Pool Size (N)", fontsize=12)
    ax.set_ylabel("Execution Time (seconds)", fontsize=12)
    ax.set_title("Algorithm Scalability — Execution Time vs Pool Size", fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    for path in ["experiments/plots/scalability_time.png", "docs/figures/scalability_time.png"]:
        fig.savefig(path, dpi=150)
    plt.close(fig)
    print("✅  Time chart saved → docs/figures/scalability_time.png")

    # ── Plot 2: Final GMV ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    for algo_name, cfg in ALGO_CONFIGS.items():
        s = summary[algo_name]
        ax.errorbar(
            POOL_SIZES,
            s["mean_gmvs"],
            yerr=s["std_gmvs"],
            label=algo_name,
            color=cfg["color"],
            marker=cfg["marker"],
            linewidth=2,
            markersize=7,
            capsize=4,
        )
    ax.set_xlabel("KOL Pool Size (N)", fontsize=12)
    ax.set_ylabel("Mean Best GMV (USD)", fontsize=12)
    ax.set_title("Algorithm Scalability — Solution Quality vs Pool Size", fontsize=13)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    fig.tight_layout()
    for path in ["experiments/plots/scalability_gmv.png", "docs/figures/scalability_gmv.png"]:
        fig.savefig(path, dpi=150)
    plt.close(fig)
    print("✅  GMV chart saved  → docs/figures/scalability_gmv.png")

    # ── Print summary table ───────────────────────────────────────
    print("\n" + "═" * 70)
    print(f"{'N':>6}  {'Algorithm':<22}  {'Time(s)':>10}  {'GMV':>12}")
    print("═" * 70)
    for N in POOL_SIZES:
        for algo_name in ALGO_CONFIGS:
            s = summary[algo_name]
            i = POOL_SIZES.index(N)
            print(
                f"{N:>6}  {algo_name:<22}  "
                f"{s['mean_times'][i]:>8.4f}s  "
                f"${s['mean_gmvs'][i]:>11,.0f}"
            )
        print("─" * 70)


if __name__ == "__main__":
    run_scalability_experiment()
