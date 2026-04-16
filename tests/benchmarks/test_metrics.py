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


# ---------- E1-E3: coverage gaps found in Task 7 code review ----------


def test_aggregate_peak_rss_and_tok_per_sec_and_n_runs():
    """E1+E2: peak_rss_mb is max over runs, median tok/s is derived,
    n_runs is the total count — previously only success_rate and wall/ttft
    medians were pinned."""
    runs = [
        RunMetrics("s1", "ollama", "m", 1.0, 10, 10, 0.2, 100.0, 50.0, True, None),
        RunMetrics("s1", "ollama", "m", 2.0, 10, 20, 0.3, 200.0, 60.0, True, None),
        RunMetrics("s1", "ollama", "m", 3.0, 10, 30, 0.4, 300.0, 70.0, True, None),
    ]
    agg = aggregate(runs)
    assert agg["peak_rss_mb"] == 300.0
    # completion_tok_per_sec values: 10/1, 20/2, 30/3 = 10, 10, 10 → median 10
    assert agg["median_completion_tok_per_sec"] == 10.0
    assert agg["n_runs"] == 3


def test_aggregate_peak_rss_includes_failed_runs():
    """E1 asymmetry: peak_rss_mb takes max over ALL runs (including failed),
    while medians use ok-only. Locks the current design so a future refactor
    can't silently switch peak_rss to ok-only."""
    runs = [
        RunMetrics("s1", "ollama", "m", 1.0, 10, 10, 0.2, 100.0, 50.0, True, None),
        # Failed run with higher RSS (crashed after allocating memory)
        RunMetrics("s1", "ollama", "m", 0.0, 0, 0, 0.0, 999.0, 0.0, False, "oom"),
    ]
    agg = aggregate(runs)
    assert agg["peak_rss_mb"] == 999.0
    assert agg["n_runs"] == 2


def test_aggregate_all_failed_runs_falls_back_to_zero_medians():
    """E3: when every run failed, ok_runs is empty; the `or [0.0]` fallback
    in aggregate() must kick in so medians become 0.0 without raising
    statistics.StatisticsError on an empty sequence."""
    runs = [
        RunMetrics("s1", "ollama", "m", 0.0, 0, 0, 0.0, 0.0, 0.0, False, "err1"),
        RunMetrics("s1", "ollama", "m", 0.0, 0, 0, 0.0, 0.0, 0.0, False, "err2"),
        RunMetrics("s1", "ollama", "m", 0.0, 0, 0, 0.0, 0.0, 0.0, False, "err3"),
    ]
    agg = aggregate(runs)
    assert agg["success_rate"] == 0.0
    assert agg["n_runs"] == 3
    # Fallback medians must all be 0.0, not a StatisticsError
    assert agg["median_wall_seconds"] == 0.0
    assert agg["median_ttft_seconds"] == 0.0
    assert agg["median_completion_tok_per_sec"] == 0.0
