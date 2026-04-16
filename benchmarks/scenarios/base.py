"""Base classes for benchmark scenarios."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from benchmarks.metrics import RunMetrics


class ChatAdapter(Protocol):
    def chat_text(self, prompt: str): ...  # noqa: E704
    def chat_vision(self, prompt: str, image_bytes: bytes, mime_type: str): ...  # noqa: E704


@dataclass(frozen=True)
class ScenarioResult:
    scenario_name: str
    tool: str
    model: str
    runs: list[RunMetrics] = field(default_factory=list)
