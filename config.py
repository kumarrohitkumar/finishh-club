"""
CONFIG - settings that can differ per machine.

WHAT IS IN HERE
    The AMFI web addresses, how long to wait for a response, how many times to
    retry, and display settings.

WHY IT EXISTS
    These change between your laptop, a test server and production. Every value
    is read from an environment variable with a sensible default, so nothing has
    to be edited in code to run somewhere else.

        export HTTP_TIMEOUT_SECONDS=90     # no code change needed

THE RULE
    Settings that change per machine live here.
    Values that describe the product live in constants.py.

USED BY
    adapters/amfi.py, step0.py
"""
import os
from typing import Final


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


APP_NAME: Final[str] = "finishh-club"
APP_VERSION: Final[str] = "0.1.0"

# --- LLM (Groq for now; see docs on switching to OpenAI) ---
GROQ_API_KEY: Final[str] = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: Final[str] = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# --- Database ---
# Neon gives you this string. Put it in .env, never in code.
#   postgresql://user:password@host.neon.tech/dbname?sslmode=require
DATABASE_URL: Final[str] = os.getenv("DATABASE_URL", "")
DB_CONNECT_TIMEOUT_SECONDS: Final[int] = _int("DB_CONNECT_TIMEOUT_SECONDS", 15)

# --- Data sources ---
AMFI_API_BASE: Final[str] = os.getenv("AMFI_API_BASE", "https://api.mfapi.in/mf")
AMFI_NAV_ALL_URL: Final[str] = os.getenv(
    "AMFI_NAV_ALL_URL", "https://portal.amfiindia.com/spages/NAVAll.txt")

# --- HTTP ---
HTTP_TIMEOUT_SECONDS: Final[int] = _int("HTTP_TIMEOUT_SECONDS", 45)
HTTP_MAX_RETRIES: Final[int] = _int("HTTP_MAX_RETRIES", 3)
USER_AGENT: Final[str] = os.getenv("USER_AGENT", f"{APP_NAME}/{APP_VERSION}")

# --- Display ---
METER_BAR_WIDTH: Final[int] = _int("METER_BAR_WIDTH", 46)
DEFAULT_SCHEME_CODE: Final[str] = os.getenv("DEFAULT_SCHEME_CODE", "119528")
