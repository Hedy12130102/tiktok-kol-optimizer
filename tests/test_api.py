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
        "countries": ["MY"],
        "category": "beauty",
        "seed": 42,
    })
    assert response.status_code == 200
    data = response.json()

    # Echo fields
    assert data["budget"] == 5000
    assert data["countries"] == ["MY"]
    assert data["category"] == "beauty"

    # Top-level fields
    assert "candidates" in data
    assert "best_algorithm" in data
    assert "selected_kols" in data
    assert "total_cost" in data
    assert "total_gmv" in data
    assert "roi" in data
    assert "results" in data

    # All six algorithms present
    assert "simulated_annealing" in data["results"]
    assert "hill_climber" in data["results"]
    assert "random_search" in data["results"]
    assert "genetic_algorithm" in data["results"]
    assert "tabu_search" in data["results"]
    assert "greedy_ranking" in data["results"]

    # Each algorithm result has the expected structure
    for algo_key in data["results"]:
        algo = data["results"][algo_key]
        assert "algorithm" in algo
        assert "selected_kols" in algo
        assert "selected_count" in algo
        assert "total_cost" in algo
        assert "total_gmv" in algo
        assert "roi" in algo
        assert "objective" in algo
        assert "history" in algo
        assert isinstance(algo["history"], list)


