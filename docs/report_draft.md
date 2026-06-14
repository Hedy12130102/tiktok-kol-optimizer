# TikTok Shop KOL Matrix Optimizer — Report Draft

---

## (a) Title

**Optimizing KOL Portfolio Selection for TikTok Shop Southeast Asia: A Multi-Algorithm Combinatorial Approach with Campaign Attribution and Metric Tracking**

---

## (b) Abstract

Cross-border TikTok Shop merchants operating in Southeast Asia face a combinatorial budget allocation problem: given a fixed marketing spend and a pool of hundreds of potential KOL creators, which subset maximizes predicted gross merchandise value (GMV)? This project formulates the problem as a variant of the 0-1 knapsack problem and implements six optimization algorithms — Simulated Annealing, Hill Climber, Random Search, Genetic Algorithm, Tabu Search, and Greedy Ranking — to solve it. A full-stack web application allows merchants to run live optimization, manage their creator database, track KOL metric trends over time via snapshot history, and close the feedback loop through post-campaign attribution (comparing predicted vs. actual GMV). A reproducible benchmark over pool sizes N ∈ {50, 100, 200, 500} (fixed budget $5,000, mean of 10 seeds) shows that the naïve Hill Climber is the weakest algorithm at every scale — and is the only method whose GMV *falls* as the pool grows — while the best algorithm's advantage over it widens from 50% at N=50 to 200% at N=500, directly confirming the "budget-exhaustion local-optima trap" hypothesis. At scale the lead is shared by the Genetic Algorithm and the 2-opt-augmented Greedy Ranking (GA tops N=50/100/500, reaching $73.2K; GR ties it at N=200 at $60.0K), with Tabu Search within a few percent up to N=100. GA wins on solution quality while Greedy Ranking matches it within ≈2% at large N while running 2–8× faster, making GR the best quality-per-second default; Simulated Annealing forms a middle tier under its live-default parameters, and Random Search trails the structured methods at every scale as a proper lower-bound baseline.

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

### 1.4 How a Merchant Uses the System

From the merchant's point of view the whole tool is five simple steps with one feedback loop:

```mermaid
flowchart TD
    A([Start]) --> B["1 · Set your budget, target market<br/>and product category"]
    B --> C["2 · The app finds the best mix of<br/>creators that fits your budget"]
    C --> D["3 · Review the picks — each with a<br/>plain-English reason"]
    D --> E{Enough creators<br/>in your niche?}
    E -->|No| F["Import your own creators, or use the<br/>simulator to see how many you need"]
    F --> B
    E -->|Yes| G["4 · Launch the campaign"]
    G --> H["5 · Enter the actual sales when it ends"]
    H --> I["See predicted vs actual accuracy —<br/>each campaign sharpens the next"]
    I --> A
```

---

## (d) Methodology

### 2.0 Research & Information Methodology

Before any code, the project followed a deliberate four-step process to identify, select, process, and analyze the information the system depends on.

**Identify.** We first framed the business problem (Section c) and decomposed it into the information it requires: (i) a *creator model* — what attributes describe a KOL and drive sales (followers, engagement, audience fit, demographics); (ii) a *market model* — how a view converts to revenue in each Southeast-Asian market and category (click-through, conversion, order value, purchasing power); and (iii) a *cost model* — how creators are actually paid on TikTok Shop. This told us exactly which quantities had to be sourced or estimated.

**Select.** Because TikTok exposes no public creator API and real fees/audience data are commercially confidential (NDAs), primary collection was infeasible, so we selected *secondary* sources under four criteria: authority (named industry analysts, consultancies, and government bodies), recency (2024–2026), regional relevance (SEA / the six target markets), and public availability. The retained set — IMF WEO, e-Conomy SEA (Google/Temasek/Bain), Cube Asia, Statista, McKinsey, Brandwatch/TTS Vibes, Kantar/NielsenIQ — is mapped to each parameter group in §2.4.1. In parallel we selected the *algorithms* to study as a deliberate spectrum from naïve to advanced (Random Search and Hill Climber as controls; Greedy Ranking as a constructive heuristic; Simulated Annealing, Genetic Algorithm, and Tabu Search as metaheuristics) so the comparison isolates the value of each search strategy.

**Process.** Raw benchmark figures were processed into (i) lookup tables of CTR/CVR/AOV/purchasing-power keyed by (category, country) (§2.4.2, §5 of `data_source.md`); (ii) a parametric GMV model with diminishing returns and quality normalisation (§2.2); and (iii) a reproducible synthetic-data generator that samples a realistic long-tailed creator population with tier-specific engagement and commission distributions (§2.4.3–2.4.4). The optimization problem itself was processed into a binary-vector formulation with a single scalar fitness function combining GMV, a near-hard budget penalty, and an audience-overlap penalty (§2.1).

**Analyze.** Finally, the processed artefacts are analyzed empirically (Section e): a reproducible, multi-seed benchmark measures solution quality and runtime across pool sizes; convergence and parameter-sensitivity studies explain *why* the algorithms differ; generated distributions are checked back against the source benchmarks; and 111 automated tests guard functional correctness. The remainder of Section (d) details each model the analysis rests on.

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

where `engagement_factor = sqrt(engagement_rate / 0.132)` and `fit_factor = sqrt(fit_score / 0.650)`. Both use `sqrt(·)` for diminishing returns and are normalised to the dataset mean (ENG_BASE=0.132, FIT_BASE=0.650) so that the average KOL gets a quality multiplier of 1.0. The `sqrt(followers)` term models diminishing returns — a 3.2M-follower Mega KOL has ≈5.7× the traction of a 100K Micro KOL, not 32×. CTR, CVR, AOV, and purchasing power multipliers are calibrated from Southeast Asian industry benchmarks (full tables and provenance in §2.4 and `docs/data_source.md`).

**Worked example (sanity check).** A Micro beauty creator in Malaysia with 100,000 followers, engagement_rate = 0.10, fit_score = 0.80:

