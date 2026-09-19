"""
CONCEPT SEARCH - finds the written explanation that answers a question.

WHAT THIS IS FOR
    Isaa uses it to answer "what is an expense ratio?" - questions with no
    single correct number, where the answer is prose we wrote ourselves.

WHAT THIS IS NOT FOR
    Numbers. NAV, returns, expense ratio values and Meter percentages all come
    from database tools, never from here. A document can be out of date and a
    model can misread it; the database cannot. See PRD section 7.1.

    That is why every result carries only a title and text, and no numeric
    fields at all - the boundary is built into the shape of the answer.

TODAY: KEYWORD SEARCH
    Postgres full-text search, with the title weighted above the body. No model,
    no API key, no download.

LATER: HYBRID
    Vector search will be added next to this, and the two combined. Keeping
    keyword search first means we can measure the improvement (rule E-4) rather
    than assume it.
"""
from __future__ import annotations

from dataclasses import dataclass

from db.connection import connect

COLLECTION = "concepts"
DEFAULT_LIMIT = 3


@dataclass(frozen=True)
class Passage:
    slug: str
    title: str
    content: str
    score: float


def search_concepts(query: str, limit: int = DEFAULT_LIMIT,
                    collection: str = COLLECTION) -> list[Passage]:
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
