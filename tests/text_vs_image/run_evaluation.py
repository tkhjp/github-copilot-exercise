#!/usr/bin/env python
"""Fully automated text-vs-image fidelity evaluation.

Pipeline per test case:
  1. Generate 'generic' description from image (Gemini Vision)
  2. Generate 'specialized' description from image (Gemini Vision, type-specific prompt)
  3. Case 1: send `specialized description + question` to Gemini as TEXT → answer
  4. Case 2: send `image + question` to Gemini Vision → answer
  5. For each of the 4 outputs × each ground-truth fact, ask Gemini to judge
     present / partial / missing. Writes all results back to test_cases.yaml.

Re-runnable: existing non-empty fields are skipped unless --force is passed.

Usage:
    python tests/text_vs_image/run_evaluation.py
    python tests/text_vs_image/run_evaluation.py --case tc01
    python tests/text_vs_image/run_evaluation.py --stage descriptions
    python tests/text_vs_image/run_evaluation.py --stage answers
    python tests/text_vs_image/run_evaluation.py --stage scoring
    python tests/text_vs_image/run_evaluation.py --force
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent
sys.path.insert(0, str(WORKSPACE / "tools"))

from lib.gemini_client import (  # noqa: E402
    GeminiConfig,
    GeminiDescribeError,
    load_config,
)
from lib.safe_path import resolve_safe  # noqa: E402

from google import genai  # noqa: E402
from google.genai import types  # noqa: E402


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

def _extract_answer_text(response) -> str:
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


def gemini_text(prompt: str, config: GeminiConfig) -> str:
    """Text-only Gemini call."""
    client = genai.Client(api_key=config.api_key)
    try:
        response = client.models.generate_content(
            model=config.model,
            contents=[prompt],
        )
    except Exception as exc:  # noqa: BLE001
        raise GeminiDescribeError(f"Gemini text API error: {exc}") from exc
    text = _extract_answer_text(response)
    if not text:
        raise GeminiDescribeError("Gemini returned empty text")
    return text


def gemini_vision(prompt: str, image_bytes: bytes, mime: str, config: GeminiConfig) -> str:
    """Image + prompt Gemini call."""
    client = genai.Client(api_key=config.api_key)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    try:
        response = client.models.generate_content(
            model=config.model,
            contents=[prompt, image_part],
        )
    except Exception as exc:  # noqa: BLE001
        raise GeminiDescribeError(f"Gemini vision API error: {exc}") from exc
    text = _extract_answer_text(response)
    if not text:
        raise GeminiDescribeError("Gemini returned empty vision response")
    return text


# ---------------------------------------------------------------------------
# YAML round-trip
# ---------------------------------------------------------------------------

def _load_yaml(path: Path):
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


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

def _guess_mime(path: Path) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")


def stage_descriptions(case: dict, image_bytes: bytes, mime: str,
                       config: GeminiConfig, force: bool) -> None:
    """Generate generic + specialized descriptions for one case."""
    descriptions = case.setdefault("descriptions", {"generic": "", "specialized": ""})

    generic_prompt = (ROOT / "prompts" / "generic.md").read_text(encoding="utf-8")

    # generic
    if descriptions.get("generic") and not force:
        print("    generic: SKIP (already populated)")
    else:
        print("    generic: calling Gemini Vision ...")
        try:
            text = gemini_vision(generic_prompt, image_bytes, mime, config)
            descriptions["generic"] = text
            print(f"      OK ({len(text)} chars)")
        except GeminiDescribeError as exc:
            print(f"      FAIL: {exc}", file=sys.stderr)
            descriptions["generic"] = f"ERROR: {exc}"

    # specialized
    spec_rel = case.get("specialized_prompt")
    if not spec_rel:
        print("    specialized: SKIP (no specialized_prompt set)")
        return
    spec_path = (ROOT / spec_rel).resolve()
    spec_prompt = spec_path.read_text(encoding="utf-8")
    if descriptions.get("specialized") and not force:
        print(f"    specialized ({spec_path.name}): SKIP")
    else:
        print(f"    specialized ({spec_path.name}): calling Gemini Vision ...")
        try:
            text = gemini_vision(spec_prompt, image_bytes, mime, config)
            descriptions["specialized"] = text
            print(f"      OK ({len(text)} chars)")
        except GeminiDescribeError as exc:
            print(f"      FAIL: {exc}", file=sys.stderr)
            descriptions["specialized"] = f"ERROR: {exc}"


def stage_answers(case: dict, image_bytes: bytes, mime: str,
                  config: GeminiConfig, force: bool) -> None:
    """Generate Case 1 (text) and Case 2 (image) answers from the question."""
    question = case["question"].strip()
    specialized = (case.get("descriptions") or {}).get("specialized") or ""

    # Case 1: text-only (specialized description + question)
    case1 = case.setdefault("case1", {"copilot_answer": "", "fact_scores": {}})
    if case1.get("copilot_answer") and not force:
        print("    case1 (text): SKIP")
    elif not specialized or specialized.startswith("ERROR"):
        print("    case1 (text): SKIP (no specialized description)")
    else:
        print("    case1 (text): calling Gemini ...")
        # Same level of instruction freedom as Case 2: the LLM may use general
        # domain knowledge. The only difference between Case 1 and Case 2 is
        # how the image content is conveyed (text description vs raw image).
        prompt = (
            "以下は、ある画像を別の Vision LLM が文字化した記述です。"
            "この記述を画像の代わりとして使い、後ろの質問に日本語で答えてください。"
            "画像に関する事実（要素、数値、配置など）はこの記述を根拠にし、"
            "判断や推論には一般的なドメイン知識を自由に使って構いません。\n\n"
            f"=== 画像記述 ===\n{specialized}\n\n"
            f"=== 質問 ===\n{question}"
        )
        try:
            text = gemini_text(prompt, config)
            case1["copilot_answer"] = text
            print(f"      OK ({len(text)} chars)")
        except GeminiDescribeError as exc:
            print(f"      FAIL: {exc}", file=sys.stderr)
            case1["copilot_answer"] = f"ERROR: {exc}"

    # Case 2: image + question
    case2 = case.setdefault("case2", {"copilot_answer": "", "fact_scores": {}})
    if case2.get("copilot_answer") and not force:
        print("    case2 (image): SKIP")
    else:
        print("    case2 (image): calling Gemini Vision ...")
        prompt = f"添付の画像を参照して、以下の質問に日本語で答えてください。\n\n{question}"
        try:
            text = gemini_vision(prompt, image_bytes, mime, config)
            case2["copilot_answer"] = text
            print(f"      OK ({len(text)} chars)")
        except GeminiDescribeError as exc:
            print(f"      FAIL: {exc}", file=sys.stderr)
            case2["copilot_answer"] = f"ERROR: {exc}"


BATCH_SIZE = 10

JUDGE_BATCH_PROMPT = """あなたは厳密な事実チェック採点者です。
以下の「確認したい事実リスト」のそれぞれが「与えられたテキスト」に含まれているかを個別に判定してください。

