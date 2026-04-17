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

JUDGE_PROMPT = """以下の description（モデル出力）の中に、各 fact の情報が含まれているか判定してください。

# Description
{description}

# Facts (JSON)
{facts_json}

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


def judge_with_gemini(gemini: genai.Client, model: str, description: str, facts: list[dict]) -> dict:
    facts_for_prompt = [{"id": f["id"], "text": f["text"]} for f in facts]
    prompt = JUDGE_PROMPT.format(
        description=description,
        facts_json=json.dumps(facts_for_prompt, ensure_ascii=False, indent=2),
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


def run_case(
    local_client: OpenAI,
    gemini_client: genai.Client,
    judge_model: str,
    quant_label: str,
    llm_model: str,
    case: dict,
    out_dir: Path,
) -> dict:
    image_path = REPO_ROOT / case["image"]
    image_bytes = image_path.read_bytes()
    mime = "image/png"
    question = case["question"]
    facts = case["ground_truth_facts"]

    t0 = time.perf_counter()
    description = call_local_llm(local_client, llm_model, image_bytes, mime, question)
    describe_seconds = time.perf_counter() - t0

    # Save the raw description
    (out_dir / f"{quant_label}_{case['id']}_description.md").write_text(
        f"# {case['id']} — {quant_label}\n\n"
        f"**Question:** {question}\n\n"
        f"**Describe wall_seconds:** {describe_seconds:.2f}\n\n"
        f"## Output\n\n{description}\n",
        encoding="utf-8",
    )

    scores = judge_with_gemini(gemini_client, judge_model, description, facts)

    # Compute per-case score
    numeric = []
    detailed = []
    for f in facts:
        fid = f["id"]
        verdict = scores.get(fid, "missing")
        if verdict not in SCORE_MAP:
            verdict = "missing"
        numeric.append(SCORE_MAP[verdict])
        detailed.append({"id": fid, "text": f["text"], "verdict": verdict})

    avg = sum(numeric) / len(numeric) if numeric else 0.0

    # Save per-case scoring detail
    (out_dir / f"{quant_label}_{case['id']}_scores.json").write_text(
        json.dumps(
            {
                "case_id": case["id"],
                "quant": quant_label,
                "model": llm_model,
                "describe_seconds": describe_seconds,
                "n_facts": len(facts),
                "score_avg": avg,
                "facts": detailed,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {"case_id": case["id"], "quant": quant_label, "n_facts": len(facts), "score_avg": avg, "describe_seconds": describe_seconds}


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
        print(f"[{args.quant_label}] running {case['id']} ({len(case['ground_truth_facts'])} facts)...", flush=True)
        row = run_case(
            local_client=local_client,
            gemini_client=gemini_client,
            judge_model=args.judge_model,
            quant_label=args.quant_label,
            llm_model=args.llm_model,
            case=case,
            out_dir=out_dir,
        )
        summary.append(row)
        print(
            f"[{args.quant_label}] {case['id']}: score {row['score_avg']:.3f} "
            f"({row['n_facts']} facts), describe {row['describe_seconds']:.1f}s",
            flush=True,
        )

    # Write per-quant summary
    summary_path = out_dir / f"{args.quant_label}_summary.json"
    avg_score = sum(r["score_avg"] for r in summary) / len(summary) if summary else 0.0
    avg_describe = sum(r["describe_seconds"] for r in summary) / len(summary) if summary else 0.0
    summary_path.write_text(
        json.dumps(
            {
                "quant": args.quant_label,
                "model": args.llm_model,
                "judge_model": args.judge_model,
                "cases": summary,
                "avg_score": avg_score,
                "avg_describe_seconds": avg_describe,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {summary_path}  avg_score={avg_score:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
