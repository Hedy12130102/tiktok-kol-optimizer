# experiments/scalability.py
"""
Scalability Analysis Experiment
================================
Tests how each of the six algorithms performs as the KOL pool size grows.

For each pool size N in [50, 100, 200, 500]:
  - Runs SA, HC, RS, GA, TS (N≤100 only), GR
  - Repeats REPEAT times with different seeds
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

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from data.generator import generate_kols
from engine.fitness import summarize_state
from engine.models import KOL
from engine.optimization.hill_climber import hill_climber
from engine.optimization.random_search import random_search
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.genetic_algorithm import genetic_algorithm
from engine.optimization.tabu_search import tabu_search
from engine.optimization.greedy_ranking import greedy_ranking

# ── Experiment configuration ──────────────────────────────────────
POOL_SIZES = [50, 100, 200, 500]
REPEAT     = 10
BUDGET     = 5_000.0
BASE_SEED  = 42

# TS is O(N²) per iteration — skip at N > 100 to avoid extremely long runtimes
TS_MAX_N = 100

ALGO_CONFIGS = {
    "Simulated Annealing": {"fn": simulated_annealing, "color": "#1D9E75", "marker": "o",  "ls": "-"},
    "Hill Climber":        {"fn": hill_climber,        "color": "#D85A30", "marker": "s",  "ls": "-"},
    "Random Search":       {"fn": random_search,       "color": "#888780", "marker": "^",  "ls": "--"},
    "Genetic Algorithm":   {"fn": genetic_algorithm,   "color": "#4A90D9", "marker": "D",  "ls": "-"},
    "Tabu Search":         {"fn": tabu_search,         "color": "#9B59B6", "marker": "v",  "ls": "-"},
    "Greedy Ranking":      {"fn": greedy_ranking,      "color": "#F39C12", "marker": "P",  "ls": ":"},
}


def dicts_to_kols(kol_dicts: list) -> list:
    return [KOL(**d) for d in kol_dicts]


def _gen_kols(n: int, seed: int) -> list:
    """Generate n KOLs via data.generator, using temp files to avoid writes."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as jf, \
         tempfile.NamedTemporaryFile(suffix=".csv",  delete=False) as cf:
        jpath, cpath = jf.name, cf.name
    kol_dicts = generate_kols(num=n, json_output_path=jpath, csv_output_path=cpath, seed=seed)
    os.unlink(jpath); os.unlink(cpath)
    return dicts_to_kols(kol_dicts)


def run_one(algo_fn, kols, budget, seed, **kwargs):
    t0 = time.perf_counter()
    state, _, _hist = algo_fn(kols, budget, seed=seed, **kwargs)
    elapsed = time.perf_counter() - t0
    gmv = summarize_state(state, kols)["total_gmv"]
    return elapsed, gmv


_CSV_PATH = "experiments/plots/scalability_results.csv"
_TS_NOTE = ("Note: Tabu Search is skipped at N > 100 — its O(N²) full-neighbourhood "
            "scan makes runtime prohibitive.")


def _filtered(mean_vals, err_vals):
    """Return (x, y, err) for the non-None entries, aligned to POOL_SIZES."""
    xs, ys, es = [], [], []
    for x, y, e in zip(POOL_SIZES, mean_vals, err_vals):
        if y is not None:
            xs.append(x); ys.append(y); es.append(e)
    return xs, ys, es