```
traction          = sqrt(100,000)            = 316.23
funnel  (CTR×CVR) = 0.035 × 0.085            = 0.0029750
AOV / PP (MY)     = $42 × 1.0
engagement_factor = sqrt(0.10 / 0.132)       = 0.870
fit_factor        = sqrt(0.80 / 0.650)       = 1.109
GMV = 316.23 × 0.0029750 × 42 × 1.0 × 0.870 × 1.109 × 200 ≈ $7,630
```

This lands within the plausible range for a single mid-tier beauty creator's monthly attributable GMV in the MY market, confirming the normalisation constant (SCALE = 200) is correctly scaled. A Mega creator (3.2M followers, same quality) would earn ≈ √(3.2M/100K) ≈ 5.66× the traction but, because commission cost also scales with GMV (§2.4.4), not 5.66× the *value-per-dollar* — which is exactly what makes mixed-tier portfolios optimal.

### 2.3 Algorithms

**Simulated Annealing (SA)** — Thermal-adaptive hybrid neighbourhood (single bit-flip, structural swap, and occasional multi-swap jumps). Acceptance probability P = exp(-δ/T). Parameters: T0=15,000; T_min=10; α=0.95; 150 iterations per temperature step (≈143 temperature levels, ≈21K evaluations). SA is the primary solver.

**Hill Climber (HC)** — Greedy local search. At each iteration it flips one *randomly chosen* bit and accepts the move only if it strictly lowers cost (raises GMV), for a fixed 5,000 iterations. Fast (O(1) evaluation per iteration) but gets trapped in local optima when expensive KOLs fill the budget and no single flip improves the portfolio.

**Random Search (RS)** — Random sampling of portfolios, where each KOL is included with a budget-aware probability so large pools do not instantly blow the budget. Lower-bound baseline demonstrating that unstructured search is significantly weaker than structured local search.

**Genetic Algorithm (GA)** — Population of 60 binary vectors evolved over 120 generations. The first individual is greedy-seeded for a strong starting point; the rest are randomly seeded at a budget-aware inclusion probability. Tournament selection (k=3), single-point crossover (probability 0.9), bit-flip mutation at rate 1/N, and elitism (the best individual always survives). Budget feasibility is enforced by the fitness penalty — there is no explicit repair operator; over-budget children are simply dominated and bred out. Diversity via population prevents premature convergence.

**Tabu Search (TS)** — Greedy-initialized. Maintains a tabu list of recently flipped indices (tenure=8 iterations) to forbid cycling. Aspiration criterion: a tabu move is accepted if it produces a new global best. Combines HC-speed with short-term memory to escape shallow local optima.

**Greedy Ranking (GR)** — Sorts KOLs by predicted GMV-per-dollar, greedily fills the budget in that order. Deterministic and instant; serves as an upper-bound reference for ratio-based heuristics.

### 2.3.1 Algorithm Improvement Measures

A core deliverable of this project is not merely running textbook algorithms but *improving* them for this specific problem. Each solver carries concrete, deliberate enhancements over its naïve form, and one (Hill Climber) is kept naïve on purpose as the experimental control.

**Simulated Annealing — thermal-adaptive hybrid neighbourhood.**
The textbook SA neighbourhood is a single bit-flip, which changes the portfolio size one creator at a time and therefore struggles to "trade" one Mega KOL for several Micros (the move would have to remove the Mega and add several Micros across many separate, mostly-worsening flips). Our operator instead mixes three move types per iteration:
- **40% single bit-flip** — fine-grained add/remove.
- **≈50% structural swap** — drop one selected KOL and add one unselected KOL, keeping total cost roughly constant while exploring budget-equivalent alternatives.
- **10% multi-swap (2–3 simultaneous flips)** — large jumps that let the search leap between the "many small KOLs" and "few big KOLs" basins in a single step, crucial on small filtered pools.

We also add an **empty-portfolio guard** (force-add a random KOL if a neighbour selects nothing) and **calibrate the temperature to the GMV landscape** (single-KOL GMV deltas are ≈$2K–$8K, so T0 = 15,000 yields an initial acceptance probability of ≈60–85% for worsening moves, cooling to near-zero acceptance by the final temperature level).

**Genetic Algorithm — greedy seeding + budget-aware initialisation + elitism.**
Three enhancements over a random-initialised GA: (1) **individual 0 is a greedy ratio-sorted solution**, giving the population an immediately strong member to recombine; (2) **the remaining individuals are seeded at a budget-aware inclusion probability** `p = clamp(budget / avg_cost / N, 0.1, 0.6)` so the initial population is roughly feasible instead of mostly over-budget (a uniform 50% inclusion would put almost every individual far over budget at large N); (3) **elitism** copies the best individual into each new generation, guaranteeing monotonic non-degradation. Budget feasibility is handled by the fitness penalty rather than an explicit repair operator, so infeasible children are simply out-competed and bred out.

**Tabu Search — aspiration criterion + no-improvement early stopping + randomised tie-breaking.**
Beyond the basic tabu list (tenure = 8), we add: (1) an **aspiration criterion** that overrides the tabu status of a move if it produces a new global best (never refuse a genuinely improving move); (2) **no-improvement early stopping** (`patience = 150`) that terminates once the global best has stalled, cutting wall-clock time dramatically without quality loss (this is why TS runs in ≈1 s at N=100 rather than tens of seconds); and (3) **randomised tie-breaking** (30% chance to accept an equal-cost neighbour) to avoid deterministic cycling on plateaus.

**Greedy Ranking — three-phase local search, not a naïve fill.**
The "baseline" is itself improved into a small local-search pipeline: **Phase 1** ratio-sorted greedy fill; **Phase 2** 2-opt swap (replace a selected KOL with an unselected one whenever it lowers cost and stays within budget); **Phase 3** drop-improvement (remove any KOL whose removal lowers cost — this matters when every KOL fits the budget and the only gains come from cutting audience-overlap penalty). These phases are why GR is competitive with the metaheuristics at scale (§3.2) despite being deterministic and ≈10× faster.

