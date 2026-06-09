"""Embedders for semantic-similarity checks.

The default ``HashEmbedder`` is deterministic and dependency-free: tokens are
hashed into a fixed-size bag-of-words vector. It is not a neural embedding,
but it is stable, offline, and good enough to flag "the output drifted a lot"
in CI. Swap in a real embedder by implementing ``embed()``.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class HashEmbedder:
    def __init__(self, dims: int = 256):
        self.dims = dims

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dims
        for token in re.findall(r"\w+", text.lower()):
            digest = hashlib.md5(token.encode()).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        return vec


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0 if norm_a == norm_b else 0.0
    return dot / (norm_a * norm_b)


def similarity(embedder: Embedder, left: str, right: str) -> float:
    return cosine(embedder.embed(left), embedder.embed(right))
