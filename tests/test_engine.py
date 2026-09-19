"""
TESTS FOR THE METER ENGINE - the most important tests in the project.

WHY THESE MATTER MOST
    A bug here is not a display glitch. It produces confident, wrong financial
    numbers, and nobody would notice by looking.

HOW THEY WORK
    Most use a made-up price series that grows at exactly one known rate. If a
    fund grows at exactly 12% a year, then EVERY rolling window must return
    12%, so 100% of windows must land in one bucket. Anything else is a bug.

WHAT THEY COVER
    known CAGR maths - buckets totalling 100 - daily stepping - too-young
    fallback - too-few-windows - weekend and holiday gaps - the same return
    bucketing differently per category - losses - empty input

ONE THAT ALREADY EARNED ITS KEEP
    test_8 originally used 9% and asserted equity=moderate, debt=strong.
    An earlier version used 7%, which is moderate on BOTH scales. The test
    failed, the scale table was checked, and the TEST was fixed - not the code.
    Changing the engine to match a wrong test would have broken the debt scale.

    Run:  python tests/test_engine.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from decimal import Decimal

from constants import MIN_WINDOWS_FOR_METER
from meter.engine import compute, compute_best, _annualised
from meter.buckets import SCALES

EQ, DEBT = SCALES["equity"], SCALES["debt"]


def series_at_rate(rate: float, years: float, start=date(2010, 1, 1), step=1):
    """Daily prices growing at exactly `rate` per year. Every rolling window
    of any length must therefore return exactly `rate`."""
    out, n = [], int(years * 365.25)
    for d in range(0, n + 1, step):
        price = 100.0 * (1.0 + rate) ** (d / 365.25)
        out.append((start + timedelta(days=d), Decimal(str(round(price, 6)))))
    return out


def test_1_known_cagr():
    # 100 -> 200 over 5 years is 14.87% per year
    got = _annualised(Decimal("100"), Decimal("200"), int(5 * 365.25))
    assert abs(got - 0.148698) < 0.0001, got


def test_2_constant_growth_lands_in_one_bucket():
    r = compute(series_at_rate(0.12, 12), 5, EQ)      # 12%/yr -> equity "strong"
    assert r.pct["strong"] == 100.0, r.pct
    assert r.pct["moderate"] == r.pct["flat"] == r.pct["loss"] == 0.0


def test_3_buckets_total_100():
    for rate in (-0.05, 0.02, 0.07, 0.12, 0.30):
        r = compute(series_at_rate(rate, 12), 3, EQ)
        assert abs(sum(r.pct.values()) - 100.0) < 0.001, (rate, r.pct)


def test_4_window_count_steps_daily():
    # 10 years of daily points, 5-year windows -> about 5 years of start dates
    s = series_at_rate(0.10, 10)
    r = compute(s, 5, EQ)
    expected = len(s) - int(5 * 365.25)
    assert abs(r.window_count - expected) <= 3, (r.window_count, expected)


def test_5_too_young_falls_back():
    r = compute_best(series_at_rate(0.11, 2.5), 5, EQ)   # only 2.5 yrs of data
    assert not r.insufficient_history
    assert r.period_years == 1 and r.requested_years == 5
    assert "no 5-year history" in r.note


def test_6_not_enough_windows_is_flagged():
    s = series_at_rate(0.10, 3.02)                        # ~7 windows of 3Y
    r = compute(s, 3, EQ)
    assert r.insufficient_history and r.window_count < MIN_WINDOWS_FOR_METER
    assert r.pct == {}                                    # never a partial bar


def test_7_gaps_do_not_break_alignment():
    """Weekends and holidays: keep only weekdays. Windows must still work."""
    s = [(d, p) for d, p in series_at_rate(0.12, 12) if d.weekday() < 5]
    r = compute(s, 5, EQ)
    assert r.pct["strong"] == 100.0, r.pct
    assert r.window_count > 1000


def test_8_same_returns_bucket_differently_per_category():
    """9%/yr is 'moderate' for equity (green starts at 10%) but 'strong' for
    debt (green starts at 8%). This is the whole reason scales differ."""
    s = series_at_rate(0.09, 12)
    assert compute(s, 3, EQ).pct["moderate"] == 100.0
    assert compute(s, 3, DEBT).pct["strong"] == 100.0


def test_9_loss_bucket():
    r = compute(series_at_rate(-0.04, 12), 3, EQ)
    assert r.pct["loss"] == 100.0


def test_10_empty_series():
    r = compute([], 3, EQ)
    assert r.insufficient_history and r.window_count == 0


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    passed = 0
    for name, fn in fns:
        try:
            fn(); print(f"  PASS  {name}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
        except Exception as e:
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
