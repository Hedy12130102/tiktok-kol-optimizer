# TikTok Shop KOL Matrix Optimizer

An AI-powered system that selects the **optimal KOL (Key Opinion Leader) portfolio** for TikTok Shop campaigns in Southeast Asia. Given a fixed marketing budget, the system uses **Simulated Annealing** — a local search optimization algorithm — to maximize predicted GMV across thousands of possible creator combinations.

> **Live Demo:** Start the backend, open `http://localhost:8000/ui` in your browser.

---

## Features

### 1. Campaign Optimizer (Dashboard)

The core feature. A merchant inputs three parameters and the system returns the mathematically optimal KOL portfolio.

**Inputs (sidebar):**
- **Marketing Budget** — slider from $500 to $20,000. The algorithm guarantees the total hiring cost stays within this limit.
- **Target Country** — Malaysia, Indonesia, Thailand, or Philippines. Only KOLs matching this market are considered.
- **Product Category** — Beauty, Tech, or Fashion. Filters the pool to relevant content creators.
- **Random Seed** — ensures reproducible results. Same seed + same data = same output every time.

**What happens when you click "Run Optimization":**
1. The backend filters the KOL pool by country + category.
2. Three algorithms run in parallel on the filtered pool:
   - **Simulated Annealing (SA)** — accepts temporarily worse solutions to escape local optima, ultimately finding the global best.
   - **Hill Climber (HC)** — greedy search that only moves uphill. Fast but gets trapped when expensive KOLs exhaust the budget.
   - **Random Search (RS)** — pure random sampling. Serves as a lower-bound baseline.
3. The algorithm with the highest predicted GMV is declared the winner.

**Outputs displayed:**
- **5 metric cards** — Best Algorithm, Predicted GMV, Budget Used (with utilization %), KOLs Selected, Candidate Pool Size.
- **Convergence Curve** — SVG line chart showing how each algorithm's best GMV improves over iterations. SA's curve shows initial dips (accepting worse solutions) then surging past HC. HC flatlines early (trapped). RS stays low.
- **Algorithm Benchmark Table** — side-by-side comparison of GMV and ROI for all three algorithms, with the winner highlighted in green.
- **Best KOL Matrix** — card grid of the selected creators, each showing:
  - **Tier badge** (Mega / Macro / Micro / Nano) — auto-classified by follower count.
  - Follower count, hiring cost, engagement rate.
  - **Fit Score bar** — visual indicator of how well the creator matches the target market (0-100%).
  - **Estimated GMV** — predicted gross merchandise value this creator will generate.
  - **"Why?" button** — expands to show 3+ data-driven reasons why this KOL was recommended.

---

### 2. Creator Management

Merchants can build their own KOL database instead of relying on synthetic data. This is the foundation for real commercial use.

**Add Creator (manual):**
- Click "Add Creator" in the header, fill out a 12-field form (Name, TikTok URL, Country, Category, Followers, Engagement Rate, Cost, Fit Score, Avg Views, Avg Likes, Female Audience Ratio, Age Group).
- Optional fields (Avg Views, Avg Likes) are auto-calculated from follower count and engagement rate if left blank.
- Validation: country must be MY/ID/TH/PH, engagement rate must be 0-1, cost must be non-negative.

**Import CSV (bulk):**
- Upload a `.csv` file with columns: `name, country, category, followers, engagement_rate, cost`.
- Optional columns: `fit_score, avg_views, avg_likes, gender_ratio, age_group, tiktok_url`.
- The system validates each row, skips invalid ones, and reports success vs failure count.

**Download Template:**
- Download a pre-filled CSV with correct headers and one example row. Fill in Excel and re-upload.

**Export:**
- Download the entire KOL database as a CSV file.

**Edit / Delete:**
- Each row in the table has edit and delete icons.
- Edit opens the form pre-filled with current values.
- Delete requires confirmation.

**Reset All:**
- Clears the entire database (requires double confirmation). Used when a merchant wants to discard synthetic data and start fresh with only their own creators.

**Filters:**
- Filter the table by Country, Category, or Tier. Results update instantly. Pagination: 20 per page.

---

### 3. Scalability Analysis

Tests how each algorithm performs as the KOL pool size grows. Proves that SA scales better than HC.

**Inputs:**
- **Pool Size (N)** — slider from 10 to 500.
- **Run Test button** — triggers the benchmark.

**Outputs:**
- **3 algorithm cards** — execution time, projected GMV, and KOLs selected for each algorithm.
- **Execution Time chart** — line chart showing runtime growth with N.
- **Solution Quality chart** — line chart showing final GMV at each N. SA consistently dominates.
- **Multi-run accumulation** — each Run Test with a different N adds a new data point to the chart.
- **Optimization Insight** — auto-generated text summarizing the SA vs HC advantage percentage.

---

### 4. Explainable AI (Why Recommended?)

Every selected KOL comes with 3+ human-readable reasons generated from the KOL's actual data:
- "Malaysia audience match is 92%, well above the 80% threshold"
- "Engagement rate 15.0% is 87% above the beauty category average"
- "Micro KOL with 80K followers — high conversion rate and precise audience targeting"
- "Predicted ROI is 45% above the pool average — high cost-effectiveness"

This addresses a real business need: marketing managers must justify KOL selection to leadership.

---

### 5. CreatorScore

