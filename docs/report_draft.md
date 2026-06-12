# TikTok Shop KOL Matrix Optimizer — Report Draft

---

## (a) Title

**Optimizing KOL Portfolio Selection for TikTok Shop Southeast Asia: A Multi-Algorithm Combinatorial Approach with Campaign Attribution and Metric Tracking**

---

## (b) Abstract

Cross-border TikTok Shop merchants operating in Southeast Asia face a combinatorial budget allocation problem: given a fixed marketing spend and a pool of hundreds of potential KOL creators, which subset maximizes predicted gross merchandise value (GMV)? This project formulates the problem as a variant of the 0-1 knapsack problem and implements six optimization algorithms — Simulated Annealing, Hill Climber, Random Search, Genetic Algorithm, Tabu Search, and Greedy Ranking — to solve it. A full-stack web application allows merchants to run live optimization, manage their creator database, track KOL metric trends over time via snapshot history, and close the feedback loop through post-campaign attribution (comparing predicted vs. actual GMV). A reproducible benchmark over pool sizes N ∈ {50, 100, 200, 500} (fixed budget $5,000, mean of 10 seeds) shows that the naïve Hill Climber is the weakest algorithm at every scale, and that the best algorithm's advantage over it widens from 76% at N=50 to 161% at N=500 — directly confirming the "budget-exhaustion local-optima trap" hypothesis. At scale the lead is shared by the Genetic Algorithm and the 2-opt-augmented Greedy Ranking (GA tops N=500 at $73.3K; GR tops N=200 at $64.4K), with Tabu Search matching them up to N=100. Simulated Annealing forms a middle tier under its live-default parameters, and Random Search is competitive only at small N before degrading into a proper lower-bound baseline.

---

## (c) Introduction

### 1.1 Background

TikTok Shop has become the dominant social commerce channel in Southeast Asia, with GMV growing over 300% year-on-year across markets including MY/ID/TH/PH/SG/VN (e-Conomy SEA 2024). For merchant brands, the central challenge in influencer marketing is not finding a single top creator — it is building a *portfolio* of creators whose combined reach, audience fit, and conversion rates maximize sales within a fixed budget.

Existing tools (agency spreadsheets, manual shortlisting) do not scale to thousands of creators and cannot explore the exponential combination space systematically. A brand with 100 candidate KOLs and a budget that fits 5–8 of them faces 2^100 possible portfolios.

### 1.2 Business Problem

Given:
- A fixed marketing budget B (USD)
- A pool of N candidate KOLs, each with cost c_i, followers f_i, engagement rate e_i, and market fit score s_i
- A target country and product category

Find the subset S ⊆ {1, …, N} such that:
- sum(c_i for i in S) ≤ B (budget constraint)
- sum(GMV_i for i in S) is maximized (objective)

This is the 0-1 knapsack problem, which is NP-hard in the general case and requires heuristic search for large N.

### 1.3 Objectives

1. Implement and compare six heuristic optimization algorithms on the KOL selection problem.
2. Build a deployable web application enabling real-time portfolio optimization with explainable recommendations.
3. Enable merchants to track creator metric changes over time and validate campaign predictions against real outcomes.
4. Produce a reproducible, multi-seed benchmark across pool sizes N ∈ {50, 100, 200, 500}.

---

## (d) Methodology

### 2.1 Problem Formulation

Each solution is a binary vector:

```
S = [x1, x2, ..., xN],  xi ∈ {0, 1}
```

The objective function is:

```
maximize  sum(xi × GMV_i)
subject to  sum(xi × cost_i) ≤ B
```

Because the optimization modules are implemented as minimizers, the fitness function is:

```
cost(S) = −total_predicted_gmv(S) + over_budget_penalty(S) + overlap_penalty(S)
```

where `over_budget_penalty = max(0, total_cost(S) − B) × 1e6` (a near-hard
constraint — any over-budget portfolio is dominated by every feasible one)
and `overlap_penalty(S)` discourages near-duplicate creators: each selected
pair that shares a similar follower range (within 50%), the same age group,
or the same gender skew adds a penalty weighted by 1,500 GMV-units. Country
and category are not penalised because `/optimize` already filters on them,
so every pair in a run shares those attributes.

