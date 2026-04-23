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


JUDGE_PROMPT_HALLUCINATION = """以下の description（Copilot の出力）を読み、
参照ドキュメントに存在しない情報（捏造）が含まれているか判定してください。

## 判定対象の参照事実（ground truth）
{facts_json}

## Copilot の出力
{description}

## タスク
1. Copilot の出力の中で、上の参照事実のどれにも該当せず、かつ事実として元の
   ドキュメントに含まれていなかった可能性が高い具体的な記述を列挙してください。
2. 一般的な要約・構造化・Markdown 整形・フォーマット装飾は hallucination とは
   みなしません。事実の追加のみを対象とします。

## 出力形式
以下の JSON 形式で厳格に返してください。JSON 以外の説明文は禁止。

{{
  "hallucination_count": <int>,
  "examples": ["...", "..."]
}}

"examples" には最大 10 件の具体的な捏造内容を原文で記載してください。
"hallucination_count" は検出総数です（11 件以上ある場合は examples を 10 件に
切り詰めても count はすべての件数）。"""


def _judge_hallucination_once(
    gemini: genai.Client,
    judge_model: str,
    response_text: str,
    facts: list[dict[str, str]],
) -> dict[str, Any]:
    prompt = JUDGE_PROMPT_HALLUCINATION.format(
        description=response_text,
        facts_json=json.dumps(
            [{"id": f["id"], "text": f["text"]} for f in facts],
            ensure_ascii=False, indent=2,
        ),
    )
    last_err: Exception | None = None
    for _ in range(3):
        try:
            resp = gemini.models.generate_content(model=judge_model, contents=[prompt])
            text = getattr(resp, "text", "") or ""
            parsed = extract_json(text)
            count = int(parsed.get("hallucination_count", 0))
            examples = list(parsed.get("examples", []))[:10]
            return {"count": count, "examples": examples}
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"hallucination judge failed after 3 retries: {last_err}")


_SLIDE_HEADER_RE = re.compile(r"^##\s*(?:Slide|スライド|slide)\s*(\d+)", re.IGNORECASE | re.MULTILINE)


def split_pptx_response_heuristic(response_text: str, n_slides: int = 8) -> list[str]:
    """Split a Copilot PPTX response into per-slide segments.

    Strategy:
      1. If response contains `## Slide N` (or `スライド N`) markers, split on those.
      2. Otherwise, put all text in segment 0 and leave the rest empty
         (the caller can then fall back to a Gemini-based splitter, added later
         if heuristic fails often in practice).

    Returns a list of length `n_slides`, 0-indexed (segment[i] corresponds to
    slide i+1).
    """
    segments = [""] * n_slides
    matches = list(_SLIDE_HEADER_RE.finditer(response_text))
    if not matches:
        segments[0] = response_text.strip()
        return segments
    for i, m in enumerate(matches):
        slide_num = int(m.group(1))
        if not (1 <= slide_num <= n_slides):
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(response_text)
        segments[slide_num - 1] = response_text[start:end].strip()
    return segments


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
    """Recall (n_runs) + hallucination (1 run — cheap, list rather than percentage)."""
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

    print(f"    [hallucination check]", flush=True)
    hallu = _judge_hallucination_once(gemini, judge_model, response_text, facts)

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
        "hallucination_count": hallu["count"],
        "hallucination_examples": hallu["examples"],
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
        # Skip empty responses (forgot-to-paste case) — avoids burning Gemini quota on
        # guaranteed-zero recall + hallucination calls.
        if not response_text.strip():
            print(f"SKIP {pid}: {resp_path.name} has empty ## Output body (paste the Copilot response)")
            continue
        scores = judge_one(gemini, args.judge_model, response_text, pid, gt, args.n_runs)
        out = scores_dir / f"png_{pid}_scores.json"
        out.write_text(json.dumps(scores, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"    → {out.name} recall={scores['recall_avg']:.3f}")

    # PPTX judging: one response file covering all 8 slides, split per-slide, then judge each.
    pptx_resp = prompt_dir / "pptx_response.md"
    if pptx_resp.exists():
        print("[pptx] splitting per-slide and judging each segment...")
        pptx_text = extract_output_section(pptx_resp)
        segments = split_pptx_response_heuristic(pptx_text, n_slides=8)
        pptx_scores: list[dict[str, Any]] = []
        all_pids = ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]
        for i, pid in enumerate(all_pids):
            if pid not in patterns:
                continue
            seg = segments[i]
            print(f"[pptx/{pid}]  ({len(seg)} chars)")
            if not seg.strip():
                # Empty segment → judge treats as missing; skip hallucination.
                facts = gt[pid]["facts"]
                pptx_scores.append({
                    "pattern_id": pid,
                    "pattern_name": gt[pid]["pattern_name"],
                    "n_runs": 0,
                    "n_facts": len(facts),
                    "recall_avg": 0.0,
                    "recall_std": 0.0,
                    "hallucination_count": 0,
                    "hallucination_examples": [],
                    "runs": [],
                    "facts": [
                        {"id": f["id"], "text": f["text"],
                         "verdict": "missing", "verdicts": ["missing"],
                         "verdict_mode": "missing", "agreement": 1.0}
                        for f in facts
                    ],
                    "note": "pptx split heuristic found no text for this slide",
                })
                continue
            scores = judge_one(gemini, args.judge_model, seg, pid, gt, args.n_runs)
            pptx_scores.append(scores)
            print(f"    → recall={scores['recall_avg']:.3f} hallu={scores['hallucination_count']}")
        (scores_dir / "pptx_scores.json").write_text(
            json.dumps(pptx_scores, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # Summary
    summary = {
        "prompt_id": args.prompt_id,
        "judge_model": args.judge_model,
        "n_runs": args.n_runs,
        "patterns_judged": patterns,
    }
    (scores_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
