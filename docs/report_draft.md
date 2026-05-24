# TikTok Shop KOL Matrix Optimizer Report Draft

## 1. Background

Cross-border TikTok Shop sellers often have a fixed marketing budget and thousands of possible creators across Southeast Asian markets. The business goal is not to find one strongest creator, but to build a KOL matrix that maximizes predicted GMV while keeping total hiring cost under budget.

## 2. Problem Formulation

Each solution is represented as a binary vector:

```text
S = [x1, x2, ..., xn], xi in {0, 1}
```

`xi = 1` means the i-th KOL is selected. The budget constraint is:

```text
sum(xi * cost_i) <= B
```

The predicted GMV contribution of each selected KOL is:

```text
followers_i * engagement_rate_i * fit_score_i
```

Because many optimization modules are framed as minimization problems, the project uses:

```text
cost = -total_predicted_gmv + over_budget_penalty
```

## 3. Algorithms

### Hill Climber

Hill Climber flips one bit at a time and only accepts a neighboring state if it improves the cost function. It is simple and fast, but it can get trapped in local optima.

### Simulated Annealing

Simulated Annealing also explores neighboring states, but it may accept a worse solution with probability:

```text
P = exp(-delta / T)
```

As temperature decreases, the algorithm gradually shifts from exploration to exploitation. This behavior helps it escape local optima during early search.

### Random Search Baseline

Random Search is included as a baseline to show that structured local search is more effective than sampling unrelated portfolios.

## 4. Evaluation

The experiment compares:

- Best predicted GMV
- Budget used
- Number of selected KOLs
- ROI
- Convergence curve

Run:

```bash
python experiments/run_comparison.py
```

The convergence chart is generated at:

```text
docs/figures/convergence.png
```

## 5. Expected Analysis

Hill Climber can quickly improve from an empty portfolio, but once it reaches a state where every single-bit change looks worse, it stops improving. In this project context, that may happen when it selects a few expensive macro influencers and cannot easily transition to a better combination of smaller creators.

Simulated Annealing can temporarily accept worse states, making it more likely to move away from an early locally optimal matrix. This supports the business insight that a mixed portfolio of macro and mid-tail KOLs may produce stronger predicted GMV than only selecting the most expensive creators.

## 6. System Implementation

The project includes:

- FastAPI backend for optimization requests
- Streamlit dashboard for parameter selection and visualization
- Reproducible mock KOL dataset generator
- Automated tests for the fitness function and algorithm interfaces
- Offline experiment script for report figures
