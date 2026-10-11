"""
EMBEDDINGS - the one place that knows how text becomes a vector.

WHAT IT DOES
    embed(["what is a SIP", ...]) -> [[0.012, -0.44, ...], ...]

WHY IT IS ITS OWN FILE (HLD section 2.5)
    Every other module asks for "the embedding of this text" and is told
    nothing about who produced it - same reasoning as adapters/base.py, where
    nothing downstream learns which website a price came from.

    Switching provider then means editing this file and re-embedding, rather
    than hunting for a model name scattered across the pipeline, the search and
    the eval.

THE DIMENSION IS A CONTRACT, NOT A SETTING
    The documents column is VECTOR(1536). A model that returns 768 or 3072 will
    not store, so a mismatch is checked HERE, with a message that says what to
    do, rather than surfacing as a psycopg error three layers away.

WHY THE KEY IS READ AT CALL TIME
    config.py reads environment variables when it is IMPORTED, which can happen
    before .env.local is loaded. isaa/loop.py already works around this the same
    way. The model name is safe to take from config because it has a default;
    the key is not, because an empty one silently disables search.

DEGRADING, NOT CRASHING
    No key, no openai package, or the API being down raises EmbeddingUnavailable
    rather than a provider-specific exception. knowledge/search.py catches it
    and falls back to keyword search, so a missing key costs quality, never
    uptime. This is the same rule as HLD section 8 for Isaa itself.

    python -m knowledge.embed "test that the key works"
"""
from __future__ import annotations

import os
import sys

from config import EMBEDDING_MODEL
from constants import EMBEDDING_DIMENSIONS

# OpenAI accepts far more per request than this. The limit that matters is
# tokens, not rows, and DRHP chunks in Phase B are much longer than a concept
# document - so the batch is sized for the long case, not the short one.
MAX_BATCH = 128


class EmbeddingUnavailable(RuntimeError):
    """No key, no package, or the provider refused. Callers fall back."""


def _api_key() -> str:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local", override=True)
    return os.getenv("OPENAI_API_KEY", "")


def available() -> bool:
    """Cheap check, so callers can choose a path without catching exceptions."""
    return bool(_api_key())


def _client():
    try:
        from openai import OpenAI
    except ImportError as exc:                      # pragma: no cover
        raise EmbeddingUnavailable(
            "the openai package is not installed - pip install -r requirements.txt"
        ) from exc

    key = _api_key()
    if not key:
        raise EmbeddingUnavailable(
            "OPENAI_API_KEY is not set. Put it in .env.local. "
            "Without it, search falls back to keywords only.")
    return OpenAI(api_key=key)


def embed(texts: list[str], model: str = EMBEDDING_MODEL) -> list[list[float]]:
    """Embed many texts, in order. One API call per MAX_BATCH."""
    if not texts:
        return []

    client = _client()
    vectors: list[list[float]] = []

    for start in range(0, len(texts), MAX_BATCH):
        batch = texts[start:start + MAX_BATCH]
        try:
            response = client.embeddings.create(model=model, input=batch)
        except Exception as exc:                    # provider-specific, not ours
            raise EmbeddingUnavailable(
                f"{type(exc).__name__}: {exc}") from exc

        # The API documents that results come back in input order, but the
        # answer is wrong in a way nobody would see if it ever did not - a
        # document would silently carry another document's meaning.
        for item in sorted(response.data, key=lambda d: d.index):
            vector = list(item.embedding)
            if len(vector) != EMBEDDING_DIMENSIONS:
                raise EmbeddingUnavailable(
                    f"{model} returned {len(vector)} dimensions, but the "
                    f"documents column is VECTOR({EMBEDDING_DIMENSIONS}). "
                    f"Changing model means a migration and re-embedding "
                    f"every row - see docs/R2_HLD.md section 2.5.")
            vectors.append(vector)

    return vectors


def embed_one(text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    return embed([text], model)[0]


def to_pgvector(vector: list[float]) -> str:
    """psycopg does not know what a vector is, so it travels as text and is
    cast in the query: %s::vector. Keeping the format in one function means
    the pipeline and the search can never disagree about it."""
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"


if __name__ == "__main__":
    probe = sys.argv[1] if len(sys.argv) > 1 else "does the embedding key work"
    try:
        vector = embed_one(probe)
    except EmbeddingUnavailable as exc:
        print(f"unavailable: {exc}")
        sys.exit(1)
    print(f"model      {EMBEDDING_MODEL}")
    print(f"dimensions {len(vector)}")
    print(f"first four {[round(x, 4) for x in vector[:4]]}")
