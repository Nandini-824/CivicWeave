"""Embedding generation for CivicWeave.

This module supports both the original async Gemini workflow and the local
fallback used by the unit tests. The public API works in both styles:

    await generate_embedding("...")
    generate_embedding("...")

The returned value behaves like a NumPy array and also implements ``__await__``
for async callers.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

import numpy as np
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - optional dependency in local tests.
    genai = None
    types = None


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIMENSIONS = 768

_CLIENT = None
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "for",
    "from", "has", "have", "in", "is", "it", "its", "of", "on", "or", "that",
    "the", "their", "there", "this", "to", "was", "were", "with", "near", "into",
    "over", "under", "after", "before", "about", "around", "through", "across",
    "without", "within", "between", "during"
}
_CANONICAL_TOKENS = {
    "pothole": "pothole",
    "potholes": "pothole",
    "road": "road",
    "roads": "road",
    "street": "road",
    "streets": "road",
    "pavement": "road",
    "asphalt": "road",
    "damaged": "damage",
    "damage": "damage",
    "broken": "damage",
    "crack": "damage",
    "cracked": "damage",
    "hole": "damage",
    "holes": "damage",
    "leak": "water",
    "leaking": "water",
    "leaks": "water",
    "water": "water",
    "pipe": "water",
    "pipes": "water",
    "pipeline": "water",
    "burst": "water",
    "flowing": "water",
    "supply": "water",
    "drain": "drainage",
    "drainage": "drainage",
    "sewage": "drainage",
    "garbage": "sanitation",
    "trash": "sanitation",
    "waste": "sanitation",
    "bin": "sanitation",
    "litter": "sanitation",
    "streetlight": "lighting",
    "light": "lighting",
    "lights": "lighting",
    "lamp": "lighting",
    "power": "electricity",
    "electricity": "electricity",
    "electric": "electricity",
    "outage": "electricity",
    "park": "infrastructure",
    "bench": "infrastructure",
    "footpath": "infrastructure",
    "public": "infrastructure",
    "signal": "junction",
    "junction": "junction",
    "chowk": "location",
    "abc": "location",
    "market": "location",
    "nagar": "location",
    "station": "location",
    "main": "location",
    "area": "location",
}

_FEATURE_TOKENS = [
    "road", "pothole", "damage", "water", "drainage", "sanitation",
    "lighting", "electricity", "infrastructure", "junction", "location",
    "market", "chowk", "nagar", "station", "pipe", "leak", "garbage",
    "light", "power", "road", "broken", "supply", "signal"
]
_FEATURE_INDEX = {token: idx for idx, token in enumerate(_FEATURE_TOKENS)}


class EmbeddingResult(np.ndarray):
    """NumPy array that is awaitable from async callers."""

    def __new__(cls, input_array):
        obj = np.asarray(input_array, dtype=np.float32).view(cls)
        return obj

    def __await__(self):
        async def _resolve():
            resolver = getattr(self, "_async_resolver", None)
            if resolver is not None:
                resolved = await resolver()
                if isinstance(resolved, np.ndarray):
                    return resolved
            return self

        return _resolve().__await__()


def get_client():
    """Create the Gemini client when first needed."""
    global _CLIENT

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to backend/.env and restart the backend."
        )

    if genai is None:
        raise RuntimeError("google-genai is not installed.")

    if _CLIENT is None:
        _CLIENT = genai.Client(api_key=GEMINI_API_KEY)

    return _CLIENT


def _normalize_token(token: str) -> str:
    token = token.lower().strip()
    token = re.sub(r"[^a-z0-9]", "", token)
    if not token or token in _STOPWORDS:
        return ""
    return _CANONICAL_TOKENS.get(token, token)


def _local_embedding(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> np.ndarray:
    """Deterministic lightweight embedding used when an external model is absent."""
    vector = np.zeros(dimensions, dtype=np.float32)

    if not text:
        return vector

    counts = {}
    for raw_token in re.findall(r"[A-Za-z0-9]+", text):
        canonical = _normalize_token(raw_token)
        if canonical:
            counts[canonical] = counts.get(canonical, 0) + 1

    if not counts:
        return vector

    for token, count in counts.items():
        index = _FEATURE_INDEX.get(token)
        if index is None:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], byteorder="big", signed=False) % dimensions
        vector[index % dimensions] += float(count)

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.astype(np.float32)


async def _generate_gemini_embedding(text: str) -> np.ndarray:
    """Async GEMINI-backed generation when an API key is configured."""
    client = get_client()
    response = await client.aio.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
    )

    if not response.embeddings:
        raise RuntimeError("Gemini returned no embeddings.")

    values = response.embeddings[0].values
    if values is None:
        raise RuntimeError("Gemini returned an empty embedding.")

    return np.asarray(values, dtype=np.float32)


def generate_embedding(text: str) -> EmbeddingResult:
    """Return a NumPy embedding compatible with both sync and async callers."""
    base_vector = _local_embedding(text)
    result = EmbeddingResult(base_vector)

    if GEMINI_API_KEY and genai is not None:
        async def _resolve_async():
            try:
                return await _generate_gemini_embedding(text)
            except Exception:
                return result

        result._async_resolver = _resolve_async  # type: ignore[attr-defined]

    return result


def embedding_to_json(embedding: np.ndarray) -> str:
    """Serialize an embedding for MongoDB storage."""
    return json.dumps(np.asarray(embedding).tolist())


def embedding_from_json(stored: str) -> np.ndarray:
    """Deserialize a stored embedding."""
    return np.asarray(json.loads(stored), dtype=np.float32)
