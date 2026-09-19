"""
DAILY UPDATE - appends today's NAV to funds we already hold.

WHAT IT DOES
    Downloads AMFI's bulk file once, and for every fund already in the database
    appends any price dates we do not have yet.

    python -m ingest.daily            # real run
    python -m ingest.daily --dry-run  # check without writing

WHAT IT DOES NOT DO
    It never adds new funds. That is the seed job's work. Keeping the two apart
    means this job is small, fast and predictable - it touches only rows that
    already exist.

THE SAFETY CHECK (rule D-4)
    This job overwrites live data, so it compares today's scheme count against
    the last successful run. A drop of more than 5% means the FILE is broken,
    not the market - funds do not vanish in thousands overnight. It stops,
    writes nothing, and records the failure.

    Without this, one bad download silently destroys good price history and
    nobody notices until a Meter looks wrong weeks later.

WHY APPEND, NOT REPLACE
    The seed job replaces a fund's whole history. This one only adds dates that
    come after the newest we hold, so a daily run costs one row per fund.
"""
from __future__ import annotations

import sys
from datetime import date

from adapters.base import PriceRecord
from config import AMFI_NAV_ALL_URL
from constants import MAX_SCHEME_COUNT_DROP_RATIO
from db import repository as repo
from db.connection import connect
from ingest.amfi_bulk import parse_bulk
from net import fetch_text

SOURCE = "amfi-daily"


def is_count_acceptable(seen: int, previous: int | None,
                        max_drop_ratio: float = MAX_SCHEME_COUNT_DROP_RATIO) -> bool:
    """Rule D-4. True means the file looks sane enough to write."""
    if seen <= 0:
        return False
    if not previous:                      # first run, or no successful run yet
        return True
    return seen >= previous * (1.0 - max_drop_ratio)


def new_prices_only(incoming: list[PriceRecord],
                    latest: date | None) -> list[PriceRecord]:
    """Only dates we do not already hold."""
    if latest is None:
        return list(incoming)
    return [r for r in incoming if r.price_date > latest]


def _last_successful_count(conn) -> int | None:
    with conn.cursor() as cur:
        cur.execute("""SELECT rows_seen FROM ingestion_runs
                       WHERE source = %s AND status = 'ok'
                       ORDER BY run_date DESC, id DESC LIMIT 1""", (SOURCE,))
        row = cur.fetchone()
    return row[0] if row else None


def _held_assets(conn) -> dict[str, tuple[int, date | None]]:
    """source_code -> (asset_id, newest price date we hold)"""
    with conn.cursor() as cur:
        cur.execute("""SELECT a.source_code, a.id, max(p.price_date)
                       FROM assets a LEFT JOIN price_history p ON p.asset_id = a.id
                       WHERE a.asset_type = 'fund' AND a.is_active
                       GROUP BY a.source_code, a.id""")
        return {code: (aid, latest) for code, aid, latest in cur.fetchall()}


def run(dry_run: bool = False) -> int:
    print("Downloading AMFI bulk file ...")
    schemes = parse_bulk(fetch_text(AMFI_NAV_ALL_URL).splitlines())
    seen = len(schemes)

    with connect() as conn:
        previous = _last_successful_count(conn)
        print(f"  {seen:,} schemes in file (last successful run: {previous or 'none'})")

        if not is_count_acceptable(seen, previous):
            message = (f"scheme count {seen:,} is more than "
                       f"{MAX_SCHEME_COUNT_DROP_RATIO:.0%} below the previous "
                       f"{previous:,} - refusing to write")
            print(f"  REJECTED: {message}")
            repo.record_run(conn, SOURCE, date.today(), seen, 0, "rejected", message)
            conn.commit()
            return 1

        held = _held_assets(conn)
        print(f"  {len(held):,} funds held locally")

        by_code: dict[str, list[PriceRecord]] = {}
        for s in schemes:
            if s.source_code in held:
                by_code.setdefault(s.source_code, []).append(
                    PriceRecord(s.source_code, s.nav_date, s.nav))

        written = touched = 0
        for code, records in by_code.items():
            asset_id, latest = held[code]
            fresh = new_prices_only(records, latest)
            if not fresh:
                continue
            touched += 1
            if dry_run:
                written += len(fresh)
                continue
            with conn.cursor() as cur:
                for r in fresh:
                    cur.execute("""INSERT INTO price_history (asset_id, price_date, price)
                                   VALUES (%s,%s,%s)
                                   ON CONFLICT (asset_id, price_date) DO NOTHING""",
                                (asset_id, r.price_date, r.price))
                    written += cur.rowcount

        if dry_run:
            print(f"  DRY RUN: would add {written:,} prices across {touched} funds")
            return 0

        repo.record_run(conn, SOURCE, date.today(), seen, written, "ok")
        conn.commit()
        print(f"  added {written:,} prices across {touched} funds")
        print(f"  database size: {repo.database_size(conn)}")
    return 0


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv))
