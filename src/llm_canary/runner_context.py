"""Shared context handed to assertions (embedder, judge provider)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from llm_canary.semantic import Embedder, HashEmbedder

if TYPE_CHECKING:
    from llm_canary.providers.base import Provider


@dataclass
class RunContext:
    embedder: Embedder = field(default_factory=HashEmbedder)
    judge_provider: Provider | None = None
