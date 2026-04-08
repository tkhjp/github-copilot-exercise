#!/usr/bin/env python
"""CLI: describe a single image file (png/jpg/webp/gif) via Gemini Vision.

Usage:
    python tools/describe_image.py <path>

Writes Markdown description to stdout. Errors go to stderr with non-zero exit.
"""
from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path

from lib.gemini_client import GeminiDescribeError, describe_image, load_config
from lib.safe_path import UnsafePathError, resolve_safe

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return mime
    # Fallback based on extension
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
        description="Describe an image file via Gemini Vision"
    )
    parser.add_argument("path", help="Path to image file (relative or absolute)")
    args = parser.parse_args()

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

    try:
        config = load_config(WORKSPACE_ROOT)
    except GeminiDescribeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    mime = _guess_mime(safe)
    image_bytes = safe.read_bytes()

    try:
        description = describe_image(image_bytes, mime, config)
    except GeminiDescribeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5

    rel_display = safe.relative_to(WORKSPACE_ROOT)
    print(f"# {rel_display} の記述")
    print(f"- mime: `{mime}`")
    print(f"- model: `{config.model}`")
    print()
    print(description)
    return 0


if __name__ == "__main__":
    sys.exit(main())
