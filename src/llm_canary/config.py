"""YAML suite / policy specifications."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class AssertionSpec(BaseModel):
    """A single assertion on a model output.

    ``type`` selects the assertion from the registry; remaining fields are
    assertion-specific (kept open via ``extra="allow"``).
    """

    model_config = ConfigDict(extra="allow")

    type: str
    value: Any = None
    threshold: float | None = None

    def param(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class CaseSpec(BaseModel):
    name: str
    prompt: str
    vars: dict[str, Any] = Field(default_factory=dict)
    assertions: list[AssertionSpec] = Field(default_factory=list)

    def rendered_prompt(self) -> str:
        return self.prompt.format(**self.vars) if self.vars else self.prompt


class ProviderSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = "echo"
    model: str = ""
    options: dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> str:
        return f"{self.name}:{self.model}" if self.model else self.name


class SuiteSpec(BaseModel):
    name: str = "canary"
    providers: list[ProviderSpec] = Field(default_factory=lambda: [ProviderSpec()])
    judge: ProviderSpec | None = None
    cases: list[CaseSpec] = Field(default_factory=list)


class TracePolicy(BaseModel):
    """Policy applied to an agent trace (JSONL of steps)."""

    max_steps: int | None = None
    max_cost_usd: float | None = None
    forbidden_tools: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_order: list[str] = Field(default_factory=list)
    max_tool_repeats: int | None = None


def load_suite(path: str | Path) -> SuiteSpec:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return SuiteSpec.model_validate(data)


def load_policy(path: str | Path) -> TracePolicy:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return TracePolicy.model_validate(data)
