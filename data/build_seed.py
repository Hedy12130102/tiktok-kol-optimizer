"""
Build the default seed creator library (data/sample_kols.json) from your own
real Excel/CSV exports (e.g. FastMoss).

This REPLACES sample_kols.json with exactly the rows in the files you pass —
it does not append to whatever is already there. The result becomes the
initialization library every merchant starts with (and, if you wire reset to
restore the seed, what /kols/reset returns to).

It runs the same validation + header-alias + number/rate-parsing + cost-estimate
pipeline as the live import endpoint, so messy headers ("Follower Count",
"Engagement Rate (%)", "Region"), formatted numbers ("250K", "$1,200", "8%"),
and country/category names are all normalised.

Usage (from project root, using the project's python):
    .conda\\python.exe data\\build_seed.py data\\fastmoss\\*.xlsx
    .conda\\python.exe data\\build_seed.py data\\Beauty_MY.xlsx data\\Fashion_ID.xlsx
    # force a default when a file lacks country/category columns AND the
    # filename can't be inferred:
    .conda\\python.exe data\\build_seed.py myfile.xlsx --country MY --category beauty

Per-file country/category are taken from (in order): an explicit column in the
file → the filename (e.g. "Beauty_MY.xlsx") → the --country/--category flags.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import crud


def _infer_defaults_from_name(path, cli_country, cli_category):
    stem_tokens = set(crud._norm_header(os.path.splitext(os.path.basename(path))[0]).split("_"))
    category = cli_category or next(
        (crud._CATEGORY_SYNONYMS[t] for t in stem_tokens if t in crud._CATEGORY_SYNONYMS), None
    )
    country = cli_country or next(
        (crud._COUNTRY_NAME_TO_CODE[t] for t in stem_tokens if t in crud._COUNTRY_NAME_TO_CODE), None
    )
    return country, category


def _read_rows(path):
    with open(path, "rb") as f:
        content = f.read()
    lower = path.lower()
    if lower.endswith(".csv"):
        return crud._read_csv_rows(content)
    if lower.endswith(".xlsx"):
        return crud._read_excel_rows(content)
    raise SystemExit(f"Unsupported file (need .csv or .xlsx): {path}")


def main():
    ap = argparse.ArgumentParser(description="Build sample_kols.json from real exports.")
    ap.add_argument("files", nargs="+", help="One or more .xlsx/.csv files (globs allowed).")
    ap.add_argument("--country", default=None, help="Fallback country code for files lacking one.")
    ap.add_argument("--category", default=None, help="Fallback category for files lacking one.")
    args = ap.parse_args()

    paths = []
    for pattern in args.files:
        matched = glob.glob(pattern)
        if not matched:
            print(f"  ! no match for: {pattern}")
        paths.extend(sorted(matched))
    if not paths:
        raise SystemExit("No input files found.")

    # Start from an empty library so the seed contains ONLY these rows.
    crud._save([])

    grand_added, grand_estimated, grand_errors = 0, 0, []
    for path in paths:
        headers, raw_rows = _read_rows(path)
        rows = crud._canonicalize_rows(headers, raw_rows)
        country, category = _infer_defaults_from_name(path, args.country, args.category)
        added, estimated, errors, total = crud._ingest_rows(rows, country, category)
        grand_added += added
        grand_estimated += estimated
        grand_errors.extend(f"{os.path.basename(path)}: {e}" for e in errors)
        print(f"  + {os.path.basename(path):<28} added={added:<4} "
              f"cost-estimated={estimated:<4} errors={len(errors)} "
              f"(defaults country={country or '—'} category={category or '—'})")

    # Snapshot the freshly built library as the restore baseline that
    # /kols/reset returns to.
    import shutil
    shutil.copyfile(crud.DATA_PATH, crud.SEED_PATH)

    print(f"\nSeed written to {crud.DATA_PATH}")
    print(f"Restore baseline written to {crud.SEED_PATH}")
    print(f"  total creators: {grand_added}")
    if grand_estimated:
        print(f"  cost estimated from followers for {grand_estimated} rows "
              f"(no price in source — replace with negotiated quotes later)")
    if grand_errors:
        print(f"  {len(grand_errors)} rows skipped:")
        for e in grand_errors[:30]:
            print(f"    - {e}")
        if len(grand_errors) > 30:
            print(f"    ... and {len(grand_errors) - 30} more")


if __name__ == "__main__":
    main()