def _summary_from_csv(csv_path=_CSV_PATH):
    """Rebuild the plotting `summary` from a results CSV, so figures can be
    regenerated/restyled WITHOUT re-running the (wall-clock-noisy) benchmark."""
    rows = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[(r["Algorithm"], int(r["N"]))] = r

    def _num(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    summary = {}
    for algo_name in ALGO_CONFIGS:
        summary[algo_name] = {
            "mean_times": [_num(rows.get((algo_name, N), {}).get("Mean_Time_Sec")) for N in POOL_SIZES],
            "std_times":  [_num(rows.get((algo_name, N), {}).get("Std_Time_Sec"))  for N in POOL_SIZES],
            "mean_gmvs":  [_num(rows.get((algo_name, N), {}).get("Mean_GMV"))       for N in POOL_SIZES],
            "std_gmvs":   [_num(rows.get((algo_name, N), {}).get("Std_GMV"))        for N in POOL_SIZES],
        }
    return summary


def make_plots(summary):
    """Render the execution-time and solution-quality figures from a summary."""
    os.makedirs("experiments/plots", exist_ok=True)
    os.makedirs("docs/figures", exist_ok=True)

    panels = [
        ("mean_times", "std_times", "Execution Time (seconds)",
         "Algorithm Scalability — Execution Time vs Pool Size", None,
         ["experiments/plots/scalability_time.png", "docs/figures/scalability_time.png"]),
        ("mean_gmvs", "std_gmvs", "Mean Best GMV (USD)",
         "Algorithm Scalability — Solution Quality vs Pool Size",
         plt.FuncFormatter(lambda x, _: f"${x:,.0f}"),
         ["experiments/plots/scalability_gmv.png", "docs/figures/scalability_gmv.png"]),
    ]
    for mean_key, std_key, ylabel, title, yfmt, paths in panels:
        fig, ax = plt.subplots(figsize=(10, 5))
        for algo_name, cfg in ALGO_CONFIGS.items():
            s = summary[algo_name]
            xs, ys, es = _filtered(s[mean_key], s[std_key])
            ax.errorbar(xs, ys, yerr=es, label=algo_name, color=cfg["color"],
                        marker=cfg["marker"], linestyle=cfg["ls"],
                        linewidth=2, markersize=7, capsize=4)
        ax.set_xlabel("KOL Pool Size (N)", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=13)
        ax.legend(fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.4)
        if yfmt is not None:
            ax.yaxis.set_major_formatter(yfmt)
        fig.text(0.5, 0.01, _TS_NOTE, ha="center", fontsize=8.5, color="#666666")
        fig.tight_layout(rect=[0, 0.045, 1, 1])
        for path in paths:
            fig.savefig(path, dpi=150)
        plt.close(fig)
        print(f"[OK] {paths[1]}")


def run_scalability_experiment():
    os.makedirs("experiments/plots", exist_ok=True)
    os.makedirs("docs/figures", exist_ok=True)

    # results[algo_name][N] = {"times": [...], "gmvs": [...]}
    results = {name: {N: {"times": [], "gmvs": []} for N in POOL_SIZES}
               for name in ALGO_CONFIGS}

    for N in POOL_SIZES:
        print(f"\n{'─'*60}")
        print(f"  Pool size N = {N}")
        print(f"{'─'*60}")

        for i in range(REPEAT):
            seed = BASE_SEED + i
            kols = _gen_kols(N, seed)

            for algo_name, cfg in ALGO_CONFIGS.items():
                # Skip TS for large pools
                if algo_name == "Tabu Search" and N > TS_MAX_N:
                    continue
                elapsed, gmv = run_one(cfg["fn"], kols, BUDGET, seed)
                results[algo_name][N]["times"].append(elapsed)
                results[algo_name][N]["gmvs"].append(gmv)

            # Print one-line progress
            vals = " ".join(
                f"{name[:2]}={results[name][N]['gmvs'][-1]:>9,.0f}"
                for name in ALGO_CONFIGS
                if results[name][N]["gmvs"]
            )
            print(f"  seed={seed}  {vals}")

    # ── Write CSV ─────────────────────────────────────────────────
    csv_path = "experiments/plots/scalability_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["N", "Algorithm", "Mean_Time_Sec", "Std_Time_Sec", "Mean_GMV", "Std_GMV"])
        for algo_name in ALGO_CONFIGS:
            for N in POOL_SIZES:
                times = results[algo_name][N]["times"]
                gmvs  = results[algo_name][N]["gmvs"]
                if not times:
                    writer.writerow([N, algo_name, "—", "—", "—", "—"])
                    continue
                writer.writerow([
                    N, algo_name,
                    round(np.mean(times), 4), round(np.std(times), 4),
                    round(np.mean(gmvs),  2),  round(np.std(gmvs),  2),
                ])
    print(f"\n[OK] CSV → {csv_path}")

    # ── Compute summary arrays ────────────────────────────────────
    summary = {}
    for algo_name in ALGO_CONFIGS:
        summary[algo_name] = {
            "mean_times": [np.mean(results[algo_name][N]["times"]) if results[algo_name][N]["times"] else None for N in POOL_SIZES],
            "std_times":  [np.std( results[algo_name][N]["times"]) if results[algo_name][N]["times"] else None for N in POOL_SIZES],
            "mean_gmvs":  [np.mean(results[algo_name][N]["gmvs"])  if results[algo_name][N]["gmvs"]  else None for N in POOL_SIZES],
            "std_gmvs":   [np.std( results[algo_name][N]["gmvs"])  if results[algo_name][N]["gmvs"]  else None for N in POOL_SIZES],
        }

    make_plots(summary)

    # ── Summary table ─────────────────────────────────────────────
    print("\n" + "═" * 75)
    print(f"{'N':>6}  {'Algorithm':<22}  {'Time(s)':>10}  {'GMV':>12}")
    print("═" * 75)
    for N in POOL_SIZES:
        for algo_name in ALGO_CONFIGS:
            s = summary[algo_name]
            i = POOL_SIZES.index(N)
            t_val = s["mean_times"][i]
            g_val = s["mean_gmvs"][i]
            t_str = f"{t_val:>8.4f}s" if t_val is not None else "      —  "
            g_str = f"${g_val:>11,.0f}" if g_val is not None else "           —"
            print(f"{N:>6}  {algo_name:<22}  {t_str}  {g_str}")
        print("─" * 75)


if __name__ == "__main__":
    # `--plot-only` restyles/regenerates the figures from the existing CSV without
    # re-running the wall-clock-noisy benchmark (keeps the reported times stable).
    if "--plot-only" in sys.argv:
        make_plots(_summary_from_csv())
        print("[OK] Figures regenerated from", _CSV_PATH)
    else:
        run_scalability_experiment()
