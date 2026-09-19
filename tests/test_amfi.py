"""
TESTS FOR THE AMFI ADAPTER.

NO NETWORK
    A fake payload is injected instead of calling the internet, so these run in
    milliseconds and give the same answer every time. Tests that depend on a
    website are slow and fail for reasons that have nothing to do with the code.

WHAT THEY COVER
    Category mapping (equity, ELSS, debt, gilt, hybrid, and unknown falling
    back to hybrid), history sorted oldest-first, prices returned as Decimal
    and not float, and bad rows skipped rather than written as zero.

WHY "UNKNOWN -> HYBRID" IS TESTED
    If AMFI invents a new category name tomorrow, the fund must land on the
    middle scale. Guessing "equity" for an unknown instrument would judge it on
    the harshest scale and show a misleading meter.

    Run:  python tests/test_amfi.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from decimal import Decimal

from adapters.amfi import AmfiAdapter, _category_of


class FakeAdapter(AmfiAdapter):
    def __init__(self, payload): self.payload = payload
    def _get(self, code): return self.payload


def payload(rows, category="Equity Scheme - Large Cap Fund", stype="Open Ended Schemes"):
    return {"meta": {"scheme_code": 119551, "scheme_name": "Test Fund - Direct Growth",
                     "fund_house": "Test AMC", "scheme_category": category,
                     "scheme_type": stype},
            "data": rows}


# ---------- category mapping (rule D-5) ----------

def test_category_equity():
    assert _category_of("Equity Scheme - Large Cap Fund", "Open Ended") == "equity"

def test_category_elss_is_equity():
    assert _category_of("Equity Scheme - ELSS", "Open Ended") == "equity"

def test_category_debt():
    assert _category_of("Debt Scheme - Liquid Fund", "Open Ended") == "debt"

def test_category_gilt_is_debt():
    assert _category_of("Debt Scheme - Gilt Fund", "Open Ended") == "debt"

def test_category_hybrid():
    assert _category_of("Hybrid Scheme - Balanced Advantage", "Open Ended") == "hybrid"

def test_category_unknown_defaults_to_hybrid():
    """Unknown -> the middle scale. Never guess an extreme scale."""
    assert _category_of("Something New", "Open Ended") == "hybrid"


# ---------- history parsing ----------

def test_history_is_sorted_ascending():
    a = FakeAdapter(payload([{"date": "16-09-2026", "nav": "120.0"},
                             {"date": "15-09-2026", "nav": "119.0"},
                             {"date": "14-09-2026", "nav": "118.0"}]))
    got = a.fetch_history("119551")
    assert [r.price_date for r in got] == [date(2026, 9, 14), date(2026, 9, 15), date(2026, 9, 16)]

def test_history_returns_decimal_not_float():
    a = FakeAdapter(payload([{"date": "16-09-2026", "nav": "120.12345"}]))
    p = a.fetch_history("119551")[0].price
    assert isinstance(p, Decimal) and p == Decimal("120.12345")

def test_history_skips_zero_nav():
    """Rule D-6: skip unusable rows, never write zero."""
    a = FakeAdapter(payload([{"date": "16-09-2026", "nav": "120.0"},
                             {"date": "15-09-2026", "nav": "0.00000"}]))
    got = a.fetch_history("119551")
    assert len(got) == 1 and got[0].price == Decimal("120.0")

def test_history_skips_malformed_rows():
    a = FakeAdapter(payload([{"date": "16-09-2026", "nav": "120.0"},
                             {"date": "bad-date", "nav": "119.0"},
                             {"date": "14-09-2026", "nav": "N.A."},
                             {"nav": "118.0"}]))
    assert len(a.fetch_history("119551")) == 1

def test_history_empty():
    assert a_empty() == []

def a_empty():
    return FakeAdapter(payload([])).fetch_history("119551")


# ---------- asset info ----------

def test_asset_info_maps_fields():
    a = FakeAdapter(payload([], category="Debt Scheme - Liquid Fund"))
    info = a.fetch_asset("119551")
    assert info.name == "Test Fund - Direct Growth"
    assert info.fund_house == "Test AMC"
    assert info.category == "debt"
    assert info.asset_type == "fund"


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
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
