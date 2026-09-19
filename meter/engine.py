"""
METER ENGINE - the calculation behind the Finishh Meter.

WHAT IT DOES
    Takes a list of (date, price) and a holding period, and answers:
    "historically, how often did this produce each kind of outcome?"

HOW
    1. Take every possible window of that length, moving one day at a time
    2. Work out the return per year for each window
    3. Sort each window into one of four buckets
    4. Return the percentages, which add up to 100

        5 years of daily data, 1-year windows  ->  about 1,100 windows

WHY IT IMPORTS NOTHING FROM THIS PROJECT
    On purpose. No database, no network, no web framework. That means:
      - it can be tested on its own, quickly, with made-up numbers
      - it will work unchanged for stocks (R3) and portfolios, because it
        never learns what a mutual fund is

    This is the riskiest code in the product. A bug here does not look like a
    bug - it produces confident, wrong financial numbers. Which is why it is
    isolated and has the most tests.

TWO FUNCTIONS
    compute()       one period. Returns "not enough history" if too young.
    compute_best()  rule M-5: if too young, falls back to the longest period
                    that does work and explains why. Never an empty bar.

USED BY
    step0.py now. The nightly Meter job later.
"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from constants import (BUCKET_ORDER, DAYS_PER_YEAR, HOLDING_PERIODS_YEARS,
                       LEAP_DAY_FALLBACK, MIN_WINDOWS_FOR_METER, PERCENT_DECIMALS,
                       PERCENT_TOTAL, Bucket, Category)

from .buckets import Scale


@dataclass
class MeterResult:
    period_years: int
    requested_years: int
    pct: dict[Bucket, float] = field(default_factory=dict)
    window_count: int = 0
    scale_used: Category | str = ""
    data_start: date | None = None
    data_end: date | None = None
    insufficient_history: bool = False
    note: str = ""


def _add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:              # 29 Feb -> non-leap year
        return d.replace(year=d.year + years, day=LEAP_DAY_FALLBACK)


def _annualised(start: Decimal, end: Decimal, days: int) -> float:
    """CAGR. Prices are Decimal for exactness; the power is float, which has far
    more precision than a percentage needs."""
    years = days / DAYS_PER_YEAR
    return (float(end) / float(start)) ** (1.0 / years) - 1.0


def _to_percentages(counts: dict[Bucket, int], total: int) -> dict[Bucket, float]:
    """Round to 1 dp and force the total to exactly 100 (rule M-3)."""
    pct = {k: round(v * PERCENT_TOTAL / total, PERCENT_DECIMALS)
           for k, v in counts.items()}
    drift = round(PERCENT_TOTAL - sum(pct.values()), PERCENT_DECIMALS)
    if drift:
        biggest = max(pct, key=lambda k: pct[k])
        pct[biggest] = round(pct[biggest] + drift, PERCENT_DECIMALS)
    return pct


def compute(series: list[tuple[date, Decimal]], years: int, scale: Scale) -> MeterResult:
    """One asset, one holding period. `series` must be (date, price) pairs."""
    series = sorted(series, key=lambda r: r[0])
    if not series:
        return MeterResult(0, years, insufficient_history=True,
                           note="No price history available.")

    dates = [r[0] for r in series]
    prices = [r[1] for r in series]
    counts: dict[Bucket, int] = {b: 0 for b in BUCKET_ORDER}

    for i, start_date in enumerate(dates):
        target = _add_years(start_date, years)
        j = bisect_left(dates, target, lo=i + 1)
        if j >= len(dates):
            break                                   # no window this long remains
        gap = (dates[j] - start_date).days
        counts[scale.bucket(_annualised(prices[i], prices[j], gap))] += 1

    total = sum(counts.values())
    if total < MIN_WINDOWS_FOR_METER:
        span_years = (dates[-1] - dates[0]).days / DAYS_PER_YEAR
        return MeterResult(
            period_years=0, requested_years=years, window_count=total,
            scale_used=scale.category, data_start=dates[0], data_end=dates[-1],
            insufficient_history=True,
            note=(f"This fund has about {span_years:.1f} years of history, "
                  f"so there is no {years}-year history to look at yet."),
        )

    return MeterResult(
        period_years=years, requested_years=years,
        pct=_to_percentages(counts, total), window_count=total,
        scale_used=scale.category, data_start=dates[0], data_end=dates[-1],
    )


def compute_best(series: list[tuple[date, Decimal]], years: int, scale: Scale) -> MeterResult:
    """Rule M-5: if the asset is too young, fall back to the longest period it
    does support, and say why. Never returns an empty bar."""
    result = compute(series, years, scale)
    if not result.insufficient_history:
        return result

    for shorter in sorted((p for p in HOLDING_PERIODS_YEARS if p < years),
                          reverse=True):
        fallback = compute(series, shorter, scale)
        if not fallback.insufficient_history:
            fallback.requested_years = years
            span = (fallback.data_end - fallback.data_start).days / DAYS_PER_YEAR
            fallback.note = (
                f"This fund is only about {span:.0f} years old, so there is no "
                f"{years}-year history yet. Here is how its {shorter} years have gone."
            )
            return fallback
    return result
