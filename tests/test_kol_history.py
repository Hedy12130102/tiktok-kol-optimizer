"""
KOL History Tracking endpoint tests.

GET  /kols/{id}/history response shape:
  {"kol_id": int, "snapshots": [...], "count": int}
  Each snapshot: {"recorded_at": str, "engagement_rate": float,
                  "fit_score": float, "followers": int, ...}

POST /kols/{id}/simulate-update response shape:
  {"message": str, "kol_id": int,
   "changes": {"engagement_rate": {"before":float,"after":float}, ...}}
"""
import os
import sys
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
import backend.crud as crud_module

client = TestClient(app)


# --- Fixtures ---

@pytest.fixture(autouse=True)
def isolated_history_file(tmp_path, monkeypatch):
    """Each test gets a fresh kol_history.json to prevent pollution."""
    tmp_file = tmp_path / "kol_history.json"
    tmp_file.write_text("[]")
    monkeypatch.setattr(crud_module, "KOL_HISTORY_PATH", str(tmp_file))
    yield str(tmp_file)


def _get_first_kol_id() -> int:
    response = client.get("/kols?limit=1")
    kols = response.json()["kols"]
    if not kols:
        pytest.skip("No KOLs in database -- run data/generator.py first")
    return kols[0]["id"]


# --- GET /kols/{id}/history ---

def test_history_empty_before_any_update():
    kol_id = _get_first_kol_id()
    response = client.get(f"/kols/{kol_id}/history")
    assert response.status_code == 200
    body = response.json()
    assert body["kol_id"] == kol_id
    assert body["snapshots"] == []
    assert body["count"] == 0


def test_history_not_found_for_invalid_id():
    response = client.get("/kols/99999/history")
    assert response.status_code == 404


def test_history_returns_snapshots_after_simulate():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    body = client.get(f"/kols/{kol_id}/history").json()
    assert body["count"] >= 1
    assert len(body["snapshots"]) >= 1


def test_history_snapshot_has_required_fields():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    snap = client.get(f"/kols/{kol_id}/history").json()["snapshots"][0]
    assert "recorded_at" in snap
    assert "engagement_rate" in snap
    assert "fit_score" in snap
    assert "followers" in snap


def test_history_newest_first():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    client.post(f"/kols/{kol_id}/simulate-update")
    body = client.get(f"/kols/{kol_id}/history").json()
    assert body["count"] >= 2
    ts = [s["recorded_at"] for s in body["snapshots"]]
    assert ts == sorted(ts, reverse=True)


def test_history_count_matches_snapshot_list():
    kol_id = _get_first_kol_id()
    client.post(f"/kols/{kol_id}/simulate-update")
    client.post(f"/kols/{kol_id}/simulate-update")
    body = client.get(f"/kols/{kol_id}/history").json()
    assert body["count"] == len(body["snapshots"])


# --- POST /kols/{id}/simulate-update ---

def test_simulate_update_returns_200():
    kol_id = _get_first_kol_id()
    assert client.post(f"/kols/{kol_id}/simulate-update").status_code == 200


def test_simulate_update_response_shape():
    kol_id = _get_first_kol_id()
    body = client.post(f"/kols/{kol_id}/simulate-update").json()
    assert body["kol_id"] == kol_id
    assert "message" in body
    changes = body["changes"]
    for metric in ("engagement_rate", "fit_score", "followers"):
        assert metric in changes
        assert "before" in changes[metric]
        assert "after" in changes[metric]


def test_simulate_update_records_snapshot():
    kol_id = _get_first_kol_id()
    before = client.get(f"/kols/{kol_id}/history").json()["count"]
    client.post(f"/kols/{kol_id}/simulate-update")
    after = client.get(f"/kols/{kol_id}/history").json()["count"]
    assert after == before + 1


def test_simulate_update_not_found():
    assert client.post("/kols/99999/simulate-update").status_code == 404


def test_simulate_update_metrics_within_bounds():
    kol_id = _get_first_kol_id()
    for _ in range(5):
        body = client.post(f"/kols/{kol_id}/simulate-update").json()
        eng = body["changes"]["engagement_rate"]["after"]
        fit = body["changes"]["fit_score"]["after"]
        fol = body["changes"]["followers"]["after"]
        assert 0.001 <= eng <= 1.0
        assert 0.01 <= fit <= 1.0
        assert fol > 0


# --- PUT /kols/{id} auto-snapshot ---

def test_put_kol_auto_records_snapshot():
    """PUT should auto-snapshot the current metrics before applying changes."""
    kol_id = _get_first_kol_id()
    original = client.get(f"/kol/{kol_id}").json()
    old_engagement = original["engagement_rate"]

    count_before = client.get(f"/kols/{kol_id}/history").json()["count"]
    client.put(f"/kols/{kol_id}", json={"engagement_rate": round(old_engagement * 1.1, 4)})
    body_after = client.get(f"/kols/{kol_id}/history").json()

    assert body_after["count"] == count_before + 1
    # Snapshot should contain the OLD value (captured before the change)
    newest_snap = body_after["snapshots"][0]
    assert newest_snap["engagement_rate"] == pytest.approx(old_engagement, rel=1e-3)
