"""
AMFI BULK FILE PARSER - reads the one big file listing every Indian fund.

WHAT THE FILE LOOKS LIKE
    It is not a plain CSV. Category and fund house arrive as HEADING lines, and
    every scheme row below a heading belongs to it until the next heading:

        Open Ended Schemes(Equity Scheme - Large Cap Fund)   <- category
        Axis Mutual Fund                                     <- fund house
        135762;INF846K01WO1;-;Axis Large Cap;Direct Plan;Growth;29.71;17-Sep-2026
        135763;...                                           <- same house

    So the parser carries state as it walks the file. Getting that wrong would
    silently label one AMC's funds as another's - which is why a test checks
    exactly that.

HOW A HEADING IS RECOGNISED
    A line with no semicolons is a heading. If it starts with "Open Ended",
    "Close Ended" or "Interval" it is a CATEGORY heading, and it also resets
    the fund house. Otherwise it is an AMC name.

THE SEED FILTER
    is_wanted() decides what gets loaded up front: Direct plan, Growth option,
    equity or hybrid. This is a storage decision, not a product one - anything
    excluded here can still be fetched on demand later.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from constants import (AMFI_SECTION_PREFIXES, SEED_CATEGORIES, SEED_OPTION,
                       SEED_PLAN, Category)

MIN_FIELDS = 8
NAV_DATE_FORMAT = "%d-%b-%Y"


@dataclass(frozen=True)
class BulkScheme:
    source_code: str
    name: str
    fund_house: str
    category: Category
    sub_category: str
    plan: str
    option: str
    isin: str
    nav: Decimal
    nav_date: date


def _category_of(section: str) -> Category:
    text = section.lower()
    if any(k in text for k in ("hybrid", "balanced", "solution")):
        return Category.HYBRID
    if any(k in text for k in ("debt", "liquid", "money market", "gilt", "overnight")):
        return Category.DEBT
    if any(k in text for k in ("equity", "elss", "index")):
        return Category.EQUITY
    return Category.HYBRID


def _sub_category_of(section: str) -> str:
    """'Open Ended Schemes(Equity Scheme - Large Cap Fund)' -> 'Equity Scheme - Large Cap Fund'"""
    if "(" in section and section.rstrip().endswith(")"):
        return section[section.index("(") + 1:-1].strip()
    return section.strip()


def parse_bulk(lines) -> list[BulkScheme]:
    section, house = "", ""
    out: list[BulkScheme] = []

    for raw in lines:
        line = raw.rstrip("\n").strip()
        if not line:
            continue

        if ";" not in line:
            if line.startswith(AMFI_SECTION_PREFIXES):
                section, house = line, ""      # a new section resets the house
            else:
                house = line
            continue

        parts = [p.strip() for p in line.split(";")]
        if len(parts) < MIN_FIELDS or not parts[0].isdigit():
            continue                           # header row or malformed

        try:
            nav = Decimal(parts[6])
            nav_date = datetime.strptime(parts[7], NAV_DATE_FORMAT).date()
        except (InvalidOperation, ValueError):
            continue                           # rule D-6: skip, never default

        out.append(BulkScheme(
            source_code=parts[0], isin=parts[1], name=parts[3],
            plan=parts[4], option=parts[5], fund_house=house,
            category=_category_of(section), sub_category=_sub_category_of(section),
            nav=nav, nav_date=nav_date,
        ))
    return out


def is_wanted(scheme: BulkScheme) -> bool:
    """The seed filter. Storage decision - see DEPLOYMENT section 1."""
    return (SEED_PLAN in scheme.plan.lower()
            and SEED_OPTION in scheme.option.lower()
            and scheme.category in SEED_CATEGORIES)
