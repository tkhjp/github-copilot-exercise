"""CLI driver for benchmark scenarios.

Usage:
    python -m benchmarks.harness \
        --tool ollama \
        --model qwen2.5-vl:7b \
        --base-url http://127.0.0.1:11434/v1 \
        --scenario s1 \
        --n-runs 3 \
        --out-dir benchmarks/out

Vision scenarios additionally require --image (S2) or --pptx-dir (S3: directory
of .png/.jpg used as a simulated pptx batch).
"""
from __future__ import annotations

import argparse
import mimetypes
import re
import sys
from pathlib import Path

from benchmarks.adapter.openai_client import AdapterConfig, LocalLLMAdapter
from benchmarks.report import write_csv, write_markdown
from benchmarks.scenarios.base import ScenarioResult
from benchmarks.scenarios.s1_text_only import S1TextOnly
from benchmarks.scenarios.s2_vision_single import S2VisionSingle
from benchmarks.scenarios.s3_vision_pptx_batch import S3VisionPptxBatch

_SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

# Windows-illegal filename chars: \ / : * ? " < > | (plus control chars).
# Used to sanitize the model id in output filenames.
_ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_filename_component(s: str) -> str:
    """Replace Windows-illegal filename chars with '-'."""
    return _ILLEGAL_FILENAME_CHARS.sub("-", s)


def _guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return mime
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(path.suffix.lower(), "application/octet-stream")


def _build_scenario(args: argparse.Namespace, parser: argparse.ArgumentParser):
    """Build the scenario object from CLI args.

    Argument-level errors (missing --image, bad --pptx-dir, empty image dir)
    call parser.error() which prints usage and exits with code 2 — distinct
    from exit code 1 (partial run failure) returned by main().
    """
    if args.scenario == "s1":
        return S1TextOnly(tool=args.tool, model=args.model, n_runs=args.n_runs)
    if args.scenario == "s2":
        if not args.image:
            parser.error("--image is required for scenario s2")
        image_path = Path(args.image)
        return S2VisionSingle(
            tool=args.tool,
            model=args.model,
            image_bytes=image_path.read_bytes(),
            mime_type=_guess_mime(image_path),
            n_runs=args.n_runs,
        )
    if args.scenario == "s3":
        if not args.pptx_dir:
            parser.error("--pptx-dir is required for scenario s3")
        pptx_dir = Path(args.pptx_dir)
        if not pptx_dir.is_dir():
            parser.error(f"--pptx-dir '{pptx_dir}' is not a directory")
        images: list[tuple[bytes, str]] = []
        for entry in sorted(pptx_dir.iterdir()):
            if entry.is_file() and entry.suffix.lower() in _SUPPORTED_IMAGE_EXTS:
                images.append((entry.read_bytes(), _guess_mime(entry)))
        if not images:
            parser.error(f"no supported images found under {pptx_dir}")
        # S3 processes each image exactly once; --n-runs does not apply.
        if args.n_runs != 3:
            print(
                f"note: --n-runs={args.n_runs} is ignored for scenario s3 "
                f"(one run per image, got {len(images)} images)",
                file=sys.stderr,
            )
        return S3VisionPptxBatch(
            tool=args.tool, model=args.model, images=images
        )
    parser.error(f"unknown scenario: {args.scenario}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local LLM benchmark harness")
    parser.add_argument("--tool", required=True, help="Candidate tool name tag")
    parser.add_argument("--model", required=True, help="Model id at the endpoint")
    parser.add_argument("--base-url", required=True, help="OpenAI-compat base URL")
    parser.add_argument("--scenario", required=True, choices=["s1", "s2", "s3"])
    parser.add_argument("--n-runs", type=int, default=3)
    parser.add_argument("--image", help="S2: path to image file")
    parser.add_argument("--pptx-dir", help="S3: directory of images")
    parser.add_argument(
        "--out-dir",
        default="benchmarks/out",
        help="Output directory for CSV and Markdown",
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0, help="Per-request timeout seconds"
    )
    args = parser.parse_args(argv)

    config = AdapterConfig(
        base_url=args.base_url,
        model=args.model,
        timeout_seconds=args.timeout,
    )
    adapter = LocalLLMAdapter(config)
    scenario = _build_scenario(args, parser)
    result: ScenarioResult = scenario.run(adapter)

    out_dir = Path(args.out_dir)
    stem = f"{_safe_filename_component(args.tool)}_{args.scenario}_{_safe_filename_component(args.model)}"
    csv_path = out_dir / f"{stem}.csv"
    md_path = out_dir / f"{stem}.md"
    write_csv(result.runs, csv_path)
    write_markdown(
        result.runs,
        md_path,
        title=f"{args.scenario.upper()} — {args.tool} / {args.model}",
    )
    print(f"wrote {csv_path}")
    print(f"wrote {md_path}")

    ok_count = sum(1 for r in result.runs if r.ok)
    if ok_count == 0:
        # 10 (not 2) so downstream scripts can tell "all runs failed" from
        # argparse's exit 2 (bad CLI args, no runs attempted).
        return 10
    if ok_count < len(result.runs):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
