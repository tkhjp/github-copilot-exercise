#!/usr/bin/env python
"""Run Gemini vision API as the extractor on the 8 PNG patterns, mirroring the
Copilot Web manual workflow but fully automated.

Usage:
    python tests/text_vs_image/extraction/extract_with_gemini.py \\
        --prompt benchmarks/out/extraction/v1/prompt.md \\
        --trial-id v2_api_gemini3 \\
        --extractor-model gemini-3-flash

Reads:
    - PNG inputs from tests/text_vs_image/extraction/p0N_*.png  (current corpus)
    - prompt body from benchmarks/out/extraction/<id>/prompt.md (the
      "## PNG / PPTX 共通プロンプト (貼付用)" code block)

Writes:
    - benchmarks/out/extraction/<trial-id>/png_p0N_response.md  (8 files)
    - benchmarks/out/extraction/<trial-id>/prompt.md            (copy of source prompt)

After this you can run:
    python tests/text_vs_image/extraction/judge_extraction.py --prompt-id <trial-id>
    python tests/text_vs_image/extraction/extraction_report.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_EXTRACTION_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_ROOT = REPO_ROOT / "benchmarks" / "out" / "extraction"

PNG_INPUTS = [
    ("p01", "p01_ui_callouts.png"),
    ("p02", "p02_before_after.png"),
    ("p03", "p03_process_flow.png"),
    ("p04", "p04_dashboard_annotated.png"),
    ("p05", "p05_hierarchical_drilldown.png"),
    ("p06", "p06_review_comments.png"),
    ("p07", "p07_mixed_dashboard.png"),
    ("p08", "p08_org_chart.png"),
]


def load_prompt_body(prompt_md: Path) -> str:
    """Pull the first fenced code block out of prompt.md (matches what humans
    paste into Copilot Web)."""
    text = prompt_md.read_text(encoding="utf-8")
    m = re.search(r"```(?:[a-zA-Z0-9_-]*)?\n(.*?)```", text, re.DOTALL)
    if not m:
        raise SystemExit(f"No fenced code block found in {prompt_md}")
    return m.group(1).strip()


def extract_one(
    client: genai.Client,
    model: str,
    prompt_body: str,
    image_path: Path,
) -> str:
    """Send one (prompt + image) request to Gemini and return the text reply."""
    image_bytes = image_path.read_bytes()
    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=[prompt_body, image_part],
            )
            text = getattr(resp, "text", "") or ""
            if text.strip():
                return text
            last_err = ValueError("empty response text")
        except Exception as e:  # network / 5xx / parse — retry
            last_err = e
            time.sleep(2 ** attempt)
    raise SystemExit(f"Gemini extract failed for {image_path.name}: {last_err}")


def write_response_md(out_path: Path, trial_id: str, image_name: str,
                      model: str, body: str, today: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# {trial_id} / {image_name}\n\n"
        f"**Date:** {today}\n"
        f"**Source:** Gemini API ({model}), trial_id={trial_id}\n\n"
        f"## Output\n\n"
    )
    out_path.write_text(header + body.strip() + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True,
                    help="Path to prompt.md whose first fenced block is the extractor prompt body")
    ap.add_argument("--trial-id", required=True,
                    help="Subdirectory name under benchmarks/out/extraction/")
    ap.add_argument("--extractor-model", default="gemini-3-flash-preview",
                    help="Gemini model id to use as the extractor (default: gemini-3-flash-preview)")
    ap.add_argument("--inputs-dir", default=str(DEFAULT_EXTRACTION_DIR),
                    help="Directory containing the 8 p0N_*.png inputs")
    ap.add_argument("--patterns", default=",".join(p for p, _ in PNG_INPUTS),
                    help="Comma-separated pattern ids to run (default: all 8)")
    ap.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    ap.add_argument("--date", default=time.strftime("%Y-%m-%d"))
    args = ap.parse_args()

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env", file=sys.stderr)
        return 1
    client = genai.Client(api_key=api_key)

    prompt_body = load_prompt_body(Path(args.prompt))
    out_dir = Path(args.out_root) / args.trial_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Persist a copy of the source prompt so the trial dir is self-describing.
    prompt_copy = out_dir / "prompt.md"
    if not prompt_copy.exists():
        prompt_copy.write_text(Path(args.prompt).read_text(encoding="utf-8"), encoding="utf-8")
        print(f"copied prompt.md → {prompt_copy}")

    inputs_dir = Path(args.inputs_dir)
    selected = {p.strip() for p in args.patterns.split(",") if p.strip()}

    for pid, fname in PNG_INPUTS:
        if pid not in selected:
            continue
        image_path = inputs_dir / fname
        if not image_path.exists():
            print(f"[skip] {fname} not found at {image_path}", file=sys.stderr)
            continue
        print(f"[{pid}] extract → {args.extractor_model} ({image_path.stat().st_size} bytes)...")
        t0 = time.time()
        body = extract_one(client, args.extractor_model, prompt_body, image_path)
        elapsed = time.time() - t0
        out_path = out_dir / f"png_{pid}_response.md"
        write_response_md(out_path, args.trial_id, fname,
                          args.extractor_model, body, args.date)
        print(f"    → {out_path.name} ({len(body)} chars, {elapsed:.1f}s)")

    print(f"done. {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
