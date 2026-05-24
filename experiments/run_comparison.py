import json, matplotlib.pyplot as plt
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.models import KOL
from engine.simulated_annealing import simulated_annealing
from engine.hill_climber import hill_climber
from engine.random_search import random_search

def load_kols(path="data/sample_kols.json") -> list:
    with open(path) as f:
        return [KOL(**d) for d in json.load(f)]

def run_experiment(budget=5000.0):
    kols = load_kols()
    print("Running Simulated Annealing...")
    _, _, sa_hist = simulated_annealing(kols, budget)
    print("Running Hill Climber...")
    _, _, hc_hist = hill_climber(kols, budget)
    print("Running Random Search...")
    _, _, rs_hist = random_search(kols, budget)

    # Unify length (truncate to shortest)
    min_len = min(len(sa_hist), len(hc_hist), len(rs_hist))

    os.makedirs("experiments/plots", exist_ok=True)
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
    print("Chart saved to experiments/plots/convergence.png")

if __name__ == "__main__":
    run_experiment()
