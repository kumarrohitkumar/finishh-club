"""
CONSTANTS - fixed values that describe the product.

WHAT IS IN HERE
    The four Meter buckets (strong / moderate / flat / loss), the asset
    categories (equity / debt / hybrid / stock), holding periods (1, 3, 5
    years), and the keywords used to work out a fund's category.

WHY IT EXISTS
    These numbers appear in several files. If the number 30 (minimum windows)
    were typed in three places, someone would change two of them one day.
    One place, one value.

THE RULE
    Values here describe the PRODUCT and never change per machine.
    Anything that changes per machine (URLs, timeouts) goes in config.py.

USED BY
    meter/buckets.py, meter/engine.py, adapters/amfi.py, step0.py
"""
from enum import StrEnum
from typing import Final


class Bucket(StrEnum):
    """The four Meter outcome groups. PRD section 6.4."""
    STRONG = "strong"
    MODERATE = "moderate"
    FLAT = "flat"
    LOSS = "loss"


class Category(StrEnum):
    """Decides which Meter scale an asset is judged on. Rule D-5."""
    EQUITY = "equity"
    DEBT = "debt"
    HYBRID = "hybrid"
    STOCK = "stock"


class AssetType(StrEnum):
    """HLD section 1: one table for every kind of asset."""
    FUND = "fund"
    STOCK = "stock"
    INDEX = "index"


class Colour(StrEnum):
    GREEN = "green"
    ORANGE = "orange"
    BLUE = "blue"
    RED = "red"


BUCKET_ORDER: Final[tuple[Bucket, ...]] = (
    Bucket.STRONG, Bucket.MODERATE, Bucket.FLAT, Bucket.LOSS,
)

BUCKET_COLOURS: Final[dict[Bucket, Colour]] = {
    Bucket.STRONG: Colour.GREEN,
    Bucket.MODERATE: Colour.ORANGE,
    Bucket.FLAT: Colour.BLUE,
    Bucket.LOSS: Colour.RED,
}

# --- Meter rules (PRD section 6.3) ---
HOLDING_PERIODS_YEARS: Final[tuple[int, ...]] = (1, 3, 5)
MIN_WINDOWS_FOR_METER: Final[int] = 30          # rule M-9
DAYS_PER_YEAR: Final[float] = 365.25
LEAP_DAY_FALLBACK: Final[int] = 28              # 29 Feb in a non-leap year
PERCENT_TOTAL: Final[float] = 100.0
PERCENT_DECIMALS: Final[int] = 1                # rule M-3

# --- Category detection keywords (rule D-5) ---
HYBRID_KEYWORDS: Final[tuple[str, ...]] = ("hybrid", "balanced", "solution")
DEBT_KEYWORDS: Final[tuple[str, ...]] = ("debt", "liquid", "money market", "gilt", "overnight")
EQUITY_KEYWORDS: Final[tuple[str, ...]] = ("equity", "elss", "index")
UNKNOWN_CATEGORY_DEFAULT: Final[Category] = Category.HYBRID  # middle scale, never an extreme

# --- Ingestion (rule D-4) ---
MAX_SCHEME_COUNT_DROP_RATIO: Final[float] = 0.05
AMFI_DATE_FORMAT: Final[str] = "%d-%m-%Y"

# --- Seed filter (DEPLOYMENT section 1) ---
# These three filters keep the seed set inside Neon's 0.5 GB free tier.
# They limit what is loaded UP FRONT. Anything else is fetched on demand.
SEED_PLAN: Final[str] = "direct"
SEED_OPTION: Final[str] = "growth"
SEED_CATEGORIES: Final[tuple[Category, ...]] = (Category.EQUITY, Category.HYBRID)
SEED_HISTORY_YEARS: Final[int] = 10

# A section heading in the AMFI bulk file starts with one of these.
AMFI_SECTION_PREFIXES: Final[tuple[str, ...]] = (
    "Open Ended", "Close Ended", "Closed Ended", "Interval",
)

# --- Forecast wording, banned (PRD section 6.5) ---
# The Finishh Meter counts past periods. It says nothing about probability.
# These phrases turn a historical count into a prediction, which is wrong and
# is precisely what SEBI regulates. Checked in code, not left to the prompt.
FORECAST_PATTERNS: Final[tuple[str, ...]] = (
    r"\bchance(s)? (of|that)\b",
    r"\bprobability of\b",
    r"\blikely to (rise|fall|return|give|grow|drop)\b",
    r"\bexpected return\b",
    r"\byou (could|can|will|should) (get|expect|earn|receive)\b",
    r"\bwill (return|give|rise|fall|grow|drop)\b",
    r"\brisk of losing\b",
    r"\bodds of\b",
)

# --- Being a good citizen of a free service ---
# mfapi.in is a free, community-run mirror of AMFI data, maintained by one
# person. Firing hundreds of requests at it as fast as the network allows is
# rude and is a good way to get blocked - which would also break our own run.
POLITE_DELAY_SECONDS: Final[float] = 0.4
