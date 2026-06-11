import csv
import json
import matplotlib.pyplot as plt
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.hill_climber import hill_climber
from engine.optimization.random_search import random_search
from engine.optimization.genetic_algorithm import genetic_algorithm
from engine.optimization.tabu_search import tabu_search
from engine.optimization.greedy_ranking import greedy_ranking
from engine.fitness import summarize_state

ALGO_COLORS = {
    "Simulated Annealing": "#1D9E75",
    "Hill Climber":        "#D85A30",
    "Random Search":       "#888780",
    "Genetic Algorithm":   "#4A90D9",
    "Tabu Search":         "#9B59B6",
    "Greedy Ranking":      "#F39C12",
}


def load_kols(path="data/sample_kols.json") -> list:
    with open(path, encoding="utf-8") as f:
        return [KOL(**d) for d in json.load(f)]


def classroom_trap_case() -> list:
    """Small scenario where hill climber gets trapped by a costly Macro KOL.

    Uses keyword arguments and the commission-rate cost model:
        cost = commission_rate × expected_gmv()
    """
    kols = [
        KOL(id=1, name="ID Mid Beauty A",   country="ID", category="beauty",  followers=650_000, engagement_rate=0.10, fit_score=1.00, commission_rate=0.15),
        KOL(id=2, name="ID Macro Beauty",   country="ID", category="beauty",  followers=900_000, engagement_rate=0.10, fit_score=1.00, commission_rate=0.15),
        KOL(id=3, name="ID Mid Beauty B",   country="ID", category="beauty",  followers=640_000, engagement_rate=0.10, fit_score=1.00, commission_rate=0.15),
        KOL(id=4, name="MY Micro Beauty",   country="MY", category="beauty",  followers=180_000, engagement_rate=0.12, fit_score=0.80, commission_rate=0.12),
        KOL(id=5, name="TH Fashion Nano",   country="TH", category="fashion", followers=260_000, engagement_rate=0.08, fit_score=0.70, commission_rate=0.12),
        KOL(id=6, name="PH Fashion Live",   country="PH", category="fashion", followers=220_000, engagement_rate=0.09, fit_score=0.75, commission_rate=0.12),
        KOL(id=7, name="MY Beauty Niche",   country="MY", category="beauty",  followers=120_000, engagement_rate=0.11, fit_score=0.85, commission_rate=0.10),
        KOL(id=8, name="ID Budget Creator", country="ID", category="beauty",  followers= 90_000, engagement_rate=0.10, fit_score=0.80, commission_rate=0.10),
    ]
    # Compute cost = commission_rate × expected_gmv (commission-based model)
    for k in kols:
        k.cost = round(k.commission_rate * k.expected_gmv(), 2)
    return kols


def run_experiment(budget=5000.0, seed=42, use_demo_case=True):
    kols = classroom_trap_case() if use_demo_case else load_kols()

    print("Running all 6 algorithms...")
    sa_state, _, sa_hist = simulated_annealing(kols, budget, seed=seed)
    hc_state, _, hc_hist = hill_climber(kols, budget, seed=seed)
    rs_state, _, rs_hist = random_search(kols, budget, seed=seed)
    ga_state, _, ga_hist = genetic_algorithm(kols, budget, seed=seed)
    ts_state, _, ts_hist = tabu_search(kols, budget, seed=seed)
    gr_state, _, gr_hist = greedy_ranking(kols, budget, seed=seed)

    all_hists = {
        "Simulated Annealing": sa_hist,
        "Hill Climber":        hc_hist,
        "Random Search":       rs_hist,
        "Genetic Algorithm":   ga_hist,
        "Tabu Search":         ts_hist,
        "Greedy Ranking":      gr_hist,
    }

    os.makedirs("experiments/plots", exist_ok=True)
    os.makedirs("docs/figures", exist_ok=True)

    # ── Convergence chart ─────────────────────────────────────────
    min_len = min(len(h) for h in all_hists.values())
    plt.figure(figsize=(11, 5))
    for name, hist in all_hists.items():
        plt.plot(hist[:min_len], label=name, color=ALGO_COLORS[name], linewidth=1.8)
    plt.xlabel("Iterations")
    plt.ylabel("Best GMV (USD)")
    plt.title("Algorithm Convergence Comparison (demo pool, commission-rate model)")
    plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    plt.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig("experiments/plots/convergence.png", dpi=150)
    plt.savefig("docs/figures/convergence.png", dpi=150)
    plt.close()
    print("Convergence chart saved.")

    # ── Summary CSV ───────────────────────────────────────────────
    all_states = {
        "Simulated Annealing": sa_state,
        "Hill Climber":        hc_state,
        "Random Search":       rs_state,
        "Genetic Algorithm":   ga_state,
        "Tabu Search":         ts_state,
        "Greedy Ranking":      gr_state,
    }
    rows = []
    for name, state in all_states.items():
        s = summarize_state(state, kols)
        rows.append({
            "algorithm":      name,
            "selected_count": int(s["selected_count"]),
            "total_cost":     round(s["total_cost"], 2),
            "total_gmv":      round(s["total_gmv"], 2),
            "roi":            round(s["roi"], 4),
        })

    csv_path = "experiments/plots/comparison_summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV saved → {csv_path}")

    print("\nSummary (sorted by GMV)")
    for row in sorted(rows, key=lambda r: r["total_gmv"], reverse=True):
        print(
            f"  {row['algorithm']:<22}: GMV=${row['total_gmv']:>10,.0f}  "
            f"cost=${row['total_cost']:>8,.0f}  KOLs={row['selected_count']}  ROI={row['roi']:.2f}"
        )


if __name__ == "__main__":
    run_experiment()
