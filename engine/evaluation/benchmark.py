# engine/evaluation/benchmark.py
"""
Benchmark — runs multiple algorithms on the same KOL pool and returns
a structured comparison dict.  Used by:
  - experiments/run_comparison.py  (convergence curves)
  - experiments/scalability.py     (time vs quality at different N)
  - backend /scalability endpoint
"""
import time
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
    sa_state, _, sa_hist = simulated_annealing(kols, budget, seed=seed, **sa_kwargs)
    results["simulated_annealing"] = _pack(sa_state, sa_hist, kols, time.perf_counter() - t0)

    # ── Simulated Annealing (improved / swap) ─────────────────────
    t0 = time.perf_counter()
    sai_state, _, sai_hist = simulated_annealing_improved(kols, budget, seed=seed, **sa_kwargs)
    results["sa_improved"] = _pack(sai_state, sai_hist, kols, time.perf_counter() - t0)

    # ── Hill Climber ──────────────────────────────────────────────
    t0 = time.perf_counter()
    hc_state, _, hc_hist = hill_climber(kols, budget, seed=seed, **hc_kwargs)
    results["hill_climber"] = _pack(hc_state, hc_hist, kols, time.perf_counter() - t0)

    # ── Random Search ─────────────────────────────────────────────
    t0 = time.perf_counter()
    rs_state, _, rs_hist = random_search(kols, budget, seed=seed, **rs_kwargs)
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