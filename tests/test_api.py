"""
API endpoint tests — covers all 6 endpoints with happy paths and edge cases.

Run:  pytest tests/test_api.py -v
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


# ════════════════════════════════════════════════════════════════
#  GET /health
# ════════════════════════════════════════════════════════════════
def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ════════════════════════════════════════════════════════════════
#  POST /optimize — happy path
# ════════════════════════════════════════════════════════════════
def test_optimize_happy_path():
    """Standard request should return 200 with all three algorithm results."""
    response = client.post("/optimize", json={
        "budget": 5000,
        "country": "MY",
        "category": "beauty",
        "seed": 42,
    })
    assert response.status_code == 200
    data = response.json()

    # Echo fields
    assert data["budget"] == 5000
    assert data["country"] == "MY"
    assert data["category"] == "beauty"

    # Top-level fields
    assert "candidates" in data
    assert "best_algorithm" in data
    assert "selected_kols" in data
    assert "total_cost" in data
    assert "total_gmv" in data
    assert "roi" in data
    assert "results" in data

    # All three algorithms present
    assert "simulated_annealing" in data["results"]
    assert "hill_climber" in data["results"]
    assert "random_search" in data["results"]

    # Each algorithm result has the expected structure
    for algo_key in ["simulated_annealing", "hill_climber", "random_search"]:
        algo = data["results"][algo_key]
        assert "algorithm" in algo
        assert "selected_kols" in algo
        assert "selected_count" in algo
        assert "total_cost" in algo
        assert "total_gmv" in algo
        assert "roi" in algo
        assert "history" in algo
        assert isinstance(algo["history"], list)


def test_optimize_includes_tier_and_creator_score():
    """Each selected KOL must include tier, creator_score and reasons fields."""
    response = client.post("/optimize", json={
        "budget": 10000,
        "country": "MY",
        "category": "beauty",
        "seed": 42,
    })
    assert response.status_code == 200
    selected = response.json()["selected_kols"]

    if selected:  # only check if there's at least one KOL selected
        kol = selected[0]
        assert "tier" in kol
        assert kol["tier"] in ["Mega", "Macro", "Micro", "Nano"]
        assert "creator_score" in kol
        assert 0.0 <= kol["creator_score"] <= 1.0
        assert "reasons" in kol
        assert isinstance(kol["reasons"], list)
        assert len(kol["reasons"]) >= 3  # spec guarantees at least 3 reasons


def test_optimize_history_arrays_same_length():
    """All three history arrays must be truncated to the same length."""
    response = client.post("/optimize", json={
        "budget": 5000, "country": "MY", "category": "beauty", "seed": 42,
    })
    results = response.json()["results"]
    lengths = [
        len(results["simulated_annealing"]["history"]),
        len(results["hill_climber"]["history"]),
        len(results["random_search"]["history"]),
    ]
    assert len(set(lengths)) == 1, f"history arrays differ in length: {lengths}"


def test_optimize_best_algorithm_has_highest_gmv():
    """The best_algorithm field must correspond to the algorithm with max GMV."""
    response = client.post("/optimize", json={
        "budget": 5000, "country": "MY", "category": "beauty", "seed": 42,
    })
    data = response.json()
    best_name = data["best_algorithm"]

    if data["candidates"] > 0:
        gmvs = {algo["algorithm"]: algo["total_gmv"]
                for algo in data["results"].values()}
        max_gmv = max(gmvs.values())
        assert gmvs[best_name] == max_gmv


# ════════════════════════════════════════════════════════════════
#  POST /optimize — input validation
# ════════════════════════════════════════════════════════════════
def test_optimize_rejects_zero_budget():
    response = client.post("/optimize", json={
        "budget": 0, "country": "MY", "category": "beauty",
    })
    assert response.status_code == 422
    assert "budget" in response.json()["detail"].lower()


def test_optimize_rejects_negative_budget():
    response = client.post("/optimize", json={
        "budget": -100, "country": "MY", "category": "beauty",
    })
    assert response.status_code == 422


def test_optimize_rejects_unknown_country():
    response = client.post("/optimize", json={
        "budget": 5000, "country": "SG", "category": "beauty",
    })
    assert response.status_code == 422
    assert "country" in response.json()["detail"].lower()


def test_optimize_rejects_unknown_category():
    response = client.post("/optimize", json={
        "budget": 5000, "country": "MY", "category": "food",
    })
    assert response.status_code == 422
    assert "category" in response.json()["detail"].lower()


def test_optimize_accepts_all_valid_countries():
    """All four target markets should be accepted."""
    for country in ["MY", "ID", "TH", "PH"]:
        response = client.post("/optimize", json={
            "budget": 5000, "country": country, "category": "beauty",
        })
        assert response.status_code == 200, f"{country} was rejected"


def test_optimize_accepts_all_valid_categories():
    for category in ["beauty", "tech", "fashion"]:
        response = client.post("/optimize", json={
            "budget": 5000, "country": "MY", "category": category,
        })
        assert response.status_code == 200, f"{category} was rejected"


# ════════════════════════════════════════════════════════════════
#  GET /kols
# ════════════════════════════════════════════════════════════════
def test_kols_returns_paginated_list():
    response = client.get("/kols")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "kols" in data
    assert isinstance(data["kols"], list)
    assert len(data["kols"]) <= data["limit"]


def test_kols_filter_by_country():
    response = client.get("/kols?country=MY&limit=200")
    assert response.status_code == 200
    for k in response.json()["kols"]:
        assert k["country"] == "MY"


def test_kols_filter_by_category():
    response = client.get("/kols?category=beauty&limit=200")
    assert response.status_code == 200
    for k in response.json()["kols"]:
        assert k["category"] == "beauty"


def test_kols_filter_by_tier():
    response = client.get("/kols?tier=Mega&limit=200")
    assert response.status_code == 200
    for k in response.json()["kols"]:
        assert k["tier"] == "Mega"


def test_kols_pagination():
    """offset=10 should return different items from offset=0."""
    page1 = client.get("/kols?limit=10&offset=0").json()["kols"]
    page2 = client.get("/kols?limit=10&offset=10").json()["kols"]
    if len(page1) == 10 and len(page2) > 0:
        ids1 = {k["id"] for k in page1}
        ids2 = {k["id"] for k in page2}
        assert ids1.isdisjoint(ids2), "Paginated results overlap"


def test_kols_rejects_invalid_country():
    response = client.get("/kols?country=SG")
    assert response.status_code == 422


def test_kols_rejects_invalid_tier():
    response = client.get("/kols?tier=Giant")
    assert response.status_code == 422


# ════════════════════════════════════════════════════════════════
#  GET /kol/{id}
# ════════════════════════════════════════════════════════════════
def test_kol_detail_existing_id():
    response = client.get("/kol/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    # Extended fields present
    assert "avg_views" in data
    assert "avg_likes" in data
    assert "gender_ratio" in data
    assert "age_group" in data


def test_kol_detail_not_found():
    response = client.get("/kol/99999")
    assert response.status_code == 404
    assert "99999" in response.json()["detail"]


# ════════════════════════════════════════════════════════════════
#  GET /top-kols
# ════════════════════════════════════════════════════════════════
def test_top_kols_returns_at_most_10():
    response = client.get("/top-kols?country=MY&category=beauty")
    assert response.status_code == 200
    data = response.json()
    assert "top_kols" in data
    assert len(data["top_kols"]) <= 10


def test_top_kols_sorted_by_creator_score_desc():
    response = client.get("/top-kols?country=MY&category=beauty")
    top = response.json()["top_kols"]
    scores = [k["creator_score"] for k in top]
    assert scores == sorted(scores, reverse=True), "top_kols not sorted by creator_score desc"


def test_top_kols_no_filter():
    """Should work without any filter parameters."""
    response = client.get("/top-kols")
    assert response.status_code == 200
    assert len(response.json()["top_kols"]) <= 10


# ════════════════════════════════════════════════════════════════
#  POST /scalability
# ════════════════════════════════════════════════════════════════
def test_scalability_returns_three_algorithms():
    response = client.post("/scalability", json={"n": 50, "budget": 5000, "seed": 42})
    assert response.status_code == 200
    data = response.json()
    assert data["n"] == 50
    assert "simulated_annealing" in data
    assert "hill_climber" in data
    assert "random_search" in data

    for algo_key in ["simulated_annealing", "hill_climber", "random_search"]:
        algo = data[algo_key]
        assert algo["time_seconds"] >= 0
        assert algo["total_gmv"] >= 0
        assert algo["selected_count"] >= 0


def test_scalability_rejects_n_too_small():
    response = client.post("/scalability", json={"n": 5, "budget": 5000})
    assert response.status_code == 422
    assert "n" in response.json()["detail"].lower()


def test_scalability_rejects_n_too_large():
    response = client.post("/scalability", json={"n": 501, "budget": 5000})
    assert response.status_code == 422


def test_scalability_rejects_zero_budget():
    response = client.post("/scalability", json={"n": 50, "budget": 0})
    assert response.status_code == 422


# ════════════════════════════════════════════════════════════════
#  Reproducibility
# ════════════════════════════════════════════════════════════════
def test_optimize_same_seed_same_result():
    """Same seed should produce identical results across two calls."""
    payload = {"budget": 5000, "country": "MY", "category": "beauty", "seed": 42}
    r1 = client.post("/optimize", json=payload).json()
    r2 = client.post("/optimize", json=payload).json()
    assert r1["total_gmv"] == r2["total_gmv"]
    assert r1["best_algorithm"] == r2["best_algorithm"]