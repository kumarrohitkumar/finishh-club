"""
RECIPROCAL RANK FUSION - how two ranked lists become one.

WHAT IT DOES
    Takes several ranked lists of the same kind of identifier and returns one
    score per identifier:

        score(doc) = sum over lists of  weight / (k + rank)      rank from 1

WHY SCORES ARE THROWN AWAY (HLD section 2.3)
    ts_rank and cosine similarity are not comparable numbers. ts_rank has no
    fixed range and grows with document length; cosine similarity sits in a
    narrow band near the top. Averaging them is arithmetic on two different
    units, and it needs a normalisation step that has to be re-tuned every time
    either side changes.

    POSITION is comparable. "First by keywords" and "first by meaning" mean the
    same thing. RRF uses only that, so it needs no calibration at all.

    It also survives one list being completely empty - which is not an edge
    case here, it is 36% of real questions.

WHY IT IMPORTS NOTHING BUT CONSTANTS
    Same rule as meter/engine.py. No database, no embedding key, no network, so
    it can be tested exhaustively in milliseconds by anyone who cloned the repo
    (tests/test_rrf.py). A fusion bug does not look like a bug - it looks like
    slightly worse search results, which nobody notices.

USED BY
    knowledge/search.py
"""
from __future__ import annotations

from constants import RRF_K, RRF_WEIGHTS


def rrf_scores(ranked_lists: dict[str, list[str]], k: int = RRF_K,
               weights: dict[str, float] | None = None) -> dict[str, float]:
    """Fuse ranked lists of identifiers into one score per identifier.

    Rule HS-5: k and the weights are the tuning, and they are ARGUMENTS rather
    than constants read inside, so the eval can sweep them instead of anyone
    guessing. A list with no weight given counts as 1.0, so adding a third
    search later cannot silently score zero."""
    weights = weights or RRF_WEIGHTS
    scores: dict[str, float] = {}

    for name, ranked in ranked_lists.items():
        weight = weights.get(name, 1.0)
        for rank, key in enumerate(ranked, start=1):
            scores[key] = scores.get(key, 0.0) + weight / (k + rank)

    return scores
