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


from benchmarks.scenarios.s2_vision_single import S2VisionSingle


def test_s2_vision_single_invokes_vision_chat():
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.return_value = MagicMock(
        content="an image of a diagram",
        prompt_tokens=200,
        completion_tokens=80,
        wall_seconds=3.5,
    )
    scenario = S2VisionSingle(
        tool="ollama",
        model="qwen2.5-vl:7b",
        image_bytes=b"\x89PNG\r\n\x1a\nfake",
        mime_type="image/png",
        n_runs=2,
    )
    result = scenario.run(fake_adapter)
    assert result.scenario_name == "s2"
    assert len(result.runs) == 2
    assert fake_adapter.chat_vision.call_count == 2
    assert result.runs[0].completion_tokens == 80


def test_s2_vision_single_requires_non_empty_image():
    import pytest as _pt
    with _pt.raises(ValueError, match="image_bytes"):
        S2VisionSingle(
            tool="ollama",
            model="qwen2.5-vl:7b",
            image_bytes=b"",
            mime_type="image/png",
        )


from benchmarks.scenarios.s3_vision_pptx_batch import S3VisionPptxBatch


def test_s3_vision_pptx_batch_runs_once_per_image():
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.return_value = MagicMock(
        content="ok",
        prompt_tokens=200,
        completion_tokens=40,
        wall_seconds=2.0,
    )
    images = [
        (b"\x89PNG\r\n\x1a\na", "image/png"),
        (b"\x89PNG\r\n\x1a\nb", "image/png"),
        (b"\x89PNG\r\n\x1a\nc", "image/png"),
    ]
    scenario = S3VisionPptxBatch(
        tool="ollama",
        model="qwen2.5-vl:7b",
        images=images,
    )
    result = scenario.run(fake_adapter)
    assert result.scenario_name == "s3"
    assert len(result.runs) == 3
    assert fake_adapter.chat_vision.call_count == 3


def test_s3_vision_pptx_batch_requires_at_least_one_image():
    import pytest as _pt
    with _pt.raises(ValueError, match="images"):
        S3VisionPptxBatch(
            tool="ollama",
            model="qwen2.5-vl:7b",
            images=[],
        )