**Random Search — budget-aware sampling.**
Pure uniform 50/50 sampling would put almost every sampled portfolio massively over budget at large N (and thus at the same `−GMV + huge penalty` cost), making RS a degenerate, uninformative baseline. We instead include each KOL with probability `≈ budget / avg_cost / N`, so sampled portfolios sit near the feasible boundary and RS remains a *meaningful* lower bound rather than a flat line.

**Hill Climber — deliberately naïve (the control).**
HC is intentionally left as a random-flip, accept-if-better local search with **no** swap moves, restarts, or memory. Its role is to isolate the value of every enhancement above: any algorithm that beats HC is demonstrating the worth of its specific improvement (temperature, population, memory, or ratio-greedy construction).

### 2.4 Data

A synthetic dataset of 300 KOLs is generated by `data/generator.py` (serialised to `data/sample_kols.json` and `data/influencers_mock.csv`). This section documents where every parameter comes from, why the resulting distributions are realistic, and how we verified them. The complete tables live in `docs/data_source.md`; the essentials and their justification are reproduced here.

#### 2.4.1 Why synthetic data, and the provenance of every parameter

The data is fully simulated rather than scraped, for two unavoidable reasons: (1) **there is no public TikTok creator API** for pricing, demographics, or historical performance, and scraping is rate-limited and prohibited by their Terms of Service; (2) **real influencer fees and audience data are commercially confidential**, covered by brand–agency–creator NDAs. Synthetic data sidesteps both the legal and privacy risk while still letting us evaluate algorithms on a statistically plausible landscape.

Crucially, "synthetic" does not mean "arbitrary." Every market multiplier is calibrated to a published industry benchmark:

| Parameter group | Source(s) |
|---|---|
| CTR / CVR by category × country | TikTok Shop SEA Partner Reports H1 2024; Cube Asia *Social Commerce in SEA* 2024; SimilarWeb / Shopify Global Ecommerce Benchmarks 2024 |
| AOV by category × country | Statista *Digital Market Outlook — SEA eCommerce* 2024; McKinsey *State of Fashion: Technology* 2024 |
| Purchasing-power multiplier | IMF World Economic Outlook Oct 2024 (GDP/capita); World Bank 2024; e-Conomy SEA 2024 (Google/Temasek/Bain) |
| Tier-specific engagement rates | Brandwatch / TTS Vibes 2025 TikTok engagement benchmarks |
| Tier-specific commission rates | TikTok Shop SEA affiliate guidelines (TTS Vibes 2025; ContentGrip 2026) |
| FMCG / Vietnam specifics | Kantar & NielsenIQ FMCG Social Commerce SEA 2024; AsiaKOL Vietnam Influencer Guide 2024 |

#### 2.4.2 Market conversion parameters and their rationality

The GMV model (§2.2) draws four market multipliers from lookup tables keyed by (category, country):

- **CTR 2.2–4.4%** and **CVR 4.5–10.8%** — both are highest for FMCG (impulse, low price friction) and lowest for Home & Living (long consideration cycle), and highest in TH/SG, lowest in PH. These ranges sit squarely within published social-commerce benchmarks, where video-driven discovery yields far higher click-through than display advertising (typically <1%) but needs strong creative alignment to convert.
- **AOV $11–$72** — highest for Fashion and in Singapore (premium market), lowest for FMCG and in Vietnam (price-sensitive, low-ticket). Magnitudes match reported per-order baskets for each vertical.
- **Purchasing-power multiplier 0.55–1.3** — anchored to GDP/capita: SG 1.3 (≈$90.7K/cap, highest checkout completion and basket size), MY 1.0 baseline (≈$13.5K), down to VN 0.55 (≈$4.7K, huge but low-ticket TikTok base). This term captures residual behavioural effects (checkout completion, payment success, returns) beyond raw AOV.

Because these multipliers are *relative*, the absolute GMV scale is then fixed by the single constant SCALE = 200, validated by the worked example in §2.2 (a 100K beauty/MY creator ≈ $7.6K).

#### 2.4.3 Population distributions and their rationality

The 300-creator population is sampled as follows, with each choice justified against reality:

- **Tier distribution — Nano 40% / Micro 35% / Macro 20% / Mega 5%.** A deliberate long tail: nano/micro creators vastly outnumber celebrity-tier accounts in any real market. This is the distribution that *creates* the optimisation problem — a flat distribution would make every portfolio interchangeable.
- **Engagement rate — tier-specific and decreasing with reach** (Nano U[0.10, 0.30] → Mega U[0.02, 0.08], with ±15% per-creator noise). Smaller accounts have tighter, more responsive communities; this inverse relationship is well documented. We verified the *generated* sample against the benchmark it targets:

| Tier | Generated avg | Generated range | Real benchmark (Brandwatch/TTS 2025) |
|------|--------------|-----------------|--------------------------------------|
| Nano  | 19.6% | 10.0–30.0% | 17–18% |
| Micro | 9.8%  | 4.2–17.1%  | 6–8%   |
| Macro | 7.1%  | 3.3–10.5%  | 5–7%   |
| Mega  | 5.7%  | 2.9–8.2%   | 4–6%   |

The generated averages run slightly hot but preserve the correct ordering and spread — the property the optimizer actually depends on. (An earlier `100000/followers` formula was discarded because it capped *every* sub-100K creator at exactly 30%, destroying tier differentiation; see `data_source.md §6.2`.)
- **Fit score — U[0.3, 1.0].** Bounded above zero because any creator a brand is even considering has at least minimal market alignment.
- **Country, category, gender, age — uniform** over their valid sets. These are not the focus of the optimisation (country+category are filtered upstream before optimisation), so uniform sampling is the neutral choice.

#### 2.4.4 Cost model and the local-optimum trap

Cost is **commission-rate based**: `cost = commission_rate × expected_gmv`, modelling the TikTok Shop affiliate structure where a creator earns a percentage of the GMV they drive. Commission rates are tier-specific and *decrease* with reach (big accounts deliver volume and negotiate lower rates): Nano U[0.25, 0.35], Micro U[0.18, 0.28], Macro U[0.12, 0.22], Mega U[0.05, 0.15].

