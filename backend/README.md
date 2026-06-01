# Backend API — Quick Reference

FastAPI service for the TikTok Shop KOL Matrix Optimizer.  
Full schema definitions live in [`docs/API_SPEC.md`](../docs/API_SPEC.md).

---

## Start the Server

From the repository root:

```bash
uvicorn backend.main:app --reload
```

The API listens on `http://localhost:8000` and auto-reloads on file changes.

- **Interactive Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Run Tests

```bash
pytest tests/test_api.py -v
```

28 endpoint tests covering all 6 routes, happy paths, edge cases, and reproducibility.

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/optimize` | Run all 3 algorithms, return best KOL matrix |
| `GET` | `/kols` | Filtered & paginated KOL list |
| `GET` | `/kol/{id}` | Single KOL detail with scores & reasons |
| `GET` | `/top-kols` | Top 10 KOLs by creator score |
| `POST` | `/scalability` | Algorithm performance at different pool sizes |

---

## 1. Health Check

```bash
# macOS / Linux
curl http://localhost:8000/health

# Windows PowerShell
curl.exe http://localhost:8000/health
```

Response:
```json
{ "status": "ok" }
```

---

## 2. Optimize a Campaign

```bash
# macOS / Linux
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"budget": 5000, "country": "MY", "category": "beauty", "seed": 42}'

# Windows PowerShell
curl.exe -X POST http://localhost:8000/optimize `
  -H "Content-Type: application/json" `
  -d '{\"budget\": 5000, \"country\": \"MY\", \"category\": \"beauty\", \"seed\": 42}'
```

Response (abbreviated):
```json
{
  "budget": 5000,
  "country": "MY",
  "category": "beauty",
  "candidates": 43,
  "best_algorithm": "Simulated Annealing",
  "selected_kols": [
    {
      "id": 7,
      "name": "KOL_7",
      "tier": "Micro",
      "creator_score": 0.71,
      "expected_gmv": 11220.0,
      "reasons": [
        "Malaysia audience match is 85%, well above the 80% threshold",
        "Engagement rate 11.0% in beauty content",
        "Micro KOL with 120K followers — high conversion rate"
      ]
    }
  ],
  "total_cost": 4780.0,
  "total_gmv": 63450.0,
  "roi": 13.27,
  "results": { "simulated_annealing": {...}, "hill_climber": {...}, "random_search": {...} }
}
```

**Request fields:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `budget` | float | yes | > 0 |
| `country` | string | no (default `"MY"`) | `MY`, `ID`, `TH`, `PH` |
| `category` | string | no (default `"beauty"`) | `beauty`, `tech`, `fashion` |
| `seed` | int | no (default `42`) | any int |

**Error responses:**

| Status | When |
|--------|------|
| `422` | `budget <= 0` |
| `422` | unknown `country` |
| `422` | unknown `category` |
| `200` with `candidates: 0` | no KOLs match the filter — *not* an error |

---

## 3. List KOLs (Filtered & Paginated)

```bash
curl "http://localhost:8000/kols?country=MY&category=beauty&tier=Micro&limit=20&offset=0"
```

Response:
```json
{
  "total": 18,
  "limit": 20,
  "offset": 0,
  "kols": [ /* up to `limit` KOLResult objects */ ]
}
```

**Query parameters:** all optional.

| Param | Type | Validation |
|-------|------|------------|
| `country` | string | `MY` / `ID` / `TH` / `PH` |
| `category` | string | `beauty` / `tech` / `fashion` |
| `tier` | string | `Mega` / `Macro` / `Micro` / `Nano` |
| `limit` | int | 1 – 200 (default 50) |
| `offset` | int | ≥ 0 (default 0) |

---

## 4. Single KOL Detail

```bash
curl http://localhost:8000/kol/7
```

Returns the full `KOLResult` plus four extended audience fields:

```json
{
  "id": 7,
  "name": "KOL_7",
  "tier": "Micro",
  "creator_score": 0.71,
  "reasons": ["..."],
  "avg_views": 45000,
  "avg_likes": 3800,
  "gender_ratio": 0.78,
  "age_group": "18-24"
}
```

Returns `404` if the ID does not exist:
```json
{ "detail": "KOL with id 99999 not found" }
```

---

## 5. Top 10 KOLs by Creator Score

```bash
curl "http://localhost:8000/top-kols?country=MY&category=beauty"
```

Response:
```json
{
  "country": "MY",
  "category": "beauty",
  "top_kols": [ /* up to 10 KOLResult objects, sorted by creator_score desc */ ]
}
```

Both query parameters are optional. Omitting both ranks across the entire pool.

---

## 6. Scalability Test

Runs all three algorithms on a freshly generated pool of `n` KOLs and reports timing + GMV.

```bash
# macOS / Linux
curl -X POST http://localhost:8000/scalability \
  -H "Content-Type: application/json" \
  -d '{"n": 200, "budget": 5000, "seed": 42}'

# Windows PowerShell
curl.exe -X POST http://localhost:8000/scalability `
  -H "Content-Type: application/json" `
  -d '{\"n\": 200, \"budget\": 5000, \"seed\": 42}'
```

Response:
```json
{
  "n": 200,
  "budget": 5000,
  "simulated_annealing": { "time_seconds": 2.34, "total_gmv": 48200.0, "roi": 10.15, "selected_count": 6 },
  "hill_climber":        { "time_seconds": 0.81, "total_gmv": 41300.0, "roi": 8.63, "selected_count": 4 },
  "random_search":       { "time_seconds": 0.52, "total_gmv": 27800.0, "roi": 5.96, "selected_count": 3 }
}
```

**Validation:** `n` must be in `[10, 500]` and `budget > 0`.

---

## Error Format

All errors follow the FastAPI convention:

```json
{ "detail": "Human-readable error message" }
```

Common status codes:

| Status | Meaning |
|--------|---------|
| `422` | Validation failure (bad input) |
| `404` | Resource not found |
| `500` | Server-side bug or missing data file |

---

## Data File Location

The backend reads `data/sample_kols.json` on every request (no in-memory cache). Regenerate the dataset with:

```bash
python data/generator.py            # default 300 KOLs
python data/generator.py --num 500  # custom pool size
```