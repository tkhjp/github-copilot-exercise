#!/usr/bin/env python
"""Judge Copilot Web verbatim-extraction responses against ground_truth.yaml.

Usage (after user has pasted Copilot responses under
benchmarks/out/extraction/{prompt_id}/):

    python tests/text_vs_image/extraction/judge_extraction.py \\
        --prompt-id my_prompt_v1 \\
        --n-runs 3

Produces:
    benchmarks/out/extraction/{prompt_id}/scores/
        png_p01_scores.json ... png_p08_scores.json
        pptx_scores.json
        summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Reuse the existing phase 4 judge infrastructure.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from phase4_quality_eval import (  # noqa: E402
    SCORE_MAP,
    JUDGE_PROMPT_EXTRACTION,
    extract_json,
    _mode_and_agreement,
    _stdev,
)

from google import genai


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_EXTRACTION_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_ROOT = REPO_ROOT / "benchmarks" / "out" / "extraction"
DEFAULT_GT = DEFAULT_EXTRACTION_DIR / "ground_truth.yaml"


PNG_FILENAMES_TO_PID = {
    "png_p01_response.md": "p01",
    "png_p02_response.md": "p02",
    "png_p03_response.md": "p03",
    "png_p04_response.md": "p04",
    "png_p05_response.md": "p05",
    "png_p06_response.md": "p06",
    "png_p07_response.md": "p07",
    "png_p08_response.md": "p08",
}


def extract_output_section(md_path: Path) -> str:
    """Return only the body after `## Output` (mirrors _load_description from
    generate_human_eval_ui.py). Falls back to the full file body if the header
    is absent."""
    text = md_path.read_text(encoding="utf-8")
    if "## Output" in text:
        text = text.split("## Output", 1)[1]
    # Strip HTML comments (common pasted placeholder).
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return text.strip()


def load_ground_truth(gt_path: Path) -> dict[str, dict[str, Any]]:
    return yaml.safe_load(gt_path.read_text(encoding="utf-8"))


def _judge_recall_once(
    gemini: genai.Client,
    judge_model: str,
    response_text: str,
    facts: list[dict[str, str]],
) -> dict[str, str]:
    """One Gemini call that returns {fact_id: verdict} for the recall dimension."""
    items_for_prompt = [{"id": f["id"], "text": f["text"]} for f in facts]
    prompt = JUDGE_PROMPT_EXTRACTION.format(
        description=response_text,
        items_json=json.dumps(items_for_prompt, ensure_ascii=False, indent=2),
    )
    last_err: Exception | None = None
    for _ in range(3):
        try:
            resp = gemini.models.generate_content(model=judge_model, contents=[prompt])
            text = getattr(resp, "text", "") or ""
            return extract_json(text)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"judge failed after 3 retries: {last_err}")


def judge_one(
    gemini: genai.Client,
    judge_model: str,
    response_text: str,
    pid: str,
    gt: dict[str, dict[str, Any]],
    n_runs: int,
) -> dict[str, Any]:
    """Run recall judging `n_runs` times and aggregate into one scores object.

    Does NOT yet compute hallucination — that lands in Task 10.
    """
    facts = gt[pid]["facts"]
    per_item_verdicts: dict[str, list[str]] = {f["id"]: [] for f in facts}
    runs_meta: list[dict[str, Any]] = []

    for run_idx in range(1, n_runs + 1):
        t0 = time.perf_counter()
        verdicts = _judge_recall_once(gemini, judge_model, response_text, facts)
        elapsed = time.perf_counter() - t0
        run_numeric: list[float] = []
        for f in facts:
            v = verdicts.get(f["id"], "missing")
            if v not in SCORE_MAP:
                v = "missing"
            per_item_verdicts[f["id"]].append(v)
            run_numeric.append(SCORE_MAP[v])
        run_avg = sum(run_numeric) / len(run_numeric) if run_numeric else 0.0
        runs_meta.append({"run": run_idx, "score_avg": run_avg, "judge_seconds": elapsed})
        print(f"    [run {run_idx}/{n_runs}] recall={run_avg:.3f} ({elapsed:.1f}s)", flush=True)

    agg_avg = sum(r["score_avg"] for r in runs_meta) / len(runs_meta) if runs_meta else 0.0
    agg_std = _stdev([r["score_avg"] for r in runs_meta])
    facts_out: list[dict[str, Any]] = []
    for f in facts:
        vlist = per_item_verdicts[f["id"]]
        mode, agreement = _mode_and_agreement(vlist)
        facts_out.append({
            "id": f["id"], "text": f["text"],
            "verdict": mode, "verdicts": vlist,
            "verdict_mode": mode, "agreement": agreement,
        })
    return {
        "pattern_id": pid,
        "pattern_name": gt[pid]["pattern_name"],
        "n_runs": n_runs,
        "n_facts": len(facts),
        "recall_avg": agg_avg,
        "recall_std": agg_std,
        "runs": runs_meta,
        "facts": facts_out,
    }


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Judge Copilot extraction responses")
    ap.add_argument("--prompt-id", required=True,
                    help="Name of the subdirectory under benchmarks/out/extraction/")
    ap.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    ap.add_argument("--gt", default=str(DEFAULT_GT))
    ap.add_argument("--judge-model", default="gemini-2.5-flash")
    ap.add_argument("--n-runs", type=int, default=3)
    ap.add_argument("--patterns", default="p01,p02,p03,p04,p05,p06,p07,p08",
                    help="Comma-separated pattern ids to judge")
    return ap.parse_args()


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    args = _parse_args()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env", file=sys.stderr)
        return 2

    gemini = genai.Client(api_key=api_key)
    gt = load_ground_truth(Path(args.gt))
    patterns = [p.strip() for p in args.patterns.split(",") if p.strip()]

    prompt_dir = Path(args.out_root) / args.prompt_id
    scores_dir = prompt_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)

    # Judge PNG responses (one file per pattern)
    for pid in patterns:
        resp_path = prompt_dir / f"png_{pid}_response.md"
        if not resp_path.exists():
            print(f"SKIP {pid}: {resp_path.name} not found")
            continue
        print(f"[png/{pid}]")
        response_text = extract_output_section(resp_path)
        scores = judge_one(gemini, args.judge_model, response_text, pid, gt, args.n_runs)
        out = scores_dir / f"png_{pid}_scores.json"
        out.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    → {out.name} recall={scores['recall_avg']:.3f}")

    # PPTX judging (single response file covering all 8 slides)
    # Splitting logic lands in Task 10; for now, if pptx_response.md exists, just
    # punt with a placeholder scores file noting the pending split step.
    pptx_resp = prompt_dir / "pptx_response.md"
    if pptx_resp.exists():
        print("[pptx] response exists but splitting deferred to Task 10 implementation")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
