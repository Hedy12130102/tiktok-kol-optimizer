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
from engine.fitness import summarize_state

def load_kols(path="data/sample_kols.json") -> list:
    with open(path, encoding="utf-8") as f:
        return [KOL(**d) for d in json.load(f)]

def classroom_trap_case() -> list:
    """Small scenario where a one-bit hill climber can get stuck on a costly macro KOL."""
    return [
        KOL(1, "ID Mid Beauty A", "ID", "beauty", 650000, 0.10, 1.00, 2500),
        KOL(2, "ID Macro Beauty", "ID", "beauty", 900000, 0.10, 1.00, 5000),
        KOL(3, "ID Mid Beauty B", "ID", "beauty", 640000, 0.10, 1.00, 2500),
        KOL(4, "MY Micro Beauty", "MY", "beauty", 180000, 0.12, 0.80, 900),
        KOL(5, "TH Tech Reviewer", "TH", "tech", 260000, 0.08, 0.70, 1200),
        KOL(6, "PH Fashion Live", "PH", "fashion", 220000, 0.09, 0.75, 1100),
        KOL(7, "MY Beauty Niche", "MY", "beauty", 120000, 0.11, 0.85, 750),
        KOL(8, "ID Budget Creator", "ID", "beauty", 90000, 0.10, 0.80, 500),
    ]

def run_experiment(budget=5000.0, seed=42, use_demo_case=True):
    kols = classroom_trap_case() if use_demo_case else load_kols()
    print("Running Simulated Annealing...")
    sa_state, _, sa_hist = simulated_annealing(kols, budget, seed=seed)
    print("Running Hill Climber...")
    hc_state, _, hc_hist = hill_climber(kols, budget, seed=seed)
    print("Running Random Search...")
    rs_state, _, rs_hist = random_search(kols, budget, max_iter=100, seed=seed)

    # Unify length (truncate to shortest)
    min_len = min(len(sa_hist), len(hc_hist), len(rs_hist))

    os.makedirs("experiments/plots", exist_ok=True)
    os.makedirs("docs/figures", exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(sa_hist[:min_len], label="Simulated Annealing", color="#1D9E75")
    plt.plot(hc_hist[:min_len], label="Hill Climber",         color="#D85A30")
    plt.plot(rs_hist[:min_len], label="Random Search",        color="#888780")
    plt.xlabel("Iterations")
    plt.ylabel("Best GMV (USD)")
    plt.title("Algorithm Convergence Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig("experiments/plots/convergence.png", dpi=150)
    plt.savefig("docs/figures/convergence.png", dpi=150)
    print("Chart saved to experiments/plots/convergence.png")

    rows = []
    for name, state in [
        ("Simulated Annealing", sa_state),
        ("Hill Climber", hc_state),
        ("Random Search", rs_state),
    ]:
        summary = summarize_state(state, kols)
        rows.append(
            {
                "algorithm": name,
                "selected_count": int(summary["selected_count"]),
                "total_cost": round(summary["total_cost"], 2),
                "total_gmv": round(summary["total_gmv"], 2),
                "roi": round(summary["roi"], 4),
            }
        )

    with open("experiments/plots/comparison_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("\nSummary")
    for row in sorted(rows, key=lambda item: item["total_gmv"], reverse=True):
        print(
            f"{row['algorithm']}: GMV=${row['total_gmv']:,.0f}, "
            f"cost=${row['total_cost']:,.0f}, KOLs={row['selected_count']}, ROI={row['roi']:.2f}"
        )

if __name__ == "__main__":
    run_experiment()
