"""
Prediction-calibration feedback loop.

Completing a campaign with a known actual-vs-predicted ratio should fold into the
tenant's calibration table and visibly move future GMV predictions — and only for
that tenant.
"""
import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _register():
    r = client.post("/auth/register", json={"email": f"c_{uuid.uuid4().hex[:8]}@s.test", "password": "secret123"})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _first_my_beauty_gmv(auth):
    k = client.get("/kols?country=MY&category=beauty&limit=1", headers=auth).json()["kols"]
    return (k[0]["id"], k[0]["expected_gmv"]) if k else (None, None)


def _record_actual(auth, campaign_id, actual):
    return client.put(f"/campaigns/{campaign_id}/actual", headers=auth,
                      json={"actual_total_gmv": actual})


def test_calibration_starts_neutral():
    auth = _register()
    s = client.get("/calibration", headers=auth).json()
    assert s["campaigns_used"] == 0
    assert s["global_factor"] == 1.0


def test_actual_below_predicted_lowers_future_predictions():
    auth = _register()
    kid, gmv_before = _first_my_beauty_gmv(auth)
    assert gmv_before and gmv_before > 0

    # Complete one MY/beauty campaign whose actual GMV is half the prediction.
    saved = client.post("/campaigns", headers=auth, json={
        "name": "cal", "countries": ["MY"], "category": "beauty",
        "budget": 5000, "best_algorithm": "Genetic Algorithm",
        "selected_kols": [], "total_cost": 1000, "predicted_gmv": 1000.0,
    }).json()
    _record_actual(auth, saved["id"], 500.0)

    s = client.get("/calibration", headers=auth).json()
    assert s["campaigns_used"] == 1
    assert abs(s["global_factor"] - 0.5) < 0.01

    # The same creator's predicted GMV should now be ~half what it was.
    kid2, gmv_after = _first_my_beauty_gmv(auth)
    assert kid2 == kid
    assert gmv_after < gmv_before
    assert abs(gmv_after / gmv_before - 0.5) < 0.05


def test_calibration_scales_optimize_total():
    auth = _register()
    before = client.post("/optimize", headers=auth,
                         json={"budget": 5000, "countries": ["MY"], "category": "beauty", "seed": 42}).json()
    if before["candidates"] == 0:
        return  # nothing to assert on an empty slice

    saved = client.post("/campaigns", headers=auth, json={
        "name": "cal", "countries": ["MY"], "category": "beauty",
        "budget": 5000, "best_algorithm": "Genetic Algorithm",
        "selected_kols": [], "total_cost": 1000, "predicted_gmv": 1000.0,
    }).json()
    _record_actual(auth, saved["id"], 500.0)

    after = client.post("/optimize", headers=auth,
                        json={"budget": 5000, "countries": ["MY"], "category": "beauty", "seed": 42}).json()
    # GMV halves; the objective-based winner (ranking) is unchanged.
    assert after["total_gmv"] < before["total_gmv"]
    assert abs(after["total_gmv"] / before["total_gmv"] - 0.5) < 0.05
    assert after["best_algorithm"] == before["best_algorithm"]


def test_per_creator_calibration_adjusts_only_that_creator():
    auth = _register()
    ks = client.get("/kols?country=MY&category=beauty&limit=2", headers=auth).json()["kols"]
    if len(ks) < 2:
        return
    c0, c1 = ks[0], ks[1]
    e0_before, e1_before = c0["expected_gmv"], c1["expected_gmv"]

    # Campaign-level actual == predicted (so the segment factor stays ~1.0), but
    # creator c0's own actual is half its prediction → only c0 should be discounted.
    saved = client.post("/campaigns", headers=auth, json={
        "name": "l3", "countries": ["MY"], "category": "beauty", "budget": 5000,
        "best_algorithm": "GA", "total_cost": 1000, "predicted_gmv": 1000.0,
        "selected_kols": [{
            "id": c0["id"], "name": c0["name"], "country": "MY", "category": "beauty",
            "followers": c0["followers"], "cost": c0["cost"],
            "predicted_gmv": 1000.0, "tier": c0["tier"],
        }],
    }).json()
    client.put(f"/campaigns/{saved['id']}/actual", headers=auth, json={
        "actual_total_gmv": 1000.0,
        "kol_actuals": [{"id": c0["id"], "actual_gmv": 500.0}],
    })

    s = client.get("/calibration", headers=auth).json()
    assert s["creators_tracked"] == 1
    assert abs(s["global_factor"] - 1.0) < 0.02   # campaign level unchanged

    after = client.get("/kols?country=MY&category=beauty&limit=2", headers=auth).json()["kols"]
    a0 = next(k for k in after if k["id"] == c0["id"])
    a1 = next(k for k in after if k["id"] == c1["id"])
    assert a0["expected_gmv"] < e0_before                    # under-deliverer discounted
    assert abs(a1["expected_gmv"] - e1_before) < 0.01        # neighbour untouched


def test_calibration_is_per_tenant():
    a = _register()
    b = _register()
    saved = client.post("/campaigns", headers=a, json={
        "name": "cal", "countries": ["MY"], "category": "beauty",
        "budget": 5000, "best_algorithm": "Genetic Algorithm",
        "selected_kols": [], "total_cost": 1000, "predicted_gmv": 1000.0,
    }).json()
    _record_actual(a, saved["id"], 500.0)

    assert client.get("/calibration", headers=a).json()["campaigns_used"] == 1
    assert client.get("/calibration", headers=b).json()["campaigns_used"] == 0
    assert client.get("/calibration", headers=b).json()["global_factor"] == 1.0
