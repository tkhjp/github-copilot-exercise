"""Local LLM client exposing the same describe_image interface as gemini_client.

Wraps benchmarks.adapter.openai_client.LocalLLMAdapter so that
tools/describe_image.py, tools/describe_pptx.py, and tools/describe_docx.py
can switch backend via LLM_BACKEND=gemini|local with no other code change.

Loads LLM_BASE_URL and LLM_MODEL from the workspace .env file (or environment).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Make benchmarks/ importable when running from tools/
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.adapter.openai_client import AdapterConfig, LocalLLMAdapter  # noqa: E402

from lib.describe_prompts import DESCRIBE_PROMPT  # noqa: E402,F401 (re-exported for back-compat)


class LocalLLMError(RuntimeError):
    """Raised when the local LLM call fails or returns empty output."""


@dataclass(frozen=True)
class LocalLLMConfig:
    base_url: str
    model: str
    api_key: str = "not-needed"
    timeout_seconds: float = 120.0


# Module-level adapter cache. Each distinct AdapterConfig-equivalent key maps
# to a single LocalLLMAdapter instance, so repeated calls (e.g. per-slide in
# describe_pptx.py) don't rebuild the underlying httpx connection pool.
_ADAPTER_CACHE: dict[tuple[str, str, str, float], LocalLLMAdapter] = {}


def _clear_adapter_cache() -> None:
    """Reset the module-level adapter cache. Intended for test isolation."""
    _ADAPTER_CACHE.clear()


def _get_adapter(config: LocalLLMConfig) -> LocalLLMAdapter:
    """Return a cached adapter for this config, building one on first use."""
    key = (config.base_url, config.model, config.api_key, config.timeout_seconds)
    if key not in _ADAPTER_CACHE:
        adapter_cfg = AdapterConfig(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
        )
        _ADAPTER_CACHE[key] = LocalLLMAdapter(adapter_cfg)
    return _ADAPTER_CACHE[key]


def load_config(workspace_root: Path) -> LocalLLMConfig:
    """Load LLM_* env vars from the workspace .env (if present) or environment.

    Precedence: shell environment wins over the .env file. python-dotenv's
    load_dotenv defaults to override=False, so a value already exported in
    the shell is not replaced by a .env entry with the same name. This is
    the same precedence gemini_client.py uses; tests that want deterministic
    behavior should monkeypatch.delenv before asserting.
    """
    env_path = workspace_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not base_url:
        raise LocalLLMError(
            f"LLM_BASE_URL not set. Expected in {env_path} or environment."
        )
    if not model:
        raise LocalLLMError(
            f"LLM_MODEL not set. Expected in {env_path} or environment."
        )
    api_key = os.environ.get("LLM_API_KEY", "not-needed")

    timeout_raw = os.environ.get("LLM_TIMEOUT_SECONDS", "120")
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise LocalLLMError(
            f"LLM_TIMEOUT_SECONDS must be a number, got {timeout_raw!r}"
        ) from exc
    if timeout <= 0:
        raise LocalLLMError(
            f"LLM_TIMEOUT_SECONDS must be > 0, got {timeout_raw!r}"
        )

    return LocalLLMConfig(
        base_url=base_url,
        model=model,
        api_key=api_key,
        timeout_seconds=timeout,
    )


def describe_image(
    image_bytes: bytes, mime_type: str, config: LocalLLMConfig
) -> str:
    """Send one image to the local LLM and return a Japanese description.

    Mirrors gemini_client.describe_image's signature so describe_image.py etc.
    can swap implementations without other changes.

    Raises LocalLLMError on failure or empty response.
    """
    if not image_bytes:
        raise LocalLLMError("Empty image bytes")

    adapter = _get_adapter(config)

    try:
        result = adapter.chat_vision(
            prompt=DESCRIBE_PROMPT,
            image_bytes=image_bytes,
            mime_type=mime_type,
        )
    except Exception as exc:  # noqa: BLE001
        raise LocalLLMError(f"Local LLM call failed: {exc}") from exc

    if not result.content.strip():
        raise LocalLLMError("Local LLM returned empty description")
    return result.content.strip()
