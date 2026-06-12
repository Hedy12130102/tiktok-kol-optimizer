# experiments/gen_figures.py
"""
Generate all docs/figures/ charts that previously lacked a script.

Figures produced
----------------
  docs/figures/algo_comparison_bars.png   — side-by-side bar chart at N=20/50/100
  docs/figures/convergence_panels.png     — 3-panel convergence at N=20/50/100
  docs/figures/tier_distribution.png      — KOL tier distribution pie + bar
  docs/figures/sensitivity_heatmap.png    — SA parameter sensitivity (T0 × alpha)

Run from project root:
    python experiments/gen_figures.py
"""

import json
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from data.generator import generate_kols
from engine.models import KOL
from engine.fitness import summarize_state
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.hill_climber import hill_climber
from engine.optimization.random_search import random_search
from engine.optimization.genetic_algorithm import genetic_algorithm
from engine.optimization.tabu_search import tabu_search
from engine.optimization.greedy_ranking import greedy_ranking

os.makedirs("docs/figures", exist_ok=True)
os.makedirs("experiments/plots", exist_ok=True)

ALGO_META = {
    "GA":  {"fn": genetic_algorithm,   "color": "#4A90D9"},
    "TS":  {"fn": tabu_search,         "color": "#9B59B6"},
    "SA":  {"fn": simulated_annealing, "color": "#1D9E75"},
    "GR":  {"fn": greedy_ranking,      "color": "#F39C12"},
    "HC":  {"fn": hill_climber,        "color": "#D85A30"},
    "RS":  {"fn": random_search,       "color": "#888780"},
}

SEED = 42


def _kols(n: int) -> list:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as jf, \
         tempfile.NamedTemporaryFile(suffix=".csv",  delete=False) as cf:
        jpath, cpath = jf.name, cf.name
    dicts = generate_kols(num=n, json_output_path=jpath, csv_output_path=cpath, seed=SEED)
    os.unlink(jpath); os.unlink(cpath)
    return [KOL(**d) for d in dicts]


def _run_all(kols, budget, skip_ts=False):
    """Return {abbrev: (state, hist)} for all algorithms."""
    out = {}
    for abbrev, meta in ALGO_META.items():
        if skip_ts and abbrev == "TS":
            continue
        state, _, hist = meta["fn"](kols, budget, seed=SEED)
        out[abbrev] = (state, hist)
    return out


# ─────────────────────────────────────────────────────────────────
# Figure 1: algo_comparison_bars.png
# Side-by-side grouped bar chart at N = 20, 50, 100
# ─────────────────────────────────────────────────────────────────
def gen_algo_comparison_bars():
    pool_sizes = [20, 50, 100]
    budgets    = {20: 500, 50: 1_250, 100: 2_500}

    gmv_data = {abbrev: [] for abbrev in ALGO_META}

    for N in pool_sizes:
        kols   = _kols(N)
        budget = N * 25
        results = _run_all(kols, budget, skip_ts=(N > 100))
        for abbrev in ALGO_META:
            if abbrev in results:
                gmv = summarize_state(results[abbrev][0], kols)["total_gmv"]
            else:
                gmv = None
            gmv_data[abbrev].append(gmv)

    x     = np.arange(len(pool_sizes))
    width = 0.13
    offsets = np.linspace(-2.5, 2.5, len(ALGO_META)) * width

    fig, ax = plt.subplots(figsize=(11, 6))
    for (abbrev, meta), offset in zip(ALGO_META.items(), offsets):
        vals = [v if v is not None else 0 for v in gmv_data[abbrev]]
        bars = ax.bar(x + offset, vals, width, label=abbrev, color=meta["color"], alpha=0.85)
        for bar, v in zip(bars, gmv_data[abbrev]):
            if v is None:
                ax.text(bar.get_x() + bar.get_width() / 2, 50,
                        "—", ha="center", va="bottom", fontsize=7, color="#aaa")

    ax.set_xlabel("KOL Pool Size (N)", fontsize=12)
    ax.set_ylabel("Best Predicted GMV (USD)", fontsize=12)
    ax.set_title("Algorithm Comparison — Solution Quality at N = 20, 50, 100", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([f"N={n}\nbudget=${budgets[n]:,}" for n in pool_sizes])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.legend(fontsize=10, title="Algorithm")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    path = "docs/figures/algo_comparison_bars.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[OK] {path}")


# ─────────────────────────────────────────────────────────────────
# Figure 2: convergence_panels.png
# 3-panel convergence plot at N = 20, 50, 100
# ─────────────────────────────────────────────────────────────────
def gen_convergence_panels():
    pool_sizes = [20, 50, 100]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for ax, N in zip(axes, pool_sizes):
        kols    = _kols(N)
        budget  = N * 25
        results = _run_all(kols, budget, skip_ts=(N > 100))

        for abbrev, (_, hist) in results.items():
            ax.plot(hist, label=abbrev, color=ALGO_META[abbrev]["color"],
                    linewidth=1.6, alpha=0.9)

        ax.set_title(f"N = {N}  (budget = ${N*25:,})", fontsize=11)
        ax.set_xlabel("Iterations", fontsize=10)
        ax.set_ylabel("Best GMV (USD)", fontsize=10)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        ax.grid(True, linestyle="--", alpha=0.35)
        ax.legend(fontsize=8)

    fig.suptitle("Convergence Comparison — Three Pool Sizes", fontsize=14, fontweight="bold")
    fig.tight_layout()
    path = "docs/figures/convergence_panels.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[OK] {path}")


