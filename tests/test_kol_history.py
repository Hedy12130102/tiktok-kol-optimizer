"""
KOL History Tracking endpoint tests.

Covers:
  GET  /kols/{id}/history          — return snapshot list
  POST /kols/{id}/simulate-update  — apply drift + record snapshot
  PUT  /kols/{id}                  — auto-snapshot before update

Run:  pytest tests/test_kol_history.py -v
"""
import os
import sys
import json

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
import backend.crud as crud_module

client = TestClient(app)

# ────────────────────────────────────────────────────────────
#  Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_history_file(tmp_path, monkeypatch):
    """Each test gets a fresh kol_history.json so tests don't pollute each other."""
    tmp_file = tmp_path / "kol_history.json"
    tmp_file.write_text("[]")
    monkeypatch.setattr(crud_module, "HISTORY_PATH", str(tmp_file))
    yield str(tmp_file)


def _get_first_kol_id() -> int:
    """Return the id of the first KOL in the database."""
    response = client.get("/kols?limit=1")
    kols = response.json()["kols"]
    if not kols:
        pytest.skip("No KOLs in database — run data/generator.py first")
    return kols[0]["id"]


# ────────────────────────────────────────────────────────────
#  GET /kols/{id}/history
# ────────────────────────────────────────────────────────────

def test_history_empty_before_any_update():
    kol_id = _get_first_kol_id()
    response = client.get(f"/kols/{kol_id}/history")
    assert response.status_code == 200
    assert response.json() == []


def test_history_not_found_for_invalid_id():
    response = client.get("/kols/99999/history")
    assert response.status_code == 404


def test_history_returns_list_after_simulate():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    response = client.get(f"/kols/{kol_id}/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 1


def test_history_snapshot_has_required_fields():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    history = client.get(f"/kols/{kol_id}/history").json()
    snap = history[0]
    assert "timestamp" in snap
    assert "kol_id" in snap
    assert "engagement_rate" in snap
    assert "fit_score" in snap
    assert "followers" in snap


def test_history_newest_first():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    client.post(f"/kols/{kol_id}/simulate-update")
    history = client.get(f"/kols/{kol_id}/history").json()
    assert len(history) >= 2
    # timestamps should be non-ascending (newest first)
    ts = [h["timestamp"] for h in history]
    assert ts == sorted(ts, reverse=True)


def test_history_kol_id_matches():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    history = client.get(f"/kols/{kol_id}/history").json()
    for snap in history:
        assert snap["kol_id"] == kol_id


# ────────────────────────────────────────────────────────────
#  POST /kols/{id}/simulate-update
# ────────────────────────────────────────────────────────────

def test_simulate_update_returns_200():
    kol_id = _get_first_kol_id()
    response = client.post(f"/kols/{kol_id}/simulate-update")
    assert response.status_code == 200


def test_simulate_update_returns_updated_kol():
    kol_id = _get_first_kol_id()
    original = client.get(f"/kol/{kol_id}").json()
    updated = client.post(f"/kols/{kol_id}/simulate-update").json()

    # The returned record should have the same id
    assert updated["id"] == kol_id
    # At least one metric should have changed (drift is random but almost always non-zero)
    changed = (
        updated.get("engagement_rate") != original.get("engagement_rate")
        or updated.get("fit_score") != original.get("fit_score")
        or updated.get("followers") != original.get("followers")
    )
    assert changed, "simulate-update should change at least one metric"


def test_simulate_update_records_snapshot():
    kol_id = _get_first_kol_id()
    history_before = client.get(f"/kols/{kol_id}/history").json()
    client.post(f"/kols/{kol_id}/simulate-update")
    history_after = client.get(f"/kols/{kol_id}/history").json()
    assert len(history_after) == len(history_before) + 1


def test_simulate_update_not_found():
    response = client.post("/kols/99999/simulate-update")
    assert response.status_code == 404


def test_simulate_update_engagement_within_bounds():
    kol_id = _get_first_kol_id()
    original = client.get(f"/kol/{kol_id}").json()
    for _ in range(5):
        updated = client.post(f"/kols/{kol_id}/simulate-update").json()
        assert 0.001 <= updated["engagement_rate"] <= 1.0
        assert 0.01 <= updated["fit_score"] <= 1.0
        assert updated["followers"] > 0


# ────────────────────────────────────────────────────────────
#  PUT /kols/{id} auto-snapshot integration
# ────────────────────────────────────────────────────────────

def test_put_kol_auto_records_snapshot():
    """Updating a KOL via PUT should auto-snapshot metrics before the change."""
    kol_id = _get_first_kol_id()
    original = client.get(f"/kol/{kol_id}").json()
    old_engagement = original["engagement_rate"]

    history_before = client.get(f"/kols/{kol_id}/history").json()
    client.put(f"/kols/{kol_id}", json={"engagement_rate": round(old_engagement * 1.1, 4)})
    history_after = client.get(f"/kols/{kol_id}/history").json()

    assert len(history_after) == len(history_before) + 1
    # Snapshot should capture the OLD value (recorded before change)
    newest_snap = history_after[0]
    assert newest_snap["engagement_rate"] == pytest.approx(old_engagement, rel=1e-3)
