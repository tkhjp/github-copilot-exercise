"""Scenario S1: text-only short prompt, baseline latency/throughput."""
from __future__ import annotations

from dataclasses import dataclass

from benchmarks.metrics import RunMetrics
from benchmarks.scenarios.base import ChatAdapter, ScenarioResult

_PROMPT = (
    "Translate the following Japanese sentence to English in one line: "
    "今日は良い天気ですね。"
)


@dataclass
class S1TextOnly:
    tool: str
    model: str
    n_runs: int = 3

    def run(self, adapter: ChatAdapter) -> ScenarioResult:
        runs: list[RunMetrics] = []
        for _ in range(self.n_runs):
            try:
                result = adapter.chat_text(_PROMPT)
                runs.append(RunMetrics(
                    scenario="s1",
                    tool=self.tool,
                    model=self.model,
                    wall_seconds=result.wall_seconds,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    ttft_seconds=0.0,  # non-streaming: TTFT not measured here
                    rss_peak_mb=0.0,   # populated by harness via psutil
                    cpu_percent_avg=0.0,
                    ok=True,
                    error=None,
                ))
            except Exception as exc:  # noqa: BLE001
                runs.append(RunMetrics(
                    scenario="s1",
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
            scenario_name="s1",
            tool=self.tool,
            model=self.model,
            runs=runs,
        )
