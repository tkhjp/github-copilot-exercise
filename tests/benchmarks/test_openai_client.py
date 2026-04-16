"""Tests for benchmarks.adapter.openai_client."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from benchmarks.adapter.openai_client import (
    AdapterConfig,
    ChatResult,
    LocalLLMAdapter,
)


def test_adapter_config_requires_base_url():
    with pytest.raises(ValueError, match="base_url"):
        AdapterConfig(base_url="", model="qwen2.5-vl:7b")


def test_adapter_config_requires_model():
    with pytest.raises(ValueError, match="model"):
        AdapterConfig(base_url="http://127.0.0.1:11434/v1", model="")


def test_adapter_config_defaults_api_key():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    assert cfg.api_key == "not-needed"


def test_chat_text_only_returns_content():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "hello"
    fake_response.usage = MagicMock(
        prompt_tokens=5, completion_tokens=2, total_tokens=7
    )
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        result = adapter.chat_text("say hello")

    assert isinstance(result, ChatResult)
    assert result.content == "hello"
    assert result.prompt_tokens == 5
    assert result.completion_tokens == 2
    assert result.wall_seconds >= 0


def test_chat_vision_encodes_image_as_data_url():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "an image of a diagram"
    fake_response.usage = MagicMock(
        prompt_tokens=100, completion_tokens=8, total_tokens=108
    )
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        result = adapter.chat_vision(
            prompt="describe", image_bytes=b"\x89PNG\r\n\x1a\n", mime_type="image/png"
        )

    assert result.content == "an image of a diagram"
    call_args = fake_openai_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    content_parts = messages[0]["content"]
    assert any(p["type"] == "text" and p["text"] == "describe" for p in content_parts)
    image_part = next(p for p in content_parts if p["type"] == "image_url")
    assert image_part["image_url"]["url"].startswith("data:image/png;base64,")


def test_chat_raises_on_empty_content():
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = ""
    fake_response.usage = MagicMock(
        prompt_tokens=1, completion_tokens=0, total_tokens=1
    )
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        with pytest.raises(RuntimeError, match="empty"):
            adapter.chat_text("hello")
