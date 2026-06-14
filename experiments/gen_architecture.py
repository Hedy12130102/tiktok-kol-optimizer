"""
System Architecture Diagram
===========================
Renders a layered architecture diagram of the KOL Optimizer to
`docs/figures/system_architecture.png` (and a copy in experiments/plots/).

Pure matplotlib (no Graphviz/dot dependency) so it regenerates anywhere the
rest of the figure pipeline runs.

Run:  python experiments/gen_architecture.py
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ── Palette ───────────────────────────────────────────────────────
C_CLIENT = "#0FB5AE"   # teal
C_API    = "#4A90D9"   # blue
C_ENGINE = "#1D9E75"   # green
C_DATA   = "#F39C12"   # amber
C_EXT    = "#9B59B6"   # purple (roadmap stubs)
BAND     = {"client": "#E9FbFA", "api": "#EAF2FB", "engine": "#E9F7F1", "data": "#FDF3E0"}
INK      = "#1F2933"
SUBINK   = "#52606D"


def box(ax, x, y, w, h, title, sub=None, fc="#FFFFFF", ec="#CBD2D9", title_color=INK, fs=10.5):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
        linewidth=1.4, edgecolor=ec, facecolor=fc, zorder=3))
    cy = y + h / 2 + (0.16 if sub else 0)
    ax.text(x + w / 2, cy, title, ha="center", va="center",
            fontsize=fs, fontweight="bold", color=title_color, zorder=4)
    if sub:
        ax.text(x + w / 2, y + h / 2 - 0.20, sub, ha="center", va="center",
                fontsize=8.4, color=SUBINK, zorder=4)


def band(ax, x, y, w, h, label, color):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.10",
        linewidth=0, facecolor=color, zorder=1))
    ax.text(x + 0.12, y + h - 0.16, label, ha="left", va="top",
            fontsize=9.5, fontweight="bold", color="#7B8794", zorder=2)


def arrow(ax, p0, p1, color=SUBINK, lw=1.6, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle=style, mutation_scale=14, linewidth=lw,
        color=color, linestyle=ls, zorder=5,
        shrinkA=2, shrinkB=2, connectionstyle="arc3,rad=0"))


def main():
    os.makedirs("docs/figures", exist_ok=True)
    os.makedirs("experiments/plots", exist_ok=True)

    fig, ax = plt.subplots(figsize=(12.6, 9.4))
    ax.set_xlim(0, 12.6)
    ax.set_ylim(0, 10.2)
    ax.axis("off")

    ax.text(0.2, 9.95, "TikTok Shop KOL Matrix Optimizer — System Architecture",
            ha="left", va="top", fontsize=15, fontweight="bold", color=INK)

    # ── Bands ─────────────────────────────────────────────────────
    band(ax, 0.2, 8.35, 9.6, 1.30, "CLIENT", BAND["client"])
    band(ax, 0.2, 6.05, 12.2, 1.95, "API  ·  FastAPI (serves the SPA + typed REST)", BAND["api"])
    band(ax, 0.2, 3.30, 9.6, 2.45, "OPTIMIZATION ENGINE  ·  pure Python", BAND["engine"])
    band(ax, 0.2, 0.55, 12.2, 2.40, "DATA  ·  JSON persistence + data prep", BAND["data"])

    # ── Client layer ──────────────────────────────────────────────
    box(ax, 0.5, 8.55, 9.0, 0.92,
        "Browser SPA  —  frontend/index.html  (vanilla JS · Tailwind CSS)",
        "Landing  ·  Optimizer  ·  Creators  ·  Campaigns  ·  Creator Pool Simulator",
        fc="#FFFFFF", ec=C_CLIENT, title_color=C_CLIENT)

    # ── API layer ─────────────────────────────────────────────────
    box(ax, 0.5, 6.35, 3.0, 1.35, "backend/main.py",
        "/optimize · /simulate-scale\n/kols · /kol · /top-kols", ec=C_API, title_color=C_API)
    box(ax, 3.75, 6.35, 3.0, 1.35, "backend/crud.py",
        "/kols add·edit·import\n/backfill-costs · /reset · history", ec=C_API, title_color=C_API)
    box(ax, 7.0, 6.35, 2.7, 1.35, "backend/campaigns.py",
        "save · list · record\nactual GMV (attribution)", ec=C_API, title_color=C_API)

    # External roadmap stubs (right rail in API band)
    box(ax, 9.95, 6.35, 2.3, 1.35, "Integration stubs",
        "TikTok Creator Mktplace\nTikTok Shop · 3rd-party\n(roadmap)", ec=C_EXT, title_color=C_EXT)

    # ── Engine layer ──────────────────────────────────────────────
    box(ax, 0.5, 4.55, 4.4, 1.05, "engine/optimization/",
        "SA · HC · RS · GA · Tabu · Greedy Ranking", ec=C_ENGINE, title_color=C_ENGINE)
    box(ax, 5.15, 4.55, 4.35, 1.05, "engine/scoring/",
        "CreatorScore · Explainer · ROI", ec=C_ENGINE, title_color=C_ENGINE)
    box(ax, 0.5, 3.45, 4.4, 0.95, "engine/fitness.py",
        "objective + budget/overlap penalty", ec=C_ENGINE, title_color=C_ENGINE)
    box(ax, 5.15, 3.45, 4.35, 0.95, "engine/models.py",
        "KOL · tiers · SEA GMV model · shortlist (top-K)", ec=C_ENGINE, title_color=C_ENGINE)

    # ── Data layer ────────────────────────────────────────────────
    box(ax, 0.5, 1.85, 2.7, 0.95, "sample_kols.json", "active library (430)", ec=C_DATA, title_color="#B9770E")
    box(ax, 3.45, 1.85, 2.6, 0.95, "seed_kols.json", "reset baseline", ec=C_DATA, title_color="#B9770E")
    box(ax, 6.30, 1.85, 2.5, 0.95, "kol_history.json", "metric snapshots", ec=C_DATA, title_color="#B9770E")
    box(ax, 9.05, 1.85, 3.0, 0.95, "campaigns.json", "attribution records", ec=C_DATA, title_color="#B9770E")
    box(ax, 0.5, 0.75, 11.5, 0.85,
        "data prep:  build_seed.py (real FastMoss CSV/Excel)   →   fill_slices.py (synthetic slice fill)   ·   generator.py (synthetic pools)",
        ec="#D9A23B", title_color="#946200", fs=9.8)

    # ── Flow arrows ───────────────────────────────────────────────
    # Client <-> API (HTTP/JSON), and FastAPI serves the SPA back (static)
    arrow(ax, (4.3, 8.55), (4.3, 7.72), color=C_API, lw=2.0)
    ax.text(4.45, 8.18, "HTTP / JSON", ha="left", va="center", fontsize=9, color=C_API, fontweight="bold")
    arrow(ax, (5.6, 7.72), (5.6, 8.55), color="#9AA5B1", lw=1.4, ls=(0, (4, 3)))
    ax.text(5.75, 8.18, "serves SPA (static)", ha="left", va="center", fontsize=8.2, color="#7B8794")

    # API -> Engine (function calls)
    arrow(ax, (2.0, 6.35), (2.5, 5.60), color=C_ENGINE, lw=1.8)
    arrow(ax, (5.0, 6.35), (6.0, 5.60), color=C_ENGINE, lw=1.8)
    ax.text(3.0, 5.95, "in-process calls", ha="center", va="center", fontsize=8.6,
            color=C_ENGINE, fontweight="bold")

    # crud/campaigns -> Engine reference too (scoring used by /kols, /top-kols)
    # Engine -> Data (reads)
    arrow(ax, (2.6, 3.45), (2.2, 2.80), color=C_DATA, lw=1.7)
    ax.text(2.9, 3.08, "read", ha="left", va="center", fontsize=8.4, color="#B9770E", fontweight="bold")

    # API (crud/campaigns) -> Data (read/write), routed down the right side
    arrow(ax, (5.25, 6.35), (5.25, 5.62), color="#9AA5B1", lw=0.0, style="-")  # spacer (no-op visual)
    arrow(ax, (10.5, 6.35), (10.5, 2.82), color=C_DATA, lw=1.7)
    ax.text(10.65, 4.6, "read / write\n(CRUD · attribution)", ha="left", va="center",
            fontsize=8.4, color="#B9770E", fontweight="bold")

    # data prep -> stores
    arrow(ax, (3.0, 1.60), (2.0, 1.85), color="#946200", lw=1.4)
    arrow(ax, (5.0, 1.60), (4.6, 1.85), color="#946200", lw=1.4)

    # left-margin "request flow" guide
    ax.annotate("", xy=(0.06, 1.0), xytext=(0.06, 9.0),
                arrowprops=dict(arrowstyle="-|>", color="#CBD2D9", lw=2))
    ax.text(0.12, 5.0, "request flow", rotation=90, ha="center", va="center",
            fontsize=8.6, color="#9AA5B1")

    fig.tight_layout()
    for path in ["docs/figures/system_architecture.png",
                 "experiments/plots/system_architecture.png"]:
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("[OK] Architecture diagram -> docs/figures/system_architecture.png")


if __name__ == "__main__":
    main()
