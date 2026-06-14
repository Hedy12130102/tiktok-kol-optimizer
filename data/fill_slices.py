"""
Top up thin (country, category) slices of the seed creator library.

The real FastMoss seed is uneven — some market×category slices (e.g. ID·fashion,
MY·fmcg) have 0-2 creators, so a merchant filtering to them gets no usable
optimization. This script brings every slice up to a minimum count by adding
clearly labelled synthetic creators (source="synthetic"), while tagging the
existing real rows source="fastmoss" so the two are always distinguishable.

It rewrites BOTH the live library (sample_kols.json) and the restore baseline
(seed_kols.json) so Reset returns to the filled library too.

Usage (from project root):
    .conda\\python.exe data\\fill_slices.py            # default min = 15 per slice
    .conda\\python.exe data\\fill_slices.py --min 20
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import crud
from data.generator import _COUNTRIES, _CATEGORIES, generate_for_slices


def main():
    ap = argparse.ArgumentParser(description="Fill thin market×category slices with synthetic creators.")
    ap.add_argument("--min", type=int, default=15, help="Minimum creators per slice (default: 15).")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for the synthetic fill.")
    args = ap.parse_args()

    # Prefer the curated seed baseline as the source of truth; fall back to live.
    src = crud.SEED_PATH if os.path.exists(crud.SEED_PATH) else crud.DATA_PATH
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    # Tag existing rows as real so synthetic fill is always distinguishable.
    for k in data:
        k.setdefault("source", "fastmoss")

    counts = collections.Counter((k["country"], k["category"]) for k in data)
    targets = {}
    for c in _COUNTRIES:
        for cat in _CATEGORIES:
            deficit = args.min - counts.get((c, cat), 0)
            if deficit > 0:
                targets[(c, cat)] = deficit

    if not targets:
        print(f"All slices already have >= {args.min} creators. Nothing to do.")
        return

    start_id = max((k["id"] for k in data), default=0) + 1
    fill = generate_for_slices(targets, start_id=start_id, seed=args.seed)
    data.extend(fill)

    for path in (crud.DATA_PATH, crud.SEED_PATH):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    real = sum(1 for k in data if k.get("source") == "fastmoss")
    synth = sum(1 for k in data if k.get("source") == "synthetic")
    print(f"Filled {len(targets)} thin slices (min {args.min}/slice).")
    print(f"  added {len(fill)} synthetic creators")
    print(f"  library now {len(data)} total  ({real} fastmoss + {synth} synthetic)")
    print(f"  written to {crud.DATA_PATH} and {crud.SEED_PATH}")

    print("\n  slices topped up:")
    for (c, cat), n in sorted(targets.items()):
        print(f"    {c}·{cat:<8} +{n}")


if __name__ == "__main__":
    main()
