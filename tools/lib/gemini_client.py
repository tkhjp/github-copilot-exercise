"""Gemini Vision client for describing images in Japanese.

Loads GEMINI_API_KEY from the workspace .env. Default model is
`gemini-2.5-flash` (fast, vision-capable, stable output). Override via
environment variable GEMINI_MODEL.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

DEFAULT_MODEL = "gemini-2.5-flash"

DESCRIBE_PROMPT = (
    "この画像を構造的に記述してください。"
    "含まれる**テキスト内容**（OCR的に全て書き出す）、"
    "**図表・ダイアグラムの構造**（ノード・接続・階層）、"
    "**色とレイアウト**、"
    "**主要な視覚要素**を網羅し、日本語で詳細に出力してください。"
    "推測ではなく画像から直接読み取れる情報のみを記述してください。"
)


class GeminiDescribeError(RuntimeError):
    """Raised when the Gemini Vision call fails or returns empty output."""


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model: str


def load_config(workspace_root: Path) -> GeminiConfig:
    """Load GEMINI_API_KEY from the workspace .env file."""
    env_path = workspace_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiDescribeError(
            f"GEMINI_API_KEY not set. Expected in {env_path} or environment."
        )
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    return GeminiConfig(api_key=api_key, model=model)


def _extract_answer_text(response) -> str:
    """Extract answer text, filtering out thinking-mode parts.

    Per JEIS project notes, Gemini thinking models occasionally emit thought
    parts into `response.text`. Iterate candidates[0].content.parts and skip
    any part flagged as `thought=True`.
    """
    try:
        candidates = response.candidates or []
        if not candidates:
            return (getattr(response, "text", "") or "").strip()
        parts = candidates[0].content.parts or []
        answer_chunks = []
        for part in parts:
            if getattr(part, "thought", False):
                continue
            text = getattr(part, "text", None)
            if text:
                answer_chunks.append(text)
        if answer_chunks:
            return "".join(answer_chunks).strip()
    except (AttributeError, IndexError):
        pass
    # Fallback to response.text (may include thought content, but better than nothing)
    return (getattr(response, "text", "") or "").strip()


def describe_image(
    image_bytes: bytes,
    mime_type: str,
    config: GeminiConfig,
) -> str:
    """Send one image to Gemini Vision and return a Japanese description.

    Raises GeminiDescribeError on API failure or empty response.
    """
    if not image_bytes:
        raise GeminiDescribeError("Empty image bytes")

    client = genai.Client(api_key=config.api_key)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    try:
        response = client.models.generate_content(
            model=config.model,
            contents=[DESCRIBE_PROMPT, image_part],
        )
    except Exception as exc:  # noqa: BLE001 - surface all SDK errors uniformly
        raise GeminiDescribeError(f"Gemini API error: {exc}") from exc

    text = _extract_answer_text(response)
    if not text:
        raise GeminiDescribeError("Gemini returned empty description")
    return text
