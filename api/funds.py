"""
FUND ENDPOINTS - browse, detail, and the Meter.

THE ONE RULE THAT SHAPES THIS FILE
    Rule N-2: the Meter is READ from meter_results. It is never computed during
    a request. Computing 5-year rolling windows takes about 9 ms of CPU plus
    loading 2,500 rows - fine at night, far too slow while someone waits.

    If you ever find yourself importing meter.engine here, stop. That belongs
    in the nightly job.

MISSING VALUES
    Rule F-6: a value we do not have comes back as null, never 0 and never "".
    The frontend shows "Not available". A zero NAV would read as a total loss.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from constants import BUCKET_COLOURS, BUCKET_ORDER, HOLDING_PERIODS_YEARS, Category
from db.connection import connect
from meter.buckets import SCALES

from .schemas import FundDetail, FundList, FundSummary, Meter, MeterBucket

router = APIRouter()

CATEGORIES = tuple(c.value for c in Category)


@router.get("/funds", response_model=FundList)
def list_funds(
    q: str | None = Query(None, description="Search the fund name"),
    category: str | None = Query(None, pattern="^(equity|debt|hybrid|stock)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    where, params = ["a.is_active", "a.asset_type = 'fund'"], []
    if category:
        where.append("a.category = %s")
        params.append(category)
    if q:
        where.append("a.name ILIKE %s")
        params.append(f"%{q}%")
    clause = " AND ".join(where)

    with connect() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM assets a WHERE {clause}", params)
        total = cur.fetchone()[0]
        cur.execute(
            f"""SELECT a.source_code, a.name, a.fund_house, a.category, a.sub_category
                FROM assets a WHERE {clause}
                ORDER BY a.name LIMIT %s OFFSET %s""",
            [*params, limit, offset],
        )
        items = [FundSummary(source_code=r[0], name=r[1], fund_house=r[2],
                             category=r[3], sub_category=r[4]) for r in cur.fetchall()]
    return FundList(items=items, total=total, limit=limit, offset=offset)


@router.get("/funds/{source_code}", response_model=FundDetail)
def fund_detail(source_code: str):
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT a.source_code, a.name, a.fund_house, a.category, a.sub_category,
                   p.latest_price, p.latest_date, p.first_date, p.points
            FROM assets a
            LEFT JOIN LATERAL (
                SELECT max(price_date) AS latest_date,
                       min(price_date) AS first_date,
                       count(*)        AS points,
                       (SELECT price FROM price_history
                         WHERE asset_id = a.id ORDER BY price_date DESC LIMIT 1) AS latest_price
                FROM price_history WHERE asset_id = a.id
            ) p ON TRUE
            WHERE a.source_code = %s AND a.asset_type = 'fund'
        """, (source_code,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"No fund with code {source_code}")

    return FundDetail(
        source_code=row[0], name=row[1], fund_house=row[2],
        category=row[3], sub_category=row[4],
        latest_nav=float(row[5]) if row[5] is not None else None,
        latest_nav_date=row[6], history_from=row[7], history_to=row[6],
        price_points=row[8] or 0,
    )


@router.get("/funds/{source_code}/meter", response_model=Meter)
def fund_meter(
    source_code: str,
    period: int = Query(3, description=f"Holding period in years: {HOLDING_PERIODS_YEARS}"),
):
    if period not in HOLDING_PERIODS_YEARS:
        raise HTTPException(
            status_code=422,
            detail=f"period must be one of {list(HOLDING_PERIODS_YEARS)}")

    with connect() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT m.shown_period_years, m.pct_strong, m.pct_moderate, m.pct_flat,
                   m.pct_loss, m.window_count, m.scale_used, m.data_start,
                   m.data_end, m.insufficient_history, m.note, m.computed_at
            FROM meter_results m JOIN assets a ON a.id = m.asset_id
            WHERE a.source_code = %s AND m.period_years = %s
        """, (source_code, period))
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No meter for {source_code} at {period}Y. "
                   "The fund may not exist, or the nightly job has not run yet.")

    labels = SCALES[Category(row[6])].labels()
    values = dict(zip(BUCKET_ORDER, (float(row[1]), float(row[2]),
                                     float(row[3]), float(row[4]))))
    buckets = [MeterBucket(key=str(b), label=labels[b], percent=values[b],
                           colour=str(BUCKET_COLOURS[b])) for b in BUCKET_ORDER]

    return Meter(
        source_code=source_code, requested_period_years=period,
        shown_period_years=row[0], buckets=buckets, window_count=row[5],
        scale=row[6], data_start=row[7], data_end=row[8],
        insufficient_history=row[9], note=row[10] or "",
        computed_at=row[11].date() if row[11] else None,
    )
