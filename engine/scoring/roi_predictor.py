# engine/scoring/roi_predictor.py
"""
ROI Predictor — estimates return-on-investment for a KOL portfolio.

Predicted GMV per KOL = KOL.expected_gmv()  (the funnel model defined in
                        engine/models.py: sqrt(followers) × CTR × CVR × AOV
                        × purchasing_power × engagement_factor × fit_factor)
Portfolio ROI         = total_predicted_gmv / total_cost

These are the same metrics used by the fitness function; this module
exposes them as clean helper functions for the backend and frontend.
"""
from typing import List

from engine.models import KOL


def predict_roi(kols: List[KOL], selected_indices: List[int]) -> dict:
    """
    Predict ROI for a selected subset of KOLs.

    Args:
        kols:             Full KOL pool.
        selected_indices: Indices (into kols) of the selected KOLs.

    Returns:
        Dict with keys:
            selected_count  int
            total_cost      float  (USD)
            total_gmv       float  (predicted USD)
            roi             float  (total_gmv / total_cost, 0 if no cost)
    """
    selected = [kols[i] for i in selected_indices]
    total_cost = sum(k.cost for k in selected)
    total_gmv  = sum(k.expected_gmv() for k in selected)
    roi = round(total_gmv / total_cost, 4) if total_cost > 0 else 0.0

    return {
        "selected_count": len(selected),
        "total_cost":     round(total_cost, 2),
        "total_gmv":      round(total_gmv, 2),
        "roi":            roi,
    }


def predict_roi_from_state(kols: List[KOL], state: List[int]) -> dict:
    """
    Convenience wrapper — accepts a binary state vector instead of indices.

    Args:
        kols:  Full KOL pool.
        state: Binary list, 1 = selected.
    """
    selected_indices = [i for i, x in enumerate(state) if x == 1]
    return predict_roi(kols, selected_indices)