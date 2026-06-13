# 🎯 TikTok Shop KOL Matrix Optimizer

**Turn a fixed influencer budget into the highest-GMV creator portfolio — powered by six competing optimization algorithms, explainable AI, and closed-loop campaign attribution.**

[![CI](https://github.com/Hedy12130102/tiktok-kol-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/Hedy12130102/tiktok-kol-optimizer/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/tests-110%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

For Southeast-Asia TikTok Shop merchants and agencies who must allocate a marketing budget across hundreds of creators — and **prove the ROI afterwards**. The system filters the creator pool by market and category, runs **six optimization algorithms in parallel** to maximize predicted GMV, explains *why* each creator was chosen, and tracks predicted-vs-actual GMV so every campaign sharpens the next.

> **▶ Live demo:** `start_server.bat` (Windows) or `uvicorn backend.main:app --reload`, then open **http://localhost:8000/ui**

---

## 💡 Why It Matters

A brand with 100 candidate creators and a budget that fits 5–8 of them faces **2¹⁰⁰ possible portfolios** — far beyond spreadsheets or gut feel. And picking the single biggest influencer is usually the *wrong* move: under TikTok Shop's commission model a mega-creator is both the most expensive *and* the least cost-efficient hire. The winning play is a **mixed-tier portfolio** of micro + nano creators that no manual shortlist reliably finds.

| Without this tool | With this tool |
|---|---|
| Manual shortlists, gut feel | Six algorithms compete; the best portfolio wins |
| Overspend on one mega-KOL | Budget-optimal mixed-tier mix, every dollar inside budget |
| "Trust me" recommendations | 3+ data-driven reasons generated per creator |
| No feedback loop | Predicted vs actual GMV tracked per campaign |

---

## 📊 Proven Results

Reproducible benchmark — `experiments/scalability.py`, fixed **$5,000** budget, **mean of 10 seeds**:

| Creator pool N | Best algorithm | Best GMV | Hill Climber GMV | **Uplift** |
|:---:|:---|---:|---:|:---:|
| 50 | Random Search | $42.7K | $24.3K | **+76%** |
| 100 | Tabu Search | $53.2K | $26.7K | **+99%** |
| 200 | Greedy Ranking | $64.4K | $27.3K | **+136%** |
| 500 | Genetic Algorithm | $73.3K | $28.1K | **+161%** |

Structured search beats naïve hill-climbing by **76–161%**, and the advantage *widens* as the creator pool grows — exactly when human shortlisting breaks down. Full methodology, per-algorithm analysis, and the factors that drive these numbers: [`docs/report_draft.md`](docs/report_draft.md).

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Optimization engine** | Pure-Python implementations of Simulated Annealing, Genetic Algorithm, Tabu Search, Hill Climber, Random Search, Greedy Ranking |
| **Backend API** | FastAPI + Pydantic — 20+ typed REST endpoints, auto-generated Swagger docs |
| **Frontend** | Single-page app (vanilla JS + Tailwind CSS), served directly by FastAPI — no separate web server |
| **Data & analytics** | NumPy / Pandas; JSON persistence; CSV import/export; calibrated SEA market model |
| **Experiments** | Matplotlib figure pipeline; seeded, fully reproducible benchmarks |
| **Quality** | 110 pytest tests; GitHub Actions CI on every push |

---

## Table of Contents

- [Why It Matters](#-why-it-matters)
- [Proven Results](#-proven-results)
- [Tech Stack](#-tech-stack)
- [Features](#features)
- [Algorithms](#algorithms)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Overview](#api-overview)
- [Testing](#testing)
- [Data Flow](#data-flow)
- [Why Structured Search Wins](#why-structured-search-wins-technical-deep-dive)
- [Contributing](#contributing)
- [License](#license)

---

## Features

The platform is organised into three product modules backed by two intelligence layers:

| Module | What it does | Highlights |
|---|---|---|
| 🎯 **Campaign Optimizer** | Runs six algorithms on your filtered creator pool and returns the budget-optimal portfolio | Winning portfolio · GMV/ROI benchmark · live convergence chart |
| 👥 **Creator Management** | Build, import, and curate your own KOL database | CRUD · CSV import/export · metric-trend sparklines |
| 📈 **Campaign Attribution** | Closes the loop by comparing predicted vs actual GMV | Accuracy % · per-campaign history |
| 🧠 **Explainable AI** | Plain-English justification for every pick | 3+ data-driven reasons per creator |
| ⭐ **CreatorScore & Tiers** | Composite quality score + tier classification | Leaderboards · badges · ranking |

### 🎯 Campaign Optimizer

The core engine. Choose a **budget**, one or more **target markets**, and a **product category**; the backend filters the creator pool and runs all six algorithms in parallel, then surfaces the highest-GMV portfolio.

- **Inputs** — budget ($100–$20,000), any of six SEA markets (MY · ID · TH · PH · SG · VN), a product category (Beauty · Fashion · Home & Living · FMCG), and an optional random seed for reproducible runs.
- **Results** — five headline metrics (winning algorithm, predicted GMV, budget utilization, creators selected, candidate-pool size); an SVG **convergence chart** tracing all six algorithms; a side-by-side **benchmark table** (GMV + ROI, winner highlighted); and the **KOL matrix** — one card per selected creator showing tier, reach, cost, engagement, fit, estimated GMV, and a **"Why?"** explainer.
- **Save** any result as a named campaign for later attribution.

### 👥 Creator Management

Bring your own creators or curate the seeded dataset.

- **CRUD + bulk operations** — add via a 12-field form, **import/export CSV** (with a downloadable template), inline edit/delete, filter by country/category/tier (paginated), and a double-confirmed full reset.
- **Metric trends** — each creator has a detail view with sparkline history for engagement, fit, and followers (↑/↓ trend arrows). **Simulate Update** applies realistic random drift to preview how a live TikTok-API refresh would move the numbers.
- **Roadmap connectors** — stubs for the TikTok Creator Marketplace API, TikTok Shop Partner API, and third-party analytics; "Coming Soon" cards capture early-access interest.

### 📈 Campaign Attribution

Turn one-shot predictions into a feedback loop. Save an optimization as a campaign, then after it runs record the **actual GMV** — the system computes `accuracy % = actual / predicted × 100` and renders a predicted-vs-actual breakdown per creator. Over many campaigns this becomes an attribution history that shows how well the GMV model tracks reality.

### 🧠 Explainable AI

No black boxes: every recommended creator ships with **3+ human-readable reasons** generated from its own data — for example:

> "Malaysia audience match is 92%, well above the 80% threshold" · "Engagement rate 15.0% is 87% above the beauty category average" · "Predicted ROI is 45% above the pool average — high cost-effectiveness"

### ⭐ CreatorScore & Tier Classification

Each creator gets a composite quality score in [0, 1] — used for leaderboards, badges, and reason generation:

```
CreatorScore = 0.30 × norm(followers)
             + 0.30 × engagement_rate
             + 0.20 × fit_score
             + 0.20 × norm(expected_gmv / cost)
```

…and a **tier** derived from follower count:

| Tier | Followers | Profile |
|------|-----------|---------|
| Mega  | > 1,000,000 | Maximum brand awareness, highest cost |
| Macro | 100,000 – 1,000,000 | Broad reach with credibility |
| Micro | 10,000 – 100,000 | Highest conversion, precise targeting |
| Nano  | < 10,000 | Niche communities, lowest cost |

The optimizer deliberately favours a **mixed-tier portfolio** over a single Mega creator — precisely where structured search beats naïve hill-climbing (see [Proven Results](#-proven-results)).

---

## Algorithms

All six solvers operate on the same binary-selection problem (each KOL is in or out, subject to the budget) and the same fitness function (`−GMV + budget_penalty + overlap_penalty`). They differ in *how* they search the 2ᴺ portfolio space:

| Algorithm | Class | Determinism | Per-run speed | Role |
|---|---|---|---|---|
| **Genetic Algorithm** | Population metaheuristic | Stochastic | Slow | Best quality at large pools |
| **Greedy Ranking** | Constructive + 2-opt local search | Deterministic | **Fastest** | Near-best & instant; interactive default |
| **Tabu Search** | Memory-based local search | Mostly deterministic | Medium (O(N²)) | Strong for N ≤ 100 |
| **Simulated Annealing** | Trajectory metaheuristic | Stochastic | Slowest | Robust escape from local optima |
| **Random Search** | Unstructured sampling | Stochastic | Fast | Lower-bound baseline |
| **Hill Climber** | Naïve local search | Stochastic | Fast | Control baseline (the "trap") |

> Benchmarked quality and runtime across N = 50–500 are in [Proven Results](#-proven-results); the mechanism behind the gap is in [Why Structured Search Wins](#why-structured-search-wins-technical-deep-dive).

### Simulated Annealing (Primary Solver)

Models the physical process of metal cooling. Starts with high temperature (accepts random moves) and gradually cools (becomes selective).

- **Neighbourhood:** Thermal-adaptive hybrid — single bit-flip, structural swap (drop one selected / add one unselected), and occasional multi-swap jumps.
- **Acceptance:** Worse solutions accepted with probability `P = e^(-delta/T)`.
- **Parameters:** T0=15,000, T_min=10, alpha=0.95, 150 iterations per temperature step (~143 temperature levels).
- **Advantage:** Escapes local optima by accepting temporarily worse portfolios.

### Hill Climber

Greedy local search. Only accepts improvements. Fast convergence but gets trapped when expensive KOLs fill the budget.

### Random Search (Lower Bound)

Pure random sampling. Demonstrates that structured search significantly outperforms random selection.

### Genetic Algorithm

Population-based evolutionary search.

- **Population:** 60 individuals over 120 generations; first individual is a greedy-seeded solution, the rest are randomly seeded at a budget-aware inclusion probability.
- **Selection:** Tournament selection (k=3).
- **Crossover:** Single-point crossover (probability 0.9). Budget feasibility is enforced by the fitness penalty rather than explicit repair, so over-budget children are culled by selection.
- **Mutation:** Bit-flip with probability 1/n per gene.
- **Elitism:** The best individual always survives into the next generation.
- **Advantage:** Diverse population avoids premature convergence; crossover creates genuinely novel portfolios.

### Tabu Search

Greedy-initialized deterministic local search with short-term memory.

- **Tabu tenure:** 8 iterations — recently flipped indices are forbidden.
- **Aspiration criterion:** A tabu move is allowed if it produces a new global best.
- **Advantage:** Systematically explores the neighbourhood without cycling; stronger than basic HC on large pools.

### Greedy Ranking (Deterministic Baseline)

Sorts KOLs by predicted GMV-per-dollar and greedily fills the budget. Instant and deterministic. Serves as an upper-bound reference for what a simple heuristic achieves.

---

## Project Structure

```
tiktok-kol-optimizer/
├── backend/
│   ├── main.py              # FastAPI: /optimize, /kols, /kol/{id}, /top-kols, /scalability,
│   │                        #          /api/connections (integration stubs)
│   ├── crud.py              # KOL CRUD: /kols/add, PUT, DELETE, /import-csv, /reset
│   │                        # also: GET /kols/{id}/history, POST /kols/{id}/simulate-update
│   ├── campaigns.py         # Campaign Attribution: POST/GET/PUT/DELETE /campaigns
│   └── README.md            # API usage guide with curl examples
├── frontend/
│   └── index.html           # Single-page app: Optimizer + Creators + Campaigns
├── engine/
│   ├── models.py            # KOL dataclass + tier property
│   ├── fitness.py           # Fitness function + budget penalty
│   ├── optimization/
│   │   ├── simulated_annealing.py
│   │   ├── hill_climber.py
│   │   ├── random_search.py
│   │   ├── genetic_algorithm.py
│   │   ├── tabu_search.py
│   │   └── greedy_ranking.py
│   ├── scoring/
│   │   ├── creator_score.py # Weighted composite score
│   │   ├── explainer.py     # Why-recommended reason generator
│   │   └── roi_predictor.py # Predicted GMV and ROI calculator
│   └── evaluation/
│       ├── benchmark.py     # Multi-algorithm comparison runner (all 6 algorithms)
│       └── sensitivity.py   # SA parameter sensitivity analysis
├── data/
│   ├── generator.py         # Synthetic KOL dataset generator (--num flag)
│   ├── sample_kols.json     # Active KOL database
│   ├── kol_history.json     # KOL metric snapshots over time
│   ├── campaigns.json       # Saved campaign attribution records
│   └── influencers_mock.csv # Same data as sample_kols in CSV format
├── experiments/
│   ├── run_comparison.py    # Convergence curve experiment (6 algorithms)
│   ├── scalability.py       # N=50 to 500 scaling benchmark (6 algorithms)
│   └── gen_figures.py       # Generates all docs/figures/ charts
├── tests/
│   ├── test_fitness.py
│   ├── test_algorithms.py
│   ├── test_scoring.py
│   ├── test_api.py          # Core endpoint tests
│   ├── test_campaigns.py    # Campaign attribution endpoint tests
│   └── test_kol_history.py  # KOL history & simulate-update tests
├── docs/
│   ├── API_SPEC.md          # Complete API contract
│   ├── data_source.md       # Data design documentation
│   ├── report_draft.md      # Academic report draft
│   └── figures/             # Experiment charts for report
├── start_server.bat         # One-click Windows startup script
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- pip (and, optionally, a virtual environment)

### 1. Install dependencies

```bash
git clone https://github.com/Hedy12130102/tiktok-kol-optimizer.git
cd tiktok-kol-optimizer
pip install -r requirements.txt
```

### 2. Generate sample data (optional)

A pre-generated `data/sample_kols.json` ships with the repo, so this step is only needed to reseed or resize the pool:

```bash
python data/generator.py              # 300 KOLs (default)
python data/generator.py --num 500    # custom pool size
python data/generator.py --num 500 --seed 7   # reproducible custom seed
```

### 3. Start the backend

```bash
# Windows (double-click or run in terminal)
start_server.bat

# macOS / Linux
uvicorn backend.main:app --reload
```

### 4. Open the app

| URL | Purpose |
|---|---|
| http://localhost:8000/ui | Web application (Optimizer · Creators · Campaigns) |
| http://localhost:8000/docs | Interactive Swagger API docs |

---

## API Overview

Full specification: [`docs/API_SPEC.md`](docs/API_SPEC.md)

### Core Optimization

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/optimize` | Run 6 algorithms, return best KOL matrix |
| `GET` | `/kols` | Filtered and paginated KOL list |
| `GET` | `/kol/{id}` | Single KOL detail + scores + reasons |
| `GET` | `/top-kols` | Top 10 by CreatorScore |
| `POST` | `/scalability` | Algorithm benchmark at given pool size |

### Creator Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/kols/add` | Add a single creator |
| `PUT` | `/kols/{id}` | Update a creator (auto-snapshots metrics) |
| `DELETE` | `/kols/{id}` | Delete a creator |
| `POST` | `/kols/import-csv` | Bulk import from CSV |
| `POST` | `/kols/reset` | Clear all data |
| `GET` | `/kols/template` | Download CSV template |
| `GET` | `/kols/export` | Export all creators as CSV |

### KOL History Tracking

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/kols/{id}/history` | Get metric snapshots (newest first) |
| `POST` | `/kols/{id}/simulate-update` | Apply random metric drift + record snapshot |

### Campaign Attribution

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/campaigns` | Save optimization result as campaign |
| `GET` | `/campaigns` | List all campaigns |
| `GET` | `/campaigns/{id}` | Single campaign detail |
| `PUT` | `/campaigns/{id}/actual` | Record actual GMV after campaign ends |
| `DELETE` | `/campaigns/{id}` | Delete a campaign |

### API Integrations (Stubs)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/connections` | List all integration statuses |
| `POST` | `/api/connections/interest` | Register early-access email for a Coming Soon integration |
| `POST` | `/api/connections/connect` | Connect an integration (returns `coming_soon` until live) |

---

## Testing

The suite has **110 tests** covering the fitness function, all six algorithms, scoring/explainer logic, and every API endpoint (optimization, CRUD, KOL history, campaign attribution).

```bash
# Run the full suite
pytest tests/ --tb=short

# With coverage
pytest tests/ --cov=engine --cov=backend
```

CI runs the suite on every push and pull request to `dev`/`master` via [GitHub Actions](.github/workflows/ci.yml).

---

## Data Flow

```
Merchant input (manual / CSV)
         |
   sample_kols.json  <--  generator.py (synthetic seed data)
         |
   Filter by country + category
         |
   +----------------------------------------------------------+
   |  SA    HC    RS    GA    Tabu   Greedy Ranking           |
   |  (global) (greedy) (random) (evol.) (memory) (ratio-sort)|
   +----------------------------------------------------------+
         |
   Best algorithm selected (highest GMV)
         |
   CreatorScore + Tier + Reasons enrichment
         |
   Frontend renders results
         |
   [Optional] Save as Campaign
         |
   Record actual GMV → accuracy % computed
         |
   campaigns.json (attribution history)
```

---

## Why Structured Search Wins (Technical Deep-Dive)

Hill Climber selects expensive Mega/Macro KOLs early, exhausts the budget, and gets trapped — no single-bit flip can improve the solution. Greedy Ranking (ratio-sort + 2-opt), Genetic Algorithm, Tabu Search, and Simulated Annealing each avoid this trap via different mechanisms — cost-effectiveness ranking, population crossover, tabu memory, and temperature-driven acceptance respectively. In the reproducible benchmark (`experiments/scalability.py`, fixed budget $5,000, mean of 10 seeds), HC is the weakest method at every pool size, and the best algorithm's GMV lead over HC widens from **+76% at N=50 to +161% at N=500**. At scale the lead is shared by GA and Greedy Ranking (GA $73.3K at N=500; GR $64.4K at N=200) versus HC's ~$28K — a ~2.6× gap that underscores the value of structured search for large creator pools. See [`docs/report_draft.md`](docs/report_draft.md) §3.2 for the full table.

---

## Contributing

Contributions are welcome. To propose a change:

1. Fork the repo and create a feature branch off `dev`.
2. Make your change and **add or update tests** — the suite must stay green (`pytest tests/`).
3. Keep the experiment figures and `docs/` in sync if you touch the engine or data model.
4. Open a pull request against `dev` with a clear description; CI must pass.

For larger ideas (new algorithms, a real TikTok data integration, multi-objective optimization), please open an issue first to discuss the design.

---

## License

Released under the **MIT License** — see [`LICENSE`](LICENSE) for the full text.

Market multipliers and distributions are calibrated from publicly available industry reports; sources are documented in [`docs/data_source.md`](docs/data_source.md).
