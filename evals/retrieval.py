"""
RETRIEVAL EVAL - scores concept search. Rule E-4.

    python -m evals.retrieval

WHAT IT MEASURES
    recall@k  - how often the correct document appears in the top k results.
                If the right document never reaches the prompt, Isaa cannot
                possibly give the right answer. This number caps everything.

    MRR       - how HIGH the correct document ranked. Finding it at position 1
                is better than position 5, and recall@5 cannot tell them apart.

WHY BOTH MATTER
    Retrieval quality and answer quality are separate failures. If recall is
    61%, no prompt change will fix the other 39% - the model never saw the
    answer. Measuring them separately is what tells you which one to work on.
"""
from __future__ import annotations

import sys

from evals.retrieval_cases import CASES
from knowledge.search import search_concepts

K = 5
TARGET_RECALL = 0.85          # rule E-4


def evaluate(k: int = K, verbose: bool = True) -> dict:
    hits = 0
    reciprocal_total = 0.0
    misses = []

    for case in CASES:
        results = search_concepts(case["q"], limit=k)
        slugs = [r.slug for r in results]
        if case["doc"] in slugs:
            hits += 1
            reciprocal_total += 1.0 / (slugs.index(case["doc"]) + 1)
        else:
            misses.append((case["q"], case["doc"], slugs[:3]))

    total = len(CASES)
    recall = hits / total
    mrr = reciprocal_total / total

    if verbose:
        print(f"Concept retrieval - keyword search (Postgres full text)\n")
        print(f"  cases        {total}")
        print(f"  recall@{k}     {recall:.1%}   (target {TARGET_RECALL:.0%})")
        print(f"  MRR          {mrr:.3f}")
        if misses:
            print(f"\n  missed {len(misses)}:")
            for q, want, got in misses:
                print(f"    {q!r}")
                print(f"        wanted {want!r}, got {got or 'nothing'}")
        print(f"\n  {'PASS' if recall >= TARGET_RECALL else 'BELOW TARGET'}"
              f" - this is the baseline to beat with vector search")

    return {"recall": recall, "mrr": mrr, "hits": hits, "total": total}


if __name__ == "__main__":
    sys.exit(0 if evaluate()["recall"] >= TARGET_RECALL else 1)
