"""
Auth + per-tenant isolation tests.

These send real Bearer tokens, so they exercise the true auth path (the
DEFAULT_TENANT fallback only applies when no Authorization header is present).
"""
import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _email():
    return f"m_{uuid.uuid4().hex[:10]}@shop.test"


def _register(email=None, password="secret123"):
    email = email or _email()
    r = client.post("/auth/register", json={"email": email, "password": password})
    return email, r


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Registration / login ──────────────────────────────────────────
def test_register_returns_token():
    email, r = _register()
    assert r.status_code == 200
    body = r.json()
    assert body["token"] and body["email"] == email


def test_register_rejects_bad_email_and_short_password():
    assert client.post("/auth/register", json={"email": "nope", "password": "secret123"}).status_code == 422
    assert client.post("/auth/register", json={"email": _email(), "password": "x"}).status_code == 422


def test_register_duplicate_email_conflicts():
    email, r1 = _register()
    assert r1.status_code == 200
    r2 = client.post("/auth/register", json={"email": email, "password": "secret123"})
    assert r2.status_code == 409


def test_login_success_and_wrong_password():
    email, _ = _register(password="goodpass1")
    ok = client.post("/auth/login", json={"email": email, "password": "goodpass1"})
    assert ok.status_code == 200 and ok.json()["token"]
    bad = client.post("/auth/login", json={"email": email, "password": "wrongpass"})
    assert bad.status_code == 401


def test_me_returns_current_account():
    email, r = _register()
    token = r.json()["token"]
    me = client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200 and me.json()["email"] == email


# ── Token enforcement ─────────────────────────────────────────────
def test_invalid_token_is_rejected():
    # A present-but-bogus token bypasses the no-auth fallback and must 401.
    r = client.get("/kols", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


# ── Per-tenant data isolation ─────────────────────────────────────
def test_new_tenant_starts_from_seed_template():
    _, r = _register()
    token = r.json()["token"]
    total = client.get("/kols?limit=1", headers=_auth(token)).json()["total"]
    assert total > 0, "a new tenant should start from the seed template, not empty"


def test_creators_are_isolated_between_tenants():
    ta = _register()[1].json()["token"]
    tb = _register()[1].json()["token"]

    a_before = client.get("/kols?limit=1", headers=_auth(ta)).json()["total"]
    b_before = client.get("/kols?limit=1", headers=_auth(tb)).json()["total"]

    add = client.post("/kols/add", headers=_auth(ta), json={
        "name": "Tenant-A-Only Creator", "country": "MY", "category": "beauty",
        "followers": 50000, "engagement_rate": 0.1, "cost": 500,
    })
    assert add.status_code == 200

    a_after = client.get("/kols?limit=1", headers=_auth(ta)).json()["total"]
    b_after = client.get("/kols?limit=1", headers=_auth(tb)).json()["total"]

    assert a_after == a_before + 1, "A's library should grow"
    assert b_after == b_before, "B's library must be unaffected by A's add"


def test_campaigns_are_isolated_between_tenants():
    ta = _register()[1].json()["token"]
    tb = _register()[1].json()["token"]

    payload = {
        "name": "A's campaign", "countries": ["MY"], "category": "beauty",
        "budget": 5000, "best_algorithm": "Genetic Algorithm",
        "selected_kols": [], "total_cost": 0, "predicted_gmv": 0,
    }
    assert client.post("/campaigns", headers=_auth(ta), json=payload).status_code == 200

    assert len(client.get("/campaigns", headers=_auth(ta)).json()) == 1
    assert client.get("/campaigns", headers=_auth(tb)).json() == []
