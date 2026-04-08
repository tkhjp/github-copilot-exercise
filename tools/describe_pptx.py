#!/usr/bin/env python
"""CLI: describe all embedded images in a .pptx file via Gemini Vision.

Usage:
    python tools/describe_pptx.py <path>
    python tools/describe_pptx.py <path> --slide 3
    python tools/describe_pptx.py <path> --slide 1-3,5

Writes Markdown (one section per image) to stdout. Errors to stderr.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.gemini_client import GeminiDescribeError, describe_image, load_config
from lib.pptx_extractor import extract_images
from lib.safe_path import UnsafePathError, resolve_safe

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Describe embedded images in a pptx file via Gemini Vision"
    )
    parser.add_argument("path", help="Path to .pptx file")
    parser.add_argument(
        "--slide",
        default="all",
        help='Slide selector: "all" (default), "3", "1-3", "1,3,5", "1-3,5"',
    )
    args = parser.parse_args()

    try:
        safe = resolve_safe(args.path, WORKSPACE_ROOT)
    except (UnsafePathError, FileNotFoundError, IsADirectoryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if safe.suffix.lower() != ".pptx":
        print(
            f"ERROR: expected .pptx, got {safe.suffix!r}",
            file=sys.stderr,
        )
        return 3

    try:
        images = extract_images(safe, slide_range=args.slide)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: failed to parse pptx: {exc}", file=sys.stderr)
        return 4

    rel_display = safe.relative_to(WORKSPACE_ROOT)
    print(f"# {rel_display} の埋め込み画像記述")
    print(f"- 対象スライド: `{args.slide}`")
    print(f"- 抽出画像数: {len(images)}")
    print()

    if not images:
        print("（指定範囲に埋め込み画像が見つかりませんでした）")
        return 0

    try:
        config = load_config(WORKSPACE_ROOT)
    except GeminiDescribeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5
    print(f"- model: `{config.model}`")
    print()

    failures = 0
    for img in images:
        print(f"## スライド {img.slide_index}, 画像 {img.image_index} (`{img.mime_type}`)")
        try:
            description = describe_image(img.blob, img.mime_type, config)
            print(description)
        except GeminiDescribeError as exc:
            failures += 1
            print(f"_(記述失敗: {exc})_")
        print()

    return 0 if failures == 0 else 6


if __name__ == "__main__":
    sys.exit(main())