### 2.2 GMV Estimation Model

The predicted GMV for KOL i is:

```
GMV_i = sqrt(followers_i)
      × CTR(category, country)
      × CVR(category, country)
      × AOV(category, country)
      × purchasing_power(country)
      × engagement_factor_i
      × fit_factor_i
      × 200
```

where `engagement_factor = sqrt(engagement_rate / 0.132)` and `fit_factor = sqrt(fit_score / 0.650)`. Both use `sqrt(·)` for diminishing returns and are normalised to the dataset mean (ENG_BASE=0.132, FIT_BASE=0.650) so that the average KOL gets a quality multiplier of 1.0. The `sqrt(followers)` term models diminishing returns — a 3.2M-follower Mega KOL has ~5.7× the traction of a 100K Micro KOL, not 32×. CTR, CVR, AOV, and purchasing power multipliers are calibrated from Southeast Asian industry benchmarks (see `docs/data_source.md`).

### 2.3 Algorithms

**Simulated Annealing (SA)** — Thermal-adaptive hybrid neighbourhood (single bit-flip, structural swap, and occasional multi-swap jumps). Acceptance probability P = exp(-δ/T). Parameters: T0=15,000; T_min=10; α=0.95; 150 iterations per temperature step (~143 temperature levels, ~21K evaluations). SA is the primary solver.

**Hill Climber (HC)** — Greedy local search. At each iteration it flips one *randomly chosen* bit and accepts the move only if it strictly lowers cost (raises GMV), for a fixed 5,000 iterations. Fast (O(1) evaluation per iteration) but gets trapped in local optima when expensive KOLs fill the budget and no single flip improves the portfolio.

**Random Search (RS)** — Random sampling of portfolios, where each KOL is included with a budget-aware probability so large pools do not instantly blow the budget. Lower-bound baseline demonstrating that unstructured search is significantly weaker than structured local search.

**Genetic Algorithm (GA)** — Population of 60 binary vectors evolved over 120 generations. The first individual is greedy-seeded for a strong starting point; the rest are randomly seeded at a budget-aware inclusion probability. Tournament selection (k=3), single-point crossover (probability 0.9), bit-flip mutation at rate 1/N, and elitism (the best individual always survives). Budget feasibility is enforced by the fitness penalty — there is no explicit repair operator; over-budget children are simply dominated and bred out. Diversity via population prevents premature convergence.

**Tabu Search (TS)** — Greedy-initialized. Maintains a tabu list of recently flipped indices (tenure=8 iterations) to forbid cycling. Aspiration criterion: a tabu move is accepted if it produces a new global best. Combines HC-speed with short-term memory to escape shallow local optima.

**Greedy Ranking (GR)** — Sorts KOLs by predicted GMV-per-dollar, greedily fills the budget in that order. Deterministic and instant; serves as an upper-bound reference for ratio-based heuristics.

### 2.4 Data

A synthetic dataset of 300 KOLs is generated by `data/generator.py` with the following calibrated distributions:
- Tier distribution: Nano 40%, Micro 35%, Macro 20%, Mega 5% (long-tail)
- Engagement rate: tier-specific uniform distributions (Nano 10–30%, Micro 4–15%, Macro 3–10%, Mega 2–8%), calibrated against TikTok benchmarks (Brandwatch/TTS Vibes 2025)
- Cost model: **commission-rate based** — `cost = commission_rate × expected_gmv`. Commission rates are tier-specific and *decrease* with reach (higher-tier KOLs negotiate lower rates because they deliver higher absolute volume): Nano Uniform(0.25, 0.35), Micro Uniform(0.18, 0.28), Macro Uniform(0.12, 0.22), Mega Uniform(0.05, 0.15), calibrated to TikTok Shop SEA affiliate commission ranges. Because cost scales with expected GMV, high-follower KOLs are both more valuable and more expensive, preserving the local-optimum trap structure.
- Fit score: Uniform(0.3, 1.0)
- Country + category: uniform over {MY, ID, TH, PH, SG, VN} × {beauty, fashion, home, fmcg}

