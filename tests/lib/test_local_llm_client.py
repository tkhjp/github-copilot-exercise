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
    _clear_adapter_cache,
    describe_image,
    load_config,
)


@pytest.fixture(autouse=True)
def _reset_adapter_cache():
    """Clear the module-level adapter cache before every test in this file,
    so patches of LocalLLMAdapter aren't shadowed by cached instances from
    a prior test."""
    _clear_adapter_cache()
    yield
    _clear_adapter_cache()


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


def test_load_config_rejects_unparseable_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """G1: LLM_TIMEOUT_SECONDS that doesn't parse as float must raise
    LocalLLMError with a clear message, not silently fall back to 120."""
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-vl:7b")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "abc")
    with pytest.raises(LocalLLMError, match="LLM_TIMEOUT_SECONDS"):
        load_config(tmp_path)


@pytest.mark.parametrize("bad_value", ["0", "-5", "-0.1"])
def test_load_config_rejects_non_positive_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_value: str
):
    """G1: timeouts <= 0 must raise, since the OpenAI SDK will either reject
    them or hang indefinitely — either way, 'silent fallback to 120' masks
    a real misconfiguration."""
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-vl:7b")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", bad_value)
    with pytest.raises(LocalLLMError, match="> 0"):
        load_config(tmp_path)


def test_load_config_accepts_valid_positive_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """G1 happy path: a valid positive timeout flows through to the config."""
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5-vl:7b")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "45.5")
    cfg = load_config(tmp_path)
    assert cfg.timeout_seconds == 45.5


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
