"""Tests for benchmarks.metrics."""
from __future__ import annotations

from benchmarks.metrics import RunMetrics, aggregate


def test_run_metrics_derives_tok_per_sec():
    m = RunMetrics(
        scenario="s1",
        tool="ollama",
        model="qwen2.5-vl:7b",
        wall_seconds=2.0,
        prompt_tokens=10,
        completion_tokens=20,
        ttft_seconds=0.5,
        rss_peak_mb=1024.0,
        cpu_percent_avg=55.5,
        ok=True,
        error=None,
    )
    assert m.completion_tok_per_sec == 10.0


def test_run_metrics_zero_wall_avoids_division():
    m = RunMetrics(
        scenario="s1",
        tool="ollama",
        model="qwen2.5-vl:7b",
        wall_seconds=0.0,
        prompt_tokens=0,
        completion_tokens=0,
        ttft_seconds=0.0,
        rss_peak_mb=0.0,
        cpu_percent_avg=0.0,
        ok=False,
        error="timeout",
    )
    assert m.completion_tok_per_sec == 0.0


def test_aggregate_computes_medians():
    runs = [
        RunMetrics("s1", "ollama", "m", 1.0, 10, 10, 0.2, 100.0, 50.0, True, None),
        RunMetrics("s1", "ollama", "m", 2.0, 10, 20, 0.3, 200.0, 60.0, True, None),
        RunMetrics("s1", "ollama", "m", 3.0, 10, 30, 0.4, 300.0, 70.0, True, None),
    ]
    agg = aggregate(runs)
    assert agg["median_wall_seconds"] == 2.0
    assert agg["median_ttft_seconds"] == 0.3
    assert agg["success_rate"] == 1.0


def test_aggregate_handles_failures_in_success_rate():
    runs = [
        RunMetrics("s1", "ollama", "m", 1.0, 10, 10, 0.2, 100.0, 50.0, True, None),
        RunMetrics("s1", "ollama", "m", 0.0, 0, 0, 0.0, 0.0, 0.0, False, "x"),
    ]
    agg = aggregate(runs)
    assert agg["success_rate"] == 0.5


def test_aggregate_empty_returns_zeros():
    agg = aggregate([])
    assert agg == {
        "median_wall_seconds": 0.0,
        "median_ttft_seconds": 0.0,
        "median_completion_tok_per_sec": 0.0,
        "peak_rss_mb": 0.0,
        "success_rate": 0.0,
        "n_runs": 0,
    }