def test_optimize_includes_tier_and_creator_score():
    """Each selected KOL must include tier, creator_score and reasons fields."""
    response = client.post("/optimize", json={
        "budget": 10000,
        "countries": ["MY"],
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


def test_optimize_history_arrays_nonempty():
    """All six algorithm history arrays must be non-empty lists."""
    response = client.post("/optimize", json={
        "budget": 5000, "countries": ["MY"], "category": "beauty", "seed": 42,
    })
    results = response.json()["results"]
    for algo_key in ["simulated_annealing", "hill_climber", "random_search",
                     "genetic_algorithm", "tabu_search", "greedy_ranking"]:
        hist = results[algo_key]["history"]
        assert isinstance(hist, list) and len(hist) > 0, \
            f"{algo_key} history is empty"


def test_optimize_best_algorithm_has_highest_objective():
    """The best_algorithm field must correspond to the algorithm with the highest
    objective (GMV net of the audience-overlap penalty) — the value the solvers
    actually optimise. Ranking by raw GMV instead would let the Random Search
    baseline win by ignoring overlap."""
    response = client.post("/optimize", json={
        "budget": 5000, "countries": ["MY"], "category": "beauty", "seed": 42,
    })
    data = response.json()
    best_name = data["best_algorithm"]

    if data["candidates"] > 0:
        objectives = {algo["algorithm"]: algo["objective"]
                      for algo in data["results"].values()}
        max_obj = max(objectives.values())
        assert objectives[best_name] == max_obj


# ════════════════════════════════════════════════════════════════
#  POST /optimize — input validation
# ════════════════════════════════════════════════════════════════
def test_optimize_rejects_zero_budget():
    response = client.post("/optimize", json={
        "budget": 0, "countries": ["MY"], "category": "beauty",
    })
    assert response.status_code == 422
    assert "budget" in response.json()["detail"].lower()


def test_optimize_rejects_negative_budget():
    response = client.post("/optimize", json={
        "budget": -100, "countries": ["MY"], "category": "beauty",
    })
    assert response.status_code == 422


def test_optimize_rejects_unknown_country():
    response = client.post("/optimize", json={
        "budget": 5000, "countries": ["JP"], "category": "beauty",
    })
    assert response.status_code == 422
    assert "countr" in response.json()["detail"].lower()


def test_optimize_rejects_unknown_category():
    response = client.post("/optimize", json={
        "budget": 5000, "countries": ["MY"], "category": "gaming",
    })
    assert response.status_code == 422
    assert "category" in response.json()["detail"].lower()


def test_optimize_accepts_all_valid_countries():
    """All six target markets should be accepted."""
    for country in ["MY", "ID", "TH", "PH", "SG", "VN"]:
        response = client.post("/optimize", json={
            "budget": 5000, "countries": [country], "category": "beauty",
        })
        assert response.status_code == 200, f"{country} was rejected"


def test_optimize_accepts_all_valid_categories():
    """All 4 product categories should be accepted."""
    for category in ["beauty", "fashion", "home", "fmcg"]:
        response = client.post("/optimize", json={
            "budget": 5000, "countries": ["MY"], "category": category,
        })
        assert response.status_code == 200, f"{category} was rejected"


def test_optimize_accepts_small_budget():
    """Budgets as low as $100 should be accepted (small merchant support)."""
    response = client.post("/optimize", json={
        "budget": 100, "countries": ["MY"], "category": "fmcg",
    })
    assert response.status_code == 200


def test_optimize_multi_country():
    """Multi-country selection should return 200 and echo all requested countries."""
    response = client.post("/optimize", json={
        "budget": 5000, "countries": ["MY", "SG"], "category": "beauty", "seed": 1,
    })
    assert response.status_code == 200
    countries = response.json()["countries"]
    assert set(countries) == {"MY", "SG"}


def test_optimize_empty_countries_uses_all():
    """Empty countries list should include KOLs from all 6 markets."""
    response = client.post("/optimize", json={
        "budget": 50000, "countries": [], "category": "beauty", "seed": 1,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["candidates"] > 0


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
    response = client.get("/kols?country=JP")
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
#  POST /simulate-scale  (synthetic creator-pool-size simulator)
# ════════════════════════════════════════════════════════════════
def test_simulate_scale_returns_monotonic_curve():
    response = client.post("/simulate-scale", json={"budget": 5000, "seed": 42})
    assert response.status_code == 200
    data = response.json()
    pts = data["points"]
    assert len(pts) >= 2
    # sizes are ascending and the achievable curve is non-decreasing (nested pools)
    assert pts == sorted(pts, key=lambda p: p["n"])
    gmvs = [p["gmv"] for p in pts]
    assert gmvs == sorted(gmvs), "achievable GMV must be monotonic in pool size"
    for p in pts:
        assert p["gmv"] >= p["baseline_gmv"] >= 0
        assert p["selected_count"] >= 0


def test_simulate_scale_target_returns_needed_n():
    response = client.post("/simulate-scale", json={"budget": 5000, "seed": 42, "target_gmv": 50000})
    assert response.status_code == 200
    data = response.json()
    needed = data["needed_n"]
    # needed_n is either None or one of the swept sizes whose gmv meets the target
    if needed is not None:
        hit = next(p for p in data["points"] if p["n"] == needed)
        assert hit["gmv"] >= 50000


def test_simulate_scale_custom_sizes():
    response = client.post("/simulate-scale", json={"budget": 5000, "seed": 1, "sizes": [30, 120]})
    assert response.status_code == 200
    assert [p["n"] for p in response.json()["points"]] == [30, 120]


def test_simulate_scale_rejects_zero_budget():
    response = client.post("/simulate-scale", json={"budget": 0})
    assert response.status_code == 422


# ════════════════════════════════════════════════════════════════
#  POST /kols/reset  — restores the seed baseline
# ════════════════════════════════════════════════════════════════
def test_reset_restores_seed_baseline():
    """Reset should restore the library to the seed baseline, not empty it."""
    # Remove a known creator, then reset and confirm the library is whole again.
    client.delete("/kol/1")
    response = client.post("/kols/reset")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0, "reset should restore creators, not clear them"
    # The previously deleted creator is back.
    assert client.get("/kol/1").status_code == 200


# ═══════════════════════════════════════════════════════════
#  Reproducibility
# ════════════════════════════════════════════════════
def test_optimize_same_seed_same_result():
    """Same seed should produce identical results across two calls."""
    payload = {"budget": 5000, "countries": ["MY"], "category": "beauty", "seed": 42}
    r1 = client.post("/optimize", json=payload).json()
    r2 = client.post("/optimize", json=payload).json()
    assert r1["total_gmv"] == r2["total_gmv"]
    assert r1["best_algorithm"] == r2["best_algorithm"]