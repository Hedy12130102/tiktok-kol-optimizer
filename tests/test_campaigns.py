"""
Campaign Attribution endpoint tests.

Run:  pytest tests/test_campaigns.py -v
"""
import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
import backend.tenancy as tenancy_module

client = TestClient(app)

# ────────────────────────────────────────────────────────────
#  Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_campaigns_file(tmp_path, monkeypatch):
    """Each test gets its own empty campaigns.json so tests don't interfere."""
    tmp_file = tmp_path / "campaigns.json"
    tmp_file.write_text("[]")
    monkeypatch.setattr(tenancy_module, "campaigns_path", lambda: str(tmp_file))
    yield str(tmp_file)


SAMPLE_CAMPAIGN = {
    "name": "MY Beauty Test Campaign",
    "countries": ["MY"],
    "category": "beauty",
    "budget": 5000.0,
    "best_algorithm": "Simulated Annealing",
    "selected_kols": [
        {
            "id": 1,
            "name": "KOL_1",
            "country": "MY",
            "category": "beauty",
            "followers": 120000,
            "cost": 750.0,
            "predicted_gmv": 11220.0,
            "tier": "Micro",
        }
    ],
    "total_cost": 750.0,
    "predicted_gmv": 11220.0,
}


# ────────────────────────────────────────────────────────────
#  POST /campaigns
# ────────────────────────────────────────────────────────────

def test_create_campaign_happy_path():
    response = client.post("/campaigns", json=SAMPLE_CAMPAIGN)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "MY Beauty Test Campaign"
    assert data["status"] == "active"
    assert data["predicted_gmv"] == 11220.0
    assert data["actual_total_gmv"] is None
    assert data["accuracy_pct"] is None
    assert "id" in data
    assert "created_at" in data


def test_create_campaign_assigns_sequential_ids():
    r1 = client.post("/campaigns", json=SAMPLE_CAMPAIGN).json()
    r2 = client.post("/campaigns", json={**SAMPLE_CAMPAIGN, "name": "Campaign 2"}).json()
    assert r2["id"] == r1["id"] + 1


# ────────────────────────────────────────────────────────────
#  GET /campaigns
# ────────────────────────────────────────────────────────────

def test_list_campaigns_empty():
    response = client.get("/campaigns")
    assert response.status_code == 200
    assert response.json() == []


def test_list_campaigns_returns_newest_first():
    client.post("/campaigns", json={**SAMPLE_CAMPAIGN, "name": "First"})
    client.post("/campaigns", json={**SAMPLE_CAMPAIGN, "name": "Second"})
    campaigns = client.get("/campaigns").json()
    assert len(campaigns) == 2
    assert campaigns[0]["name"] == "Second"
    assert campaigns[1]["name"] == "First"


# ────────────────────────────────────────────────────────────
#  GET /campaigns/{id}
# ────────────────────────────────────────────────────────────

def test_get_campaign_by_id():
    created = client.post("/campaigns", json=SAMPLE_CAMPAIGN).json()
    response = client.get(f"/campaigns/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_campaign_not_found():
    response = client.get("/campaigns/99999")
    assert response.status_code == 404
    assert "99999" in response.json()["detail"]


# ────────────────────────────────────────────────────────────
#  PUT /campaigns/{id}/actual
# ────────────────────────────────────────────────────────────

def test_record_actual_gmv():
    created = client.post("/campaigns", json=SAMPLE_CAMPAIGN).json()
    cid = created["id"]

    response = client.put(f"/campaigns/{cid}/actual", json={"actual_total_gmv": 10000.0})
    assert response.status_code == 200
    data = response.json()
    assert data["actual_total_gmv"] == 10000.0
    assert data["status"] == "completed"
    assert data["accuracy_pct"] == pytest.approx(10000.0 / 11220.0 * 100, rel=1e-3)
    assert data["completed_at"] is not None


def test_record_actual_gmv_with_kol_breakdown():
    created = client.post("/campaigns", json=SAMPLE_CAMPAIGN).json()
    cid = created["id"]

    payload = {
        "actual_total_gmv": 9500.0,
        "kol_actuals": [{"id": 1, "actual_gmv": 9500.0}],
    }
    response = client.put(f"/campaigns/{cid}/actual", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["kol_actuals"][0]["actual_gmv"] == 9500.0


def test_accuracy_pct_over_100_allowed():
    """Campaigns can outperform predictions — accuracy > 100% is valid."""
    created = client.post("/campaigns", json=SAMPLE_CAMPAIGN).json()
    response = client.put(f"/campaigns/{created['id']}/actual", json={"actual_total_gmv": 15000.0})
    data = response.json()
    assert data["accuracy_pct"] > 100.0


def test_record_actual_campaign_not_found():
    response = client.put("/campaigns/99999/actual", json={"actual_total_gmv": 5000.0})
    assert response.status_code == 404


# ────────────────────────────────────────────────────────────
#  DELETE /campaigns/{id}
# ────────────────────────────────────────────────────────────

def test_delete_campaign():
    created = client.post("/campaigns", json=SAMPLE_CAMPAIGN).json()
    cid = created["id"]

    response = client.delete(f"/campaigns/{cid}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    # Should be gone
    assert client.get(f"/campaigns/{cid}").status_code == 404


def test_delete_campaign_not_found():
    response = client.delete("/campaigns/99999")
    assert response.status_code == 404


# ────────────────────────────────────────────────────────────
#  Lifecycle integration test
# ────────────────────────────────────────────────────────────

def test_full_campaign_lifecycle():
    """Create → verify active → record actual → verify completed."""
    # 1. Create
    r = client.post("/campaigns", json=SAMPLE_CAMPAIGN)
    assert r.status_code == 200
    cid = r.json()["id"]

    # 2. Active status
    assert client.get(f"/campaigns/{cid}").json()["status"] == "active"

    # 3. Record actual
    r = client.put(f"/campaigns/{cid}/actual", json={"actual_total_gmv": 9800.0})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["accuracy_pct"] == pytest.approx(9800 / 11220 * 100, rel=1e-3)

    # 4. List shows completed
    campaigns = client.get("/campaigns").json()
    assert any(c["status"] == "completed" for c in campaigns)
