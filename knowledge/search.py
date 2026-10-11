"""
CONCEPT SEARCH - finds the written explanation that answers a question.

WHAT THIS IS FOR
    Isaa uses it to answer "what is an expense ratio?" - questions with no
    single correct number, where the answer is prose we wrote ourselves.

WHAT THIS IS NOT FOR
    Numbers. NAV, returns, expense ratio values and Meter percentages all come
    from database tools, never from here. A document can be out of date and a
    model can misread it; the database cannot. See PRD section 7.1.

    That is why every result carries only a title and text, and no financial
    fields at all - the boundary is built into the shape of the answer. Rule
    HS-6: hybrid search changed how documents are FOUND, never what a document
    is allowed to contain.

NOW: HYBRID (R2 Phase A)
    Two searches run over the same documents and their rankings are merged.

        question ──┬── keyword  (ts_rank, Postgres full text)
                   └── vector   (cosine distance, pgvector)
                              │
                       Reciprocal Rank Fusion
                              │
                          top 3 → Isaa

    Keyword search was measured first, alone: recall@5 = 64.0%. Every failure
    was a question sharing no words with its answer - "how much did it fall at
    its worst" against the drawdown document. Those return NOTHING, not a wrong
    answer, so no amount of prompt work could have recovered them.

WHY BOTH HALVES STAY (rule HS-4)
    Vectors are worse at exact strings. "ELSS", "Rule 138", a scheme code -
    these are tokens to match, not meanings to approximate. Dropping the
    keyword half to "upgrade" to vectors would lose the cases it never failed.

WHY RRF AND NOT A WEIGHTED AVERAGE (HLD section 2.3)
    ts_rank and cosine similarity are not comparable numbers. ts_rank has no
    fixed range and depends on document length; cosine similarity sits in a
    narrow band near the top. Averaging them raw is arithmetic on two different
    units.

    RRF throws the scores away and uses POSITION only. It needs no calibration,
    survives one list being empty - which is precisely the 36% case - and has
    one number to tune.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from constants import (CANDIDATE_MULTIPLIER, MIN_CANDIDATES,
                       MIN_SEMANTIC_SIMILARITY, RRF_K, RRF_WEIGHTS)
from db.connection import connect
from knowledge.fusion import rrf_scores

COLLECTION = "concepts"
DEFAULT_LIMIT = 3


@dataclass(frozen=True)
class Passage:
    slug: str
    title: str
    content: str
    score: float


def _candidates(limit: int) -> int:
    """How deep each half searches before fusion.

    A document ranked 8th by keywords and 2nd by vectors should be able to win.
    If each list were cut to 3 first, it could never be seen - the fusion would
    be merging two already-made decisions instead of making one."""
    return max(MIN_CANDIDATES, limit * CANDIDATE_MULTIPLIER)


# ------------------------------------------------------------ the two halves

def search_lexical(query: str, limit: int = DEFAULT_LIMIT,
                   collection: str = COLLECTION) -> list[Passage]:
    """Postgres full text, title weighted above body (see migration 002).

    Returns nothing when nothing matches, which is the honest answer and is
    what makes rule HS-7 easy on this half."""
    if not query or not query.strip():
        return []

    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT slug, title, content,
                   ts_rank(search_vector, websearch_to_tsquery('english', %s)) AS score
            FROM documents
            WHERE collection = %s
              AND search_vector @@ websearch_to_tsquery('english', %s)
            ORDER BY score DESC
            LIMIT %s
        """, (query, collection, query, limit))
        rows = cur.fetchall()

    return [Passage(slug=r[0], title=r[1], content=r[2], score=float(r[3]))
            for r in rows]


def search_semantic(query: str, limit: int = DEFAULT_LIMIT,
                    collection: str = COLLECTION,
                    floor: float = MIN_SEMANTIC_SIMILARITY) -> list[Passage]:
    """Nearest neighbours by cosine distance, then everything too far away is
    dropped (rule HS-7).

    The floor is not optional. <=> always returns the nearest rows that exist,
    so without it a question about cricket comes back with the three
    least-unrelated finance documents and Isaa answers from them.

    Raises EmbeddingUnavailable if there is no key - the caller decides."""
    if not query or not query.strip():
        return []

    from knowledge.embed import embed_one, to_pgvector
    vector = to_pgvector(embed_one(query))

    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT slug, title, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM documents
            WHERE collection = %s
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (vector, collection, vector, limit))
        rows = cur.fetchall()

    return [Passage(slug=r[0], title=r[1], content=r[2], score=float(r[3]))
            for r in rows if float(r[3]) >= floor]


# ------------------------------------------------------------------ fusion

def search_hybrid(query: str, limit: int = DEFAULT_LIMIT,
                  collection: str = COLLECTION, k: int = RRF_K,
                  weights: dict[str, float] | None = None) -> list[Passage]:
    """Both halves, fused. Falls back to keywords alone if embeddings are not
    available - a missing key costs quality, never uptime."""
    from knowledge.embed import EmbeddingUnavailable

    depth = _candidates(limit)
    lexical = search_lexical(query, depth, collection)

    try:
        semantic = search_semantic(query, depth, collection)
    except EmbeddingUnavailable as exc:
        print(f"  [semantic search unavailable, keywords only: {exc}]")
        semantic = []

    if not lexical and not semantic:
        return []                                   # rule HS-7

    by_slug = {p.slug: p for p in semantic}
    by_slug.update({p.slug: p for p in lexical})    # identical text either way

    scores = rrf_scores(
        {"lexical": [p.slug for p in lexical],
         "semantic": [p.slug for p in semantic]},
        k=k, weights=weights)

    # Ties broken by slug so the order is the same on every run. An eval that
    # moves between runs cannot tell you whether a change helped.
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return [replace(by_slug[slug], score=score) for slug, score in ordered[:limit]]


# ------------------------------------------------------------- public entry

def search_concepts(query: str, limit: int = DEFAULT_LIMIT,
                    collection: str = COLLECTION) -> list[Passage]:
    """What Isaa calls. Hybrid since R2 Phase A.

    The signature is unchanged from R1 on purpose: isaa/tools.py did not have
    to be touched, which is the test of whether this stayed behind its
    boundary."""
    return search_hybrid(query, limit, collection)
