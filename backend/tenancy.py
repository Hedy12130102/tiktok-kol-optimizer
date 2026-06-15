"""
Multi-tenant data isolation.

Each merchant (tenant) gets its own folder under data/tenants/{tenant_id}/ holding
that tenant's sample_kols.json / seed_kols.json / kol_history.json / campaigns.json.
The current tenant for a request is held in a context variable, set by the
`require_tenant` auth dependency (backend/auth.py). The data modules
(crud.py / main.py / campaigns.py) resolve their file paths through the helpers here
instead of module-level constants, so a single code path serves every tenant.

Test/dev escape hatch: set env DEFAULT_TENANT to make unauthenticated requests fall
back to a fixed tenant, and KOL_DATA_DIR to relocate the whole data tree.
"""
import contextvars
import os

# Root data directory (overridable for tests).
DATA_DIR = os.environ.get("KOL_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
TENANTS_DIR = os.path.join(DATA_DIR, "tenants")
USERS_PATH = os.path.join(DATA_DIR, "users.json")

# The library every new tenant is seeded from (the curated FastMoss seed + fill).
TEMPLATE_SEED = os.path.join(DATA_DIR, "seed_kols.json")

# Unauthenticated fallback tenant (tests set this so the suite needs no tokens).
DEFAULT_TENANT = os.environ.get("DEFAULT_TENANT")

# Request-scoped current tenant id.
_current_tenant: contextvars.ContextVar = contextvars.ContextVar("current_tenant", default=None)


def set_current_tenant(tenant_id):
    _current_tenant.set(tenant_id)


def current_tenant() -> str:
    tid = _current_tenant.get() or DEFAULT_TENANT
    if not tid:
        # Should never happen on a route guarded by require_tenant.
        raise RuntimeError("No tenant in request context")
    return tid


# ── Per-tenant path resolvers ─────────────────────────────────────
def tenant_dir(tenant_id: str = None) -> str:
    return os.path.join(TENANTS_DIR, tenant_id or current_tenant())


def data_path() -> str:
    return os.path.join(tenant_dir(), "sample_kols.json")


def seed_path() -> str:
    return os.path.join(tenant_dir(), "seed_kols.json")


def history_path() -> str:
    return os.path.join(tenant_dir(), "kol_history.json")


def campaigns_path() -> str:
    return os.path.join(tenant_dir(), "campaigns.json")


# ── Provisioning ──────────────────────────────────────────────────
def provision_tenant(tenant_id: str):
    """Create a fresh data folder for a new tenant, seeded from the template."""
    d = tenant_dir(tenant_id)
    os.makedirs(d, exist_ok=True)

    seed = "[]"
    if os.path.exists(TEMPLATE_SEED):
        with open(TEMPLATE_SEED, encoding="utf-8") as f:
            seed = f.read()

    for name, content in (
        ("sample_kols.json", seed),
        ("seed_kols.json", seed),
        ("kol_history.json", "[]"),
        ("campaigns.json", "[]"),
    ):
        p = os.path.join(d, name)
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)


def tenant_exists(tenant_id: str) -> bool:
    return os.path.isdir(tenant_dir(tenant_id))
