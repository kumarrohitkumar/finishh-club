"""
REPOSITORY - every database read and write lives here.

WHY ONE FILE
    SQL in one place. No other module writes queries, so when a table changes
    there is exactly one file to look at. It also keeps psycopg out of the
    business logic, which is why the Meter engine can be tested without a
    database at all.

BULK INSERTS USE COPY
    Inserting 3,000 prices one row at a time is thousands of round trips to
    Neon. COPY streams them in one go - a few hundred times faster.
"""
from __future__ import annotations

from datetime import date

from adapters.base import AssetInfo, PriceRecord
from meter.engine import MeterResult


def upsert_asset(conn, info: AssetInfo) -> int:
    """Insert the asset, or update it if we already hold it. Returns its id."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO assets (asset_type, source_code, name, fund_house,
                                category, sub_category, plan, option, isin)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (asset_type, source_code) DO UPDATE
               SET name = EXCLUDED.name,
                   fund_house = EXCLUDED.fund_house,
                   category = EXCLUDED.category,
                   sub_category = EXCLUDED.sub_category,
                   updated_at = now()
            RETURNING id
        """, (str(info.asset_type), info.source_code, info.name, info.fund_house,
              str(info.category), info.sub_category,
              getattr(info, "plan", ""), getattr(info, "option", ""),
              getattr(info, "isin", None)))
        return cur.fetchone()[0]


def insert_prices(conn, asset_id: int, records: list[PriceRecord],
                  since: date | None = None) -> int:
    """Replace this asset's price history. `since` caps how far back we keep."""
    rows = [r for r in records if since is None or r.price_date >= since]
    if not rows:
        return 0
    with conn.cursor() as cur:
        cur.execute("DELETE FROM price_history WHERE asset_id = %s", (asset_id,))
        with cur.copy("COPY price_history (asset_id, price_date, price) FROM STDIN") as cp:
            for r in rows:
                cp.write_row((asset_id, r.price_date, r.price))
    return len(rows)


def save_meter(conn, asset_id: int, requested_years: int, result: MeterResult) -> None:
    """Rule M-4: meters are written by the nightly job, never computed on read."""
    from constants import Bucket
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO meter_results
                (asset_id, period_years, shown_period_years,
                 pct_strong, pct_moderate, pct_flat, pct_loss,
                 window_count, scale_used, data_start, data_end,
                 insufficient_history, note, computed_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
            ON CONFLICT (asset_id, period_years) DO UPDATE SET
                shown_period_years = EXCLUDED.shown_period_years,
                pct_strong = EXCLUDED.pct_strong,
                pct_moderate = EXCLUDED.pct_moderate,
                pct_flat = EXCLUDED.pct_flat,
                pct_loss = EXCLUDED.pct_loss,
                window_count = EXCLUDED.window_count,
                scale_used = EXCLUDED.scale_used,
                data_start = EXCLUDED.data_start,
                data_end = EXCLUDED.data_end,
                insufficient_history = EXCLUDED.insufficient_history,
                note = EXCLUDED.note,
                computed_at = now()
        """, (asset_id, requested_years, result.period_years or requested_years,
              result.pct.get(Bucket.STRONG, 0), result.pct.get(Bucket.MODERATE, 0),
              result.pct.get(Bucket.FLAT, 0), result.pct.get(Bucket.LOSS, 0),
              result.window_count, str(result.scale_used),
              result.data_start, result.data_end,
              result.insufficient_history, result.note))


def record_run(conn, source: str, run_date: date, seen: int, written: int,
               status: str, error: str = "") -> None:
    """Rule D-4 needs yesterday's count to compare against."""
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO ingestion_runs
                       (source, run_date, rows_seen, rows_written, status, error, finished_at)
                       VALUES (%s,%s,%s,%s,%s,%s, now())""",
                    (source, run_date, seen, written, status, error))


def counts(conn) -> dict[str, int]:
    with conn.cursor() as cur:
        cur.execute("""SELECT (SELECT count(*) FROM assets),
                              (SELECT count(*) FROM price_history),
                              (SELECT count(*) FROM meter_results)""")
        a, p, m = cur.fetchone()
    return {"assets": a, "prices": p, "meters": m}


def database_size(conn) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        return cur.fetchone()[0]
