"""
Campaign Attribution — save optimization predictions, record actual GMV, compare.

Endpoints
---------
  POST   /campaigns                   Save a new campaign from optimization results
  GET    /campaigns                   List all campaigns (newest first)
  GET    /campaigns/{id}              Get single campaign detail
  PUT    /campaigns/{id}/actual       Record actual GMV after campaign ends
  DELETE /campaigns/{id}              Delete a campaign
"""
import json
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend import tenancy
from backend.auth import require_tenant

router = APIRouter()

# Campaign storage is resolved per-tenant at call time (backend/tenancy.py).


# ════════════════════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════════════════════
def _load() -> List[dict]:
    path = tenancy.campaigns_path()
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(data: List[dict]):
    with open(tenancy.campaigns_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _next_id(data: List[dict]) -> int:
    return max((d["id"] for d in data), default=0) + 1


# ════════════════════════════════════════════════════════════════
#  Pydantic models
# ════════════════════════════════════════════════════════════════
class KOLPrediction(BaseModel):
    id: int
    name: str
    country: str
    category: str
    followers: int
    cost: float
    predicted_gmv: float
    tier: str = ""


class CampaignCreate(BaseModel):
    name: str
    countries: List[str] = []
    category: str
    budget: float
    best_algorithm: str
    selected_kols: List[KOLPrediction]
    total_cost: float
    predicted_gmv: float


class KOLActual(BaseModel):
    id: int
    actual_gmv: float


class ActualResultsUpdate(BaseModel):
    actual_total_gmv: float
    kol_actuals: Optional[List[KOLActual]] = None   # per-KOL breakdown (optional)
    notes: Optional[str] = None


# ════════════════════════════════════════════════════════════════
#  Endpoints
# ════════════════════════════════════════════════════════════════
@router.post("/campaigns")
def save_campaign(req: CampaignCreate, _t: str = Depends(require_tenant)):
    """Persist an optimization result as a trackable campaign."""
    data = _load()
    campaign = {
        "id":             _next_id(data),
        "name":           req.name,
        "created_at":     datetime.utcnow().isoformat(),
        "countries":      req.countries,
        "category":       req.category,
        "budget":         req.budget,
        "best_algorithm": req.best_algorithm,
        "selected_kols":  [k.model_dump() for k in req.selected_kols],
        "total_cost":     req.total_cost,
        "predicted_gmv":  req.predicted_gmv,
        # filled after campaign ends:
        "actual_total_gmv": None,
        "kol_actuals":      None,
        "accuracy_pct":     None,
        "notes":            None,
        "completed_at":     None,
        "status":           "active",   # active | completed
    }
    data.append(campaign)
    _save(data)
    return campaign


@router.get("/campaigns")
def list_campaigns(_t: str = Depends(require_tenant)):
    """Return all campaigns sorted newest-first."""
    data = _load()
    data.sort(key=lambda d: d["created_at"], reverse=True)
    return data


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: int, _t: str = Depends(require_tenant)):
    data = _load()
    c = next((d for d in data if d["id"] == campaign_id), None)
    if not c:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return c


@router.put("/campaigns/{campaign_id}/actual")
def record_actual(campaign_id: int, req: ActualResultsUpdate, _t: str = Depends(require_tenant)):
    """
    Record actual GMV after the campaign finishes.
    Computes accuracy_pct = actual / predicted × 100.
    """
    data = _load()
    idx = next((i for i, d in enumerate(data) if d["id"] == campaign_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    c = data[idx]
    c["actual_total_gmv"] = req.actual_total_gmv
    if req.kol_actuals:
        c["kol_actuals"] = [k.model_dump() for k in req.kol_actuals]
    if req.notes:
        c["notes"] = req.notes
    if c["predicted_gmv"] > 0:
        c["accuracy_pct"] = round(req.actual_total_gmv / c["predicted_gmv"] * 100, 1)
    c["status"] = "completed"
    c["completed_at"] = datetime.utcnow().isoformat()

    _save(data)
    return c


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int, _t: str = Depends(require_tenant)):
    data = _load()
    before = len(data)
    data = [d for d in data if d["id"] != campaign_id]
    if len(data) == before:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    _save(data)
    return {"deleted": True, "id": campaign_id}
