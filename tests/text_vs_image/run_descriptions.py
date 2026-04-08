#!/usr/bin/env python
"""Populate test_cases.yaml with Gemini descriptions for each test case.

Runs both the generic prompt and the type-specialized prompt for every image,
then writes the results back into the YAML in-place.

Usage:
    python tests/text_vs_image/run_descriptions.py
    python tests/text_vs_image/run_descriptions.py --only generic
    python tests/text_vs_image/run_descriptions.py --only specialized
    python tests/text_vs_image/run_descriptions.py --case tc01
    python tests/text_vs_image/run_descriptions.py --force  # overwrite existing

Designed to be re-runnable: existing non-empty descriptions are skipped unless
--force is passed. Manual edits to scores/answers in the YAML are preserved.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent  # copilot_demo/
sys.path.insert(0, str(WORKSPACE / "tools"))

from lib.gemini_client import (  # noqa: E402
    GeminiConfig,
    GeminiDescribeError,
    load_config,
)
from lib.safe_path import resolve_safe  # noqa: E402

# google-genai imports for the custom-prompt call
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402


def _extract_answer_text(response) -> str:
    """Same logic as gemini_client._extract_answer_text but reused here."""
    try:
        candidates = response.candidates or []
        if not candidates:
            return (getattr(response, "text", "") or "").strip()
        parts = candidates[0].content.parts or []
        chunks = []
        for part in parts:
            if getattr(part, "thought", False):
                continue
            text = getattr(part, "text", None)
            if text:
                chunks.append(text)
        if chunks:
            return "".join(chunks).strip()
    except (AttributeError, IndexError):
        pass
    return (getattr(response, "text", "") or "").strip()


def describe_with_prompt(
    image_bytes: bytes,
    mime: str,
    prompt_text: str,
    config: GeminiConfig,
) -> str:
    """Call Gemini with a custom prompt for one image."""
    client = genai.Client(api_key=config.api_key)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    try:
        response = client.models.generate_content(
            model=config.model,
            contents=[prompt_text, image_part],
        )
    except Exception as exc:  # noqa: BLE001
        raise GeminiDescribeError(f"Gemini API error: {exc}") from exc
    text = _extract_answer_text(response)
    if not text:
        raise GeminiDescribeError("Gemini returned empty description")
    return text


def _guess_mime(path: Path) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")


def _load_yaml_preserving(path: Path):
    """Load YAML preserving structure for round-trip writing."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(data, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=120,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=["generic", "specialized"],
        help="Only run one prompt variant",
    )
    parser.add_argument("--case", help="Only run a specific test case id (e.g. tc01)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-empty descriptions",
    )
    args = parser.parse_args()

    yaml_path = ROOT / "test_cases.yaml"
    data = _load_yaml_preserving(yaml_path)

    try:
        config = load_config(WORKSPACE)
    except GeminiDescribeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    print(f"Using model: {config.model}")
    generic_prompt = (ROOT / "prompts" / "generic.md").read_text(encoding="utf-8")

    cases = data["test_cases"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"ERROR: case {args.case} not found", file=sys.stderr)
            return 2

    for case in cases:
        case_id = case["id"]
        image_rel = case["image"]
        try:
            image_path = resolve_safe(image_rel, WORKSPACE)
        except Exception as exc:  # noqa: BLE001
            print(f"[{case_id}] image error: {exc}", file=sys.stderr)
            continue

        mime = _guess_mime(image_path)
        image_bytes = image_path.read_bytes()
        print(f"\n[{case_id}] {case['title']} ({image_path.name})")

        descriptions = case.setdefault("descriptions", {"generic": "", "specialized": ""})

        # generic
        if args.only != "specialized":
            if descriptions.get("generic") and not args.force:
                print("  generic: SKIP (already populated, use --force)")
            else:
                print("  generic: calling Gemini ...")
                try:
                    text = describe_with_prompt(image_bytes, mime, generic_prompt, config)
                    descriptions["generic"] = text
                    print(f"    OK ({len(text)} chars)")
                except GeminiDescribeError as exc:
                    print(f"    FAIL: {exc}", file=sys.stderr)
                    descriptions["generic"] = f"ERROR: {exc}"

        # specialized
        if args.only != "generic":
            spec_rel = case.get("specialized_prompt")
            if not spec_rel:
                print("  specialized: SKIP (no specialized_prompt set)")
            else:
                spec_path = (ROOT / spec_rel).resolve()
                spec_prompt = spec_path.read_text(encoding="utf-8")
                if descriptions.get("specialized") and not args.force:
                    print(f"  specialized ({spec_path.name}): SKIP (use --force)")
                else:
                    print(f"  specialized ({spec_path.name}): calling Gemini ...")
                    try:
                        text = describe_with_prompt(image_bytes, mime, spec_prompt, config)
                        descriptions["specialized"] = text
                        print(f"    OK ({len(text)} chars)")
                    except GeminiDescribeError as exc:
                        print(f"    FAIL: {exc}", file=sys.stderr)
                        descriptions["specialized"] = f"ERROR: {exc}"

        # write back after each case so we don't lose work on failure
        _dump_yaml(data, yaml_path)

    print(f"\nWrote {yaml_path.relative_to(WORKSPACE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