判定基準:
- present: 事実が明確に、正確な値・名前・関係で含まれている
- partial: 部分的に言及されているが、細部 (数値・名前・方向など) が欠けている / ずれている
- missing: 事実が全く言及されていない、または明確に間違っている

出力は次の形式の **JSON 配列のみ** を返してください。説明文・前置き・コードフェンスは一切付けないでください。
配列の順序と要素数は入力の事実リストと完全に一致させてください。

[
  {"id": "f01", "verdict": "present" | "partial" | "missing", "reason": "簡潔な根拠 (日本語 30 文字以内)"},
  {"id": "f02", ...},
  ...
]

=== 確認したい事実リスト (id と本文) ===
%FACTS%

=== 与えられたテキスト ===
%TEXT%
"""


def _parse_judge_batch(raw: str, expected_ids: list[str]) -> dict[str, tuple[str, str]]:
    """Parse batched judge output into {fact_id: (verdict, reason)}.

    Tolerates markdown fences and trailing junk. Falls back to per-id missing
    if parsing fails for any id.
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # First [...] substring
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return {fid: ("missing", f"unparseable-batch:{raw[:40]}") for fid in expected_ids}
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {fid: ("missing", f"invalid-json-batch:{raw[:40]}") for fid in expected_ids}
    out: dict[str, tuple[str, str]] = {}
    if isinstance(arr, list):
        for item in arr:
            if not isinstance(item, dict):
                continue
            fid = str(item.get("id", "")).strip()
            verdict = str(item.get("verdict", "")).strip().lower()
            reason = str(item.get("reason", "")).strip()
            if fid and verdict in {"present", "partial", "missing"}:
                out[fid] = (verdict, reason)
    # Ensure every expected id is present; mark unreturned ones as missing
    for fid in expected_ids:
        if fid not in out:
            out[fid] = ("missing", "not-returned-by-judge")
    return out


