# TikTok Shop KOL Matrix Optimizer

An AI-powered system that selects the **optimal KOL (Key Opinion Leader) portfolio** for TikTok Shop campaigns in Southeast Asia. Given a fixed marketing budget, the system runs **six optimization algorithms** in parallel — including Simulated Annealing, Genetic Algorithm, and Tabu Search — to maximize predicted GMV across thousands of possible creator combinations, then tracks real campaign outcomes and compares them against predictions.

> **Live Demo:** Run `start_server.bat` (Windows) or `uvicorn backend.main:app --reload`, then open `http://localhost:8000/ui`.

---

## Features

### 1. Campaign Optimizer (Dashboard)

The core feature. A merchant inputs parameters and the system returns the mathematically optimal KOL portfolio from six competing algorithms.

**Inputs (sidebar):**
- **Marketing Budget** — slider from $100 to $20,000. All algorithms guarantee the total hiring cost stays within this limit.
- **Target Countries** — multi-select: Malaysia, Indonesia, Thailand, Philippines, Singapore, Vietnam, or All Countries. Selecting multiple countries pools creators from all chosen markets.
- **Product Category** — Beauty, Fashion, Home & Living, or FMCG.
- **Advanced Settings** — collapse/expand panel containing Random Seed (for reproducible results) and other tuning options.

**What happens when you click "Run Optimization":**
1. The backend filters the KOL pool by country + category.
2. All six algorithms run on the filtered pool:
   - **Simulated Annealing (SA)** — accepts temporarily worse solutions to escape local optima; primary solver.
   - **Hill Climber (HC)** — greedy local search, fast but gets trapped in local optima.
   - **Random Search (RS)** — pure random sampling, serves as a lower-bound baseline.
   - **Genetic Algorithm (GA)** — population-based evolutionary search with crossover and mutation; greedy-seeded initial population.
   - **Tabu Search (TS)** — greedy-initialized local search with a tabu list to avoid revisiting recent moves; aspiration criterion allows breaking tabu for new global bests.
   - **Greedy Ranking (GR)** — sorts KOLs by GMV/cost ratio and greedily fills budget; deterministic upper-bound reference.
3. The algorithm with the highest predicted GMV is declared the winner.

**Outputs displayed:**
- **5 metric cards** — Best Algorithm, Predicted GMV, Budget Used (with utilization %), KOLs Selected, Candidate Pool Size.
- **Convergence Chart** — SVG line chart showing all six algorithms' best GMV over iterations. SA's curve shows initial dips (accepting worse solutions) then surging; HC and TS plateau early; GA converges steadily; GR hits its answer instantly.
- **Algorithm Benchmark Table** — side-by-side comparison of GMV and ROI for all six algorithms, with the winner highlighted.
- **Best KOL Matrix** — card grid of selected creators, each showing tier badge, followers, cost, engagement rate, fit score bar, estimated GMV, and a "Why?" explainer button.

**Save Campaign:** After running optimization, click "Save Campaign" to record the prediction as a named campaign for later attribution tracking.

---

### 2. Creator Management

Merchants can build their own KOL database. The Creators page opens with a **Data Sources** panel:

**Manual Import (Active):**
- **Add Creator** — 12-field form (Name, TikTok URL, Country, Category, Followers, Engagement Rate, Commission Rate, Fit Score, Avg Views, Avg Likes, Female Audience Ratio, Age Group).
- **Import CSV** — bulk upload with required columns `name, country, category, followers, engagement_rate, cost` and optional extended fields.
- **Download Template** — pre-filled CSV with correct headers and one example row.
- **Export** — download entire KOL database as CSV.
- **Edit / Delete** — inline table actions with delete confirmation.
- **Reset All** — clears the entire database (double confirmation required).
- **Filters** — by Country, Category, or Tier; pagination at 20 per page.

**Future API Integrations (Coming Soon):**
- TikTok Creator Marketplace API — direct creator search and invite
- TikTok Shop Partner API — live sales data and affiliate metrics
- Analytics Platforms — third-party engagement data (e.g., Sprout Social, Brandwatch)

