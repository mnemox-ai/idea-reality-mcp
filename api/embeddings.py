"""Semantic embeddings for score_history (P1: activate the query-log moat).

The scorer's similarity/duplicate detection historically matched idea_text with
SQL LIKE on a handful of keywords — it misses paraphrases ("app to split bills"
vs "expense sharing tool"). This module adds semantic embeddings so similarity is
computed in vector space instead.

Design (kept deliberately simple for the ~10k-row scale):
- Provider: OpenAI `text-embedding-3-small` (1536-d, ~$0.02 / 1M tokens). Called
  over plain httpx — no SDK — to match the rest of the codebase.
- Storage: a packed float32 BLOB per row (1536 * 4 = 6 KB). Portable across Turso
  (libSQL) and the local SQLite fallback; no dependency on a vector extension.
- Search: brute-force cosine over all stored vectors in NumPy. At 10k rows this is
  a single ~10k x 1536 matmul (< ~50 ms). If the corpus ever reaches 6 figures,
  swap this for Turso's native F32_BLOB + vector_distance_cos index — the storage
  format is already a float32 blob, so that migration is additive.

Env:
- OPENAI_API_KEY   (required to compute embeddings; absent -> functions raise/skip)
- EMBED_MODEL      (optional, default 'text-embedding-3-small')
"""

from __future__ import annotations

import os
import struct
from typing import Sequence

import httpx

EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = 1536  # text-embedding-3-small native dimension
_OPENAI_URL = "https://api.openai.com/v1/embeddings"
_MAX_BATCH = 2048  # OpenAI hard cap on inputs per request
_TIMEOUT = 60.0


class EmbeddingError(RuntimeError):
    """Raised when the embedding provider is unavailable or returns a bad payload."""


def embeddings_enabled() -> bool:
    """True if an API key is configured. Callers should degrade gracefully when False."""
    return bool(os.environ.get("OPENAI_API_KEY"))


def embed_texts(texts: Sequence[str], *, timeout: float = _TIMEOUT) -> list[list[float]]:
    """Embed a batch of texts. Returns one vector per input, in order.

    Splits into <=2048-input requests. Raises EmbeddingError on any failure so the
    caller decides whether to retry or skip (we never want a silent partial batch).
    """
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EmbeddingError("OPENAI_API_KEY not set")
    # OpenAI rejects empty strings; substitute a single space so indices stay aligned.
    cleaned = [(t if t and t.strip() else " ") for t in texts]

    out: list[list[float]] = []
    with httpx.Client(timeout=timeout) as client:
        for start in range(0, len(cleaned), _MAX_BATCH):
            chunk = cleaned[start : start + _MAX_BATCH]
            resp = client.post(
                _OPENAI_URL,
                headers={"Authorization": f"Bearer {key}"},
                json={"model": EMBED_MODEL, "input": chunk},
            )
            if resp.status_code != 200:
                raise EmbeddingError(f"embeddings HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json().get("data")
            if not isinstance(data, list) or len(data) != len(chunk):
                raise EmbeddingError("embeddings response shape mismatch")
            # API guarantees data is returned in input order, but sort on index to be safe.
            for item in sorted(data, key=lambda d: d.get("index", 0)):
                vec = item.get("embedding")
                if not isinstance(vec, list) or len(vec) != EMBED_DIM:
                    raise EmbeddingError("embedding vector shape mismatch")
                out.append(vec)
    return out


def embed_one(text: str, *, timeout: float = _TIMEOUT) -> list[float]:
    """Embed a single text -> one vector."""
    return embed_texts([text], timeout=timeout)[0]


def pack_embedding(vec: Sequence[float]) -> bytes:
    """Pack a float vector into a compact little-endian float32 BLOB."""
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack_embedding(blob: bytes) -> list[float]:
    """Inverse of pack_embedding."""
    if not blob:
        return []
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))
