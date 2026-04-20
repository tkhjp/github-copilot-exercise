#!/usr/bin/env python
"""Phase 4 quality evaluation for Gemma 4 E4B quantization sweep.

For each (quant, test_case) pair:
  1. Call the local LM Studio endpoint with the tc's question + image
  2. Save the raw description
  3. Use Gemini 2.5 Flash as judge: score each ground_truth_fact as
     present (1.0) / partial (0.5) / missing (0.0)

Aggregates per-tc and per-quant averages into a CSV/Markdown pair that
Phase 4's model-selection report consumes.

Usage:
    python tests/text_vs_image/phase4_quality_eval.py \\
        --base-url http://127.0.0.1:1234/v1 \\
        --quant-model gemma4-e4b-q4:gemma4-e4b-q5:gemma4-e4b-q8 \\
        --out-dir benchmarks/out/phase4/quality
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

SCORE_MAP = {"present": 1.0, "partial": 0.5, "missing": 0.0}

JUDGE_PROMPT_EXTRACTION = """以下の description（モデル出力）の中に、各 fact の情報が含まれているか判定してください。

# Description
{description}

# Facts (JSON)
{items_json}

# 判定ルール
各 fact について以下のいずれかで判定してください：
- present: fact の内容が description にほぼそのまま、あるいは明確に含まれている
- partial: fact の一部のみ（ラベルは合っているが値が微妙に違う、など）が含まれている
- missing: fact に対応する言及が description に全くない、または明らかに誤っている

# 出力形式
以下の JSON だけを出力してください。説明文・前置き・コードブロック記号（```）は一切含めないでください。

{{
  "f01": "present",
  "f02": "partial",
  "f03": "missing",
  ...
}}
"""

JUDGE_PROMPT_JUDGMENT = """以下の reasoning（モデルによる判断・推論の出力）の中で、各 reasoning point がモデルの判断として実質的に述べられているかを判定してください。

# Reasoning (モデル出力)
{description}

# Reasoning points (JSON)
{items_json}

# 判定ルール
各 reasoning point について以下のいずれかで判定してください：
- present: reasoning point の主張がモデルの判断として明確に述べられている。言い換えや別表現でも、意味が一致していれば present。
- partial: reasoning point の一部のみが述べられている、または近い結論だがサイズ・規模・方向性などが微妙に違う。
- missing: reasoning point に対応する判断が reasoning に全く出ていない、または明確に矛盾する主張がなされている。

# 出力形式
以下の JSON だけを出力してください。説明文・前置き・コードブロック記号（```）は一切含めないでください。

