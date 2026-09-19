"""
DATABASE CONNECTION - one place that knows how to reach Postgres.

WHAT IT DOES
    Reads DATABASE_URL from the environment and hands back a connection.

WHY IT IS ITS OWN FILE
    Every other file asks this one for a connection. When we move from Neon to
    somewhere else, only the connection string changes - no code does.

WHERE THE URL COMES FROM
    A .env file, never code. A connection string contains a password, and a
    password in code ends up in git.

        DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require

IF IT IS MISSING
    You get a clear message telling you what to do, not a stack trace from deep
    inside a driver.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

# .env holds defaults you may commit; .env.local holds secrets and wins.
# `neon link` writes DATABASE_URL into .env.local, so that one is loaded last.
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_HERE, ".env"))
load_dotenv(os.path.join(_HERE, ".env.local"), override=True)

SETUP_HELP = """
DATABASE_URL is not set.

  1. Create a free Postgres database at  https://neon.com
  2. Copy the connection string it shows you
  3. Add it to the .env file in this folder:

       DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require

  4. Run again.
"""


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(SETUP_HELP)
    return url


@contextmanager
def connect():
    """A connection that always gets closed, even if something fails."""
    from config import DB_CONNECT_TIMEOUT_SECONDS

    conn = psycopg.connect(database_url(), connect_timeout=DB_CONNECT_TIMEOUT_SECONDS)
    try:
        yield conn
    finally:
        conn.close()


def check() -> None:
    """Prove the database is reachable and has what we need."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT version()")
        print("connected:", cur.fetchone()[0].split(",")[0])

        cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('vector','citext')")
        have = {row[0] for row in cur.fetchall()}
        for ext in ("vector", "citext"):
            print(f"extension {ext}:", "present" if ext in have else "MISSING - migration will add it")

        cur.execute("""SELECT table_name FROM information_schema.tables
                       WHERE table_schema = 'public' ORDER BY table_name""")
        tables = [r[0] for r in cur.fetchall()]
        print("tables:", ", ".join(tables) if tables else "none yet - run: python -m db.migrate")


if __name__ == "__main__":
    check()
