"""
Test isolation for the multi-tenant backend.

Before the backend is imported we point the data tree at a throwaway directory
(KOL_DATA_DIR) and enable an unauthenticated fallback tenant (DEFAULT_TENANT), so
the existing suite hits a private, pre-seeded "test" tenant without needing tokens.
The auth/isolation tests (tests/test_auth.py) send real Bearer tokens, which take
precedence over the fallback.
"""
import atexit
import json
import os
import shutil
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# Isolated, auto-cleaned data tree for the whole test session.
_TMP = tempfile.mkdtemp(prefix="kol_test_")
_TEST_TENANT = "test"
_TENANT_DIR = os.path.join(_TMP, "tenants", _TEST_TENANT)
os.makedirs(_TENANT_DIR, exist_ok=True)

# Generate a deterministic synthetic library for the default test tenant.
from data.generator import generate_kols  # noqa: E402

_DATA = os.path.join(_TENANT_DIR, "sample_kols.json")
generate_kols(num=300, seed=42, json_output_path=_DATA, csv_output_path=None)
shutil.copyfile(_DATA, os.path.join(_TENANT_DIR, "seed_kols.json"))  # reset baseline
for _name in ("kol_history.json", "campaigns.json"):
    with open(os.path.join(_TENANT_DIR, _name), "w", encoding="utf-8") as f:
        json.dump([], f)

# Also expose the synthetic library as the global template so newly registered
# tenants (auth tests) start from a non-empty library too.
shutil.copyfile(_DATA, os.path.join(_TMP, "seed_kols.json"))

# Must be set BEFORE backend.tenancy / backend.main are imported by test modules.
os.environ["KOL_DATA_DIR"] = _TMP
os.environ["DEFAULT_TENANT"] = _TEST_TENANT

atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))