Each KOL is assigned a composite quality score in [0, 1]:

```
CreatorScore = 0.30 * norm(followers)
             + 0.30 * engagement_rate
             + 0.20 * fit_score
             + 0.20 * norm(expected_gmv / cost)
```

Used for leaderboard ranking, quality display, and reason generation.

---

### 6. KOL Tier Classification

| Tier | Followers | Characteristics |
|------|-----------|-----------------|
| Mega | > 1,000,000 | Maximum brand awareness, highest cost |
| Macro | 100,000 - 1,000,000 | Broad coverage with credibility |
| Micro | 10,000 - 100,000 | Highest conversion, precise targeting |
| Nano | < 10,000 | Niche communities, lowest cost |

The optimizer typically selects a **mixed-tier portfolio** rather than spending on a single Mega KOL. This is where SA outperforms HC.

---

## Algorithms

### Simulated Annealing (Primary Solver)

Models the physical process of metal cooling. Starts with high temperature (accepts random moves) and gradually cools (becomes selective).

- **Neighbourhood:** Hybrid bit-flip + swap.
- **Acceptance:** Worse solutions accepted with probability `P = e^(-delta/T)`.
- **Parameters:** T0=50000, T_min=1.0, alpha=0.95, 500 iterations per temperature.
- **Advantage:** Escapes local optima by accepting temporarily worse portfolios.

### Hill Climber (Comparison Baseline)

Greedy local search. Only accepts improvements. Fast convergence but gets trapped when expensive KOLs fill the budget.

### Random Search (Lower Bound)

Pure random sampling. Demonstrates that structured search significantly outperforms random selection.

---

## Project Structure

```
tiktok-kol-optimizer/
├── backend/
│   ├── main.py              # FastAPI: /optimize, /kols, /kol/{id}, /top-kols, /scalability
│   ├── crud.py              # FastAPI: /kols/add, PUT, DELETE, /import-csv, /reset
│   └── README.md            # API usage guide with curl examples
├── frontend/
│   └── index.html           # Single-page app: Dashboard + Creators + Scalability
├── engine/
│   ├── models.py            # KOL dataclass + tier property
│   ├── fitness.py           # Fitness function + budget penalty
│   ├── optimization/
│   │   ├── simulated_annealing.py
│   │   ├── sa_improved.py   # Swap neighbourhood variant
│   │   ├── hill_climber.py
│   │   └── random_search.py
│   ├── scoring/
│   │   ├── creator_score.py # Weighted composite score
│   │   ├── explainer.py     # Why-recommended reason generator
│   │   └── roi_predictor.py # Predicted GMV and ROI calculator
│   └── evaluation/
│       ├── benchmark.py     # Multi-algorithm comparison runner
│       └── sensitivity.py   # SA parameter sensitivity analysis
├── data/
│   ├── generator.py         # Synthetic KOL dataset generator (--num flag)
│   ├── sample_kols.json     # Active KOL database
│   └── influencers_mock.csv # Same data in CSV format
├── experiments/
│   ├── run_comparison.py    # Convergence curve experiment
│   └── scalability.py       # N=50 to 500 scaling benchmark
├── tests/
│   ├── test_fitness.py
│   ├── test_algorithms.py
│   ├── test_scoring.py
│   └── test_api.py          # 28 endpoint tests
├── docs/
│   ├── API_SPEC.md          # Complete API contract
│   ├── data_source.md       # Data design documentation
│   └── figures/             # Experiment charts for report
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

**2. Generate sample data** (optional, skip if using manual input)

```bash
python data/generator.py           # 300 KOLs
python data/generator.py --num 500 # custom size
```

**3. Start the backend**

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/optimize` | Run 3 algorithms, return best KOL matrix |
| `GET` | `/kols` | Filtered and paginated KOL list |
| `GET` | `/kol/{id}` | Single KOL detail + scores + reasons |
| `GET` | `/top-kols` | Top 10 by CreatorScore |
| `POST` | `/scalability` | Algorithm benchmark at given pool size |
| `POST` | `/kols/add` | Add a single creator |
| `PUT` | `/kols/{id}` | Update a creator |
| `DELETE` | `/kols/{id}` | Delete a creator |
| `POST` | `/kols/import-csv` | Bulk import from CSV |
| `POST` | `/kols/reset` | Clear all data |
| `GET` | `/kols/template` | Download CSV template |
| `GET` | `/kols/export` | Export all creators as CSV |

---

## Run Tests

```bash
pytest tests/ --tb=short
```

CI runs automatically on every push and pull request via GitHub Actions.

---

## Data Flow

```
Merchant input (manual / CSV)
         |
   sample_kols.json  <--  generator.py (synthetic seed data)
         |
   Filter by country + category
         |
   +------------------------------------------+
   |  SA          HC          Random Search    |
   |  (global)    (greedy)    (baseline)       |
   +------------------------------------------+
         |
   Best algorithm selected (highest GMV)
         |
   CreatorScore + Tier + Reasons enrichment
         |
   Frontend renders results
```

---

## Key Insight

Hill Climber selects expensive Mega KOLs early, exhausts the budget, and gets trapped. No single-bit flip can improve the solution. Simulated Annealing accepts temporarily worse portfolios, allowing it to discover higher-value mixed-tier combinations. In testing, SA outperforms HC by approximately 97% in predicted GMV.

---

## License

MIT