The generator accepts `--num` and `--seed` parameters (`python data/generator.py --num 500 --seed 42`) for reproducibility. The commission-rate cost model preserves the classic trap: a Macro/Mega KOL may consume a large share of the budget while a portfolio of Micro+Nano KOLs at the same total cost produces higher aggregate GMV through higher engagement multipliers.

### 2.5 System Architecture

```
frontend/index.html  (single-page app, vanilla JS, Tailwind CSS)
        │
        │  HTTP/JSON
        ▼
backend/main.py      (FastAPI, /optimize endpoint, 6 algorithms)
backend/crud.py      (KOL CRUD, /kols/{id}/history, /simulate-update)
backend/campaigns.py (Campaign Attribution CRUD)
        │
        ├── engine/optimization/  (SA, HC, RS, GA, TS, GR)
        ├── engine/scoring/       (CreatorScore, Explainer, ROI)
        ├── engine/fitness.py     (objective function)
        └── data/
            ├── sample_kols.json
            ├── kol_history.json  (metric snapshots over time)
            └── campaigns.json    (attribution records)
```

The frontend is served directly from FastAPI (`/ui`) as a static single-page application, requiring no separate web server.

---

## (e) Validation / Verification

### 3.1 Experimental Setup

The primary cross-pool benchmark (`experiments/scalability.py`) runs all six algorithms at N ∈ {50, 100, 200, 500} with a **fixed budget of $5,000**, repeated over **10 seeds** (42–51); we report the mean GMV and runtime per algorithm. With the budget held fixed while the pool grows, larger N means more good, cheap creators compete for the same spend, so solution quality rises with N for every method that can exploit the richer pool. TS is evaluated only up to N=100 because its O(N²) full-neighbourhood enumeration per iteration makes it slow at larger pools.

Two supplementary experiments use a **proportional budget** of B = N × $25 at smaller pools for visualization: the convergence panels and the side-by-side bar chart (`experiments/gen_figures.py`, N ∈ {20, 50, 100}), and the single-pool convergence curve on an 8-KOL "trap" scenario (`experiments/run_comparison.py`).

---

### 3.2 Full Cross-Pool Comparison

The central experiment: all six algorithms run at N ∈ {50, 100, 200, 500} with a fixed $5,000 budget, averaged over 10 seeds. Results are reproduced verbatim from `experiments/plots/scalability_results.csv` (GMV in USD, rounded; the **best** per row in bold).

**Table 1. Mean Best Predicted GMV by Algorithm and Pool Size**
*(commission-rate cost model; fixed budget = $5,000; mean of seeds 42–51)*

| N | GA | GR | TS | RS | SA | HC | Best vs HC |
|----|-------|-------|-------|-------|-------|-------|-----------|
| 50 | 41,991 | 40,735 | 41,697 | **42,692** | 38,804 | 24,267 | +76% |
| 100 | 53,116 | 53,036 | **53,171** | 47,238 | 45,278 | 26,722 | +99% |
| 200 | 63,512 | **64,401** | — | 52,974 | 49,604 | 27,283 | +136% |
| 500 | **73,305** | 71,865 | — | 54,741 | 53,390 | 28,118 | +161% |

*TS not benchmarked at N>200 due to its O(N²) neighbourhood enumeration.*

**Key findings:**

1. **Hill Climber is the weakest at every scale, and its gap widens with N.** The best algorithm beats HC by 76% at N=50, rising monotonically to 161% at N=500. The commission-rate dataset creates a severe local-optima trap: a single random bit-flip cannot escape a portfolio that has spent its budget on a few expensive Macro/Mega creators, whereas every other method discovers mixed-tier Micro+Nano portfolios. This directly confirms the budget-exhaustion trap hypothesis.

