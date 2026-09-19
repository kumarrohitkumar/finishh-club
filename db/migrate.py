"""
MIGRATION RUNNER - applies .sql files to the database, in order, once each.

WHAT IT DOES
    Finds numbered .sql files in db/migrations, works out which have not been
    applied yet, and runs them inside a transaction.

WHY NOT ALEMBIC
    Alembic is a large dependency built for auto-generating migrations from an
    ORM. We write plain SQL and have a handful of files. This is about 60 lines
    and has no hidden behaviour.

HOW IT TRACKS WHAT IS DONE
    A schema_migrations table holding one row per applied version. On a fresh
    database that table is empty, so everything runs.

ORDERING
    Files sort by NUMBER, not by text. Sorting as text would put 010 before 009.

    Run:  python -m db.migrate
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
FILENAME_RE = re.compile(r"^(\d+)_(.+)\.sql$")

TRACKING_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INT PRIMARY KEY,
    name        TEXT NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    sql: str


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Every correctly named .sql file, ordered by version number."""
    directory = Path(directory)
    if not directory.is_dir():
        return []

    found: list[Migration] = []
    for path in directory.iterdir():
        match = FILENAME_RE.match(path.name)
        if not match:
            continue
        found.append(Migration(
            version=int(match.group(1)),
            name=match.group(2),
            path=path,
            sql=path.read_text(),
        ))
    return sorted(found, key=lambda m: m.version)


def pending(migrations: list[Migration], applied: set[int]) -> list[Migration]:
    """Those not yet recorded in schema_migrations."""
    return [m for m in migrations if m.version not in applied]


def applied_versions(conn) -> set[int]:
    with conn.cursor() as cur:
        cur.execute(TRACKING_TABLE_SQL)
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def apply(conn, migration: Migration) -> None:
    """Run one migration and record it, in a single transaction."""
    with conn.cursor() as cur:
        cur.execute(migration.sql)
        cur.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
            (migration.version, migration.name),
        )
    conn.commit()


def run() -> int:
    from db.connection import connect

    with connect() as conn:
        todo = pending(discover(), applied_versions(conn))
        if not todo:
            print("Database is up to date.")
            return 0
        for migration in todo:
            print(f"  applying {migration.version:03d}_{migration.name} ...", end="", flush=True)
            try:
                apply(conn, migration)
                print(" ok")
            except Exception as exc:
                conn.rollback()
                print(f" FAILED\n    {type(exc).__name__}: {exc}")
                return 1
        print(f"Applied {len(todo)} migration(s).")
    return 0


if __name__ == "__main__":
    sys.exit(run())
