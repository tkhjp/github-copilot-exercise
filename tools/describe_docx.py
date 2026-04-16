#!/usr/bin/env python
"""CLI: describe all embedded images in a .docx file via the configured backend.

Usage:
    python tools/describe_docx.py <path>

Backend is selected by LLM_BACKEND (gemini (default) | local).

Writes Markdown to stdout. Errors to stderr.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from lib.docx_extractor import extract_images
from lib.safe_path import UnsafePathError, resolve_safe

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

_BACKEND = os.environ.get("LLM_BACKEND", "gemini").lower()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Describe embedded images in a docx file via configured LLM backend"
    )
    parser.add_argument("path", help="Path to .docx file")
    args = parser.parse_args()

    try:
        safe = resolve_safe(args.path, WORKSPACE_ROOT)
    except (UnsafePathError, FileNotFoundError, IsADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if safe.suffix.lower() != ".docx":
        print(f"ERROR: expected .docx, got {safe.suffix!r}", file=sys.stderr)
        return 3

    try:
        images = extract_images(safe)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to parse docx: {exc}", file=sys.stderr)
        return 4

    rel_display = safe.relative_to(WORKSPACE_ROOT)
    print(f"# {rel_display} の埋め込み画像記述")
    print(f"- 抽出画像数: {len(images)}")
    print(f"- backend: `{_BACKEND}`")
    print()

    if not images:
        print("（埋め込み画像が見つかりませんでした）")
        return 0

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
    except _BackendError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5
    print(f"- model: `{config.model}`")
    print()

    failures = 0
    for img in images:
        print(f"## 画像 {img.image_index} (`{img.mime_type}`, rel_id=`{img.rel_id}`)")
        try:
            description = _describe(img.blob, img.mime_type, config)
            print(description)
        except _BackendError as exc:
            failures += 1
            print(f"_(記述失敗: {exc})_")
        print()

    return 0 if failures == 0 else 6


if __name__ == "__main__":
    sys.exit(main())
