# Backend API — Quick Reference

FastAPI service for the TikTok Shop KOL Matrix Optimizer.  
Full schema definitions live in [`docs/API_SPEC.md`](../docs/API_SPEC.md).

---

## Start the Server

**Windows (recommended):**
```
start_server.bat
```

**macOS / Linux:**
```bash
uvicorn backend.main:app --reload
```

The API listens on `http://localhost:8000` and auto-reloads on file changes.

- **Interactive Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Run Tests

```bash
pytest tests/ -v
```

---

## Endpoints

### Core

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/optimize` | Run all 6 algorithms, return best KOL matrix |
| `GET` | `/kols` | Filtered & paginated KOL list |
| `GET` | `/kol/{id}` | Single KOL detail with scores & reasons |
| `GET` | `/top-kols` | Top 10 KOLs by creator score |
| `POST` | `/scalability` | Algorithm performance at different pool sizes |

### Creator CRUD

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/kols/add` | Add a creator |
| `PUT` | `/kols/{id}` | Update a creator (auto-snapshots metrics) |
| `DELETE` | `/kols/{id}` | Delete a creator |
| `POST` | `/kols/import-csv` | Bulk import from CSV upload |
| `POST` | `/kols/reset` | Clear entire database |
| `GET` | `/kols/template` | Download CSV template |
| `GET` | `/kols/export` | Export all creators as CSV |

### KOL History Tracking

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/kols/{id}/history` | Metric snapshots (newest first) |
| `POST` | `/kols/{id}/simulate-update` | Apply random drift + record snapshot |

### Campaign Attribution

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/campaigns` | Save optimization result as campaign |
| `GET` | `/campaigns` | List all campaigns |
| `GET` | `/campaigns/{id}` | Single campaign detail |
| `PUT` | `/campaigns/{id}/actual` | Record actual GMV |
| `DELETE` | `/campaigns/{id}` | Delete campaign |

### API Integrations (Stubs)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/connections` | List integrations and statuses |
| `POST` | `/api/connections/interest` | Register early-access email |
| `POST` | `/api/connections/connect` | Connect integration (returns `coming_soon`) |

---

## 1. Health Check

```bash
curl http://localhost:8000/health
```
Response: `{ "status": "ok" }`

---

## 2. Optimize a Campaign

```bash
# macOS / Linux — beauty campaign, single country
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"budget": 5000, "countries": ["MY"], "category": "beauty", "seed": 42}'

# Multi-country — pool creators from MY + SG + ID
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"budget": 5000, "countries": ["MY","SG","ID"], "category": "beauty", "seed": 42}'

# All countries (omit countries or pass empty array)
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{"budget": 200, "countries": [], "category": "fmcg", "seed": 42}'

# Windows PowerShell
curl.exe -X POST http://localhost:8000/optimize `
  -H "Content-Type: application/json" `
  -d '{\"budget\": 5000, \"countries\": [\"MY\"], \"category\": \"beauty\", \"seed\": 42}'
```

Valid categories: `beauty`, `fashion`, `home`, `fmcg`  
Valid countries: `MY`, `ID`, `TH`, `PH`, `SG`, `VN`  
Minimum budget: `$100`

Response (abbreviated):
```json
{
  "best_algorithm": "Simulated Annealing",
  "total_gmv": 63450.0,
  "roi": 13.27,
  "results": {
    "simulated_annealing": { "total_gmv": 63450.0, "history": [...] },
    "hill_climber":        { "total_gmv": 51200.0, "history": [...] },
    "random_search":       { "total_gmv": 32100.0, "history": [...] },
    "genetic_algorithm":   { "total_gmv": 60800.0, "history": [...] },
    "tabu_search":         { "total_gmv": 58400.0, "history": [...] },
    "greedy_ranking":      { "total_gmv": 47200.0, "history": [...] }
  }
}
```

---

## 3. KOL History Tracking

Every `PUT /kols/{id}` call automatically snapshots the KOL's `engagement_rate`, `fit_score`, `followers`, `avg_views`, and `avg_likes` to `data/kol_history.json` before applying changes.

```bash
# View history (newest first)
curl http://localhost:8000/kols/7/history

# Simulate a TikTok API refresh (random drift + snapshot)
curl -X POST http://localhost:8000/kols/7/simulate-update
```

Drift ranges: engagement_rate ±[−8%,+12%], fit_score ±[−5%,+8%], followers ±[−2%,+6%].

---

## 4. Campaign Attribution

```bash
# Save a campaign after optimization
curl -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{"name": "MY Beauty June", "country": "MY", "category": "beauty",
       "budget": 5000, "best_algorithm": "Simulated Annealing",
       "selected_kols": [...], "total_cost": 4780, "predicted_gmv": 63450}'

# Record actual GMV (transitions status to "completed")
curl -X PUT http://localhost:8000/campaigns/1/actual \
  -H "Content-Type: application/json" \
  -d '{"actual_total_gmv": 58200}'
```

`accuracy_pct = actual_total_gmv / predicted_gmv × 100`

---

## Data File Locations

| File | Purpose |
|------|---------|
| `data/sample_kols.json` | Active KOL database |
| `data/kol_history.json` | Metric snapshots (auto-updated on every PUT) |
| `data/campaigns.json` | Campaign attribution records |

---

## Error Format

```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|--------|---------|
| `422` | Validation failure |
| `404` | Resource not found |
| `500` | Server-side bug or missing data file |
