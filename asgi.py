"""
ASGI ENTRY POINT for serverless hosting (Vercel).

WHY THIS FILE EXISTS
    Vercel's Python runtime treats every .py under api/ as its own function.
    Our api/ is a package, not a folder of functions, so everything is routed
    to this single file instead and FastAPI does its own routing.

KNOWN LIMITATION OF SERVERLESS FOR THIS APP
    Two things fit badly:

    1. The connection pool is pointless. Each cold invocation is a new process,
       so it pays the ~700 ms connection cost again. Neon's pooled endpoint
       softens this but does not remove it.
    2. Isaa can take 45-60 seconds on the smaller model, and Vercel's hobby
       plan caps a function at 60 seconds. Some Isaa requests will time out.

    Fund browsing and the Meter are plain reads and are fine. A long-running
    host (Render, Fly, a VPS) remains the better home for this API - see
    render.yaml. This file exists so the app can be live today.
"""
from api.main import app  # noqa: F401  - Vercel looks for `app`
