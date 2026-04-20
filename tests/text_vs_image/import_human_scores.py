#!/usr/bin/env python
"""Merge an exported human_scores.json from the eval UI back into per-quant summaries.

For each `(quant, tc)` present in the exported scores, writes
`{quality_dir}/{quant}_{tc}_human_scores.json` (per-case detail) and
`{quality_dir}/{quant}_human_summary.json` (aggregate — analogous to the LLM
`{quant}_summary.json`). Prints a comparison table of LLM vs human averages.

Usage:
    python tests/text_vs_image/import_human_scores.py \
        --scores-json ~/Downloads/human_scores.json \
        --quality-dir benchmarks/out/phase4/quality
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_QUALITY_DIR = REPO_ROOT / "benchmarks" / "out" / "phase4" / "quality"
DEFAULT_CASES_YAML = REPO_ROOT / "tests" / "text_vs_image" / "test_cases.yaml"

SCORE_MAP = {"present": 1.0, "partial": 0.5, "missing": 0.0}


def _load_cases(cases_yaml: Path) -> dict[str, dict]:
    data = yaml.safe_load(cases_yaml.read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["test_cases"]}


def _load_llm_summary(quality_dir: Path, quant: str) -> dict | None:
    p = quality_dir / f"{quant}_summary.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_case_detail(
    quality_dir: Path, quant: str, tc_id: str, facts: list[dict], verdicts: dict[str, str]
) -> tuple[int, float]:
    detailed = []
    numeric = []
    for f in facts:
        verdict = verdicts.get(f["id"])
        if verdict not in SCORE_MAP:
            verdict = "missing"
        detailed.append({"id": f["id"], "text": f["text"], "verdict": verdict})
        numeric.append(SCORE_MAP[verdict])
    avg = sum(numeric) / len(numeric) if numeric else 0.0
    out = {
        "case_id": tc_id,
        "quant": quant,
        "source": "human",
        "n_facts": len(facts),
        "score_avg": avg,
        "facts": detailed,
    }
    (quality_dir / f"{quant}_{tc_id}_human_scores.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(facts), avg


def main() -> int:
    ap = argparse.ArgumentParser(description="Import human scores from eval UI")
    ap.add_argument("--scores-json", required=True, help="Path to human_scores.json exported by the UI")
    ap.add_argument("--quality-dir", default=str(DEFAULT_QUALITY_DIR))
    ap.add_argument("--cases-yaml", default=str(DEFAULT_CASES_YAML))
    args = ap.parse_args()

    payload = json.loads(Path(args.scores_json).read_text(encoding="utf-8"))
    scores = payload.get("scores") if "scores" in payload else payload
    if not isinstance(scores, dict):
        print("ERROR: scores file must be a dict of {quant: {tc: {fact_id: verdict}}}", file=sys.stderr)
        return 2

    quality_dir = Path(args.quality_dir)
    cases = _load_cases(Path(args.cases_yaml))

    print(f"{'quant':<8} {'tc':<6} {'n':>4} {'human':>8} {'llm':>8} {'Δ':>7}")
    print("-" * 48)

    for quant, tcs in sorted(scores.items()):
        llm_summary = _load_llm_summary(quality_dir, quant)
        llm_scores = {c["case_id"]: c["score_avg"] for c in (llm_summary or {}).get("cases", [])}
        human_cases = []
        for tc_id, verdicts in sorted(tcs.items()):
            if tc_id not in cases:
                print(f"WARNING: unknown test case {tc_id} for {quant}", file=sys.stderr)
                continue
            facts = cases[tc_id]["ground_truth_facts"]
            n, avg = _write_case_detail(quality_dir, quant, tc_id, facts, verdicts)
            human_cases.append({"case_id": tc_id, "quant": quant, "n_facts": n, "score_avg": avg})
            llm_avg = llm_scores.get(tc_id)
            delta = (avg - llm_avg) if llm_avg is not None else None
            print(
                f"{quant:<8} {tc_id:<6} {n:>4} {avg:>8.3f} "
                f"{(llm_avg if llm_avg is not None else float('nan')):>8.3f} "
                f"{(delta if delta is not None else float('nan')):>+7.3f}"
            )

        if human_cases:
            human_avg = sum(c["score_avg"] for c in human_cases) / len(human_cases)
            summary = {
                "quant": quant,
                "source": "human",
                "paired_llm_summary": f"{quant}_summary.json",
                "cases": human_cases,
                "avg_score": human_avg,
            }
            (quality_dir / f"{quant}_human_summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"  → wrote {quant}_human_summary.json  avg={human_avg:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
