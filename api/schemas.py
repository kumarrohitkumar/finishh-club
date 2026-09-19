"""
API RESPONSE SHAPES - what the React app receives.

WHY PYDANTIC MODELS AND NOT PLAIN DICTS
    They are checked. If a query stops returning `latest_nav`, the response
    fails here rather than reaching the frontend as `undefined` and showing a
    blank where a number should be.

    They also document the API for free - FastAPI turns these into OpenAPI docs
    at /docs.

TWO PRODUCT RULES LIVE IN THESE SHAPES
    F-4  every figure carries `source` and a date. Not optional extras
    M-6  a meter always carries the `scale` it was judged on, and every bucket
         carries its `label`. Without them a user compares a debt meter to an
         equity meter and draws the wrong conclusion
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class FundSummary(BaseModel):
    source_code: str
    name: str
    fund_house: str
    category: str
    sub_category: str


class FundList(BaseModel):
    items: list[FundSummary]
    total: int
    limit: int
    offset: int


class FundDetail(BaseModel):
    source_code: str
    name: str
    fund_house: str
    category: str
    sub_category: str
    latest_nav: float | None = Field(None, description="None means not available (rule F-6)")
    latest_nav_date: date | None
    history_from: date | None
    history_to: date | None
    price_points: int
    source: str = "AMFI"


class MeterBucket(BaseModel):
    key: str
    label: str
    percent: float
    colour: str


class Meter(BaseModel):
    source_code: str
    requested_period_years: int
    shown_period_years: int
    buckets: list[MeterBucket]
    window_count: int
    scale: str
    data_start: date | None
    data_end: date | None
    insufficient_history: bool
    note: str = ""
    computed_at: date | None
    source: str = "AMFI"
    disclaimer: str = ("These are historical rolling periods, not a prediction. "
                       "Past performance does not indicate future returns.")