Click any Coming Soon card to register interest for early access.

**KOL Detail Modal:** Click any creator row to open a detail view showing full metrics and the **Metric Trends** section — sparkline charts for engagement rate, fit score, and followers over time, with trend arrows (↑ green / ↓ red). Click **Simulate Update** to apply a realistic TikTok API refresh with random drift and see the sparklines update live.

---

### 3. Campaign Attribution

Track real-world campaign outcomes against optimization predictions.

**Workflow:**
1. Run optimizer → click "Save Campaign" → give the campaign a name.
2. After the campaign ends, open the Campaigns page, find the campaign, and click "Record Actual GMV".
3. Enter the actual total GMV achieved. The system computes **accuracy %** = (actual / predicted) × 100.

**Campaign table** shows: name, status (Active / Completed), country, category, predicted GMV, actual GMV, accuracy, and algorithm used.

**Campaign detail modal** shows a bar chart comparing predicted vs. actual GMV and a breakdown per selected KOL.

---

### 4. Explainable AI (Why Recommended?)

Every selected KOL comes with 3+ human-readable reasons generated from the KOL's actual data:
- "Malaysia audience match is 92%, well above the 80% threshold"
- "Engagement rate 15.0% is 87% above the beauty category average"
- "Micro KOL with 80K followers — high conversion rate and precise audience targeting"
- "Predicted ROI is 45% above the pool average — high cost-effectiveness"

---

### 5. CreatorScore

Each KOL is assigned a composite quality score in [0, 1]:

```
CreatorScore = 0.30 × norm(followers)
             + 0.30 × engagement_rate
             + 0.20 × fit_score
             + 0.20 × norm(expected_gmv / cost)
```

Used for leaderboard ranking, quality display, and reason generation.

---

### 6. KOL Tier Classification

| Tier | Followers | Characteristics |
|------|-----------|-----------------|
| Mega | > 1,000,000 | Maximum brand awareness, highest cost |
| Macro | 100,000 – 1,000,000 | Broad coverage with credibility |
| Micro | 10,000 – 100,000 | Highest conversion, precise targeting |
| Nano | < 10,000 | Niche communities, lowest cost |

The optimizer typically selects a **mixed-tier portfolio** rather than spending on a single Mega KOL — this is where SA, GA, and TS outperform HC.

---

## Algorithms

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

**1. Install dependencies**

```bash
git clone https://github.com/Hedy12130102/tiktok-kol-optimizer.git
cd tiktok-kol-optimizer
pip install -r requirements.txt
```

**2. Generate sample data** (optional — skip if using manual input)

```bash
python data/generator.py           # 300 KOLs (default)
python data/generator.py --num 500 # custom size
```

**3. Start the backend**

Windows (double-click or run in terminal):
```
start_server.bat
```

macOS / Linux:
```bash
uvicorn backend.main:app --reload
```

**4. Open the app**

```
http://localhost:8000/ui
```

Swagger API docs: `http://localhost:8000/docs`

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

## Run Tests

```bash
pytest tests/ --tb=short
```

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

## Key Insight

Hill Climber selects expensive Mega/Macro KOLs early, exhausts the budget, and gets trapped — no single-bit flip can improve the solution. Greedy Ranking (ratio-sort + 2-opt), Genetic Algorithm, Tabu Search, and Simulated Annealing each avoid this trap via different mechanisms — cost-effectiveness ranking, population crossover, tabu memory, and temperature-driven acceptance respectively. In the reproducible benchmark (`experiments/scalability.py`, fixed budget $5,000, mean of 10 seeds), HC is the weakest method at every pool size, and the best algorithm's GMV lead over HC widens from **+76% at N=50 to +161% at N=500**. At scale the lead is shared by GA and Greedy Ranking (GA $73.3K at N=500; GR $64.4K at N=200) versus HC's ~$28K — a ~2.6× gap that underscores the value of structured search for large creator pools. See [`docs/report_draft.md`](docs/report_draft.md) §3.2 for the full table.

---

## License

MIT
