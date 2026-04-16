"""Tests for benchmark scenarios."""
from __future__ import annotations

from unittest.mock import MagicMock

from benchmarks.scenarios.base import ScenarioResult
from benchmarks.scenarios.s1_text_only import S1TextOnly


def test_s1_text_only_runs_once_and_returns_metrics():
    fake_adapter = MagicMock()
    fake_adapter.chat_text.return_value = MagicMock(
        content="abc",
        prompt_tokens=5,
        completion_tokens=3,
        wall_seconds=0.5,
    )
    scenario = S1TextOnly(
        tool="ollama", model="qwen2.5-vl:7b", n_runs=1
    )
    result = scenario.run(fake_adapter)
    assert isinstance(result, ScenarioResult)
    assert result.scenario_name == "s1"
    assert len(result.runs) == 1
    assert result.runs[0].ok is True
    assert result.runs[0].completion_tokens == 3


def test_s1_text_only_captures_error_and_marks_not_ok():
    fake_adapter = MagicMock()
    fake_adapter.chat_text.side_effect = RuntimeError("boom")
    scenario = S1TextOnly(
        tool="ollama", model="qwen2.5-vl:7b", n_runs=1
    )
    result = scenario.run(fake_adapter)
    assert result.runs[0].ok is False
    assert result.runs[0].error == "boom"


def test_s1_text_only_respects_n_runs():
    fake_adapter = MagicMock()
    fake_adapter.chat_text.return_value = MagicMock(
        content="abc",
        prompt_tokens=5,
        completion_tokens=3,
        wall_seconds=0.5,
    )
    scenario = S1TextOnly(
        tool="ollama", model="qwen2.5-vl:7b", n_runs=3
    )
    result = scenario.run(fake_adapter)
    assert len(result.runs) == 3
    assert fake_adapter.chat_text.call_count == 3