This single design choice is what makes the problem hard and interesting. Because cost scales with GMV, a Macro/Mega creator is *both* more valuable *and* more expensive in roughly the same proportion — so spending the whole budget on one big account is rarely optimal. A portfolio of Micro+Nano creators at the same total cost typically produces higher aggregate GMV via superior engagement multipliers (the `sqrt(followers)` diminishing-returns term ensures the big account's reach advantage is sub-linear). This is the **budget-exhaustion local-optimum trap**: a greedy or single-flip solver that grabs the tempting big account first cannot escape, while temperature (SA), population recombination (GA), tabu memory (TS), and ratio-greedy construction with 2-opt (GR) each escape it by a different mechanism (§3.2–3.3).

The generator is fully reproducible — `generate_kols(num=300, seed=42)` (CLI: `python data/generator.py --num 500 --seed 42`) always yields the same dataset, which is essential for the fair, repeatable algorithm comparison in §3.

### 2.5 System Architecture

The system is a four-layer monolith:

1. **Client** — a single-page app (`frontend/index.html`, vanilla JS + Tailwind) with the Landing, Optimizer, Creators, Campaigns, and Creator Pool Simulator views.
2. **API** — FastAPI (`main.py` optimization + simulator, `crud.py` creator management, `campaigns.py` attribution) that both serves the SPA as static files and exposes the typed REST surface; integration connectors (TikTok Creator Marketplace, TikTok Shop, third-party analytics) are roadmap stubs.
3. **Optimization engine** — pure Python with no web/DB dependencies: `engine/optimization/` (the six solvers), `engine/scoring/` (CreatorScore, Explainer, ROI), `engine/fitness.py` (the objective), and `engine/models.py` (KOL, tiers, the SEA GMV model, candidate shortlisting).
4. **Data** — JSON persistence (`sample_kols.json`, `kol_history.json`, `campaigns.json`), seeded offline by `build_seed.py` (from real FastMoss CSV/Excel) and `fill_slices.py` (synthetic slice fill), with `generator.py` producing the synthetic pools used by the simulator and benchmarks.

Key architectural choices: the engine takes no web/database dependencies, so it is unit-testable in isolation and reusable from both the API and the `experiments/` harness; candidate shortlisting (top-K by CreatorScore before optimization) decouples `/optimize` latency from library size; and all persistence is plain JSON behind a small data-access seam (`KOL_DATA_PATH` is env-overridable), which is what lets the test suite run against an isolated dataset without touching production data.

---

## (e) Validation / Verification

### 3.0 Validation Strategy

The project's outcomes are validated at four complementary levels, so that "it works" means both *correct* and *effective*:

1. **Functional correctness (does the code do what it claims?)** — 111 automated `pytest` tests assert algorithm interface contracts (valid binary states, budget compliance), fitness/penalty behaviour, scoring and explainer logic, and the full REST surface (optimization, CRUD, KOL history, campaign attribution). They run in CI on every push (§3.9).
2. **Empirical effectiveness (does it produce good portfolios?)** — controlled simulation experiments measure *solution quality* (predicted GMV) and *runtime* across pool sizes, with every algorithm compared on identical data under identical budgets (§3.1–3.6).
3. **Data plausibility (is the input model realistic?)** — the synthetic generator's output distributions are checked back against the published benchmarks they target (e.g. generated vs real engagement rates per tier, §2.4.3), and the GMV formula is sanity-checked with a worked example (§2.2).
4. **Reproducibility (can the results be trusted and repeated?)** — fixed seeds, shared generated pools, and multi-seed averaging make every number in this section regenerable from `experiments/` with no hidden state.

The subsections below detail the experiments, simulations, and evaluations that implement levels 2–4; level 1 is summarised in §3.9.

### 3.1 Experimental Setup

The primary cross-pool benchmark (`experiments/scalability.py`) runs all six algorithms at N ∈ {50, 100, 200, 500} with a **fixed budget of $5,000**, repeated over **10 seeds** (42–51). For each (algorithm, N) cell we record mean ± standard deviation of both the best predicted GMV and the wall-clock runtime.

**Fairness controls.** Within a given (N, seed) trial, all six algorithms receive the *identical* generated KOL pool (the seed controls dataset generation) and are each themselves seeded with the same value, so any quality difference is attributable to the algorithm, not to luck in the data or in the random draws. The fitness function, budget, and overlap penalty are shared across all solvers.

**Why these choices.**
- *Ten seeds, not one.* The per-cell standard deviations are large (often $8K–$14K at N ≤ 200; see the σ column in `scalability_results.csv`), so any single-seed ranking is unreliable. Averaging ten independent datasets is what lets us make defensible claims like "HC is worst at every N." Differences smaller than roughly one σ (e.g. the N=50 ordering among GA/GR/TS/RS) should be read as ties.
- *Fixed budget, growing N.* Holding the budget at $5,000 while the pool grows means larger N supplies *more good, cheap Micro/Nano creators competing for the same spend*. Every method that can exploit the richer pool improves with N, while a method stuck in the first greedy basin (HC) does not — so the *relative* gap is itself a measurement of search quality.
- *TS capped at N ≤ 100.* Tabu Search enumerates all N single-flip neighbours every iteration (O(N²) total work); even with early stopping this is the one method whose cost grows quadratically, so we do not benchmark it at N > 100 to avoid skewing runtime comparisons.

Two supplementary experiments use a **proportional budget** of B = N × $25 at smaller pools for visualization: the convergence panels and the side-by-side bar chart (`experiments/gen_figures.py`, N ∈ {20, 50, 100}), and the single-pool convergence curve on an 8-KOL "trap" scenario (`experiments/run_comparison.py`). These use a proportional budget specifically so the number of selected creators stays in a readable 5–8 range as N changes, making the convergence *shape* legible.

---

### 3.2 Full Cross-Pool Comparison

The central experiment: all six algorithms run at N ∈ {50, 100, 200, 500} with a fixed $5,000 budget, averaged over 10 seeds. Results are reproduced verbatim from `experiments/plots/scalability_results.csv` (GMV in USD, rounded; the **best** per row in bold).

**Table 1. Mean Best Predicted GMV by Algorithm and Pool Size**
*(commission-rate cost model; fixed budget = $5,000; mean of seeds 42–51)*

| N | GA | GR | TS | RS | SA | HC | Best vs HC |
|----|-------|-------|-------|-------|-------|-------|-----------|
| 50 | **41,448** | 39,851 | 41,201 | 36,917 | 36,932 | 27,631 | +50% |
| 100 | **48,370** | 46,524 | 47,040 | 42,682 | 43,538 | 27,082 | +79% |
| 200 | 59,917 | **60,042** | — | 51,291 | 53,137 | 25,998 | +131% |
| 500 | **73,172** | 71,924 | — | 56,248 | 59,610 | 24,421 | +200% |

*TS not benchmarked at N>100 due to its O(N²) neighbourhood enumeration. Per-cell σ is large (≈$5K–$12K), so differences within ~one σ — e.g. GA/TS/GR at N=50 and GA/GR at N=200 — should be read as ties.*

**Key findings:**

1. **Hill Climber is the weakest at every scale, and is the only method whose GMV *falls* with N.** While every structured method climbs as the pool grows, HC actually *declines* ($27.6K at N=50 → $24.4K at N=500): a bigger pool offers more tempting expensive creators for it to commit its budget to, and its single random bit-flip can never escape that basin. The best algorithm beats HC by 50% at N=50, rising monotonically to **+200% at N=500** (a ~3× gap). This is the budget-exhaustion local-optima trap, measured directly — and the *widening* gap is itself the value of structured search.

2. **GA leads on quality almost everywhere; 2-opt Greedy Ranking ties it at scale.** GA tops N=50, N=100 and N=500 ($73.2K); GR edges it at N=200 ($60.0K vs $59.9K) and trails it by only ≈2% at N=500. The two are statistically tied at N≥200. GR is not a naïve baseline — after its ratio-sorted fill it runs 2-opt swaps and drop-improvement, which is why it matches population search while running 2–8× faster (see §3.6).

3. **TS matches the leaders up to N=100.** Tabu Search is within a few percent of GA at both N=50 ($41.2K) and N=100 ($47.0K); we cap it at N≤100 because its full O(N²) neighbourhood enumeration scales quadratically (its runtime already more than doubles from N=50 to N=100; §3.6).

4. **SA is a robust middle tier; RS is a clear baseline at every N.** SA (T0=15,000, 150 iters/level) climbs steadily but lands below GA/GR/TS at every scale — its fixed evaluation budget, spread from a cold (empty) start over a growing landscape, under-delivers versus the greedy-seeded leaders. Random Search rises with N but falls progressively further behind the leaders (≈−11% vs GA at N=50, ≈−23% at N=500), correctly serving as the lower-bound baseline — though it still comfortably beats the trapped HC throughout.

See `docs/figures/scalability_gmv.png` for the GMV-vs-N curves and `docs/figures/algo_comparison_bars.png` for a side-by-side small-N visual (N=20/50/100, proportional budget).

---

### 3.3 Comparative Analysis of All Six Algorithms

Pulling the GMV (§3.2), runtime (§3.6) and convergence (§3.5) evidence together, each algorithm occupies a distinct point in the quality/speed/robustness space:

**Greedy Ranking (GR) — the efficiency champion.** Deterministic, ≈0.02 s at N≤200 (rising to ≈0.42 s at N=500 as the 2-opt swap phase becomes O(N²)), and yet 2nd-best at N=500 and best at N=200. Its three-phase design (ratio-sort → 2-opt → drop) extracts almost all the available GMV in a single forward pass plus a handful of local repairs. Its only structural weakness is that it commits to one greedy basin: with no stochastic component it cannot discover a portfolio that requires temporarily *worsening* the GMV/cost ratio. On this dataset that basin happens to be excellent, so GR shines — but on an adversarial instance designed to punish ratio-greedy choices it would have no escape hatch.

**Genetic Algorithm (GA) — the quality champion.** Best at N=50, N=100 and N=500 ($73.2K), and a statistical tie with GR at N=200. Crossover is the differentiator: it recombines good *partial* portfolios ("these three high-ROI Nano creators" + "this efficient Macro") that trajectory methods can only reach one flip at a time. The cost is runtime (≈0.90 s at N=500 — 2nd-slowest, behind SA) and the largest hyper-parameter surface (population, generations, tournament size, crossover/mutation rates). Greedy seeding guarantees it never does *worse* than GR's starting point, and elitism guarantees monotonic improvement.

**Tabu Search (TS) — strong but quadratic.** Within a few percent of GA through N=100 ($47.0K) by systematically scanning the full neighbourhood and using memory to avoid cycling. The aspiration criterion prevents it from refusing a genuinely best-ever move, and early stopping keeps it fast in wall-clock terms. The hard limit is algorithmic: the O(N²) per-iteration scan makes it the wrong tool for large pools — its runtime already more than doubles from N=50 (0.30 s) to N=100 (0.73 s) — which is why we cap it at N ≤ 100.

**Simulated Annealing (SA) — robust escape, middle-tier output here.** SA is the only method with a *provable* mechanism for escaping local optima (Metropolis acceptance), and its convergence curves (§3.5) show the characteristic late jump as the temperature falls. But under its live-default evaluation budget (spread over the whole landscape, starting from an *empty* portfolio rather than a greedy seed) it lands below GA/GR/TS at every scale — though it cleanly separates from the RS baseline at large N ($59.6K vs $56.2K at N=500). It is the slowest method because it performs the most evaluations. SA's quality is the most *tunable* of the six — more iterations per temperature level is the direct lever (see Conclusion, future work).

**Random Search (RS) — honest baseline.** With budget-aware sampling it rises with N ($36.9K→$56.2K) but falls progressively further behind the leaders (≈−11% vs GA at N=50, ≈−23% at N=500) as the feasible space explodes. It has no learning mechanism, so it is exactly the lower bound a structured method should beat — clearly trailing GA/GR at every N while still comfortably beating the trapped HC.

**Hill Climber (HC) — the trapped control.** Worst at every N by a wide margin, and the *only* method that gets worse as N grows ($27.6K→$24.4K). It is fast and simple, but the naïve random-flip neighbourhood with accept-if-better cannot trade an expensive committed creator for a better-value bundle, so it never leaves its first basin. HC is the yardstick: the +50%→+200% gap over HC *is* the measured value of structured search.

**Table 2. Algorithm Profiles (at a glance)**

| Algorithm | Class | Per-run cost | GMV at N=500 | Determinism | Core improvement | Main limitation | Best used when |
|---|---|---|---|---|---|---|---|
| Greedy Ranking | Constructive + local search | ≈0.02 s @N≤200, 0.42 s @N=500 | $71.9K (2nd) | Deterministic | 2-opt + drop phases | Single greedy basin, no stochastic escape | Interactive / real-time; need a fast strong answer |
| Genetic Algorithm | Population metaheuristic | ≈0.90 s | **$73.2K (best)** | Stochastic | Greedy seed + budget-aware init + elitism | 2nd-slowest; many hyper-parameters | Large pools, quality matters most, runtime relaxed |
| Tabu Search | Memory-based local search | ≈0.73 s @N=100 (O(N²)) | n/a (capped) | Mostly deterministic | Aspiration + early stop | Quadratic per-iteration scan | Small/medium pools (N ≤ 100) |
| Simulated Annealing | Trajectory metaheuristic | ≈2.67 s (slowest) | $59.6K (mid) | Stochastic | Thermal-adaptive hybrid moves | Fixed eval budget thin at large N; empty start | Rugged landscapes; when tuned for more evaluations |
| Random Search | Unstructured sampling | ≈0.38 s | $56.2K (mid-low) | Stochastic | Budget-aware inclusion prob | No learning; plateaus | Sanity-check lower bound only |
| Hill Climber | Naïve local search | ≈0.29 s | $24.4K (worst) | Stochastic | (intentionally none — control) | Trapped in first basin | Never for production; control baseline |

---

### 3.4 Factors That Shape the Results

The ranking above is not absolute — it is produced by an interaction of problem and algorithm properties. The most important factors:

1. **Pool size N (the dominant factor).** As N grows with the budget fixed, the pool contains *more* cheap high-ROI Micro/Nano creators, so the achievable GMV rises for every method that can exploit them — GA/GR climb from ≈$40K (N=50) to ≈$73K (N=500). HC cannot exploit them (it stays trapped), so its GMV actually *declines* (≈$27.6K→$24.4K): a larger pool simply offers more expensive creators for it to over-commit to. The consequence is that the **relative gap widens with N** (+50% → +200%): N does not just scale the numbers, it amplifies the *quality difference* between trapped and untrapped search. N also drives cost asymmetrically — TS's O(N²) scan is the only runtime that grows quadratically, and GR's 2-opt phase makes its own runtime jump only at N=500.

2. **Budget level and cost model.** The budget sets how many creators are selected and therefore the search difficulty. A *tight* budget selects very few creators, shrinking the effective search space until all methods converge to the same trivial answer (the degenerate case we avoid). A *looser* budget lets more creators fit, so portfolio composition — and thus the ability to escape the greedy basin — matters more. The commission-rate cost model (§2.4.4) is what couples cost to value and creates the trap in the first place; under a flat per-creator fee the single-biggest-KOL heuristic would win and the algorithms would barely differ.

3. **Seed / dataset variance.** Per-cell standard deviations are large relative to the gaps among the top methods. This is why the N=50 leader (GA, by a hair) must be read as a near-tie with TS and GR, and why we average ten seeds before drawing any conclusion. Variance shrinks as N grows (more creators average out idiosyncratic draws), which is why the large-N rankings — where GA and GR clearly separate from the rest — are the trustworthy ones.

4. **Starting point — greedy seeding is the single biggest lever.** The three methods that begin from a ratio-sorted greedy solution (GR, GA, TS) dominate the three that begin from an empty or random portfolio (SA, HC, RS) at every large N. The convergence panels (§3.5) make this visceral: GR/GA/TS are near their final value within hundreds of evaluations, while SA must climb for thousands. A strong initial solution is worth more here than any amount of clever exploration from a cold start.

5. **Evaluation budget and neighbourhood design.** For the trajectory methods, *how many* solutions are evaluated and *which* neighbours are reachable matter enormously. SA's ≈21K evaluations sound like a lot, but spread over a large landscape from a cold start they under-deliver versus GA's ≈7,200 *seeded, recombined* evaluations. SA's hybrid swap/multi-swap neighbourhood (§2.3.1) is precisely what lets it eventually escape — without it, SA would degenerate toward HC.

6. **Problem structure (the GMV model).** The `sqrt(followers)` diminishing-returns term plus the proportional commission cost are what make mixed-tier portfolios optimal. These two modelling choices, not the algorithms, decide *whether the trap exists at all*. They are calibrated (§2.4) so the trap is realistic rather than contrived — but it is worth stating plainly that the algorithm ranking is conditional on this model.

---

### 3.5 Convergence Analysis

See `docs/figures/convergence_panels.png` (three-panel N=20/50/100, proportional budget) and `docs/figures/convergence.png` (the 8-KOL "trap" demo from `run_comparison.py`, budget=$5,000).

**At N=20:** Every algorithm *except* Hill Climber converges to the same optimum (≈$2,540) within a few hundred iterations — the pool is small enough that GA, TS, SA, GR and even Random Search all find it. HC alone is trapped well below (≈$1,780), unable to improve its greedy portfolio with a single bit-flip.

**At N=50:** GA and RS settle at the top (≈$8,500) quickly. SA is the interesting case: it sits on an intermediate shelf (≈$6,600) for most of the run and only jumps up to ≈$8,500 late (around iteration 8,000), illustrating the temperature-driven escape from a local optimum. TS and GR plateau a little lower (≈$7,300–7,800), and HC is trapped at ≈$5,100 and never escapes.

**At N=100:** GA, TS and GR jump to the best value (≈$26K) almost immediately thanks to greedy seeding / ratio-sorting, and RS reaches a respectable ≈$22K. SA climbs *steadily* from a low start but, under its fixed evaluation budget, finishes well below the leaders (≈$17–18K) at this scale. HC stays flat near the bottom. This panel is the clearest picture of why SA forms a middle tier at large N in §3.2.

**8-KOL trap demo (`convergence.png`):** On the hand-built scenario where one expensive Macro creator tempts a greedy solver, all global methods (SA, GA, TS) and Greedy Ranking reach ≈$37–38K while HC settles slightly lower (≈$36.4K), confirming the trap on a minimal, human-readable instance.

---

### 3.6 Execution Time Scaling

See `docs/figures/scalability_time.png`. Mean wall-clock seconds over 10 seeds (from `scalability_results.csv`), ordered fastest-to-slowest at N=500:

**Table 3. Mean Execution Time (seconds) by Algorithm and Pool Size**

| Algorithm | N=50 | N=100 | N=200 | N=500 | Growth in N |
|-----------|------|-------|-------|-------|-------------|
| Hill Climber | 0.154 | 0.176 | 0.177 | 0.294 | ~flat (cheap control) |
| Random Search | 0.150 | 0.166 | 0.218 | 0.383 | ~linear, shallow |
| Greedy Ranking | **0.017** | **0.041** | **0.060** | 0.415 | flat then 2-opt jump |
| Genetic Algorithm | 0.296 | 0.343 | 0.483 | 0.904 | ~linear |
| Tabu Search | 0.299 | 0.731 | — | — | **quadratic (O(N²))** |
| Simulated Annealing | 0.972 | 1.175 | 1.564 | 2.667 | ~linear, steepest |

**Reading the six-algorithm time comparison:**

- **Greedy Ranking is the fastest by a wide margin up to N=200** (17–60 ms — an order of magnitude below everything else) *and* one of the two strongest at scale, which is exactly what makes it the best quality-per-second option for interactive use. Its one runtime surprise is at N=500, where the O(N²) 2-opt swap phase pushes it to ≈0.42 s (and widens its variance) — still sub-half-second, but no longer "free."
- **Simulated Annealing is the slowest at every N** (0.97 s → 2.67 s) because it performs the most fitness evaluations (temperature-level schedule × iterations); its runtime grows roughly linearly in N.
- **Tabu Search is the only method with super-linear growth**: its full single-flip neighbourhood is O(N²) per iteration, so wall-clock time more than doubles from N=50 (0.30 s) to N=100 (0.73 s, with high variance). Extrapolated to N=500 it would dominate every other method — the concrete reason we cap it at N ≤ 100.
- **GA sits in the middle** (0.30 s → 0.90 s), buying its top-tier large-N quality with a modest, near-linear runtime — notably *faster* than SA despite higher quality.
- **HC and RS are cheap and nearly flat** (≈0.15–0.38 s across the whole range); neither does enough work to cost much, which is consistent with their role as the trapped control and the lower-bound baseline.

The practical takeaway: at the production library scale (hundreds of creators), every algorithm except SA finishes well under one second, so runtime is rarely the binding constraint — quality and the greedy-seed advantage (§3.4) dominate the choice. The optimizer further decouples API latency from library size via candidate shortlisting (top-K by CreatorScore before optimization), so live `/optimize` stays fast even on a 10K-creator pool.

---

### 3.7 Pool-Size Effects and Algorithm Selection (N-by-N)

This section answers two questions directly: **how does the pool size N change each algorithm's behaviour, and which algorithm should you actually use at each N?**

**How N reshapes the rankings.** With the budget fixed at $5,000, a larger pool means more cheap, high-ROI Micro/Nano creators competing for the same spend. The algorithms split into three responses:

- **Exploiters (GA, GR, TS).** Greedy-seeded methods convert the richer pool into more GMV almost immediately: GA/GR rise from ≈$40K (N=50) to ≈$73K (N=500). They separate cleanly from the field at N≥200, and the GA↔GR gap stays within ≈2% — a genuine tie that the runtime column (§3.6) breaks in GR's favour.
- **Laggards (SA, RS).** Both improve with N but cannot keep pace: SA is held back by a fixed evaluation budget spread thin from a cold start, RS by the absence of any learning mechanism as the feasible space explodes. They form a stable middle/lower tier (SA $59.6K, RS $56.2K at N=500), with SA pulling clear of RS only at large N.
- **The trapped control (HC).** HC is the diagnostic case: its GMV *falls* as N grows ($27.6K→$24.4K), because a bigger pool just offers more expensive creators for its budget-exhausting first move to lock onto, and no single bit-flip can undo that commitment. Every other method's *widening* lead over HC (+50%→+200%) is the quantitative signature of escaping the local-optima trap.

So N is not a neutral scale factor — it *amplifies* the quality difference between greedy-seeded global search and trapped/unstructured search, and it is the single most important determinant of the ranking.

**Best algorithm at each N (quality, speed, and the recommendation):**

**Table 4. Recommended Algorithm by Pool Size**

| Pool size N | Highest GMV | Best quality-per-second | Recommended choice | Why |
|:---:|---|---|---|---|
| **≤ 50** | GA ($41.4K) — TS/GR within ~4% (tie) | GR (≈17 ms) | **Greedy Ranking** | Near-best quality in ~20 ms; differences are within one σ |
| **100** | GA ($48.4K) — TS/GR close behind | GR (≈41 ms) | **GA or GR** | GA for the top number; GR if latency matters |
| **200** | GR ($60.0K) ≈ GA ($59.9K) (tie) | GR (≈60 ms) | **Greedy Ranking** | Ties GA on quality at ~8× the speed |
| **500** | GA ($73.2K) | GR (≈0.42 s, $71.9K) | **GA** for max GMV; **GR** if sub-second latency is required | GA's ≈$1.2K (≈2%) edge costs ~0.5 s extra |

**Summary.** Across every pool size tested, **Genetic Algorithm delivers the top or tied-top GMV**, and **Greedy Ranking matches it within ≈2% at N≥200 while running 2–8× faster** — so GR is the best default for an interactive product, and GA is the right pick when maximum predicted GMV justifies the extra runtime. Tabu Search is a strong third choice but only for N ≤ 100 (quadratic cost). Simulated Annealing and Random Search are dependable mid/baseline tiers, and Hill Climber is never appropriate for production — it serves purely as the trapped control that quantifies the value of the others.

---

### 3.8 SA Parameter Sensitivity

See `docs/figures/sensitivity_heatmap.png` (single-seed SA grid at N=100, budget=$2,500, so absolute GMV is lower than the §3.2 table). The clearest signal is that the lowest initial temperature, T0=500, is consistently the weakest column — too little early exploration leaves SA stuck near its starting point, HC-like. Across the rest of the grid (T0 ≥ 1,000) the surface is fairly flat and noisy: no single (T0, α) cell dominates, and cell-to-cell differences are on the order of single-seed variance. The practical takeaway is that SA is robust to these two hyper-parameters once T0 is not pathologically low; the live default (T0=15,000, α=0.95) sits in this broad, well-behaved region. A multi-seed average per cell would smooth the remaining noise — `engine/evaluation/sensitivity.py` does exactly this (5 repeats) for a cleaner surface.

---

### 3.9 Campaign Attribution Accuracy

The post-campaign attribution feature records actual GMV after campaigns complete and computes `accuracy_pct = actual / predicted × 100` (implemented in `backend/campaigns.py`, covered by `tests/test_campaigns.py`). This closes the prediction→outcome loop so a merchant can see, per campaign, how close the optimizer's predicted GMV was to the realised figure. Because the project ships with synthetic data and no real TikTok Shop sales feed, we do not report a calibrated accuracy number here — the attribution pipeline is validated functionally by the campaign CRUD tests rather than against ground-truth GMV. Validating calibration against real affiliate sales data is left to future work (see §f).

---

### 3.10 Automated Tests

```
tests/test_fitness.py        — fitness function + budget penalty        ( 6)
tests/test_algorithms.py     — all 6 algorithm interfaces               (34)
tests/test_scoring.py        — CreatorScore weighting + normalisation   ( 7)
tests/test_creator_score.py  — CreatorScore edge cases                  ( 3)
tests/test_explainer.py      — recommendation reason generation         ( 4)
tests/test_api.py            — core API + simulate-scale + reset        (32)
tests/test_campaigns.py      — campaign attribution CRUD                (13)
tests/test_kol_history.py    — KOL history tracking + simulate-update   (12)
```

Total: **111 tests** (isolated from production data via `tests/conftest.py`). Run with: `pytest tests/ --tb=short`

---

## (f) Conclusion

### Summary

This project formulated TikTok Shop KOL portfolio selection as a budget-constrained 0-1 knapsack variant and delivered an end-to-end system around it: six optimization algorithms, a calibrated Southeast-Asian GMV model, a FastAPI backend with a single-page web app, explainable per-creator recommendations, KOL metric-history tracking, and closed-loop campaign attribution — all validated by a reproducible multi-seed benchmark and 111 automated tests.

### Key Findings

- **Structured search decisively beats naïve local search.** Every method outperforms the random-flip Hill Climber at every pool size, and the advantage widens monotonically from **+50% (N=50) to +200% (N=500)** — HC is in fact the only method whose GMV *falls* as the pool grows — directly confirming the budget-exhaustion local-optima trap hypothesis.
- **The lead at scale is shared by GA and an improved Greedy Ranking.** GA tops N=50/100/500 ($73.2K at N=500) and the 2-opt-augmented GR ties it at N=200 ($60.0K), within ≈2% of each other; Tabu Search stays within a few percent of GA through N=100. GA wins on quality, GR wins on quality-per-second (2–8× faster); see the best-algorithm-per-N guide (§3.7).
- **A well-engineered greedy heuristic is the efficiency champion.** GR delivers near-best quality at an order-of-magnitude lower runtime — the best quality-per-second and the right default for interactive use.
- **Simulated Annealing is the most tunable middle-tier method**, trailing at large N only because its fixed evaluation budget starts from a cold (empty) portfolio.
- **The single biggest lever on quality is the starting point**: greedy-seeded methods (GR/GA/TS) dominate cold-start methods (SA/HC/RS), and the relative ranking is shaped most by pool size N, the budget/cost model, and seed variance (§3.4).

### Achievements & Contributions

- A deployable optimizer that returns a budget-feasible, **mixed-tier** portfolio in seconds, each pick justified by 3+ human-readable reasons.
- Concrete algorithm **improvements over textbook baselines** — SA's thermal-adaptive hybrid neighbourhood, GA's greedy seeding + budget-aware init + elitism, TS's aspiration criterion + early stopping, and GR's 2-opt + drop phases — together with a rigorous, reproducible benchmark that *quantifies* the value of each.
- A fully **documented, calibrated synthetic data model** for SEA TikTok Shop that makes the optimization trap realistic, plus two product layers — metric-history tracking and campaign attribution — that turn a one-shot recommender into a campaign-management loop.

### Reflection & Insights

The most instructive surprise was that a well-engineered *greedy* method (Greedy Ranking with 2-opt) rivals population metaheuristics on this problem at a fraction of the cost — a reminder that problem-specific construction heuristics often match general-purpose search, and that "more sophisticated" is not automatically "better." The work also showed how fragile single-seed conclusions are: a stable ranking only emerged after averaging ten seeds, which reshaped how we report every result (variance-aware, with ties acknowledged). Finally, building the attribution loop made concrete that an optimizer is only as trustworthy as its objective model — motivating calibration against real outcomes as the natural next step.

### Future Work

- **Calibrate against reality.** Connect the (currently stubbed) TikTok Shop Partner API to replace synthetic GMV with measured affiliate sales, and report calibrated prediction accuracy through the existing attribution pipeline.
- **Multi-objective optimization.** Optimize GMV *and* audience diversity/reach on a Pareto front rather than a single scalarized objective.
- **Close SA's large-N gap.** Increase SA's evaluations per temperature level or add random restarts, and warm-start all solvers from the greedy seed.
- **Learning from feedback.** Explore approaches that improve the GMV model over time from accumulated campaign-attribution data.
