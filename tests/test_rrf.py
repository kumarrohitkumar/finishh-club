"""
TESTS FOR RECIPROCAL RANK FUSION - how the two searches are merged.

WHY THIS IS TESTED ON ITS OWN
    rrf_scores() takes lists of strings and returns a dict. No database, no
    embedding key, no network - the same reason meter/engine.py is isolated.
    It runs in milliseconds and can be run by anyone who has cloned the repo.

    The eval (python -m evals.retrieval) measures whether fusion RETRIEVES
    better. These tests check that the arithmetic is what we think it is. Both
    are needed: a recall number cannot tell you that the weights were applied
    to the wrong list.

THE ONE THAT MATTERS MOST
    test_4. A document found by only ONE search must still survive. That is
    the entire reason hybrid search was built - 36% of real questions return
    nothing from keyword search, and fusion is only useful if the vector half
    can carry those alone.

    Run:  python tests/test_rrf.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import RRF_K
from knowledge.fusion import rrf_scores


def ranked(**lists):
    return rrf_scores(lists)


def test_1_formula_is_one_over_k_plus_rank():
    # One list, one document, rank 1. Nothing to fuse - just the formula.
    scores = ranked(lexical=["nav"])
    assert abs(scores["nav"] - 1.0 / (RRF_K + 1)) < 1e-12, scores


def test_2_rank_decides_order_not_raw_score():
    # The input carries no scores at all. Position is the only signal.
    scores = ranked(lexical=["a", "b", "c"])
    assert scores["a"] > scores["b"] > scores["c"]


def test_3_agreement_beats_a_single_first_place():
    # 'both' is 2nd in each list; 'one' is 1st in a single list.
    # Two mid-table votes must outweigh one top vote - that is what makes
    # fusion more than "trust whichever search is louder".
    scores = ranked(lexical=["one", "both"], semantic=["other", "both"])
    assert scores["both"] > scores["one"], scores
    assert 2.0 / (RRF_K + 2) == scores["both"]


def test_4_a_document_only_one_search_found_survives():
    # THE case hybrid search exists for: keyword search returned nothing,
    # the vector half found the answer. It must still come out on top.
    scores = rrf_scores({"lexical": [], "semantic": ["drawdown", "nav"]})
    order = sorted(scores, key=lambda s: -scores[s])
    assert order[0] == "drawdown", order
    assert "drawdown" in scores and scores["drawdown"] > 0


def test_5_empty_everywhere_is_empty():
    # Rule HS-7 depends on this: no candidates means no answer, so Isaa says
    # it does not know rather than being handed the least-bad document.
    assert rrf_scores({"lexical": [], "semantic": []}) == {}
    assert rrf_scores({}) == {}


def test_6_weights_can_favour_one_half():
    # Same two lists, weight moved to the semantic side. The winner flips.
    lists = {"lexical": ["keyword-win"], "semantic": ["vector-win"]}
    even = rrf_scores(lists, weights={"lexical": 1.0, "semantic": 1.0})
    assert even["keyword-win"] == even["vector-win"]

    tilted = rrf_scores(lists, weights={"lexical": 0.5, "semantic": 2.0})
    assert tilted["vector-win"] > tilted["keyword-win"], tilted


def test_7_k_controls_how_much_rank_one_matters():
    # Small k: first place is worth far more than second.
    # Large k: the two flatten towards each other. This is the HS-5 dial, and
    # a sweep over it is only meaningful if it actually changes the spread.
    sharp = rrf_scores({"lexical": ["a", "b"]}, k=1)
    flat = rrf_scores({"lexical": ["a", "b"]}, k=1000)
    assert sharp["a"] / sharp["b"] > flat["a"] / flat["b"]


def test_8_missing_weight_defaults_to_one():
    # A new list added to the fusion later must not silently score zero.
    scores = rrf_scores({"lexical": ["a"], "brand-new": ["a"]},
                        weights={"lexical": 1.0})
    assert scores["a"] == 2.0 / (RRF_K + 1), scores


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    passed = 0
    for name, fn in fns:
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
        except Exception as e:
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
