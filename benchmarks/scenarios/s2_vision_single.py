"""Scenario S2: describe a single image, measuring vision encoder cost."""
from __future__ import annotations

from dataclasses import dataclass

from benchmarks.metrics import RunMetrics
from benchmarks.scenarios.base import ChatAdapter, ScenarioResult

_PROMPT = (
    "この画像を構造的に記述してください。"
    "含まれるテキスト（OCR）・図の構造・色とレイアウト・主要な視覚要素を"
    "網羅し、日本語で詳細に出力してください。"
)


@dataclass
class S2VisionSingle:
    tool: str
    model: str
    image_bytes: bytes
    mime_type: str
    n_runs: int = 3

    def __post_init__(self) -> None:
        if not self.image_bytes:
            raise ValueError("image_bytes must be non-empty")

    def run(self, adapter: ChatAdapter) -> ScenarioResult:
        runs: list[RunMetrics] = []
        for _ in range(self.n_runs):
            try:
                result = adapter.chat_vision(
                    prompt=_PROMPT,
                    image_bytes=self.image_bytes,
                    mime_type=self.mime_type,
                )
                runs.append(RunMetrics(
                    scenario="s2",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=result.wall_seconds,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    ttft_seconds=0.0,
                    rss_peak_mb=0.0,
                    cpu_percent_avg=0.0,
                    ok=True,
                    error=None,
                ))
            except Exception as exc:  # noqa: BLE001
                runs.append(RunMetrics(
                    scenario="s2",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=0.0,
                    prompt_tokens=0,
                    completion_tokens=0,
                    ttft_seconds=0.0,
                    rss_peak_mb=0.0,
                    cpu_percent_avg=0.0,
                    ok=False,
                    error=str(exc),
                ))
        return ScenarioResult(
            scenario_name="s2",
            tool=self.tool,
            model=self.model,
            runs=runs,
        )
