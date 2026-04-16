#!/usr/bin/env python
"""CLI: describe a single image file (png/jpg/webp/gif) via the configured backend.

Usage:
    python tools/describe_image.py <path>

Backend is selected by the LLM_BACKEND environment variable:
    LLM_BACKEND=gemini (default) — uses lib.gemini_client
    LLM_BACKEND=local            — uses lib.local_llm_client (OpenAI-compatible)

Writes Markdown description to stdout. Errors go to stderr with non-zero exit.
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

from lib.safe_path import UnsafePathError, resolve_safe

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}

_VALID_BACKENDS = {"gemini", "local"}

# _BACKEND is captured at module import time. Changing os.environ["LLM_BACKEND"]
# after import has no effect — use a fresh subprocess (or module reimport in
# tests) if you need to switch backends mid-process.
_BACKEND = os.environ.get("LLM_BACKEND", "gemini").lower()


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return mime
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }.get(ext, "application/octet-stream")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Describe an image file via configured LLM backend"
    )
    parser.add_argument("path", help="Path to image file (relative or absolute)")
    args = parser.parse_args()

    if _BACKEND not in _VALID_BACKENDS:
        print(
            f"ERROR: unknown LLM_BACKEND={_BACKEND!r}. "
            f"Expected one of: {sorted(_VALID_BACKENDS)}",
            file=sys.stderr,
        )
        return 7

    try:
        safe = resolve_safe(args.path, WORKSPACE_ROOT)
    except (UnsafePathError, FileNotFoundError, IsADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if safe.suffix.lower() not in SUPPORTED_EXT:
        print(
            f"ERROR: unsupported extension {safe.suffix!r}. "
            f"Supported: {sorted(SUPPORTED_EXT)}",
            file=sys.stderr,
        )
        return 3

    mime = _guess_mime(safe)
    image_bytes = safe.read_bytes()

    if _BACKEND == "local":
        from lib.local_llm_client import (
            LocalLLMError as _BackendError,
            describe_image as _describe,
            load_config as _load_config,
        )
    else:
        from lib.gemini_client import (
            GeminiDescribeError as _BackendError,
            describe_image as _describe,
            load_config as _load_config,
        )

    try:
        config = _load_config(WORKSPACE_ROOT)
        description = _describe(image_bytes, mime, config)
    except _BackendError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5

    rel_display = safe.relative_to(WORKSPACE_ROOT)
    print(f"# {rel_display} の記述")
    print(f"- mime: `{mime}`")
    print(f"- backend: `{_BACKEND}`")
    print(f"- model: `{config.model}`")
    print()
    print(description)
    return 0


if __name__ == "__main__":
    sys.exit(main())
