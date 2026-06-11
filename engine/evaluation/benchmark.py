# engine/evaluation/benchmark.py
"""
Benchmark — runs all six algorithms on the same KOL pool and returns
a structured comparison dict.  Used by:
  - experiments/run_comparison.py  (convergence curves)
  - experiments/scalability.py     (time vs quality at different N)
  - backend /scalability endpoint
"""
import time
import csv
from statistics import mean, stdev
from typing import Dict, List, Optional

from engine.models import KOL
from engine.fitness import summarize_state
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.hill_climber import hill_climber
from engine.optimization.random_search import random_search
from engine.optimization.genetic_algorithm import genetic_algorithm
from engine.optimization.tabu_search import tabu_search
from engine.optimization.greedy_ranking import greedy_ranking


def run_benchmark(
    kols: List[KOL],
    budget: float,
    seed: Optional[int] = 42,
    sa_kwargs:  Optional[dict] = None,
    hc_kwargs:  Optional[dict] = None,
    rs_kwargs:  Optional[dict] = None,
    ga_kwargs:  Optional[dict] = None,
    ts_kwargs:  Optional[dict] = None,
    gr_kwargs:  Optional[dict] = None,
) -> Dict[str, dict]:
    """
    Run all six algorithms on the same KOL pool and return results.

    Args:
        kols:       KOL candidate pool.
        budget:     Marketing budget (USD).
        seed:       Shared random seed for fair comparison.
        sa/hc/rs/ga/ts/gr_kwargs: Extra kwargs forwarded to each algorithm.

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
    ga_kwargs = ga_kwargs or {}
    ts_kwargs = ts_kwargs or {}
    gr_kwargs = gr_kwargs or {}

    results = {}

    # ── Simulated Annealing ───────────────────────────────────────
    t0 = time.perf_counter()
    sa_state, _, sa_hist = simulated_annealing(kols, budget, seed=seed, **sa_kwargs)
    results["simulated_annealing"] = _pack(sa_state, sa_hist, kols, time.perf_counter() - t0)

    # ── Hill Climber ──────────────────────────────────────────────
    t0 = time.perf_counter()
    hc_state, _, hc_hist = hill_climber(kols, budget, seed=seed, **hc_kwargs)
    results["hill_climber"] = _pack(hc_state, hc_hist, kols, time.perf_counter() - t0)

    # ── Random Search ─────────────────────────────────────────────
    t0 = time.perf_counter()
    rs_state, _, rs_hist = random_search(kols, budget, seed=seed, **rs_kwargs)
    results["random_search"] = _pack(rs_state, rs_hist, kols, time.perf_counter() - t0)

    # ── Genetic Algorithm ─────────────────────────────────────────
    t0 = time.perf_counter()
    ga_state, _, ga_hist = genetic_algorithm(kols, budget, seed=seed, **ga_kwargs)
    results["genetic_algorithm"] = _pack(ga_state, ga_hist, kols, time.perf_counter() - t0)

    # ── Tabu Search ───────────────────────────────────────────────
    t0 = time.perf_counter()
    ts_state, _, ts_hist = tabu_search(kols, budget, seed=seed, **ts_kwargs)
    results["tabu_search"] = _pack(ts_state, ts_hist, kols, time.perf_counter() - t0)

    # ── Greedy Ranking ────────────────────────────────────────────
    t0 = time.perf_counter()
    gr_state, _, gr_hist = greedy_ranking(kols, budget, seed=seed, **gr_kwargs)
    results["greedy_ranking"] = _pack(gr_state, gr_hist, kols, time.perf_counter() - t0)

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


def export_benchmark_csv(
    kols: List[KOL],
    budget: float,
    run_times: int = 5,
    output_path: str = "docs/figures/algorithm_comparison.csv",
) -> None:
    """
    Repeated benchmark experiments with statistical aggregation → CSV.
    Includes mean GMV, GMV std-dev, mean runtime, and mean ROI per algorithm.
    """
    algo_keys = [
        ("simulated_annealing", "SA"),
        ("hill_climber",        "Hill-Climber"),
        ("random_search",       "Random-Search"),
        ("genetic_algorithm",   "GA"),
        ("tabu_search",         "Tabu-Search"),
        ("greedy_ranking",      "Greedy-Ranking"),
    ]

    records = {key: {"gmv": [], "time": [], "roi": []} for key, _ in algo_keys}

    for idx in range(run_times):
        bench = run_benchmark(kols, budget, seed=idx)
        for key, _ in algo_keys:
            d = bench[key]
            records[key]["gmv"].append(d["total_gmv"])
            records[key]["time"].append(d["time_seconds"])
            records[key]["roi"].append(d["roi"])

    rows = []
    for key, display in algo_keys:
        d = records[key]
        rows.append({
            "algorithm": display,
            "avg_gmv":   round(mean(d["gmv"]), 2),
            "std_gmv":   round(stdev(d["gmv"]) if len(d["gmv"]) > 1 else 0.0, 2),
            "avg_time":  round(mean(d["time"]), 4),
            "avg_roi":   round(mean(d["roi"]), 4),
        })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["algorithm", "avg_gmv", "std_gmv", "avg_time", "avg_roi"])
        writer.writeheader()
        writer.writerows(rows)
