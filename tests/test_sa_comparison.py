"""SA comparison — verifies both SA variants run on the same pool."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from engine.models import KOL
from engine.optimization.simulated_annealing import simulated_annealing
from engine.optimization.sa_improved import simulated_annealing_improved
from engine.fitness import summarize_state


def test_sa_both_variants_return_valid_states():
    """Both SA and SA-Improved should return valid binary states from the same pool."""
    with open("data/sample_kols.json") as f:
        kols = [KOL(**d) for d in json.load(f)]
    kols_my = [k for k in kols if k.country == "MY" and k.category == "beauty"]
    budget = 5000.0

    sa_state, _, _ = simulated_annealing(kols_my, budget=budget, max_iter=50, seed=42)
    sai_state, _, _ = simulated_annealing_improved(kols_my, budget=budget, max_iter=50, seed=42)

    assert len(sa_state) == len(kols_my)
    assert len(sai_state) == len(kols_my)
    assert all(x in (0, 1) for x in sa_state)
    assert all(x in (0, 1) for x in sai_state)


if __name__ == "__main__":
    # Full comparison script (not a test — run directly)
    with open("data/sample_kols.json") as f:
        kols = [KOL(**d) for d in json.load(f)]
    kols_my = [k for k in kols if k.country == "MY" and k.category == "beauty"]
    budget = 5000.0

    print(f"Loaded {len(kols_my)} Malaysian beauty KOLs\n")
    print("Running Standard SA...")
    sa_state, _, _ = simulated_annealing(kols_my, budget=budget, max_iter=500, seed=42)
    print("Running Improved SA...")
    sai_state, _, _ = simulated_annealing_improved(kols_my, budget=budget, max_iter=500, swap_prob=0.6, seed=42)

    sa_r = summarize_state(sa_state, kols_my)
    sai_r = summarize_state(sai_state, kols_my)
    print(f"\nStandard SA  GMV: {sa_r['total_gmv']:.2f}")
    print(f"Improved SA  GMV: {sai_r['total_gmv']:.2f}")
    imp = (sai_r['total_gmv'] - sa_r['total_gmv']) / sa_r['total_gmv'] * 100
    print(f"Improvement: {imp:.2f}%")
