"""
STEP 0 - the thin slice. The first thing built, on purpose.

WHAT IT DOES
    One fund, end to end:
        fetch real history  ->  compute the Meter  ->  print it

        python step0.py 119528

WHY THIS FIRST
    From R1_PLAN.md: before building layers properly, get one fund working all
    the way through. If the data format is wrong, or the Meter maths is off, or
    a field is missing, you find out in a day rather than in week three.

    No database. No Docker. No web server. Just Python.

WHAT IT PROVES
    - AMFI data can be fetched and parsed
    - Categories map correctly to Meter scales
    - The Meter maths produces sensible numbers on real funds
    - The adapter interface holds up

WHAT REPLACES IT
    Nothing is thrown away. build_meters() becomes the nightly job, the adapter
    becomes the ingestion job, and the printing is replaced by the API and the
    React frontend.
"""
from __future__ import annotations

import sys

from adapters.amfi import AmfiAdapter
from adapters.base import AssetInfo, PriceRecord
from config import DEFAULT_SCHEME_CODE, METER_BAR_WIDTH
from constants import BUCKET_COLOURS, BUCKET_ORDER, HOLDING_PERIODS_YEARS
from meter.buckets import SCALES
from meter.engine import MeterResult, compute_best

RULE_WIDTH = 78


def build_meters(info: AssetInfo, history: list[PriceRecord]) -> dict[int, MeterResult]:
    """One Meter per holding period, on the scale for this asset's category."""
    scale = SCALES[info.category]
    series = [(record.price_date, record.price) for record in history]
    return {years: compute_best(series, years, scale) for years in HOLDING_PERIODS_YEARS}


def _bar(percentage: float) -> str:
    filled = int(round(percentage / 100 * METER_BAR_WIDTH))
    return "#" * filled + "." * (METER_BAR_WIDTH - filled)


def render(result: MeterResult, requested_years: int) -> None:
    heading = f"  {requested_years}-year holding period"
    if result.period_years and result.period_years != requested_years:
        heading += f"   (showing {result.period_years}Y - see note)"
    print(heading)

    if result.insufficient_history and not result.pct:
        print(f"      {result.note}\n")
        return

    labels = SCALES[result.scale_used].labels()
    for bucket in BUCKET_ORDER:
        value = result.pct.get(bucket, 0.0)
        print(f"      {labels[bucket]:<26} {_bar(value)} {value:5.1f}%"
              f"   ({BUCKET_COLOURS[bucket]})")

    print(f"      windows: {result.window_count:,}   "
          f"data: {result.data_start} to {result.data_end}   "
          f"scale: {result.scale_used}")
    if result.note:
        print(f"      note: {result.note}")
    print()


def main(scheme_code: str) -> int:
    adapter = AmfiAdapter()

    print(f"\nFetching scheme {scheme_code} ...")
    info = adapter.fetch_asset(scheme_code)
    history = adapter.fetch_history(scheme_code)

    if not history:
        print("No usable price history.")
        return 1

    print(f"\n{info.name}")
    print(f"{info.fund_house}  |  {info.sub_category}  |  Meter scale: {info.category}")
    print(f"{len(history):,} NAV points from "
          f"{history[0].price_date} to {history[-1].price_date}")
    print("\n" + "=" * RULE_WIDTH)
    print("FINISHH METER  -  how often each outcome happened, historically")
    print("=" * RULE_WIDTH + "\n")

    for years, result in build_meters(info, history).items():
        render(result, years)

    print("These are historical rolling periods, not a prediction.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SCHEME_CODE))
