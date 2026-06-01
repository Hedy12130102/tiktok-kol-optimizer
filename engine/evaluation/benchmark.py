# engine/evaluation/benchmark.py
"""
Benchmark — runs multiple algorithms on the same KOL pool and returns
a structured comparison dict.  Used by:
  - experiments/run_comparison.py  (convergence curves)
  - experiments/scalability.py     (time vs quality at different N)
  - backend /scalability endpoint

ALG-08: Add batch repeated experiment and CSV result export
"""
import time
import csv
import json
from statistics import mean, stdev
from typing import Dict, List, Optional

from engine.models import KOL
from engine.fitness import summarize_state
from engine.optimization.hill_climber import hill_climber
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.sa_improved import simulated_annealing_improved
from engine.optimization.random_search import random_search


def run_benchmark(
    kols: List[KOL],
    budget: float,
    seed: Optional[int] = 42,
    sa_kwargs: Optional[dict] = None,
    hc_kwargs: Optional[dict] = None,
    rs_kwargs: Optional[dict] = None,
) -> Dict[str, dict]:
    """
    Run all four algorithms on the same KOL pool and return results.

    Args:
        kols:       KOL candidate pool.
        budget:     Marketing budget (USD).
        seed:       Shared random seed for fair comparison.
        sa_kwargs:  Extra keyword args forwarded to simulated_annealing().
        hc_kwargs:  Extra keyword args forwarded to hill_climber().
        rs_kwargs:  Extra keyword args forwarded to random_search().

    Returns:
        Dict keyed by algorithm name, each value is:
        {
            "state":          List[int],
            "history":        List[float],
            "time_seconds":   float,
            "selected_count": int,
            "total_cost":     float,
            "total_gmv":      float,
            "roi":            float,
        }
    """
    sa_kwargs = sa_kwargs or {}
    hc_kwargs = hc_kwargs or {}
    rs_kwargs = rs_kwargs or {}

    results = {}

    # ── Simulated Annealing (standard) ────────────────────────────
    t0 = time.perf_counter()
    sa_state, _, sa_hist = simulated_annealing(kols, budget, seed=seed,** sa_kwargs)
    results["simulated_annealing"] = _pack(sa_state, sa_hist, kols, time.perf_counter() - t0)

    # ── Simulated Annealing (improved / swap) ─────────────────────
    t0 = time.perf_counter()
    sai_state, _, sai_hist = simulated_annealing_improved(kols, budget, seed=seed, **sai_kwargs)
    results["sa_improved"] = _pack(sai_state, sai_hist, kols, time.perf_counter() - t0)

    # ── Hill Climber ──────────────────────────────────────────────
    t0 = time.perf_counter()
    hc_state, _, hc_hist = hill_climber(kols, budget, seed=seed,** hc_kwargs)
    results["hill_climber"] = _pack(hc_state, hc_hist, kols, time.perf_counter() - t0)

    # ── Random Search ─────────────────────────────────────────────
    t0 = time.perf_counter()
    rs_state, _, rs_hist = random_search(kols, budget, seed=seed, rs_kwargs)
    results["random_search"] = _pack(rs_state, rs_hist, kols, time.perf_counter() - t0)

    return results


def _pack(state: List[int], history: List[float], kols: List[KOL], elapsed: float) -> dict:
    summary = summarize_state(state, kols)
    return {
        "state":          state,
        "history":        history,
        "time_seconds":   round(elapsed, 4),
        "selected_count": int(summary["selected_count"]),
        "total_cost":     round(summary["total_cost"], 2),
        "total_gmv":      round(summary["total_gmv"], 2),
        "roi":            round(summary["roi"], 4),
    }


# ===================== ALG-08 NEW FEATURE =====================
def export_benchmark_csv(
    kols: List[KOL],
    budget: float,
    run_times: int = 5,
    output_path: str = "docs/figures/algorithm_comparison.csv"
) -> None:
    """
    Conduct repeated benchmark experiments and export statistical data to CSV file.
    Include average GMV, GMV standard deviation, average runtime and average ROI.
    """
    algorithm_mapping = [
        ("simulated_annealing", "SA"),
        ("sa_improved", "SA-Improved"),
        ("hill_climber", "Hill-Climber"),
        ("random_search", "Random-Search")
    ]

    record_container = {alg_key: {"gmv":[], "time":[], "roi":[]} for alg_key, _ in algorithm_mapping}

    for idx in range(run_times):
        bench_res = run_benchmark(kols, budget, seed=idx)
        for alg_key, _ in algorithm_mapping:
            data = bench_res[alg_key]
            record_container[alg_key]["gmv"].append(data["total_gmv"])
            record_container[alg_key]["time"].append(data["time_seconds"])
            record_container[alg_key]["roi"].append(data["roi"])

    csv_rows = []
    for raw_key, display_name in algorithm_mapping:
        data = record_container[raw_key]
        avg_gmv = mean(data["gmv"])
        std_gmv = stdev(data["gmv"]) if len(data["gmv"]) > 1 else 0.0
        avg_time = mean(data["time"])
        avg_roi = mean(data["roi"])

        csv_rows.append({
            "algorithm": display_name,
            "avg_gmv": round(avg_gmv, 2),
            "std_gmv": round(std_gmv, 2),
            "avg_time": round(avg_time, 4),
            "avg_roi": round(avg_roi, 4)
        })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["algorithm", "avg_gmv", "std_gmv", "avg_time", "avg_roi"])
        writer.writeheader()
        writer.writerows(csv_rows)
