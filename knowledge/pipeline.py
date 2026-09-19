"""
KNOWLEDGE PIPELINE - loads the concept documents into the database.

WHAT IT DOES
    Reads every .md file in knowledge/concepts, takes the first heading as the
    title and the rest as the content, and stores it in the documents table.

    python -m knowledge.pipeline

WHY THE FILES ARE THE SOURCE OF TRUTH
    The documents live as markdown in the repo, not as rows typed into a
    database. They can be reviewed in a diff, corrected in an editor, and
    reloaded at any time. Re-running replaces by slug, so nothing duplicates.

NO EMBEDDINGS YET
    The embedding column stays empty for now. Search runs on Postgres full-text
    search first, which gives a baseline to measure vector search against later.
    Adding embeddings without a baseline means never knowing if they helped.
"""
from __future__ import annotations

import sys
from pathlib import Path

from db.connection import connect

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


def load(directory: Path = CONCEPTS_DIR) -> int:
    files = sorted(directory.glob("*.md"))
    if not files:
        print(f"No .md files in {directory}")
        return 1

    with connect() as conn, conn.cursor() as cur:
        for path in files:
            slug, title, content = read_document(path)
            cur.execute("""
                INSERT INTO documents (collection, slug, title, content, metadata)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (collection, slug) DO UPDATE
                   SET title = EXCLUDED.title, content = EXCLUDED.content
            """, (COLLECTION, slug, title, content, '{"source": "in-house"}'))
        conn.commit()
        cur.execute("SELECT count(*) FROM documents WHERE collection = %s", (COLLECTION,))
        total = cur.fetchone()[0]

    print(f"Loaded {len(files)} files. {total} documents in '{COLLECTION}'.")
    return 0


if __name__ == "__main__":
    sys.exit(load())
