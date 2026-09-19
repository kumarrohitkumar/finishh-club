"""
THE API - what the React app talks to.

    uvicorn api.main:app --reload
    http://127.0.0.1:8000/docs       interactive documentation

CORS
    The React app runs on a different port in development and a different
    domain in production, so the browser blocks requests unless the server
    allows that origin. allow_credentials is on because the session cookie must
    travel with each request. Origins are an explicit list - "*" with
    credentials is rejected by browsers and would be unsafe anyway.
    See DEPLOYMENT section 11.
"""
from __future__ import annotations

import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.connection import close_pool, pool

from config import APP_NAME, APP_VERSION

from .funds import router as funds_router
from .isaa import router as isaa_router

# In development the React app is on localhost:5173. In production it is on a
# different domain entirely, so the list has to come from the environment.
#
# It is an explicit list, never "*". A browser rejects "*" together with
# allow_credentials, and allowing any origin to send a session cookie would be
# a real hole once login exists.
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Open the connection pool before the first request rather than during it.

    Without this the first visitor pays ~900 ms for the TLS handshake and for
    waking Neon's compute. With it, that cost lands on startup where nobody is
    waiting."""
    pool()
    yield
    close_pool()


app = FastAPI(
    lifespan=lifespan,
    title="Finishh club API",
    version=APP_VERSION,
    description="Explains Indian mutual funds. Never gives investment advice.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(funds_router, tags=["funds"])
app.include_router(isaa_router, tags=["isaa"])


@app.get("/", tags=["system"])
def root():
    """Opening the bare address should not look like a broken server."""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "list funds": "/funds?limit=20&category=equity&q=large",
            "fund detail": "/funds/{source_code}",
            "finishh meter": "/funds/{source_code}/meter?period=3",
            "ask isaa": "POST /isaa/ask",
            "health": "/health",
        },
    }


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}
