"""
NIGHTLY METER JOB - recomputes every asset's Finishh Meter and stores it.

WHY IT RUNS AT NIGHT
    Rule M-4 and N-2: a Meter is read from a table, never calculated while a
    user waits. Computing 5-year rolling windows over 2,500 prices takes real
    time; reading one row takes a millisecond.

    python -m meter.job              # every asset
    python -m meter.job 119528       # one asset, by source code

WHY IT COMMITS PER ASSET
    A run over thousands of funds will sometimes be interrupted. Committing
    after each asset means a restart continues from where it stopped instead of
    losing everything.

WHAT IT DOES NOT KNOW
    It does not fetch anything. It reads prices already in the database and
    writes meters back. Downloading is the ingestion jobs' work. Keeping them
    separate means a network problem can never corrupt a Meter.
"""
from __future__ import annotations

import sys
import time

from constants import HOLDING_PERIODS_YEARS, Category
from db import repository as repo
from db.connection import connect
from meter.buckets import SCALES
from meter.engine import compute_best


def _assets(conn, source_code: str | None):
    with conn.cursor() as cur:
        if source_code:
            cur.execute("""SELECT id, source_code, name, category FROM assets
                           WHERE source_code = %s""", (source_code,))
        else:
            cur.execute("""SELECT id, source_code, name, category FROM assets
                           WHERE is_active ORDER BY id""")
        return cur.fetchall()


def _series(conn, asset_id: int):
    with conn.cursor() as cur:
        cur.execute("""SELECT price_date, price FROM price_history
                       WHERE asset_id = %s ORDER BY price_date""", (asset_id,))
        return cur.fetchall()


def run(source_code: str | None = None) -> int:
    started = time.time()
    done = skipped = failed = 0

    with connect() as conn:
        assets = _assets(conn, source_code)
        print(f"Computing meters for {len(assets):,} asset(s) ...\n")

        for asset_id, code, name, category in assets:
            series = _series(conn, asset_id)
            if not series:
                skipped += 1
                continue
            try:
                scale = SCALES[Category(category)]
                for years in HOLDING_PERIODS_YEARS:
                    repo.save_meter(conn, asset_id, years,
                                    compute_best(series, years, scale))
                conn.commit()
                done += 1
                if source_code or done % 25 == 0:
                    print(f"  {done:>5} done  ({name[:44]})")
            except Exception as exc:
                conn.rollback()
                failed += 1
                print(f"  FAILED {code} {name[:40]}: {type(exc).__name__}: {exc}")

        counts = repo.counts(conn)
        elapsed = time.time() - started
        print(f"\n  {done} computed, {skipped} skipped (no prices), {failed} failed")
        print(f"  {counts['meters']} meter rows in total, {elapsed:.1f}s")
        if done:
            print(f"  {elapsed / done * 1000:.0f} ms per asset")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
