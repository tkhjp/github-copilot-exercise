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


# ---------- Expanded coverage (Task 6 code-review follow-up: C1-C4) ----------


def test_chat_vision_rejects_empty_image_bytes():
    """C1: chat_vision must guard against empty bytes before calling the backend."""
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        with pytest.raises(ValueError, match="image_bytes"):
            adapter.chat_vision(
                prompt="describe", image_bytes=b"", mime_type="image/png"
            )
    # Backend must not have been called at all
    fake_openai_client.chat.completions.create.assert_not_called()


@pytest.mark.parametrize("whitespace_only", ["   ", "\n", "\t\n  ", "\r\n"])
def test_chat_raises_on_whitespace_only_content(whitespace_only: str):
    """C2: content that strips to empty (whitespace-only) must also raise."""
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = whitespace_only
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


def test_adapter_passes_timeout_and_model_to_openai_sdk():
    """C3: AdapterConfig.timeout_seconds must reach OpenAI(...) and model must
    reach chat.completions.create — guards against copy-paste refactors that
    drop one of these kwargs."""
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1",
        model="qwen2.5-vl:7b",
        timeout_seconds=42.5,
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "ok"
    fake_response.usage = MagicMock(
        prompt_tokens=1, completion_tokens=1, total_tokens=2
    )
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ) as openai_ctor:
        adapter = LocalLLMAdapter(cfg)
        adapter.chat_text("hi")

    # Constructor got the timeout
    openai_ctor.assert_called_once()
    ctor_kwargs = openai_ctor.call_args.kwargs
    assert ctor_kwargs["base_url"] == "http://127.0.0.1:11434/v1"
    assert ctor_kwargs["timeout"] == 42.5

    # chat.completions.create got the model
    create_kwargs = fake_openai_client.chat.completions.create.call_args.kwargs
    assert create_kwargs["model"] == "qwen2.5-vl:7b"


def test_chat_tolerates_missing_usage_field():
    """C4: some OpenAI-compatible backends (llama.cpp --api, older LM Studio)
    omit `response.usage` or return None. The adapter must default tokens to 0
    rather than raising AttributeError."""
    cfg = AdapterConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_openai_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "pong"
    fake_response.usage = None  # backend did not report usage
    fake_openai_client.chat.completions.create.return_value = fake_response

    with patch(
        "benchmarks.adapter.openai_client.OpenAI",
        return_value=fake_openai_client,
    ):
        adapter = LocalLLMAdapter(cfg)
        result = adapter.chat_text("ping")

    assert result.content == "pong"
    assert result.prompt_tokens == 0
    assert result.completion_tokens == 0
