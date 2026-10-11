"""
KNOWLEDGE PIPELINE - loads the concept documents into the database and embeds
the ones that changed.

WHAT IT DOES
    Reads every .md file in knowledge/concepts, takes the first heading as the
    title and the rest as the content, stores it, and gives it a vector.

    python -m knowledge.pipeline
    python -m knowledge.pipeline --reembed    # force, after a model change

WHY THE FILES ARE THE SOURCE OF TRUTH
    The documents live as markdown in the repo, not as rows typed into a
    database. They can be reviewed in a diff, corrected in an editor, and
    reloaded at any time. Re-running replaces by slug, so nothing duplicates.

EMBEDDING ONLY WHAT CHANGED (rule HS-2)
    Every row carries a hash of the text that was embedded. On reload:

        hash matches    -> leave the vector alone, no API call
        hash differs    -> re-embed, because the meaning moved
        hash is NULL    -> never embedded, embed it

    With 32 short documents this saves a few paise. The reason it is built now
    is Phase B: one DRHP is roughly 2,000 chunks, and re-embedding all of them
    every time one page is corrected is money and minutes for nothing.

    The hash covers title AND content, because both go into the vector.

WITHOUT A KEY
    The load still works and the vectors stay NULL. Search then runs on
    keywords alone, exactly as it did in R1. Loading documents must not require
    an API key - that would make the whole knowledge base hostage to a secret.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from db.connection import connect
from knowledge.embed import EmbeddingUnavailable, available, embed, to_pgvector

CONCEPTS_DIR = Path(__file__).resolve().parent / "concepts"
COLLECTION = "concepts"


def read_document(path: Path) -> tuple[str, str, str]:
    """Returns (slug, title, content). The first '# ' line is the title."""
    lines = path.read_text().splitlines()
    title, body_start = path.stem.replace("-", " ").title(), 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title, body_start = line[2:].strip(), i + 1
            break
    content = "\n".join(lines[body_start:]).strip()
    return path.stem, title, content


def content_hash(title: str, content: str) -> str:
    """Identifies the exact text that was embedded.

    Title and content are joined with a separator that cannot appear in either,
    so that moving a line between them changes the hash. Without it, a title
    ending where a body begins could hash the same two different ways."""
    return hashlib.sha256(f"{title}\x00{content}".encode()).hexdigest()


def embed_text(title: str, content: str) -> str:
    """What actually gets embedded.

    The title is included because a question is usually closer to the title
    than to any sentence in the body - "what is NAV" against a document headed
    "NAV". Embedding the body alone throws that signal away."""
    return f"{title}\n\n{content}"


def load(directory: Path = CONCEPTS_DIR, reembed: bool = False) -> int:
    files = sorted(directory.glob("*.md"))
    if not files:
        print(f"No .md files in {directory}")
        return 1

    with connect() as conn, conn.cursor() as cur:
        pending: list[tuple[int, str, str]] = []     # id, title, content

        for path in files:
            slug, title, content = read_document(path)
            # The update deliberately does NOT touch content_hash, so RETURNING
            # hands back the hash of the text we embedded LAST time. That is
            # the value to compare against.
            cur.execute("""
                INSERT INTO documents (collection, slug, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (collection, slug) DO UPDATE
                   SET title = EXCLUDED.title, content = EXCLUDED.content
                RETURNING id, content_hash
            """, (COLLECTION, slug, title, content, '{"source": "in-house"}'))
            doc_id, stored_hash = cur.fetchone()

            if reembed or stored_hash != content_hash(title, content):
                pending.append((doc_id, title, content))

        conn.commit()
        print(f"Loaded {len(files)} files. {len(pending)} need embedding.")

        if pending and not available():
            print("  no OPENAI_API_KEY - vectors left empty, search stays on "
                  "keywords only")
        elif pending:
            try:
                vectors = embed([embed_text(t, c) for _, t, c in pending])
            except EmbeddingUnavailable as exc:
                print(f"  embedding FAILED: {exc}")
                print("  documents are stored; run again once it is fixed")
                return 1

            for (doc_id, title, content), vector in zip(pending, vectors):
                cur.execute("""
                    UPDATE documents
                       SET embedding = %s::vector,
                           content_hash = %s,
                           embedded_at = now()
                     WHERE id = %s
                """, (to_pgvector(vector), content_hash(title, content), doc_id))
            conn.commit()
            print(f"  embedded {len(vectors)}")

        cur.execute("""SELECT count(*), count(embedding)
                       FROM documents WHERE collection = %s""", (COLLECTION,))
        total, embedded = cur.fetchone()

    print(f"\n  {total} documents in '{COLLECTION}', {embedded} with vectors")
    return 0


if __name__ == "__main__":
    sys.exit(load(reembed="--reembed" in sys.argv))
