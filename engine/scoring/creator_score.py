# engine/scoring/creator_score.py
"""
CreatorScore — composite KOL quality score in range [0, 1].

Formula
-------
CreatorScore = 0.30 × norm_followers
             + 0.30 × engagement_rate
             + 0.20 × fit_score
             + 0.20 × cost_effectiveness

Where:
  norm_followers    = followers / max_followers  (normalised across the pool)
  engagement_rate   = already in [0, 1]
  fit_score         = already in [0, 1]
  cost_effectiveness = norm(expected_gmv / cost)  (normalised across the pool)

All weights sum to 1.0.  The score is used for:
  - /top-kols leaderboard ranking
  - Displaying per-KOL quality in the frontend
  - Generating recommendation reasons
"""
from typing import List

from engine.models import KOL


# Weight constants — must sum to 1.0
W_FOLLOWERS    = 0.30
W_ENGAGEMENT   = 0.30
W_FIT          = 0.20
W_COST_EFF     = 0.20


def _safe_norm(values: List[float]) -> List[float]:
    """Min-max normalise a list to [0, 1].  Returns all-zeros if range is 0."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def compute_creator_score(kols: List[KOL]) -> List[float]:
    """
    Compute CreatorScore for each KOL in the pool.

    Args:
        kols: List of KOL objects (pool to score together).

    Returns:
        List of float scores, same order as input kols.
    """
    if not kols:
        return []

    followers_norm = _safe_norm([float(k.followers) for k in kols])
    engagement     = [k.engagement_rate for k in kols]          # already 0-1
    fit            = [k.fit_score for k in kols]                 # already 0-1

    # cost_effectiveness = expected_gmv / cost  (higher is better)
    raw_ce = [k.expected_gmv() / k.cost if k.cost > 0 else 0.0 for k in kols]
    ce_norm = _safe_norm(raw_ce)

    scores = [
        round(
            W_FOLLOWERS  * followers_norm[i]
            + W_ENGAGEMENT * engagement[i]
            + W_FIT        * fit[i]
            + W_COST_EFF   * ce_norm[i],
            4,
        )
        for i in range(len(kols))
    ]
    return scores


def add_scores_to_kols(kols: List[KOL]) -> List[dict]:
    """
    Return a list of dicts (one per KOL) with a new 'creator_score' key added.
    Used by the backend to enrich API responses without mutating the KOL dataclass.
    """
    scores = compute_creator_score(kols)
    result = []
    for kol, score in zip(kols, scores):
        d = kol.__dict__.copy()
        d["creator_score"] = score
        d["expected_gmv"]  = kol.expected_gmv()
        result.append(d)
    return result