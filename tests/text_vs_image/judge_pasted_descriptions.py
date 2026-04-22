#!/usr/bin/env python
"""Run the Gemini judge on already-pasted Copilot descriptions.

`phase4_quality_eval.py` runs a local LLM first to generate a description, then
judges it with Gemini. For Copilot we already have the description (manually
pasted into `{quant}_{tc}_description.md`), so this script does ONLY the judge
step and writes `{quant}_{tc}_scores.json` + `{quant}_judgment_summary.json` in
the same schema.

Requires:
    GEMINI_API_KEY    — set in `.env` or the environment

Run (after pasting all 6 description.md):
    python tests/text_vs_image/judge_pasted_descriptions.py \\
        --quant-labels copilot_png,copilot_pptx,copilot_docx \\
        --case-ids tc02_judge,tc03_judge \\
        --n-runs 3
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google import genai

# Reuse helpers from the main evaluator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_quality_eval import (  # noqa: E402
    SCORE_MAP,
    _items_for_case,
    _mode_and_agreement,
    _stdev,
    _summary_filename,
    judge_with_gemini,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CASES_YAML = REPO_ROOT / "tests" / "text_vs_image" / "test_cases.yaml"
DEFAULT_QUALITY_DIR = REPO_ROOT / "benchmarks" / "out" / "phase4" / "quality"


def extract_output_section(md_text: str) -> str:
    """Return the body after the `## Output` header, stripping HTML comments."""
    if "## Output" not in md_text:
        # Fall back to whole body if header is missing.
        body = md_text
    else:
        body = md_text.split("## Output", 1)[1]
    # Drop HTML comments (<!-- ... -->), leading whitespace.
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    return body.strip()


def judge_case(
    gemini_client,
    judge_model: str,
    quality_dir: Path,
    quant_label: str,
    case: dict,
    n_runs: int,
) -> dict | None:
    test_type, items = _items_for_case(case)
    if not items:
        print(f"  skip {case['id']}: no scorable items", file=sys.stderr)
        return None

    desc_md = quality_dir / f"{quant_label}_{case['id']}_description.md"
    if not desc_md.exists():
        print(f"  skip {case['id']}: missing {desc_md.name}", file=sys.stderr)
        return None
    description = extract_output_section(desc_md.read_text(encoding="utf-8"))
    if not description:
        print(f"  skip {case['id']}: description body is empty in {desc_md.name}", file=sys.stderr)
        return None

    per_item_verdicts: dict[str, list[str]] = {it["id"]: [] for it in items}
    runs_meta: list[dict] = []

    for run_idx in range(1, n_runs + 1):
        t0 = time.perf_counter()
        scores = judge_with_gemini(gemini_client, judge_model, description, items, test_type)
        elapsed = time.perf_counter() - t0

        run_numeric: list[float] = []
        run_detailed: list[dict] = []
        for it in items:
            iid = it["id"]
            verdict = scores.get(iid, "missing")
            if verdict not in SCORE_MAP:
                verdict = "missing"
            per_item_verdicts[iid].append(verdict)
            run_numeric.append(SCORE_MAP[verdict])
            run_detailed.append({"id": iid, "text": it["text"], "verdict": verdict})
        run_avg = sum(run_numeric) / len(run_numeric) if run_numeric else 0.0
        runs_meta.append({"run": run_idx, "score_avg": run_avg, "judge_seconds": elapsed})

        (quality_dir / f"{quant_label}_{case['id']}_judge_run{run_idx}_scores.json").write_text(
            json.dumps({
                "case_id": case["id"],
                "quant": quant_label,
                "model": "pasted-by-human",
                "judge": judge_model,
                "test_type": test_type,
                "run": run_idx,
                "judge_seconds": elapsed,
                "n_facts": len(items),
                "score_avg": run_avg,
                "facts": run_detailed,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  [run {run_idx}/{n_runs}] score {run_avg:.3f}, judge {elapsed:.1f}s", flush=True)

    # Aggregate
    run_avgs = [r["score_avg"] for r in runs_meta]
    aggregate_score_avg = sum(run_avgs) / len(run_avgs) if run_avgs else 0.0
    aggregate_score_std = _stdev(run_avgs)
    aggregate_judge = sum(r["judge_seconds"] for r in runs_meta) / len(runs_meta) if runs_meta else 0.0

    facts_out: list[dict] = []
    for it in items:
        vlist = per_item_verdicts[it["id"]]
        mode, agreement = _mode_and_agreement(vlist)
        facts_out.append({
            "id": it["id"],
            "text": it["text"],
            "verdict": mode,
            "verdicts": vlist,
            "verdict_mode": mode,
            "agreement": agreement,
        })

    (quality_dir / f"{quant_label}_{case['id']}_scores.json").write_text(
        json.dumps({
            "case_id": case["id"],
            "quant": quant_label,
            "model": "pasted-by-human",
            "judge": judge_model,
            "test_type": test_type,
            "n_runs": n_runs,
            "describe_seconds": None,
            "judge_seconds": aggregate_judge,
            "n_facts": len(items),
            "score_avg": aggregate_score_avg,
            "score_std": aggregate_score_std,
            "runs": runs_meta,
            "facts": facts_out,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "case_id": case["id"],
        "quant": quant_label,
        "test_type": test_type,
        "n_facts": len(items),
        "n_runs": n_runs,
        "score_avg": aggregate_score_avg,
        "score_std": aggregate_score_std,
        "judge_seconds": aggregate_judge,
    }


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")

    ap = argparse.ArgumentParser(description="Judge pasted Copilot descriptions with Gemini")
    ap.add_argument("--quant-labels", default="copilot_png,copilot_pptx,copilot_docx",
                    help="Comma-separated quant labels to judge")
    ap.add_argument("--case-ids", default="tc02_judge,tc03_judge",
                    help="Comma-separated case ids (judgment only)")
    ap.add_argument("--cases-yaml", default=str(DEFAULT_CASES_YAML))
    ap.add_argument("--out-dir", default=str(DEFAULT_QUALITY_DIR))
    ap.add_argument("--judge-model", default="gemini-2.5-flash")
    ap.add_argument("--n-runs", type=int, default=3,
                    help="Number of independent judge runs per case (default 3, matches local LLM setup)")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env or environment", file=sys.stderr)
        return 2

    gemini_client = genai.Client(api_key=api_key)

    cases_data = yaml.safe_load(Path(args.cases_yaml).read_text(encoding="utf-8"))
    all_cases = {c["id"]: c for c in cases_data["test_cases"]}

    quants = [q.strip() for q in args.quant_labels.split(",") if q.strip()]
    case_ids = [c.strip() for c in args.case_ids.split(",") if c.strip()]
    selected_cases = [all_cases[cid] for cid in case_ids if cid in all_cases]
    missing = [cid for cid in case_ids if cid not in all_cases]
    if missing:
        print(f"WARNING: cases not in yaml: {missing}", file=sys.stderr)
    if not selected_cases:
        print(f"ERROR: no matching cases in {args.cases_yaml}", file=sys.stderr)
        return 3

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Track summaries per (quant, test_type)
    summaries: dict[tuple[str, str], list[dict]] = {}

    for quant in quants:
        print(f"\n=== {quant} ===")
        for case in selected_cases:
            print(f"[{case['id']}]")
            result = judge_case(gemini_client, args.judge_model, out_dir, quant, case, args.n_runs)
            if result:
                key = (quant, result["test_type"])
                summaries.setdefault(key, []).append(result)

    # Write per-quant summaries (matches phase4_quality_eval output layout)
    for (quant, test_type), cases_list in summaries.items():
        if not cases_list:
            continue
        summary_path = out_dir / _summary_filename(quant, test_type)
        avg = sum(c["score_avg"] for c in cases_list) / len(cases_list)
        summary_path.write_text(
            json.dumps({
                "quant": quant,
                "model": "pasted-by-human",
                "judge": args.judge_model,
                "source": "judge-only (Copilot pasted)",
                "n_runs": args.n_runs,
                "cases": cases_list,
                "avg_score": avg,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"→ wrote {summary_path.name}  avg={avg:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