2. **GA and 2-opt Greedy Ranking lead at scale.** GA tops N=500 ($73.3K) and GR tops N=200 ($64.4K); the two are within ~2% of each other at N≥200. Greedy Ranking is not a naïve baseline here — after its ratio-sorted fill it runs 2-opt swaps and drop-improvement, which is why it stays competitive with population search while being roughly 4–10× faster (see §3.4).

3. **TS matches the leaders up to N=100.** Tabu Search ties GA/GR at N=100 ($53.2K) and is near them at N=50; we cap it at N≤100 because its full O(N²) neighbourhood enumeration scales poorly, even with the no-improvement early stopping that keeps its wall-clock time low on the tested pools.

4. **SA is a middle tier under live defaults; RS degrades into a baseline.** SA (T0=15,000, 150 iters/level) lands below GA/GR/TS at large N — its fixed evaluation budget is spread thinly over a large landscape. Random Search is competitive at N=50 (it actually wins on this small, easy pool) but flattens out by N=500, correctly serving as the lower-bound baseline at scale.

See `docs/figures/scalability_gmv.png` for the GMV-vs-N curves and `docs/figures/algo_comparison_bars.png` for a side-by-side small-N visual (N=20/50/100, proportional budget).

---

### 3.3 Convergence Analysis

See `docs/figures/convergence_panels.png` (three-panel N=20/50/100, proportional budget) and `docs/figures/convergence.png` (the 8-KOL "trap" demo from `run_comparison.py`, budget=$5,000).

**At N=20:** Every algorithm *except* Hill Climber converges to the same optimum (~$2,540) within a few hundred iterations — the pool is small enough that GA, TS, SA, GR and even Random Search all find it. HC alone is trapped well below (~$1,780), unable to improve its greedy portfolio with a single bit-flip.

**At N=50:** GA and RS settle at the top (~$8,500) quickly. SA is the interesting case: it sits on an intermediate shelf (~$6,600) for most of the run and only jumps up to ~$8,500 late (around iteration 8,000), illustrating the temperature-driven escape from a local optimum. TS and GR plateau a little lower (~$7,300–7,800), and HC is trapped at ~$5,100 and never escapes.

**At N=100:** GA, TS and GR jump to the best value (~$26K) almost immediately thanks to greedy seeding / ratio-sorting, and RS reaches a respectable ~$22K. SA climbs *steadily* from a low start but, under its fixed evaluation budget, finishes well below the leaders (~$17–18K) at this scale. HC stays flat near the bottom. This panel is the clearest picture of why SA forms a middle tier at large N in §3.2.

**8-KOL trap demo (`convergence.png`):** On the hand-built scenario where one expensive Macro creator tempts a greedy solver, all global methods (SA, GA, TS) and Greedy Ranking reach ~$37–38K while HC settles slightly lower (~$36.4K), confirming the trap on a minimal, human-readable instance.

---

### 3.4 Execution Time Scaling

See `docs/figures/scalability_time.png`. Mean wall-clock seconds over 10 seeds (from `scalability_results.csv`):

| Algorithm | N=50 | N=100 | N=200 | N=500 |
|-----------|------|-------|-------|-------|
| Greedy Ranking | 0.03s | 0.06s | 0.11s | 0.35s |
| Random Search | 0.23s | 0.26s | 0.35s | 0.57s |
| Hill Climber | 0.28s | 0.25s | 0.29s | 0.37s |
| Genetic Algorithm | 0.42s | 0.57s | 0.75s | 1.37s |
| Tabu Search | 0.52s | 1.00s | — | — |
| Simulated Annealing | 1.44s | 1.88s | 2.53s | 3.96s |

Greedy Ranking is the fastest method by an order of magnitude *and* one of the strongest at scale, making it the best quality-per-second option for interactive use. SA is the slowest because it performs the most evaluations (~143 temperature levels × 150 iterations); its runtime grows roughly linearly in N. TS's no-improvement early stopping keeps it near 1s through N=100, but its per-iteration O(N²) neighbourhood scan is why we still cap it at N≤100. GA sits in between, buying its strong large-N quality with ~1.4s at N=500.