def _score_batch(facts: list[dict], subject_text: str,
                 config: GeminiConfig) -> dict[str, tuple[str, str]]:
    """Score up to BATCH_SIZE facts in a single LLM call. Returns {id: (verdict, reason)}."""
    facts_section = "\n".join(f"- {f['id']}: {f['text']}" for f in facts)
    prompt = (
        JUDGE_BATCH_PROMPT
        .replace("%FACTS%", facts_section)
        .replace("%TEXT%", subject_text)
    )
    expected_ids = [f["id"] for f in facts]
    try:
        raw = gemini_text(prompt, config)
    except GeminiDescribeError as exc:
        return {fid: ("missing", f"api-error:{exc}") for fid in expected_ids}
    return _parse_judge_batch(raw, expected_ids)


def stage_scoring(case: dict, config: GeminiConfig, force: bool) -> None:
    """Score each fact × each of the 4 columns via LLM-as-judge."""
    facts = case.get("ground_truth_facts") or []
    if not facts:
        print("    scoring: SKIP (no facts)")
        return

    columns = [
        ("descriptions.generic", (case.get("descriptions") or {}).get("generic") or "",
         case.setdefault("description_scores", {}).setdefault("generic", {})),
        ("descriptions.specialized", (case.get("descriptions") or {}).get("specialized") or "",
         case.setdefault("description_scores", {}).setdefault("specialized", {})),
        ("case1.copilot_answer", (case.get("case1") or {}).get("copilot_answer") or "",
         case.setdefault("case1", {}).setdefault("fact_scores", {})),
        ("case2.copilot_answer", (case.get("case2") or {}).get("copilot_answer") or "",
         case.setdefault("case2", {}).setdefault("fact_scores", {})),
    ]

    # Also keep reasons for transparency
    reasons = case.setdefault("score_reasons", {})

    for col_name, subject_text, score_dict in columns:
        if not subject_text or subject_text.startswith("ERROR"):
            print(f"    scoring {col_name}: SKIP (empty/error subject)")
            continue
        col_reasons = reasons.setdefault(col_name, {})
        pending = [f for f in facts if f["id"] not in score_dict or force]
        if not pending:
            print(f"    scoring {col_name}: all {len(facts)} facts already scored")
            continue
        num_batches = (len(pending) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"    scoring {col_name}: {len(pending)} facts in {num_batches} batch(es) of {BATCH_SIZE} ...")
        for batch_idx in range(num_batches):
            batch = pending[batch_idx * BATCH_SIZE : (batch_idx + 1) * BATCH_SIZE]
            results = _score_batch(batch, subject_text, config)
            present = partial = missing = 0
            for fid, (verdict, reason) in results.items():
                score_dict[fid] = verdict
                col_reasons[fid] = reason
                if verdict == "present":
                    present += 1
                elif verdict == "partial":
                    partial += 1
                else:
                    missing += 1
            print(
                f"      batch {batch_idx + 1}/{num_batches}: "
                f"✓{present} △{partial} ✗{missing}"
            )
            # small rate-limit cushion between batches
            time.sleep(0.2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

STAGES = ("descriptions", "answers", "scoring")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="Only run a specific case id (e.g. tc01)")
    parser.add_argument(
        "--stage",
        choices=STAGES,
        help="Only run one stage (default: all three in order)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing non-empty fields (descriptions, answers, scores)",
    )
    args = parser.parse_args()

    yaml_path = ROOT / "test_cases.yaml"
    data = _load_yaml(yaml_path)

    try:
        config = load_config(WORKSPACE)
    except GeminiDescribeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    print(f"Using model: {config.model}")
    stages_to_run = [args.stage] if args.stage else list(STAGES)
    print(f"Stages: {', '.join(stages_to_run)}")
    print(f"Force overwrite: {args.force}")

    cases = data["test_cases"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"ERROR: case {args.case} not found", file=sys.stderr)
            return 2

    for case in cases:
        print(f"\n[{case['id']}] {case['title']}")
        try:
            image_path = resolve_safe(case["image"], WORKSPACE)
        except Exception as exc:  # noqa: BLE001
            print(f"  image error: {exc}", file=sys.stderr)
            continue
        mime = _guess_mime(image_path)
        image_bytes = image_path.read_bytes()

        if "descriptions" in stages_to_run:
            print("  == Stage 1: descriptions ==")
            stage_descriptions(case, image_bytes, mime, config, args.force)
            _dump_yaml(data, yaml_path)

        if "answers" in stages_to_run:
            print("  == Stage 2: answers (Case 1 + Case 2) ==")
            stage_answers(case, image_bytes, mime, config, args.force)
            _dump_yaml(data, yaml_path)

        if "scoring" in stages_to_run:
            print("  == Stage 3: LLM-as-judge scoring ==")
            stage_scoring(case, config, args.force)
            _dump_yaml(data, yaml_path)

    print(f"\nWrote {yaml_path.relative_to(WORKSPACE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