{{
  "j01": "present",
  "j02": "partial",
  ...
}}
"""


def _items_for_case(case: dict) -> tuple[str, list[dict]]:
    """Return (test_type, items) where items is the scored list.

    Extraction cases use `ground_truth_facts`, judgment cases use `reasoning_points`.
    """
    if case.get("test_type") == "judgment":
        items = case.get("reasoning_points") or []
        return "judgment", items
    return "extraction", case.get("ground_truth_facts") or []


def _summary_filename(quant: str, test_type: str) -> str:
    if test_type == "judgment":
        return f"{quant}_judgment_summary.json"
    return f"{quant}_summary.json"


def call_local_llm(client: OpenAI, model: str, image_bytes: bytes, mime: str, question: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def extract_json(text: str) -> dict:
    """Pull the first { ... } JSON object out of a response that might have prose."""
    text = text.strip()
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"no JSON object in judge output: {text[:200]}")
    blob = text[start : end + 1]
    return json.loads(blob)


def judge_with_gemini(
    gemini: genai.Client,
    model: str,
    description: str,
    items: list[dict],
    test_type: str,
) -> dict:
    items_for_prompt = [{"id": f["id"], "text": f["text"]} for f in items]
    template = JUDGE_PROMPT_JUDGMENT if test_type == "judgment" else JUDGE_PROMPT_EXTRACTION
    prompt = template.format(
        description=description,
        items_json=json.dumps(items_for_prompt, ensure_ascii=False, indent=2),
    )
    # Retry up to 2 times on parse failure
    last_err = None
    for _ in range(3):
        try:
            resp = gemini.models.generate_content(model=model, contents=[prompt])
            text = getattr(resp, "text", "") or ""
            return extract_json(text)
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1)
    raise RuntimeError(f"judge failed after retries: {last_err}")


def _stdev(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mean = sum(xs) / len(xs)
    return (sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def _mode_and_agreement(verdicts: list[str]) -> tuple[str, float]:
    if not verdicts:
        return "missing", 0.0
    counts: dict[str, int] = {}
    for v in verdicts:
        counts[v] = counts.get(v, 0) + 1
    mode = max(counts.items(), key=lambda kv: (kv[1], -list(SCORE_MAP.keys()).index(kv[0])))[0]
    return mode, counts[mode] / len(verdicts)


def run_case(
    local_client: OpenAI,
    gemini_client: genai.Client,
    judge_model: str,
    quant_label: str,
    llm_model: str,
    case: dict,
    out_dir: Path,
    n_runs: int = 1,
) -> dict:
    image_path = REPO_ROOT / case["image"]
    image_bytes = image_path.read_bytes()
    mime = "image/png"
    question = case["question"]
    test_type, items = _items_for_case(case)
    if not items:
        raise ValueError(
            f"case {case.get('id')} has no scorable items "
            f"(expected ground_truth_facts or reasoning_points)"
        )

    per_item_verdicts: dict[str, list[str]] = {it["id"]: [] for it in items}
    runs_meta: list[dict] = []

    for run_idx in range(1, n_runs + 1):
        t0 = time.perf_counter()
        description = call_local_llm(local_client, llm_model, image_bytes, mime, question)
        describe_seconds = time.perf_counter() - t0

        # Save this run's raw description. For n_runs==1 we also keep the legacy
        # flat name so external tools that expect it still work.
        run_md = out_dir / f"{quant_label}_{case['id']}_run{run_idx}_description.md"
        run_md.write_text(
            f"# {case['id']} — {quant_label}  run {run_idx}/{n_runs}  ({test_type})\n\n"
            f"**Question:** {question}\n\n"
            f"**Describe wall_seconds:** {describe_seconds:.2f}\n\n"
            f"## Output\n\n{description}\n",
            encoding="utf-8",
        )
        if n_runs == 1:
            (out_dir / f"{quant_label}_{case['id']}_description.md").write_text(
                run_md.read_text(encoding="utf-8"), encoding="utf-8"
            )

        scores = judge_with_gemini(gemini_client, judge_model, description, items, test_type)

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

        (out_dir / f"{quant_label}_{case['id']}_run{run_idx}_scores.json").write_text(
            json.dumps(
                {
                    "case_id": case["id"],
                    "quant": quant_label,
                    "model": llm_model,
                    "test_type": test_type,
                    "run": run_idx,
                    "describe_seconds": describe_seconds,
                    "n_facts": len(items),
                    "score_avg": run_avg,
                    "facts": run_detailed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        runs_meta.append(
            {
                "run": run_idx,
                "score_avg": run_avg,
                "describe_seconds": describe_seconds,
            }
        )
        print(
            f"  [run {run_idx}/{n_runs}] score {run_avg:.3f}, describe {describe_seconds:.1f}s",
            flush=True,
        )

    # Aggregate: per-fact mode + agreement, case avg/std over runs.
    run_avgs = [r["score_avg"] for r in runs_meta]
    run_describes = [r["describe_seconds"] for r in runs_meta]
    aggregate_score_avg = sum(run_avgs) / len(run_avgs) if run_avgs else 0.0
    aggregate_score_std = _stdev(run_avgs)
    aggregate_describe = sum(run_describes) / len(run_describes) if run_describes else 0.0

    facts_out: list[dict] = []
    for it in items:
        vlist = per_item_verdicts[it["id"]]
        mode, agreement = _mode_and_agreement(vlist)
        facts_out.append(
            {
                "id": it["id"],
                "text": it["text"],
                "verdict": mode,            # backward-compat: single verdict = mode across runs
                "verdicts": vlist,          # per-run verdict list (length == n_runs)
                "verdict_mode": mode,
                "agreement": agreement,     # fraction of runs that agreed with the mode
            }
        )

    (out_dir / f"{quant_label}_{case['id']}_scores.json").write_text(
        json.dumps(
            {
                "case_id": case["id"],
                "quant": quant_label,
                "model": llm_model,
                "test_type": test_type,
                "n_runs": n_runs,
                "describe_seconds": aggregate_describe,
                "n_facts": len(items),
                "score_avg": aggregate_score_avg,
                "score_std": aggregate_score_std,
                "runs": runs_meta,
                "facts": facts_out,
            },
            ensure_ascii=False,
            indent=2,
        ),
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
        "describe_seconds": aggregate_describe,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 4 quality eval")
    ap.add_argument("--base-url", required=True, help="LM Studio OpenAI-compatible endpoint, e.g. http://127.0.0.1:1234/v1")
    ap.add_argument("--quant-label", required=True, help="Label for this run (e.g. q4 / q5 / q8)")
    ap.add_argument("--llm-model", required=True, help="Model identifier loaded in LM Studio")
    ap.add_argument(
        "--cases-yaml",
        default=str(REPO_ROOT / "tests/text_vs_image/test_cases.yaml"),
    )
    ap.add_argument("--case-ids", nargs="*", default=["tc01", "tc02", "tc03", "tc04"])
    ap.add_argument("--judge-model", default="gemini-2.5-flash")
    ap.add_argument("--out-dir", default="benchmarks/out/phase4/quality")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--n-runs", type=int, default=1,
                    help="Number of independent describe+judge iterations per case. >1 exposes LLM/judge stochastic variance.")
    args = ap.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env or environment", file=sys.stderr)
        return 2

    gemini_client = genai.Client(api_key=api_key)
    local_client = OpenAI(base_url=args.base_url, api_key="not-needed", timeout=args.timeout)

    cases_data = yaml.safe_load(Path(args.cases_yaml).read_text(encoding="utf-8"))
    all_cases = {c["id"]: c for c in cases_data["test_cases"]}
    selected = [all_cases[cid] for cid in args.case_ids if cid in all_cases]
    if not selected:
        print(f"ERROR: no matching cases in {args.cases_yaml}", file=sys.stderr)
        return 3

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for case in selected:
        _, items = _items_for_case(case)
        if not items:
            print(
                f"WARNING: skipping {case['id']} — no ground_truth_facts / reasoning_points",
                file=sys.stderr,
            )
            continue
        n_items = len(items)
        print(
            f"[{args.quant_label}] running {case['id']} ({n_items} items, n_runs={args.n_runs})...",
            flush=True,
        )
        row = run_case(
            local_client=local_client,
            gemini_client=gemini_client,
            judge_model=args.judge_model,
            quant_label=args.quant_label,
            llm_model=args.llm_model,
            case=case,
            out_dir=out_dir,
            n_runs=args.n_runs,
        )
        summary.append(row)
        std_str = f" ±{row['score_std']:.3f}" if row['n_runs'] > 1 else ""
        print(
            f"[{args.quant_label}] {case['id']}: score {row['score_avg']:.3f}{std_str} "
            f"({row['n_facts']} {row['test_type']}, {row['n_runs']} runs), "
            f"describe avg {row['describe_seconds']:.1f}s",
            flush=True,
        )

    # Write one summary file per test_type so extraction and judgment runs coexist.
    by_type: dict[str, list[dict]] = {}
    for r in summary:
        by_type.setdefault(r["test_type"], []).append(r)

    for test_type, rows in by_type.items():
        path = out_dir / _summary_filename(args.quant_label, test_type)
        avg_score = sum(r["score_avg"] for r in rows) / len(rows) if rows else 0.0
        avg_describe = sum(r["describe_seconds"] for r in rows) / len(rows) if rows else 0.0
        # Mean of per-case stdevs (rough indicator of within-case noise across the suite)
        avg_std = sum(r.get("score_std", 0.0) for r in rows) / len(rows) if rows else 0.0
        n_runs_max = max((r.get("n_runs", 1) for r in rows), default=1)
        path.write_text(
            json.dumps(
                {
                    "quant": args.quant_label,
                    "model": args.llm_model,
                    "judge_model": args.judge_model,
                    "test_type": test_type,
                    "n_runs": n_runs_max,
                    "cases": rows,
                    "avg_score": avg_score,
                    "avg_score_std": avg_std,
                    "avg_describe_seconds": avg_describe,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        std_msg = f" ±{avg_std:.3f}" if n_runs_max > 1 else ""
        print(f"wrote {path}  avg_score={avg_score:.3f}{std_msg}  (n_runs={n_runs_max})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
