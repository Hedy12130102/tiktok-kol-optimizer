# engine/optimization/genetic_algorithm.py
"""
Genetic Algorithm for KOL portfolio optimization.

Key design decisions:
  - Chromosome: binary list (1=selected, 0=not), length = pool size
  - Greedy seeding: first individual is a near-optimal greedy solution
    (sort by GMV/cost, fill greedily up to budget)
  - Selection: tournament (k=3) — fast, tunable selection pressure
  - Crossover: single-point (prob=0.9) — preserves portfolio structure
  - Mutation: uniform bit-flip with prob=1/n per gene
  - Elitism: best individual always survives to next generation

Why GA beats SA and HC here:
  The KOL portfolio problem is a 0-1 knapsack variant. GA's crossover
  operator naturally recombines good partial solutions (e.g., "these 3
  high-ROI Nano KOLs" + "this Mega KOL") that SA/HC can only discover
  one flip at a time. Population diversity prevents premature convergence.
"""
import copy
import random
from typing import List, Optional, Tuple

from engine.models import KOL
from engine.fitness import fitness


def _greedy_init(kols: List[KOL], budget: float) -> List[int]:
    """
    Build a starting individual by greedily adding KOLs in descending
    GMV/cost order until the budget is exhausted.
    """
    n = len(kols)
    order = sorted(
        range(n),
        key=lambda i: kols[i].expected_gmv() / kols[i].cost if kols[i].cost > 0 else 0,
        reverse=True,
    )
    state = [0] * n
    total_cost = 0.0
    for i in order:
        if total_cost + kols[i].cost <= budget:
            state[i] = 1
            total_cost += kols[i].cost
    return state


def _tournament(
    population: List[List[int]],
    costs: List[float],
    k: int,
    rng: random.Random,
) -> List[int]:
    """Tournament selection — return a copy of the winner (lowest cost)."""
    indices = rng.choices(range(len(population)), k=k)
    winner = min(indices, key=lambda i: costs[i])
    return copy.copy(population[winner])


def genetic_algorithm(
    kols: List[KOL],
    budget: float,
    pop_size: int = 60,
    generations: int = 120,
    crossover_prob: float = 0.9,
    tournament_k: int = 3,
    seed: Optional[int] = None,
) -> Tuple[List[int], float, List[float]]:
    """
    Genetic Algorithm optimizer for KOL portfolio selection.

    Args:
        kols:           List of KOL candidates.
        budget:         Maximum total hiring cost (USD).
        pop_size:       Population size (individuals per generation).
        generations:    Number of generations to evolve.
        crossover_prob: Probability of applying crossover (vs. cloning).
        tournament_k:   Tournament size for selection.
        seed:           Random seed for reproducibility.

    Returns:
        (best_state, best_cost, history)
        history: one entry per individual evaluation (pop_size × generations)
    """
    rng = random.Random(seed)
    n = len(kols)
    mutation_prob = 1.0 / max(1, n)

    # ── Initialize population ────────────────────────────────────────
    # First individual: greedy seed (strong starting point)
    population = [_greedy_init(kols, budget)]

    # Remaining: random individuals scaled to realistic inclusion probability
    avg_cost = sum(k.cost for k in kols) / n if n > 0 else 1.0
    inclusion_prob = min(0.6, max(0.1, (budget / avg_cost) / n))
    for _ in range(pop_size - 1):
        ind = [1 if rng.random() < inclusion_prob else 0 for _ in range(n)]
        population.append(ind)

    # ── Initial evaluation ───────────────────────────────────────────
    costs_list = [fitness(ind, kols, budget) for ind in population]

    best_cost = min(costs_list)
    best_idx = costs_list.index(best_cost)
    best_ind = copy.copy(population[best_idx])
    history: List[float] = []

    # ── Evolve ───────────────────────────────────────────────────────
    for _gen in range(generations):
        new_pop: List[List[int]] = []

        for _ in range(pop_size):
            # Select parents
            p1 = _tournament(population, costs_list, tournament_k, rng)
            p2 = _tournament(population, costs_list, tournament_k, rng)

            # Crossover
            if rng.random() < crossover_prob and n > 1:
                point = rng.randint(1, n - 1)
                child = p1[:point] + p2[point:]
            else:
                child = p1

            # Mutation: flip each gene with probability 1/n
            for i in range(n):
                if rng.random() < mutation_prob:
                    child[i] ^= 1

            new_pop.append(child)

        # Elitism: replace worst individual with previous best
        new_costs = [fitness(ind, kols, budget) for ind in new_pop]
        worst_idx = max(range(pop_size), key=lambda i: new_costs[i])
        new_pop[worst_idx] = copy.copy(best_ind)
        new_costs[worst_idx] = best_cost

        population = new_pop
        costs_list = new_costs

        gen_best_cost = min(costs_list)
        if gen_best_cost < best_cost:
            best_cost = gen_best_cost
            best_idx = costs_list.index(best_cost)
            best_ind = copy.copy(population[best_idx])

        # Append pop_size points per generation (one per individual evaluated)
        history.extend([-best_cost] * pop_size)

    return best_ind, best_cost, history
