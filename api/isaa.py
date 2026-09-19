"""
ISAA ENDPOINT - what the chat box on the website calls.

WHY THE RESPONSE INCLUDES tools_used
    The frontend shows where an answer came from. More importantly, it is the
    evidence trail: every number Isaa states should appear in one of these tool
    results. Returning it makes that checkable from outside the system, not only
    inside the eval.

RATE LIMIT
    One user asking questions is cheap. A page with a bug that calls this in a
    loop is not. The per-session cap is rule N-11 and it is here from the start,
    not added after the first surprise bill.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from isaa.loop import RateLimited, ask

router = APIRouter()

MAX_QUESTION_CHARS = 500
WINDOW_SECONDS = 60
MAX_PER_WINDOW = 10

_recent: list[float] = []


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_CHARS)
    fund_code: str | None = Field(None, description="The fund page the user is on")


class ToolCall(BaseModel):
    tool: str
    args: dict


class AskResponse(BaseModel):
    answer: str
    tools_used: list[ToolCall]
    steps: int
    seconds: float
    disclaimer: str = ("Isaa explains, it does not advise. "
                       "Nothing here is a recommendation to buy or sell.")


def _wait_message(seconds: float) -> str:
    """"Try again in 18001 seconds" is technically true and useless."""
    if seconds < 90:
        return f"Isaa is busy. Try again in about {int(seconds)} seconds."
    if seconds < 3600:
        return f"Isaa is busy. Try again in about {round(seconds / 60)} minutes."
    return (f"Isaa has used up today's free allowance. It resets in about "
            f"{round(seconds / 3600)} hours. Fund data and meters still work.")


def _within_rate_limit() -> bool:
    now = time.time()
    _recent[:] = [t for t in _recent if now - t < WINDOW_SECONDS]
    if len(_recent) >= MAX_PER_WINDOW:
        return False
    _recent.append(now)
    return True


@router.post("/isaa/ask", response_model=AskResponse)
def isaa_ask(body: AskRequest):
    if not _within_rate_limit():
        raise HTTPException(
            status_code=429,
            detail=f"Too many questions. Please wait a moment "
                   f"(limit {MAX_PER_WINDOW} per {WINDOW_SECONDS}s).")

    try:
        turn = ask(body.question, fund_code=body.fund_code)
    except RateLimited as exc:
        # Do not hold the request open for minutes. Tell the caller when to
        # come back and let them decide.
        raise HTTPException(
            status_code=429,
            detail=_wait_message(exc.retry_after),
            headers={"Retry-After": str(int(exc.retry_after))})
    except Exception as exc:
        # Isaa is not on the critical path (HLD section 8). If the model is
        # unavailable the rest of the site must keep working.
        raise HTTPException(
            status_code=503,
            detail=f"Isaa is unavailable right now ({type(exc).__name__}). "
                   "Fund data and meters are unaffected.")

    return AskResponse(
        answer=turn.answer,
        tools_used=[ToolCall(tool=c["tool"], args=c["args"]) for c in turn.tool_calls],
        steps=turn.steps,
        seconds=round(turn.seconds, 2),
    )
