"""
Test isolation: point the backend at a throwaway data directory before it is
imported, and seed it with a fresh synthetic dataset.

Without this, the CRUD/import tests mutate (and the reset test would overwrite)
the production data/sample_kols.json. pytest imports conftest.py before any test
module, so setting the KOL_*_PATH env vars here guarantees backend.main and
backend.crud read these isolated paths at import time.
"""
import atexit
import json
import os
import shutil
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Isolated, auto-cleaned data dir for the whole test session.
_TMP = tempfile.mkdtemp(prefix="kol_test_")
_DATA = os.path.join(_TMP, "sample_kols.json")
_SEED = os.path.join(_TMP, "seed_kols.json")
_HISTORY = os.path.join(_TMP, "kol_history.json")

# Generate a deterministic synthetic library — independent of production data.
from data.generator import generate_kols  # noqa: E402

generate_kols(
    num=300,
    seed=42,
    json_output_path=_DATA,
    csv_output_path=os.path.join(_TMP, "mock.csv"),
)
shutil.copyfile(_DATA, _SEED)          # reset test restores to this baseline
with open(_HISTORY, "w", encoding="utf-8") as f:
    json.dump([], f)

# Must be set BEFORE backend.main / backend.crud are imported by test modules.
os.environ["KOL_DATA_PATH"] = _DATA
os.environ["KOL_SEED_PATH"] = _SEED
os.environ["KOL_HISTORY_PATH"] = _HISTORY

atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))
