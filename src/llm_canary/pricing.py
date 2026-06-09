"""Rough per-model price table for cost estimation (USD per 1M tokens).

Estimates are good enough for CI budget gates; exact billing always comes
from the provider's invoice.
"""

from __future__ import annotations

# (input_per_1m, output_per_1m), matched by longest model-name prefix
PRICES: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1": (2.00, 8.00),
    "o3": (2.00, 8.00),
    "claude-opus": (15.00, 75.00),
    "claude-sonnet": (3.00, 15.00),
    "claude-haiku": (0.80, 4.00),
    "echo": (0.0, 0.0),
    "fixture": (0.0, 0.0),
}

DEFAULT_PRICE = (1.00, 2.00)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = DEFAULT_PRICE
    best = -1
    for prefix, pair in PRICES.items():
        if model.startswith(prefix) and len(prefix) > best:
            best = len(prefix)
            price_in, price_out = pair
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def estimate_tokens(text: str) -> int:
    """Cheap deterministic token estimate (~4 chars per token)."""
    return max(1, len(text) // 4)
