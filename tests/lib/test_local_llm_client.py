"""Tests for tools.lib.local_llm_client."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Tests run with tools/ on sys.path via conftest.py, so this import
# mirrors how describe_image.py imports from lib.
from lib.local_llm_client import (
    LocalLLMConfig,
    LocalLLMError,
    describe_image,
    load_config,
)


def test_load_config_reads_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LLM_BASE_URL=http://127.0.0.1:11434/v1\n"
        "LLM_MODEL=qwen2.5-vl:7b\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    cfg = load_config(tmp_path)
    assert isinstance(cfg, LocalLLMConfig)
    assert cfg.base_url == "http://127.0.0.1:11434/v1"
    assert cfg.model == "qwen2.5-vl:7b"


def test_load_config_missing_base_url_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(LocalLLMError, match="LLM_BASE_URL"):
        load_config(tmp_path)


def test_load_config_missing_model_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    with pytest.raises(LocalLLMError, match="LLM_MODEL"):
        load_config(tmp_path)


def test_describe_image_rejects_empty_bytes():
    cfg = LocalLLMConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    with pytest.raises(LocalLLMError, match="Empty"):
        describe_image(b"", "image/png", cfg)


def test_describe_image_returns_content_from_adapter():
    cfg = LocalLLMConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.return_value = MagicMock(content="結果")
    with patch(
        "lib.local_llm_client.LocalLLMAdapter", return_value=fake_adapter
    ):
        out = describe_image(b"\x89PNG\r\n\x1a\nfake", "image/png", cfg)
    assert out == "結果"


def test_describe_image_wraps_adapter_errors():
    cfg = LocalLLMConfig(
        base_url="http://127.0.0.1:11434/v1", model="qwen2.5-vl:7b"
    )
    fake_adapter = MagicMock()
    fake_adapter.chat_vision.side_effect = RuntimeError("boom")
    with patch(
        "lib.local_llm_client.LocalLLMAdapter", return_value=fake_adapter
    ):
        with pytest.raises(LocalLLMError, match="boom"):
            describe_image(b"\x89PNG\r\n\x1a\nfake", "image/png", cfg)