---

### 3.5 SA Parameter Sensitivity

See `docs/figures/sensitivity_heatmap.png` (single-seed SA grid at N=100, budget=$2,500, so absolute GMV is lower than the §3.2 table). The clearest signal is that the lowest initial temperature, T0=500, is consistently the weakest column — too little early exploration leaves SA stuck near its starting point, HC-like. Across the rest of the grid (T0 ≥ 1,000) the surface is fairly flat and noisy: no single (T0, α) cell dominates, and cell-to-cell differences are on the order of single-seed variance. The practical takeaway is that SA is robust to these two hyper-parameters once T0 is not pathologically low; the live default (T0=15,000, α=0.95) sits in this broad, well-behaved region. A multi-seed average per cell would smooth the remaining noise — `engine/evaluation/sensitivity.py` does exactly this (5 repeats) for a cleaner surface.

---

### 3.6 Campaign Attribution Accuracy

The post-campaign attribution feature records actual GMV after campaigns complete and computes `accuracy_pct = actual / predicted × 100` (implemented in `backend/campaigns.py`, covered by `tests/test_campaigns.py`). This closes the prediction→outcome loop so a merchant can see, per campaign, how close the optimizer's predicted GMV was to the realised figure. Because the project ships with synthetic data and no real TikTok Shop sales feed, we do not report a calibrated accuracy number here — the attribution pipeline is validated functionally by the campaign CRUD tests rather than against ground-truth GMV. Validating calibration against real affiliate sales data is left to future work (see §f).

---

### 3.7 Automated Tests

```
tests/test_fitness.py        — fitness function + budget penalty        ( 6)
tests/test_algorithms.py     — all 6 algorithm interfaces               (34)
tests/test_scoring.py        — CreatorScore weighting + normalisation   ( 7)
tests/test_creator_score.py  — CreatorScore edge cases                  ( 3)
tests/test_explainer.py      — recommendation reason generation         ( 4)
tests/test_sa_comparison.py  — SA vs HC trap scenario                   ( 1)
tests/test_sa_improved.py    — SA neighbourhood / acceptance behaviour  ( 3)
tests/test_api.py            — core API endpoint tests                  (31)
tests/test_campaigns.py      — campaign attribution CRUD                (13)
tests/test_kol_history.py    — KOL history tracking + simulate-update   (12)
```

Total: **114 tests**. Run with: `pytest tests/ --tb=short`

---

## (f) Conclusion

This project demonstrates that every structured search method consistently outperforms the naïve random-flip Hill Climber for the KOL portfolio selection problem across all tested pool sizes (N=50 to N=500). The performance gap between HC and the best algorithm widens monotonically from 76% at N=50 to 161% at N=500, directly confirming the budget-exhaustion local-optima trap hypothesis: as more diverse KOLs become available, HC's inability to escape its initial portfolio with a single bit-flip becomes increasingly costly. At scale the lead is shared by the Genetic Algorithm and the 2-opt-augmented Greedy Ranking — GA wins at N=500 and GR at N=200, within ~2% of each other — with Tabu Search matching them up to N=100. Notably, Greedy Ranking delivers near-best quality at an order-of-magnitude lower runtime, making it the strongest choice for interactive use, while GA is the method to beat when pools grow large and runtime is less constrained. Simulated Annealing, under its live-default parameters, trails the leaders at large N; tuning its evaluation budget upward (more iterations per temperature level) is the most direct lever for closing that gap.

Beyond the optimization core, the system adds two practically important features: **KOL metric trend tracking** (time-series snapshots enabling merchants to observe creator performance drift over time) and **campaign attribution** (closing the feedback loop between algorithm predictions and real campaign outcomes). Together, these transform the tool from a one-shot recommender into a campaign management platform.

Future work could extend the GMV model with actual TikTok Shop API data if partner access becomes available, add multi-objective optimization (GMV + audience diversity), and explore reinforcement learning approaches that improve the GMV model from attribution feedback over time.
