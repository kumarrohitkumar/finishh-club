"""
TESTS FOR THE AMFI BULK FILE PARSER.

WHAT THE FILE LOOKS LIKE
    AMFI publishes one big text file. It is not a plain CSV - the category and
    the fund house arrive as HEADING LINES, and every scheme row below them
    belongs to that heading until the next one appears.

        Open Ended Schemes(Equity Scheme - Large Cap Fund)   <- category
        Axis Mutual Fund                                     <- fund house
        135762;INF846K01WO1;-;Axis Large Cap;Direct Plan;Growth;29.71;17-Sep-2026

    So the parser has to remember where it is in the file. That is exactly the
    kind of thing that breaks quietly, which is why it is tested first.

    Run:  python tests/test_bulk_parser.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest.amfi_bulk import parse_bulk, is_wanted

HEADER = "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date"

SAMPLE = f"""{HEADER}

Open Ended Schemes(Equity Scheme - Large Cap Fund)

Axis Mutual Fund

100001;INF001;-;Axis Large Cap Fund;Direct Plan;Growth Option;45.12;17-Sep-2026
100002;INF002;-;Axis Large Cap Fund;Regular Plan;Growth Option;42.10;17-Sep-2026
100003;INF003;-;Axis Large Cap Fund;Direct Plan;IDCW Option;30.00;17-Sep-2026

HDFC Mutual Fund

100004;INF004;-;HDFC Large Cap Fund;Direct Plan;Growth;88.40;17-Sep-2026

Open Ended Schemes(Debt Scheme - Liquid Fund)

SBI Mutual Fund

200001;INF201;-;SBI Liquid Fund;Direct Plan;Growth;3900.10;17-Sep-2026
"""


def test_finds_every_scheme_row():
    assert len(parse_bulk(SAMPLE.splitlines())) == 5


def test_category_comes_from_the_section_heading():
    by_code = {s.source_code: s for s in parse_bulk(SAMPLE.splitlines())}
    assert by_code["100001"].category == "equity"
    assert by_code["200001"].category == "debt"


def test_fund_house_comes_from_the_amc_heading():
    by_code = {s.source_code: s for s in parse_bulk(SAMPLE.splitlines())}
    assert by_code["100001"].fund_house == "Axis Mutual Fund"
    assert by_code["100004"].fund_house == "HDFC Mutual Fund"
    assert by_code["200001"].fund_house == "SBI Mutual Fund"


def test_fund_house_resets_on_a_new_section():
    """A bug here would label SBI's liquid fund as an HDFC fund."""
    by_code = {s.source_code: s for s in parse_bulk(SAMPLE.splitlines())}
    assert by_code["200001"].fund_house != "HDFC Mutual Fund"


def test_plan_and_option_are_kept():
    by_code = {s.source_code: s for s in parse_bulk(SAMPLE.splitlines())}
    assert by_code["100002"].plan.lower().startswith("regular")
    assert "idcw" in by_code["100003"].option.lower()


def test_header_row_is_not_a_scheme():
    assert all(s.source_code != "Scheme Code" for s in parse_bulk(SAMPLE.splitlines()))


def test_nav_and_date_are_parsed():
    s = {x.source_code: x for x in parse_bulk(SAMPLE.splitlines())}["100001"]
    assert str(s.nav) == "45.12" and s.nav_date.isoformat() == "2026-09-17"


# ---------- the seed filter (DEPLOYMENT section 1) ----------

def test_wanted_keeps_direct_growth_equity():
    s = {x.source_code: x for x in parse_bulk(SAMPLE.splitlines())}
    assert is_wanted(s["100001"])


def test_wanted_rejects_regular_plan():
    s = {x.source_code: x for x in parse_bulk(SAMPLE.splitlines())}
    assert not is_wanted(s["100002"])


def test_wanted_rejects_idcw_option():
    s = {x.source_code: x for x in parse_bulk(SAMPLE.splitlines())}
    assert not is_wanted(s["100003"])


def test_wanted_rejects_debt_for_the_seed_set():
    """Debt is excluded from the seed only. It is still fetchable on demand."""
    s = {x.source_code: x for x in parse_bulk(SAMPLE.splitlines())}
    assert not is_wanted(s["200001"])


def test_empty_input():
    assert parse_bulk([]) == []


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    p = 0
    for n, f in fns:
        try: f(); print(f"  PASS  {n}"); p += 1
        except AssertionError as e: print(f"  FAIL  {n}: {e}")
        except Exception as e: print(f"  ERROR {n}: {type(e).__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
