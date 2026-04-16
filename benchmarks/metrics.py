"""Benchmark metrics container and aggregation."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RunMetrics:
    scenario: str
    tool: str
    model: str
    wall_seconds: float
    prompt_tokens: int
    completion_tokens: int
    ttft_seconds: float
    rss_peak_mb: float
    cpu_percent_avg: float
    ok: bool
    error: str | None

    @property
    def completion_tok_per_sec(self) -> float:
        if self.wall_seconds <= 0:
            return 0.0
        return self.completion_tokens / self.wall_seconds


def aggregate(runs: Sequence[RunMetrics]) -> dict[str, float | int]:
    if not runs:
        return {
            "median_wall_seconds": 0.0,
            "median_ttft_seconds": 0.0,
            "median_completion_tok_per_sec": 0.0,
            "peak_rss_mb": 0.0,
            "success_rate": 0.0,
            "n_runs": 0,
        }
    ok_runs = [r for r in runs if r.ok]
    walls = [r.wall_seconds for r in ok_runs] or [0.0]
    ttfts = [r.ttft_seconds for r in ok_runs] or [0.0]
    tps = [r.completion_tok_per_sec for r in ok_runs] or [0.0]
    return {
        "median_wall_seconds": statistics.median(walls),
        "median_ttft_seconds": statistics.median(ttfts),
        "median_completion_tok_per_sec": statistics.median(tps),
        "peak_rss_mb": max((r.rss_peak_mb for r in runs), default=0.0),
        "success_rate": len(ok_runs) / len(runs),
        "n_runs": len(runs),
    }
