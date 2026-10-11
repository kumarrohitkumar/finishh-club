"""
RETRIEVAL EVAL - scores concept search three ways. Rules E-4 and HS-8.

    python -m evals.retrieval              # print the table
    python -m evals.retrieval --write      # also record it in evals/RESULTS.md

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

WHY THREE RUNS AND NOT ONE (rule HS-8)
    "We added embeddings" is not a result. The same 25 questions are scored on
    keywords alone, vectors alone, and the two fused - so the honest question
    can be answered:

        did the fusion beat BOTH halves, or did it just beat the weaker one?

    If hybrid does not beat semantic on its own, the keyword half is dead
    weight and should be argued for again rather than kept out of habit.

ON RUNNING THIS
    It needs the database and, for two of the three runs, an embedding key.
    Each question is one API call, so a full run is 25 of them - fractions of
    a paisa, but not free, which is why it is a command and not a test.
"""
from __future__ import annotations

import sys
from datetime import date

from evals.retrieval_cases import CASES
from knowledge.embed import EmbeddingUnavailable, available
from knowledge.search import search_hybrid, search_lexical, search_semantic

K = 5
TARGET_RECALL = 0.85          # rule E-4, and the Phase A target in R2_PRD 2.3
RESULTS_PATH = "evals/RESULTS.md"


def evaluate(search_fn, k: int = K) -> dict:
    """Score one search function over the whole case set."""
    hits = 0
    reciprocal_total = 0.0
    misses = []
    empties = 0

    for case in CASES:
        results = search_fn(case["q"], limit=k)
        slugs = [r.slug for r in results]
        if not slugs:
            empties += 1
        if case["doc"] in slugs:
            hits += 1
            reciprocal_total += 1.0 / (slugs.index(case["doc"]) + 1)
        else:
            misses.append((case["q"], case["doc"], slugs[:3]))

    total = len(CASES)
    return {"recall": hits / total, "mrr": reciprocal_total / total,
            "hits": hits, "total": total, "misses": misses,
            "returned_nothing": empties}


def _report(label: str, result: dict, k: int) -> None:
    print(f"\n{label}")
    print(f"  recall@{k}          {result['recall']:.1%}")
    print(f"  MRR               {result['mrr']:.3f}")
    print(f"  returned nothing  {result['returned_nothing']}/{result['total']}")
    if result["misses"]:
        print(f"  missed {len(result['misses'])}:")
        for q, want, got in result["misses"]:
            print(f"    {q!r}")
            print(f"        wanted {want!r}, got {got or 'nothing'}")


def _write_results(rows: dict, k: int) -> None:
    lines = [
        "# Retrieval results",
        "",
        f"Measured {date.today()} on `evals/retrieval_cases.py` "
        f"({len(CASES)} questions). Rule HS-8.",
        "",
        f"Run it yourself: `python -m evals.retrieval`",
        "",
        "| search | recall@%d | MRR | returned nothing |" % k,
        "|---|---|---|---|",
    ]
    for label, r in rows.items():
        if r is None:
            lines.append(f"| {label} | not run | - | - |")
            continue
        lines.append(f"| {label} | {r['recall']:.1%} | {r['mrr']:.3f} | "
                     f"{r['returned_nothing']}/{r['total']} |")
    lines += ["", f"Target: recall@{k} of {TARGET_RECALL:.0%} (rule E-4).", ""]

    with open(RESULTS_PATH, "w") as handle:
        handle.write("\n".join(lines))
    print(f"\nwritten to {RESULTS_PATH}")


def run(k: int = K, write: bool = False) -> int:
    print(f"Concept retrieval - {len(CASES)} questions, k={k}\n"
          f"{'=' * 60}")

    rows: dict[str, dict | None] = {}

    lexical = evaluate(lambda q, limit: search_lexical(q, limit), k)
    rows["lexical (keyword only)"] = lexical
    _report("lexical  - Postgres full text, the R1 baseline", lexical, k)

    if not available():
        print("\nsemantic and hybrid SKIPPED - no OPENAI_API_KEY.")
        print("Put it in .env.local and run again to get the other two numbers.")
        rows["semantic (vectors only)"] = None
        rows["hybrid (RRF)"] = None
        if write:
            _write_results(rows, k)
        return 1

    try:
        semantic = evaluate(lambda q, limit: search_semantic(q, limit), k)
        hybrid = evaluate(lambda q, limit: search_hybrid(q, limit), k)
    except EmbeddingUnavailable as exc:
        print(f"\nsemantic and hybrid FAILED: {exc}")
        return 1

    rows["semantic (vectors only)"] = semantic
    rows["hybrid (RRF)"] = hybrid
    _report("semantic - pgvector cosine, floor applied", semantic, k)
    _report("hybrid   - the two fused by RRF", hybrid, k)

    print(f"\n{'=' * 60}")
    print(f"  lexical   {lexical['recall']:.1%}")
    print(f"  semantic  {semantic['recall']:.1%}")
    print(f"  hybrid    {hybrid['recall']:.1%}   (target {TARGET_RECALL:.0%})")

    best_half = max(lexical["recall"], semantic["recall"])
    if hybrid["recall"] < best_half:
        print("\n  WARNING: fusion is worse than one of its halves alone.")
        print("  Tune RRF_K or the weights, or use the better half directly.")

    if write:
        _write_results(rows, k)

    return 0 if hybrid["recall"] >= TARGET_RECALL else 1


if __name__ == "__main__":
    sys.exit(run(write="--write" in sys.argv))
