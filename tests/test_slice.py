"""
TESTS FOR THE STEP 0 RUNNER - the glue between adapter and engine.

WHAT IT CHECKS
    All three periods (1Y, 3Y, 5Y) are produced, the correct scale is chosen
    from the fund's category, a young fund falls back instead of showing an
    empty bar, and the scale name is available for display (rule M-6).

WRITTEN BEFORE THE CODE
    This file was created before step0.py existed and was run first to confirm
    it failed with ModuleNotFoundError. A test that has never failed proves
    nothing - it may be passing for the wrong reason.

    Run:  python tests/test_slice.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from decimal import Decimal

from adapters.base import AssetInfo, PriceRecord
from step0 import build_meters


def info(category="equity"):
    return AssetInfo("119551", "Test Fund", "Test AMC", category, "Large Cap")


def history(rate, years, start=date(2010, 1, 1)):
    out, n = [], int(years * 365.25)
    for d in range(n + 1):
        p = 100.0 * (1.0 + rate) ** (d / 365.25)
        out.append(PriceRecord("119551", start + timedelta(days=d), Decimal(str(round(p, 6)))))
    return out


def test_returns_all_three_periods():
    m = build_meters(info(), history(0.12, 12))
    assert sorted(m) == [1, 3, 5]


def test_uses_the_category_scale():
    """9%/yr: moderate on equity, strong on debt. The scale must follow category."""
    h = history(0.09, 12)
    assert build_meters(info("equity"), h)[3].pct["moderate"] == 100.0
    assert build_meters(info("debt"), h)[3].pct["strong"] == 100.0


def test_young_fund_falls_back_not_empty():
    m = build_meters(info(), history(0.11, 2.5))
    assert m[5].period_years == 1          # fell back
    assert m[5].requested_years == 5
    assert m[5].pct                        # never an empty bar (rule M-5)


def test_scale_label_is_available():
    """Rule M-6: the scale in use must always be displayable."""
    m = build_meters(info(), history(0.12, 12))
    assert m[3].scale_used == "equity"


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    p = 0
    for n, f in fns:
        try:
            f(); print(f"  PASS  {n}"); p += 1
        except AssertionError as e: print(f"  FAIL  {n}: {e}")
        except Exception as e: print(f"  ERROR {n}: {type(e).__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