# ─────────────────────────────────────────────────────────────────
# Figure 3: tier_distribution.png
# Pie + bar chart of the generated KOL dataset
# ─────────────────────────────────────────────────────────────────
def gen_tier_distribution():
    # Use the real sample_kols.json if present, else generate
    json_path = "data/sample_kols.json"
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as f:
            raw = json.load(f)
        kols = [KOL(**d) for d in raw]
    else:
        dicts = generate_kols(num=300, json_output_path=None, csv_output_path=None, seed=SEED)
        kols  = [KOL(**d) for d in dicts]

    TIERS = ["Mega", "Macro", "Micro", "Nano"]
    TIER_COLORS = {"Mega": "#9B59B6", "Macro": "#4A90D9", "Micro": "#1D9E75", "Nano": "#F39C12"}

    tier_counts = {t: sum(1 for k in kols if k.tier == t) for t in TIERS}
    category_counts = {}
    for k in kols:
        category_counts.setdefault(k.category, {t: 0 for t in TIERS})
        category_counts[k.category][k.tier] += 1

    fig = plt.figure(figsize=(13, 5))
    gs  = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[1, 1.4])

    # --- Left: pie chart ---
    ax_pie = fig.add_subplot(gs[0])
    counts = [tier_counts[t] for t in TIERS]
    colors = [TIER_COLORS[t] for t in TIERS]
    wedges, texts, autotexts = ax_pie.pie(
        counts, labels=TIERS, colors=colors,
        autopct="%1.0f%%", startangle=140,
        textprops={"fontsize": 11}, pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(10)
    ax_pie.set_title(f"Tier Distribution  (N={len(kols)})", fontsize=12, fontweight="bold")

    # --- Right: stacked bar by category ---
    ax_bar = fig.add_subplot(gs[1])
    cats = sorted(category_counts.keys())
    bottoms = np.zeros(len(cats))
    for tier in TIERS:
        vals = [category_counts[c][tier] for c in cats]
        ax_bar.bar(cats, vals, bottom=bottoms, color=TIER_COLORS[tier], label=tier, alpha=0.85)
        bottoms += np.array(vals)

    ax_bar.set_xlabel("Category", fontsize=11)
    ax_bar.set_ylabel("Number of KOLs", fontsize=11)
    ax_bar.set_title("Tier Distribution by Category", fontsize=12, fontweight="bold")
    ax_bar.legend(title="Tier", fontsize=10)
    ax_bar.grid(True, axis="y", linestyle="--", alpha=0.4)

    fig.tight_layout()
    path = "docs/figures/tier_distribution.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[OK] {path}")


# ─────────────────────────────────────────────────────────────────
# Figure 4: sensitivity_heatmap.png
# SA parameter sensitivity: T0 × alpha → GMV at N=100
# ─────────────────────────────────────────────────────────────────
def gen_sensitivity_heatmap():
    N      = 100
    budget = N * 25
    kols   = _kols(N)

    T0_VALUES    = [500, 1_000, 5_000, 10_000, 50_000, 100_000]
    ALPHA_VALUES = [0.90, 0.92, 0.95, 0.97, 0.99]

    grid = np.zeros((len(ALPHA_VALUES), len(T0_VALUES)))

    for i, alpha in enumerate(ALPHA_VALUES):
        for j, T0 in enumerate(T0_VALUES):
            state, _, _ = simulated_annealing(
                kols, budget, seed=SEED, T0=T0, alpha=alpha
            )
            grid[i, j] = summarize_state(state, kols)["total_gmv"]
        print(f"  alpha={alpha}  done")

    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(grid, aspect="auto", cmap="YlGn", origin="lower")

    ax.set_xticks(range(len(T0_VALUES)))
    ax.set_xticklabels([f"{v:,}" for v in T0_VALUES], fontsize=10)
    ax.set_yticks(range(len(ALPHA_VALUES)))
    ax.set_yticklabels([str(a) for a in ALPHA_VALUES], fontsize=10)
    ax.set_xlabel("Initial Temperature T₀", fontsize=12)
    ax.set_ylabel("Cooling Rate α", fontsize=12)
    ax.set_title("SA Parameter Sensitivity — Best GMV (N=100, budget=$2,500)", fontsize=13)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Best GMV (USD)", fontsize=11)
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))

    # Annotate cells
    for i in range(len(ALPHA_VALUES)):
        for j in range(len(T0_VALUES)):
            ax.text(j, i, f"${grid[i,j]:,.0f}", ha="center", va="center",
                    fontsize=7.5, color="black" if grid[i,j] > grid.max()*0.6 else "dimgray")

    fig.tight_layout()
    path = "docs/figures/sensitivity_heatmap.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[OK] {path}")


if __name__ == "__main__":
    print("=== Generating figures ===\n")
    print("1/4  algo_comparison_bars.png ...")
    gen_algo_comparison_bars()
    print("2/4  convergence_panels.png ...")
    gen_convergence_panels()
    print("3/4  tier_distribution.png ...")
    gen_tier_distribution()
    print("4/4  sensitivity_heatmap.png (slow — SA grid search) ...")
    gen_sensitivity_heatmap()
    print("\nAll figures saved to docs/figures/")
