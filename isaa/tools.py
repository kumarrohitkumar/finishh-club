"""
ISAA'S TOOLS - the only ways Isaa can obtain information.

THE BOUNDARY (PRD section 7.1)
    Two kinds of tool, and they must never blur:

      DATABASE TOOLS  return numbers. Exact, current, from Postgres.
      SEARCH TOOL     returns prose. Explanations we wrote ourselves.

    Isaa must never state a number that came from the search tool. A document
    can be out of date and a model can misread it. Telling someone an expense
    ratio is 0.5% when it is 1.8% is real financial harm.

HOW THE RULE IS ENFORCED, NOT JUST STATED
    1. search_concepts returns objects with no numeric fields at all
    2. every database tool records what it returned, so eval E-2 can trace each
       number in an answer back to a tool result
    3. the system prompt says it as well - but that is the weakest layer, which
       is why it is not the only one

ADDING A TOOL
    One entry in TOOLS and one entry in DECLARATIONS. Nothing else changes.
    This is extension point 3 from the HLD.
"""
from __future__ import annotations

from constants import BUCKET_ORDER, HOLDING_PERIODS_YEARS, Category
from db.connection import connect
from knowledge.search import search_concepts as _search
from meter.buckets import SCALES

MAX_FUND_RESULTS = 5


# ----------------------------------------------------------- database tools

def find_fund(name: str) -> list[dict]:
    """Look up funds by name. Returns codes so other tools can be called."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT source_code, name, fund_house, category
                       FROM assets
                       WHERE is_active AND name ILIKE %s
                       ORDER BY name LIMIT %s""",
                    (f"%{name}%", MAX_FUND_RESULTS))
        rows = cur.fetchall()
    if not rows:
        return []
    return [{"source_code": r[0], "name": r[1], "fund_house": r[2],
             "category": r[3]} for r in rows]


def get_fund_details(source_code: str) -> dict:
    """Facts about one fund. Every number in an answer must come from here."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT a.name, a.fund_house, a.category, a.sub_category,
                   (SELECT price FROM price_history WHERE asset_id = a.id
                     ORDER BY price_date DESC LIMIT 1),
                   (SELECT max(price_date) FROM price_history WHERE asset_id = a.id),
                   (SELECT min(price_date) FROM price_history WHERE asset_id = a.id),
                   (SELECT count(*) FROM price_history WHERE asset_id = a.id)
            FROM assets a WHERE a.source_code = %s
        """, (source_code,))
        row = cur.fetchone()

    if not row:
        return {"error": f"No fund with code {source_code}"}

    return {
        "source_code": source_code, "name": row[0], "fund_house": row[1],
        "category": row[2], "sub_category": row[3],
        "latest_nav": float(row[4]) if row[4] is not None else None,
        "latest_nav_date": str(row[5]) if row[5] else None,
        "history_from": str(row[6]) if row[6] else None,
        "price_points": row[7],
        "source": "AMFI",
    }


def get_meter(source_code: str, period_years: int | None = None) -> dict:
    """All three holding periods in ONE call unless one is named.

    Why: "is this fund risky?" made the model call this three times - three
    round trips, three times the tokens, and about 45 seconds. The three
    periods are one row lookup each; there is no reason to make the model ask
    three times. Fewer, better tool calls is the whole lesson.
    """
    if period_years is None:
        periods = {}
        for years in HOLDING_PERIODS_YEARS:
            result = _one_meter(source_code, years)
            if "error" in result:
                return result
            periods[f"{years}Y"] = result
        first = periods[f"{HOLDING_PERIODS_YEARS[0]}Y"]
        return {
            "source_code": source_code,
            "scale": first["scale"],
            "data_from": first["data_from"],
            "data_to": first["data_to"],
            "by_holding_period": periods,
            "source": "AMFI",
            "meaning": ("Share of past rolling periods that ended in each outcome, "
                        "for each holding period. Historical only - not a prediction."),
        }
    return _one_meter(source_code, period_years)


def _one_meter(source_code: str, period_years: int) -> dict:
    """The Finishh Meter. Read from the table - never computed here (rule N-2)."""
    if period_years not in HOLDING_PERIODS_YEARS:
        return {"error": f"period_years must be one of {list(HOLDING_PERIODS_YEARS)}"}

    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT m.shown_period_years, m.pct_strong, m.pct_moderate, m.pct_flat,
                   m.pct_loss, m.window_count, m.scale_used, m.data_start,
                   m.data_end, m.insufficient_history, m.note
            FROM meter_results m JOIN assets a ON a.id = m.asset_id
            WHERE a.source_code = %s AND m.period_years = %s
        """, (source_code, period_years))
        row = cur.fetchone()

    if not row:
        return {"error": f"No meter for {source_code} at {period_years}Y"}

    labels = SCALES[Category(row[6])].labels()
    values = (float(row[1]), float(row[2]), float(row[3]), float(row[4]))
    return {
        "source_code": source_code,
        "requested_period_years": period_years,
        "shown_period_years": row[0],
        "buckets": [{"outcome": str(b), "meaning": labels[b], "percent_of_periods": v}
                    for b, v in zip(BUCKET_ORDER, values)],
        "window_count": row[5], "scale": row[6],
        "data_from": str(row[7]) if row[7] else None,
        "data_to": str(row[8]) if row[8] else None,
        "insufficient_history": row[9], "note": row[10] or "",
        "source": "AMFI",
        "meaning": ("Share of past rolling periods that ended in each outcome. "
                    "Historical only - not a prediction."),
    }


# ------------------------------------------------------------- search tool

def search_concepts(question: str) -> list[dict]:
    """Explanations only. Carries no numeric fields, by design."""
    return [{"title": p.title, "explanation": p.content}
            for p in _search(question, limit=3)]


TOOLS = {
    "find_fund": find_fund,
    "get_fund_details": get_fund_details,
    "get_meter": get_meter,
    "search_concepts": search_concepts,
}

NUMERIC_TOOLS = {"get_fund_details", "get_meter"}    # used by eval E-2

DECLARATIONS = [
    {"type": "function", "function": {
        "name": "find_fund",
        "description": ("Find funds by name or part of a name. Use this first when "
                        "the user names a fund, to get its source_code."),
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string", "description": "Part of the fund name"}},
            "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "get_fund_details",
        "description": ("Facts about one fund: latest NAV, category, fund house, "
                        "how much history we hold. Use this for any factual number "
                        "about a fund. Never state a NAV you did not get from here."),
        "parameters": {"type": "object", "properties": {
            "source_code": {"type": "string"}}, "required": ["source_code"]}}},
    {"type": "function", "function": {
        "name": "get_meter",
        "description": ("The Finishh Meter for a fund: how often each outcome "
                        "happened historically. Call this ONCE and leave "
                        "period_years out to get 1, 3 and 5 years together - "
                        "do not call it separately for each period. "
                        "Historical distribution, never a forecast."),
        "parameters": {"type": "object", "properties": {
            "source_code": {"type": "string"},
            "period_years": {"type": "integer", "enum": list(HOLDING_PERIODS_YEARS),
                             "description": "Leave out to get all three at once"}},
            "required": ["source_code"]}}},
    {"type": "function", "function": {
        "name": "search_concepts",
        "description": ("Look up a written explanation of a financial term or idea, "
                        "such as expense ratio, XIRR, drawdown or SIP. Returns prose "
                        "only. Never take a number from this tool."),
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string"}}, "required": ["question"]}}},
]
