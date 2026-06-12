"""
Creator CRUD & CSV import — data management endpoints.

Endpoints
---------
  POST   /kols/add                   Add a single KOL
  POST   /kols/import-csv            Bulk import from CSV
  PUT    /kols/{id}                  Update a KOL (auto-snapshots old values)
  DELETE /kols/{id}                  Delete a KOL
  GET    /kols/template              Download CSV template
  GET    /kols/export                Export all KOLs as CSV
  GET    /kols/{id}/history          Metric history snapshots for a KOL
  POST   /kols/{id}/simulate-update  Simulate a TikTok API refresh (random drift)

All writes persist to data/sample_kols.json immediately.
KOL metric history persists to data/kol_history.json.
"""
import csv
import io
import json
import os
import random
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator

router = APIRouter()

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "sample_kols.json",
)

KOL_HISTORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "kol_history.json",
)

# ── KOL history helpers ───────────────────────────────────────
_SNAPSHOT_FIELDS = ("engagement_rate", "fit_score", "followers", "commission_rate", "avg_views", "avg_likes")


def _load_history() -> List[dict]:
    if not os.path.exists(KOL_HISTORY_PATH):
        return []
    with open(KOL_HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_history(data: List[dict]):
    with open(KOL_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _record_snapshot(kol_record: dict):
    """Append a timestamped snapshot of the KOL's current metrics to history."""
    history = _load_history()
    entry = next((h for h in history if h["kol_id"] == kol_record["id"]), None)
    if entry is None:
        entry = {"kol_id": kol_record["id"], "snapshots": []}
        history.append(entry)

    snapshot = {"recorded_at": datetime.utcnow().isoformat()}
    for f in _SNAPSHOT_FIELDS:
        if f in kol_record and kol_record[f] is not None:
            snapshot[f] = kol_record[f]
    entry["snapshots"].append(snapshot)
    _save_history(history)

VALID_COUNTRIES = ["MY", "ID", "TH", "PH", "SG", "VN"]
VALID_CATEGORIES = ["beauty", "fashion", "home", "fmcg"]

CSV_TEMPLATE_HEADER = [
    "name", "country", "category", "followers",
    "engagement_rate", "fit_score", "commission_rate", "cost",
    "avg_views", "avg_likes", "gender_ratio", "age_group",
    "tiktok_url",
]


# ════════════════════════════════════════════════════════════════
#  Pydantic models
# ════════════════════════════════════════════════════════════════
class KOLCreate(BaseModel):
    """Fields required to add a new KOL."""
    name: str
    country: str = "MY"
    category: str = "beauty"
    followers: int
    engagement_rate: float
    fit_score: float = 0.75
    commission_rate: float = 0.15
    cost: float = 0.0
    avg_views: Optional[int] = None
    avg_likes: Optional[int] = None
    gender_ratio: Optional[float] = None
    age_group: Optional[str] = None
    tiktok_url: Optional[str] = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v):
        if v not in VALID_COUNTRIES:
            raise ValueError(f"country must be one of: {', '.join(VALID_COUNTRIES)}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        v = v.lower()
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(VALID_CATEGORIES)}")
        return v

    @field_validator("followers")
    @classmethod
    def validate_followers(cls, v):
        if v < 0:
            raise ValueError("followers must be non-negative")
        return v

    @field_validator("cost")
    @classmethod
    def validate_cost(cls, v):
        if v < 0:
            raise ValueError("cost must be non-negative")
        return v

    @field_validator("engagement_rate")
    @classmethod
    def validate_engagement(cls, v):
        if not (0 <= v <= 1):
            raise ValueError("engagement_rate must be between 0 and 1")
        return round(v, 4)

    @field_validator("fit_score")
    @classmethod
    def validate_fit(cls, v):
        if not (0 <= v <= 1):
            raise ValueError("fit_score must be between 0 and 1")
        return round(v, 4)


class KOLUpdate(BaseModel):
    """All fields optional for partial update."""
    name: Optional[str] = None
    country: Optional[str] = None
    category: Optional[str] = None
    followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    fit_score: Optional[float] = None
    commission_rate: Optional[float] = None
    cost: Optional[float] = None
    avg_views: Optional[int] = None
    avg_likes: Optional[int] = None
    gender_ratio: Optional[float] = None
    age_group: Optional[str] = None
    tiktok_url: Optional[str] = None


# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════
def _load() -> List[dict]:
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(data: List[dict]):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(data: List[dict]) -> int:
    if not data:
        return 1
    return max(d["id"] for d in data) + 1


def _auto_fill(d: dict) -> dict:
    """Fill computed fields if not provided."""
    if d.get("avg_views") is None:
        d["avg_views"] = int(d["followers"] * 0.3)
    if d.get("avg_likes") is None:
        d["avg_likes"] = int(d["avg_views"] * d["engagement_rate"])
    if d.get("gender_ratio") is None:
        d["gender_ratio"] = 0.5
    if d.get("age_group") is None:
        d["age_group"] = "18-24"
    return d


# ════════════════════════════════════════════════════════════════
#  Endpoints
# ════════════════════════════════════════════════════════════════
@router.post("/kols/add")
def add_kol(kol: KOLCreate):
    """Add a single KOL to the database."""
    data = _load()
    new_id = _next_id(data)

    record = {"id": new_id, **kol.model_dump()}
    record = _auto_fill(record)
    data.append(record)
    _save(data)

    return {"message": f"KOL '{kol.name}' added with id {new_id}", "id": new_id, "kol": record}


@router.put("/kols/{kol_id}")
def update_kol(kol_id: int, updates: KOLUpdate):
    """Update an existing KOL. Snapshots current metrics before applying changes."""
    data = _load()
    idx = next((i for i, d in enumerate(data) if d["id"] == kol_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"KOL with id {kol_id} not found")

    changes = updates.model_dump(exclude_none=True)
    if "country" in changes and changes["country"] not in VALID_COUNTRIES:
        raise HTTPException(status_code=422, detail=f"country must be one of: {', '.join(VALID_COUNTRIES)}")
    if "category" in changes:
        changes["category"] = changes["category"].lower()
        if changes["category"] not in VALID_CATEGORIES:
            raise HTTPException(status_code=422, detail=f"category must be one of: {', '.join(VALID_CATEGORIES)}")

    # Auto-snapshot BEFORE applying changes (track history)
    _record_snapshot(data[idx])

    data[idx].update(changes)
    _save(data)

    return {"message": f"KOL {kol_id} updated", "kol": data[idx]}


@router.get("/kols/{kol_id}/history")
def get_kol_history(kol_id: int):
    """Return all metric snapshots for a KOL, newest first."""
    data = _load()
    if not any(d["id"] == kol_id for d in data):
        raise HTTPException(status_code=404, detail=f"KOL with id {kol_id} not found")

    history = _load_history()
    entry = next((h for h in history if h["kol_id"] == kol_id), None)
    snapshots = list(reversed(entry["snapshots"])) if entry else []
    return {"kol_id": kol_id, "snapshots": snapshots, "count": len(snapshots)}


@router.post("/kols/{kol_id}/simulate-update")
def simulate_kol_update(kol_id: int):
    """
    Simulate a TikTok API metric refresh: apply realistic random drift to
    engagement_rate, fit_score, followers, and record a new snapshot.
    Useful for demos and testing trend visualisation without a real API.
    """
    data = _load()
    idx = next((i for i, d in enumerate(data) if d["id"] == kol_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail=f"KOL with id {kol_id} not found")

    kol = data[idx]
    rng = random.Random()   # fresh RNG each call → different values

    def drift(val: float, lo: float, hi: float, min_v: float, max_v: float) -> float:
        """Apply multiplicative drift within [min_v, max_v]."""
        factor = 1 + rng.uniform(lo, hi)
        return round(max(min_v, min(max_v, val * factor)), 4)

    old_eng = kol.get("engagement_rate", 0.08)
    old_fit = kol.get("fit_score", 0.75)
    old_fol = kol.get("followers", 100000)

    # Snapshot BEFORE applying drift (consistent with update_kol behavior)
    _record_snapshot(dict(kol))

    kol["engagement_rate"] = drift(old_eng, -0.08, +0.12, 0.01, 0.50)
    kol["fit_score"]        = drift(old_fit, -0.05, +0.08, 0.10, 1.00)
    kol["followers"]        = int(drift(old_fol, -0.02, +0.06, 1000, 50_000_000))
    kol["avg_views"]        = int(kol["followers"] * rng.uniform(0.20, 0.40))
    kol["avg_likes"]        = int(kol["avg_views"] * kol["engagement_rate"])

    _save(data)

    return {
        "message": "Simulated metric refresh applied",
        "kol_id": kol_id,
        "changes": {
            "engagement_rate": {"before": old_eng, "after": kol["engagement_rate"]},
            "fit_score":        {"before": old_fit, "after": kol["fit_score"]},
            "followers":        {"before": old_fol, "after": kol["followers"]},
        },
    }


@router.delete("/kols/{kol_id}")
def delete_kol(kol_id: int):
    """Delete a KOL from the database."""
    data = _load()
    before = len(data)
    data = [d for d in data if d["id"] != kol_id]
    if len(data) == before:
        raise HTTPException(status_code=404, detail=f"KOL with id {kol_id} not found")
    _save(data)
    return {"message": f"KOL {kol_id} deleted", "remaining": len(data)}


@router.post("/kols/import-csv")
async def import_csv(file: UploadFile = File(...)):
    """
    Bulk import KOLs from a CSV file.

    Required columns: name, country, category, followers, engagement_rate, cost
    Optional columns: fit_score, avg_views, avg_likes, gender_ratio, age_group, tiktok_url
    """
    if not file.filename.endswith((".csv", ".CSV")):
        raise HTTPException(status_code=422, detail="File must be a .csv file")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM from Excel
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))

    required = {"name", "country", "category", "followers", "engagement_rate", "cost"}
    if not required.issubset(set(reader.fieldnames or [])):
        missing = required - set(reader.fieldnames or [])
        raise HTTPException(
            status_code=422,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}",
        )

    data = _load()
    added = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            record = {
                "id":              _next_id(data),
                "name":            row["name"].strip(),
                "country":         row["country"].strip().upper(),
                "category":        row["category"].strip().lower(),
                "followers":       int(row["followers"]),
                "engagement_rate": round(float(row["engagement_rate"]), 4),
                "fit_score":       round(float(row.get("fit_score") or 0.75), 4),
                "commission_rate": round(float(row.get("commission_rate") or 0.15), 4),
                "cost":            round(float(row["cost"]), 2),
                "avg_views":       int(row["avg_views"]) if row.get("avg_views") else None,
                "avg_likes":       int(row["avg_likes"]) if row.get("avg_likes") else None,
                "gender_ratio":    round(float(row["gender_ratio"]), 2) if row.get("gender_ratio") else None,
                "age_group":       row.get("age_group", "").strip() or None,
                "tiktok_url":      row.get("tiktok_url", "").strip() or None,
            }
            if record["country"] not in VALID_COUNTRIES:
                errors.append(f"Row {row_num}: invalid country '{record['country']}'")
                continue
            if record["category"] not in VALID_CATEGORIES:
                errors.append(f"Row {row_num}: invalid category '{record['category']}'")
                continue

            record = _auto_fill(record)
            data.append(record)
            added += 1
        except (ValueError, KeyError) as e:
            errors.append(f"Row {row_num}: {str(e)}")

    _save(data)

    return {
        "message": f"Imported {added} KOLs",
        "added": added,
        "errors": errors,
        "total": len(data),
    }


@router.get("/kols/template")
def download_template():
    """Return a CSV template with headers and one example row."""
    from fastapi.responses import StreamingResponse

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_TEMPLATE_HEADER)
    writer.writerow([
        "Lisa Beauty", "MY", "beauty", 250000,
        0.08, 0.85, 0.15, 1200,
        75000, 6000, 0.78, "18-24",
        "https://tiktok.com/@lisa_beauty",
    ])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kol_template.csv"},
    )


@router.get("/kols/export")
def export_csv():
    """Export all KOLs as a downloadable CSV file."""
    from fastapi.responses import StreamingResponse

    data = _load()
    output = io.StringIO()
    if data:
        all_keys = []
        seen = set()
        for d in data:
            for k in d.keys():
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)
        writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            writer.writerow({k: row.get(k, "") for k in all_keys})
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kol_export.csv"},
    )


@router.post("/kols/reset")
def reset_database():
    """
    Clear ALL KOL data from the database.

    Used when a merchant wants to start fresh with only their own
    manually entered creators, discarding all synthetic/seed data.
    This action is irreversible.
    """
    _save([])
    return {"message": "Database cleared successfully", "total": 0}