"""
Prediction calibration — closes the loop from actual campaign GMV back into
future GMV predictions.

When a campaign is completed with its real GMV, we fold the actual/predicted
ratio (EWMA + shrinkage) into a per-tenant calibration table: one global factor
plus per-(category, country) segment factors. When presenting a predicted GMV we
multiply by the matching factor, so a model that systematically over- or
under-predicts a segment self-corrects over time.

Stored at data/tenants/{id}/calibration.json. A brand-new tenant has no history,
so every factor defaults to 1.0 (predictions unchanged — zero behaviour change
until real outcomes arrive).
"""
import contextvars
import json
import os

from backend import tenancy

# How fast a new observation moves the factor, how much a thin segment / creator
# is pulled toward its prior, and clamps on absurd single-campaign ratios.
_EWMA_ALPHA = 0.3
_SHRINK_PRIOR = 3       # segment → global
_SHRINK_CREATOR = 2     # creator → segment
_MIN_RATIO, _MAX_RATIO = 0.2, 5.0

# Per-request cache so a single /optimize call doesn't re-read the file per creator.
_CACHE: contextvars.ContextVar = contextvars.ContextVar("cal_cache", default=None)


def _path() -> str:
    return os.path.join(tenancy.tenant_dir(), "calibration.json")


def _default() -> dict:
    return {"global": {"factor": 1.0, "n": 0}, "segments": {}, "creators": {}}


def load() -> dict:
    p = _path()
    if not os.path.exists(p):
        return _default()
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default()


def _cached() -> dict:
    c = _CACHE.get()
    if c is None:
        c = load()
        _CACHE.set(c)
    return c


def _save(data: dict):
    with open(_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _seg_key(category: str, country: str) -> str:
    return f"{category}|{country}"


def _update_ewma(entry: dict, ratio: float) -> dict:
    if entry["n"] == 0:
        entry["factor"] = round(ratio, 4)
    else:
        entry["factor"] = round((1 - _EWMA_ALPHA) * entry["factor"] + _EWMA_ALPHA * ratio, 4)
    entry["n"] += 1
    return entry


def _clamp(r: float) -> float:
    return max(_MIN_RATIO, min(_MAX_RATIO, r))


def record_outcome(category: str, countries, predicted_gmv: float, actual_gmv: float,
                   creator_ratios: dict = None) -> dict:
    """Fold one completed campaign's outcome into the table:
      - L1 global + L2 (category, country) segments from the campaign-level ratio
      - L3 per-creator factors from each creator's own actual/predicted ratio.
    """
    data = load()
    if predicted_gmv and predicted_gmv > 0 and actual_gmv is not None and actual_gmv >= 0:
        ratio = _clamp(actual_gmv / predicted_gmv)
        _update_ewma(data["global"], ratio)
        for c in (countries or []):
            key = _seg_key(category, c)
            data["segments"][key] = _update_ewma(data["segments"].get(key, {"factor": 1.0, "n": 0}), ratio)

    creators = data.setdefault("creators", {})
    for cid, cratio in (creator_ratios or {}).items():
        creators[str(cid)] = _update_ewma(creators.get(str(cid), {"factor": 1.0, "n": 0}), _clamp(cratio))

    _save(data)
    _CACHE.set(data)
    return data


def _segment_factor(data: dict, category: str, country: str) -> float:
    g = data["global"]["factor"] if data["global"]["n"] > 0 else 1.0
    seg = data["segments"].get(_seg_key(category, country))
    if not seg or seg["n"] == 0:
        return g
    w = seg["n"] / (seg["n"] + _SHRINK_PRIOR)
    return w * seg["factor"] + (1 - w) * g


def factor(category: str, country: str, creator_id=None) -> float:
    """Calibration multiplier for a creator: the (category, country) segment factor
    (itself shrunk toward global), further refined by the creator's own track
    record when available. No history anywhere → 1.0."""
    data = _cached()
    seg = _segment_factor(data, category, country)
    if creator_id is not None:
        ce = data.get("creators", {}).get(str(creator_id))
        if ce and ce["n"] > 0:
            w = ce["n"] / (ce["n"] + _SHRINK_CREATOR)
            return round(w * ce["factor"] + (1 - w) * seg, 4)
    return round(seg, 4)


def summary() -> dict:
    """Compact view for the UI."""
    data = load()
    n = data["global"]["n"]
    return {
        "campaigns_used": n,
        "global_factor": round(data["global"]["factor"], 3) if n > 0 else 1.0,
        "creators_tracked": len(data.get("creators", {})),
        "segments": {
            k: {"factor": round(v["factor"], 3), "n": v["n"]}
            for k, v in data["segments"].items()
        },
    }
