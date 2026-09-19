"""
TESTS FOR THE DAILY UPDATE SAFETY CHECK (rule D-4).

THE DANGER
    The daily job overwrites live data. If AMFI ever serves a truncated or
    broken file, a naive job would happily wipe good prices and replace them
    with nothing. Nobody would notice until a Meter looked wrong weeks later.

THE GUARD
    Compare today's scheme count against the last successful run. A drop of
    more than 5% means something is wrong with the file, not with the market -
    funds do not disappear in thousands overnight. Stop, write nothing, alert.

    Run:  python tests/test_daily.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest.daily import is_count_acceptable, new_prices_only
from adapters.base import PriceRecord
from datetime import date
from decimal import Decimal


def test_first_ever_run_is_allowed():
    """No previous run to compare against - must not block the first load."""
    assert is_count_acceptable(seen=14000, previous=None)


def test_previous_zero_is_allowed():
    assert is_count_acceptable(seen=14000, previous=0)


def test_same_count_is_fine():
    assert is_count_acceptable(seen=14000, previous=14000)


def test_more_schemes_is_fine():
    """New funds launch. Growth is normal."""
    assert is_count_acceptable(seen=14500, previous=14000)


def test_small_drop_is_fine():
    """A few funds merge or close. 2% is normal."""
    assert is_count_acceptable(seen=13720, previous=14000)


def test_drop_just_under_the_limit_is_fine():
    assert is_count_acceptable(seen=13310, previous=14000)      # 4.9%


def test_big_drop_is_rejected():
    """Rule D-4: a broken file must never overwrite good data."""
    assert not is_count_acceptable(seen=13000, previous=14000)  # 7.1%


def test_catastrophic_drop_is_rejected():
    assert not is_count_acceptable(seen=12, previous=14000)


def test_empty_file_is_rejected():
    assert not is_count_acceptable(seen=0, previous=14000)


# ---------- appending only what is new ----------

def rec(day, price):
    return PriceRecord("X", date(2026, 9, day), Decimal(price))


def test_only_dates_after_the_latest_are_kept():
    incoming = [rec(15, "10"), rec(16, "11"), rec(17, "12")]
    assert [r.price_date.day for r in new_prices_only(incoming, latest=date(2026, 9, 15))] == [16, 17]


def test_nothing_new_returns_empty():
    incoming = [rec(15, "10")]
    assert new_prices_only(incoming, latest=date(2026, 9, 15)) == []


def test_no_existing_data_keeps_everything():
    incoming = [rec(15, "10"), rec(16, "11")]
    assert len(new_prices_only(incoming, latest=None)) == 2


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    p = 0
    for n, f in fns:
        try: f(); print(f"  PASS  {n}"); p += 1
        except AssertionError as e: print(f"  FAIL  {n}: {e}")
        except Exception as e: print(f"  ERROR {n}: {type(e).__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
