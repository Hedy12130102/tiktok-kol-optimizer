# TikTok Shop KOL Matrix Optimizer

An AI-powered system that selects the **optimal KOL (Key Opinion Leader) portfolio** for TikTok Shop campaigns in Southeast Asia. Given a fixed marketing budget, the system uses **Local Search & Optimization** algorithms to maximise predicted GMV (Gross Merchandise Value) across thousands of possible creator combinations.

---

## Problem Formulation

KOL selection is modelled as a **budget-constrained combinatorial optimisation problem**:

- **State space**: binary vector `S = [x₁, x₂, ..., xₙ]`, where `xᵢ = 1` means KOL *i* is selected
- **Constraint**: `Σ(xᵢ × costᵢ) ≤ B` — total hiring cost must not exceed budget `B`
- **Objective**: maximise predicted GMV = `Σ(xᵢ × followersᵢ × engagement_rateᵢ × fit_scoreᵢ)`
- **Cost function**: `Cost(S) = −GMV(S) + Penalty(S)` where penalty = `max(0, overspend) × 10⁶`
- **Neighbourhood**: bit-flip (add/remove one KOL) and swap (exchange one selected for one unselected)

---

## Algorithms

| Algorithm | Strategy | Role |
|-----------|----------|------|
| **Simulated Annealing** | Accepts worse solutions with probability `e^(−ΔE/T)`, escapes local optima | Primary solver |
| **SA Improved** | Hybrid bit-flip + swap neighbourhood | Enhanced solver |
| **Hill Climber** | Greedy — only accepts improvements | Comparison baseline |
| **Random Search** | Pure random sampling | Lower-bound baseline |

---

## Project Structure

```
tiktok-kol-optimizer/
├── backend/
│   ├── main.py              # FastAPI routes (/optimize, /kols, /kol/{id}, /top-kols, /scalability)
│   └── README.md            # API usage & curl examples
├── data/
│   ├── generator.py         # Mock KOL dataset generator (--num flag supported)
│   ├── sample_kols.json     # 300 KOL records
│   └── influencers_mock.csv # Same data in CSV format
├── engine/
│   ├── models.py            # KOL dataclass + tier property
│   ├── fitness.py           # Fitness function & summarize_state
│   ├── optimization/
│   │   ├── hill_climber.py
│   │   ├── simulated_annealing.py
│   │   ├── sa_improved.py   # Swap neighbourhood variant
│   │   └── random_search.py
│   ├── scoring/
│   │   ├── creator_score.py # Weighted composite score (0–1)
│   │   ├── roi_predictor.py # Predicted GMV & ROI
│   │   └── explainer.py     # Why-recommended reason generator
│   └── evaluation/
│       ├── benchmark.py     # Multi-algorithm runner
│       └── sensitivity.py   # SA parameter sensitivity analysis
├── experiments/
│   ├── run_comparison.py    # Convergence curve comparison
│   └── scalability.py       # N = 50 / 100 / 200 / 500 scaling test
├── frontend/
│   └── app.py               # Streamlit dashboard
├── tests/
│   ├── test_fitness.py
│   ├── test_algorithms.py
│   ├── test_scoring.py
│   └── test_api.py
├── docs/
│   ├── API_SPEC.md          # Single source of truth for all API field names
│   ├── data_source.md       # Data design decisions
│   └── figures/             # All experiment charts
├── requirements.txt
└── README.md
```

---

## Quick Start

**1. Clone and install dependencies**

```bash
git clone https://github.com/Hedy12130102/tiktok-kol-optimizer.git
cd tiktok-kol-optimizer
pip install -r requirements.txt
```

**2. Generate mock KOL data**

```bash
python data/generator.py
# or specify pool size:
python data/generator.py --num 300
```

**3. Start the backend** (Terminal 1)

```bash
uvicorn backend.main:app --reload
# API docs available at: http://localhost:8000/docs
```

**4. Start the frontend** (Terminal 2)

```bash
streamlit run frontend/app.py
# Opens at: http://localhost:8501
```

**5. Run offline experiments**

```bash
# Convergence curve comparison
python experiments/run_comparison.py

# Scalability analysis (N = 50 → 500)
python experiments/scalability.py
```

---

## API Overview

Full specification: [`docs/API_SPEC.md`](docs/API_SPEC.md)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/optimize` | Run all algorithms, return best KOL matrix |
| `GET` | `/kols` | Filtered & paginated KOL list |
| `GET` | `/kol/{id}` | Single KOL detail with scores & reasons |
| `GET` | `/top-kols` | Top 10 KOLs by creator score |
| `POST` | `/scalability` | Algorithm performance at different pool sizes |

**Example — optimise a campaign:**

```bash
# macOS / Linux
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"budget": 5000, "country": "MY", "category": "beauty", "seed": 42}'

# Windows PowerShell
curl -X POST http://localhost:8000/optimize `
  -H "Content-Type: application/json" `
  -d '{\"budget\": 5000, \"country\": \"MY\", \"category\": \"beauty\", \"seed\": 42}'
```

---

## Run Tests

```bash
pytest tests/ --tb=short
```

CI runs automatically on every push and pull request to `dev` and `master`.

---

## Branch Strategy

```
master   ← stable releases only
└── dev  ← integration branch (all PRs merge here first)
    ├── feat/algo-scoring
    ├── feat/data-experiments
    ├── feat/backend-extend
    ├── feat/frontend-enhance
    └── feat/report
```

> Never push directly to `dev` or `master`. Always open a Pull Request.

---

## CreatorScore Formula

Each KOL is assigned a composite score in `[0, 1]`:

```
CreatorScore = 0.30 × norm(followers)
             + 0.30 × engagement_rate
             + 0.20 × fit_score
             + 0.20 × norm(expected_gmv / cost)
```

---

## Key Insight

Hill Climber selects expensive macro KOLs early, exhausts the budget, and gets trapped — it cannot escape by flipping one bit. Simulated Annealing accepts temporarily worse solutions, allowing it to transition to a higher-value mixed portfolio of macro and micro KOLs.

---

## License

MIT
## Experiment Insight

Hill Climber only accepts better neighboring states, so it may become trapped after choosing a locally attractive but budget-consuming combination. Simulated Annealing sometimes accepts worse states early in the search, which helps it escape local optima and discover stronger mixed KOL portfolios.
