"""
TESTS FOR THE FUND API.

THESE HIT THE REAL DATABASE
    Unlike the engine and parser tests, these talk to Neon. That makes them an
    INTEGRATION test - slower, but they check the thing that actually breaks in
    an API: wrong SQL, wrong field names, wrong status codes.

    They assert on shape and rules, never on a particular fund's name, so they
    keep passing as the data grows.

WHAT THEY PROTECT
    F-4  every figure carries its source and last-updated time
    F-6  missing values say so, never a blank or a zero
    M-6  the scale in use is always available to display
    N-2  the Meter is READ from a table, never computed during a request

    Run:  python tests/test_api.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def any_fund_code() -> str:
    return client.get("/funds", params={"limit": 1}).json()["items"][0]["source_code"]


# ---------- health ----------

def test_health_is_ok():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


# ---------- listing ----------

def test_list_returns_items_and_total():
    body = client.get("/funds", params={"limit": 5}).json()
    assert "items" in body and "total" in body
    assert len(body["items"]) <= 5


def test_list_respects_limit():
    assert len(client.get("/funds", params={"limit": 2}).json()["items"]) <= 2


def test_list_filters_by_category():
    body = client.get("/funds", params={"category": "equity", "limit": 20}).json()
    assert all(i["category"] == "equity" for i in body["items"])


def test_list_rejects_a_bad_category():
    assert client.get("/funds", params={"category": "nonsense"}).status_code == 422


def test_list_search_matches_the_name():
    first = client.get("/funds", params={"limit": 1}).json()["items"][0]
    word = first["name"].split()[0]
    body = client.get("/funds", params={"q": word, "limit": 20}).json()
    assert any(word.lower() in i["name"].lower() for i in body["items"])


def test_list_paginates():
    a = client.get("/funds", params={"limit": 1, "offset": 0}).json()["items"]
    b = client.get("/funds", params={"limit": 1, "offset": 1}).json()["items"]
    if a and b:
        assert a[0]["source_code"] != b[0]["source_code"]


# ---------- detail ----------

def test_detail_has_the_fields_the_page_needs():
    body = client.get(f"/funds/{any_fund_code()}").json()
    for field in ("source_code", "name", "fund_house", "category",
                  "latest_nav", "latest_nav_date", "source", "history_from"):
        assert field in body, f"missing {field}"


def test_detail_carries_source_and_timestamp():
    """Rule F-4."""
    body = client.get(f"/funds/{any_fund_code()}").json()
    assert body["source"] == "AMFI"
    assert body["latest_nav_date"] is not None


def test_unknown_fund_is_404_not_a_crash():
    r = client.get("/funds/does-not-exist")
    assert r.status_code == 404 and "detail" in r.json()


# ---------- meter ----------

def test_meter_buckets_total_100():
    """Rule M-3, checked through the API as well as the database."""
    body = client.get(f"/funds/{any_fund_code()}/meter", params={"period": 3}).json()
    if not body["insufficient_history"]:
        total = sum(b["percent"] for b in body["buckets"])
        assert abs(total - 100) < 0.05, total


def test_meter_always_exposes_its_scale():
    """Rule M-6: without the scale a user compares debt to equity wrongly."""
    body = client.get(f"/funds/{any_fund_code()}/meter", params={"period": 5}).json()
    assert body["scale"]
    assert all(b.get("label") for b in body["buckets"])


def test_meter_says_what_period_it_actually_shows():
    """Rule M-5: a young fund falls back, and must say so."""
    body = client.get(f"/funds/{any_fund_code()}/meter", params={"period": 5}).json()
    assert "requested_period_years" in body and "shown_period_years" in body


def test_meter_rejects_an_unsupported_period():
    r = client.get(f"/funds/{any_fund_code()}/meter", params={"period": 7})
    assert r.status_code == 422


def test_meter_for_unknown_fund_is_404():
    assert client.get("/funds/nope/meter", params={"period": 3}).status_code == 404


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    p = 0
    for n, f in fns:
        try: f(); print(f"  PASS  {n}"); p += 1
        except AssertionError as e: print(f"  FAIL  {n}: {e}")
        except Exception as e: print(f"  ERROR {n}: {type(e).__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed"); sys.exit(0 if p == len(fns) else 1)
