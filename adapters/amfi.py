"""
AMFI ADAPTER - fetches Indian mutual fund data.

WHAT IT DOES
    Given a scheme code, returns the fund's details and its full NAV history as
    PriceRecord objects.

WHERE THE DATA COMES FROM
    AMFI (Association of Mutual Funds in India) publishes NAV for every Indian
    mutual fund, free, every day.

    Step 0 uses mfapi.in, a community mirror, because it returns one fund's
    entire history in a single request - ideal for testing the idea.
    Step 2 will switch to AMFI's official bulk files for the real backfill.
    The interface does not change, which is the point of having one.

TWO THINGS IT DECIDES
    1. Category (rule D-5). AMFI gives text like "Equity Scheme - Large Cap
       Fund". We map that to equity, debt or hybrid, which picks the Meter
       scale. Hybrid is checked FIRST, because hybrid scheme names often also
       contain the words "equity" or "debt".

    2. Bad rows (rule D-6). A NAV of zero, "N.A." or an unreadable date is
       skipped and counted - never written as zero. A zero NAV would look like
       a total loss to the Meter.

USED BY
    step0.py now. The daily ingestion job later.
"""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from config import AMFI_API_BASE
from constants import (AMFI_DATE_FORMAT, DEBT_KEYWORDS, EQUITY_KEYWORDS,
                       HYBRID_KEYWORDS, UNKNOWN_CATEGORY_DEFAULT, AssetType,
                       Category)

from net import fetch

from .base import AssetInfo, PriceRecord


def _category_of(scheme_category: str, scheme_type: str) -> Category:
    """Map AMFI's category text to a Meter scale (rule D-5).

    Order matters: "hybrid" is checked first because a hybrid scheme's text
    often also contains "equity" or "debt".
    """
    text = f"{scheme_category} {scheme_type}".lower()
    for keywords, category in (
        (HYBRID_KEYWORDS, Category.HYBRID),
        (DEBT_KEYWORDS, Category.DEBT),
        (EQUITY_KEYWORDS, Category.EQUITY),
    ):
        if any(k in text for k in keywords):
            return category
    return UNKNOWN_CATEGORY_DEFAULT


class AmfiAdapter:
    def _get(self, code: str) -> dict:
        return json.loads(fetch(f"{AMFI_API_BASE}/{code}"))

    def fetch_asset(self, source_code: str) -> AssetInfo:
        m = self._get(source_code)["meta"]
        return AssetInfo(
            source_code=str(m["scheme_code"]),
            name=m["scheme_name"],
            fund_house=m.get("fund_house", ""),
            category=_category_of(m.get("scheme_category", ""), m.get("scheme_type", "")),
            sub_category=m.get("scheme_category", ""),
            asset_type=AssetType.FUND,
        )

    def fetch_history(self, source_code: str) -> list[PriceRecord]:
        out, skipped = [], 0
        for row in self._get(source_code)["data"]:
            try:
                nav = Decimal(row["nav"])
                if nav <= 0:                       # rule D-6: skip, never default to zero
                    skipped += 1
                    continue
                out.append(PriceRecord(
                    source_code=str(source_code),
                    price_date=datetime.strptime(row["date"], AMFI_DATE_FORMAT).date(),
                    price=nav,
                ))
            except (InvalidOperation, ValueError, KeyError):
                skipped += 1
        out.sort(key=lambda r: r.price_date)
        if skipped:
            print(f"  [skipped {skipped} unusable rows]")
        return out
