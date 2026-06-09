"""Provider protocol and completion record."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from llm_canary.config import ProviderSpec


@dataclass
class Completion:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class Provider(ABC):
    def __init__(self, spec: ProviderSpec):
        self.spec = spec

    @abstractmethod
    def complete(self, prompt: str) -> Completion: ...
