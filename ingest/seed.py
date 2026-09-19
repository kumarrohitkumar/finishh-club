"""
SEED LOADER - puts a sample of real funds into the database.

WHAT IT DOES
    1. Download AMFI's bulk file (every Indian fund, one request)
    2. Keep only Direct + Growth + equity/hybrid  (the seed filter)
    3. Take a sample of them
    4. For each: fetch its NAV history, store it, compute its Meters, store those

    python -m ingest.seed            # 25 funds
    python -m ingest.seed 100        # 100 funds

WHY A SAMPLE FIRST
    The full seed set is 1,168 funds and about 0.36 GB. Loading a handful first
    proves the whole path works - parse, fetch, store, compute - before spending
    an hour on the rest. Re-running is safe: assets are upserted and each fund's
    prices are replaced, not duplicated.

HISTORY IS CAPPED
    SEED_HISTORY_YEARS (10) keeps us inside Neon's 0.5 GB free tier. A 5-year
    Meter still gets roughly 1,300 windows, far above the minimum of 30.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

from adapters.amfi import AmfiAdapter
from adapters.base import AssetInfo
from config import AMFI_NAV_ALL_URL
from constants import (DAYS_PER_YEAR, HOLDING_PERIODS_YEARS, SEED_HISTORY_YEARS,
                       AssetType)
from db import repository as repo
from db.connection import connect
from ingest.amfi_bulk import BulkScheme, is_wanted, parse_bulk
from meter.buckets import SCALES
from net import fetch_text
from meter.engine import compute_best

DEFAULT_SAMPLE = 25


def download_bulk() -> list[str]:
    return fetch_text(AMFI_NAV_ALL_URL).splitlines()


def to_asset_info(scheme: BulkScheme) -> AssetInfo:
    info = AssetInfo(
        source_code=scheme.source_code, name=scheme.name,
        fund_house=scheme.fund_house, category=scheme.category,
        sub_category=scheme.sub_category, asset_type=AssetType.FUND,
    )
    object.__setattr__(info, "plan", scheme.plan)
    object.__setattr__(info, "option", scheme.option)
    object.__setattr__(info, "isin", scheme.isin or None)
    return info


def seed(sample_size: int = DEFAULT_SAMPLE) -> int:
    print("Downloading AMFI bulk file ...")
    schemes = parse_bulk(download_bulk())
    wanted = [s for s in schemes if is_wanted(s)]
    print(f"  {len(schemes):,} schemes in file -> {len(wanted):,} match the seed filter")

    # spread the sample across fund houses instead of taking the first N,
    # which would all be from whichever AMC sorts first
    by_house: dict[str, list[BulkScheme]] = {}
    for s in wanted:
        by_house.setdefault(s.fund_house, []).append(s)
    picked: list[BulkScheme] = []
    while len(picked) < sample_size and by_house:
        for house in list(by_house):
            if by_house[house]:
                picked.append(by_house[house].pop(0))
            else:
                del by_house[house]
            if len(picked) >= sample_size:
                break

    cutoff = date.today() - timedelta(days=int(SEED_HISTORY_YEARS * DAYS_PER_YEAR))
    adapter = AmfiAdapter()
    ok = failed = total_prices = 0

    print(f"\nLoading {len(picked)} funds (history from {cutoff}) ...\n")
    with connect() as conn:
        for n, scheme in enumerate(picked, 1):
            label = scheme.name[:46]
            try:
                history = adapter.fetch_history(scheme.source_code)
                if not history:
                    print(f"  {n:>3}. {label:<48} no history, skipped")
                    failed += 1
                    continue

                info = to_asset_info(scheme)
                asset_id = repo.upsert_asset(conn, info)
                kept = repo.insert_prices(conn, asset_id, history, since=cutoff)

                series = [(r.price_date, r.price) for r in history
                          if r.price_date >= cutoff]
                scale = SCALES[scheme.category]
                for years in HOLDING_PERIODS_YEARS:
                    repo.save_meter(conn, asset_id, years,
                                    compute_best(series, years, scale))
                conn.commit()

                total_prices += kept
                ok += 1
                print(f"  {n:>3}. {label:<48} {kept:>5} prices  [{scheme.category}]")
            except Exception as exc:
                conn.rollback()
                failed += 1
                print(f"  {n:>3}. {label:<48} FAILED {type(exc).__name__}: {exc}")

        repo.record_run(conn, "amfi-seed", date.today(), len(picked), ok,
                        "ok" if failed == 0 else "failed")
        conn.commit()

        c = repo.counts(conn)
        print(f"\n  loaded {ok} funds, {failed} failed, {total_prices:,} prices")
        print(f"  database now: {c['assets']} assets, {c['prices']:,} prices, "
              f"{c['meters']} meters, size {repo.database_size(conn)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    size = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SAMPLE
    sys.exit(seed(size))
