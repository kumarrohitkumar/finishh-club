"""
ADAPTER INTERFACE - the shape every data source must fit.

WHAT IT DOES
    Defines three things:
      PriceRecord    one price on one date
      AssetInfo      a fund's name, house and category
      SourceAdapter  the two methods every source must provide

WHY IT EXISTS
    This is extension point 1 from the HLD. Today prices come from AMFI.
    Later they come from NSE for stocks, or a paid provider.

    Because every source returns the same PriceRecord, nothing downstream has
    to change. The Meter engine, the database and Isaa never learn where a
    price came from.

        AMFI   -> PriceRecord -+
        NSE    -> PriceRecord -+--> everything else, unchanged
        paid   -> PriceRecord -+

    Adding a source means writing one new class here. If it ever means changing
    something else, the design was wrong.

USED BY
    adapters/amfi.py implements it. step0.py consumes it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from constants import AssetType, Category


@dataclass(frozen=True)
class PriceRecord:
    source_code: str
    price_date: date
    price: Decimal


@dataclass(frozen=True)
class AssetInfo:
    source_code: str
    name: str
    fund_house: str
    category: Category     # picks the Meter scale
    sub_category: str
    asset_type: AssetType = AssetType.FUND


class SourceAdapter(Protocol):
    def fetch_asset(self, source_code: str) -> AssetInfo: ...
    def fetch_history(self, source_code: str) -> list[PriceRecord]: ...
