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


# --- Hybrid search (R2 Phase A, rules HS-1 to HS-8) ---
# The vector width. It is a PRODUCT value, not a machine one: the database
# column is VECTOR(1536) and an embedding of a different width simply will not
# store. Changing this means a migration and re-embedding every row, which is
# why it lives next to the column definition rather than in config.py.
EMBEDDING_DIMENSIONS: Final[int] = 1536

# Reciprocal Rank Fusion. A document scores by its POSITION in each ranked
# list, never by the raw score, because ts_rank and cosine similarity are not
# comparable numbers:
#
#       score(doc) = sum over lists of  weight / (RRF_K + rank)
#
# k decides how fast the reward decays with rank. Low k makes the top result
# dominate; high k flattens the lists towards equality. 60 is the value from
# the original RRF paper and the usual starting point.
#
# Rule HS-5 asks for one tunable number. This is it - with the weights below
# as the finer adjustment. Both are arguments to the search functions, so the
# eval can sweep them instead of anyone guessing.
RRF_K: Final[int] = 60
RRF_WEIGHTS: Final[dict[str, float]] = {"lexical": 1.0, "semantic": 1.0}

# Rule HS-7. Vector search ALWAYS returns its nearest neighbours, however far
# away they are - "nothing matched" is not a thing it can say. Without a floor,
# a question about cricket returns the three least-unrelated finance documents
# and Isaa answers from them.
#
# Cosine similarity, so 1.0 is identical and 0.0 is unrelated. Measured against
# the eval set, not guessed: raise it until unrelated questions return nothing,
# stop before real questions start being dropped.
MIN_SEMANTIC_SIMILARITY: Final[float] = 0.30

# Each half searches wider than the final answer, because a document ranked 8th
# by keywords and 2nd by vectors should still be able to win the fusion. If
# both lists were cut to 3 first, that document would never be seen.
CANDIDATE_MULTIPLIER: Final[int] = 4
MIN_CANDIDATES: Final[int] = 10
