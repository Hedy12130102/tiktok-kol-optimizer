# TikTok Shop KOL Matrix Optimizer

This project is built around the **Local Search & Optimization** course module. It models TikTok Shop KOL portfolio selection in Southeast Asia as a budget-constrained combinatorial optimization problem, then compares **Hill Climber**, **Simulated Annealing**, and **Random Search**.

## Problem Formulation

- **State**: binary vector `S = [x1, x2, ..., xn]`, where `1` means selecting a KOL.
- **Constraint**: total hiring cost must not exceed the campaign budget `B`.
- **Objective**: maximize predicted GMV.
- **Cost function**: `cost = -predicted_gmv + over_budget_penalty`.

Predicted GMV is estimated as:

```text
followers * engagement_rate * fit_score
```

## Project Structure

```text
tiktok-kol-optimizer/
├── backend/                 # FastAPI routes
├── data/                    # Mock KOL data generator and sample data
├── engine/                  # Optimization models, fitness, and algorithms
├── experiments/             # Offline comparison experiment scripts
├── frontend/                # Streamlit dashboard
├── tests/                   # Pytest test cases
├── docs/                    # Report draft and generated figures
├── requirements.txt
└── README.md
```

## Quick Start

Install dependencies:

```bash
pip install -r requirements.txt
```

Generate reproducible mock KOL data:

```bash
python data/generator.py
```

Start the backend:

```bash
uvicorn backend.main:app --reload
```

Start the frontend in another terminal:

```bash
streamlit run frontend/app.py
```

Run the offline comparison experiment:

```bash
python experiments/run_comparison.py
```

Generated outputs:

- `experiments/plots/convergence.png`
- `experiments/plots/comparison_summary.csv`
- `docs/figures/convergence.png`

## API

Health check:

```bash
curl http://localhost:8000/health
```

Optimize a campaign:

```bash
curl -X POST http://localhost:8000/optimize ^
  -H "Content-Type: application/json" ^
  -d "{\"budget\":5000,\"country\":\"MY\",\"category\":\"beauty\",\"seed\":42}"
```

## Experiment Insight

Hill Climber only accepts better neighboring states, so it may become trapped after choosing a locally attractive but budget-consuming combination. Simulated Annealing sometimes accepts worse states early in the search, which helps it escape local optima and discover stronger mixed KOL portfolios.
