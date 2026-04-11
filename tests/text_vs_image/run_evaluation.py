#!/usr/bin/env python
"""Fully automated text-vs-image fidelity evaluation (v2 — two-phase).

Phase 1: Describe model comparison (Gemini only)
  - For each extraction case, generate 4 descriptions (2 models x 2 prompts)
  - Score each description against ground_truth_facts using GPT-5.4 as judge
  - Auto-select the best model and write phase1_result

Phase 2: Answer comparison (GPT-5.4)
  - A1 (text_via_gpt): Send descriptions + question as text-only to GPT-5.4
  - A2 (image_via_gpt): Send image + question to GPT-5.4 Vision
  - Extraction: score A1/A2 against ground_truth_facts
  - Judgment: self-scoring via JSON block appended to question prompt

Usage:
    python tests/text_vs_image/run_evaluation.py --phase 1
    python tests/text_vs_image/run_evaluation.py --phase 2
    python tests/text_vs_image/run_evaluation.py --phase all --auto-select
    python tests/text_vs_image/run_evaluation.py --phase 2 --describe-model gemini_3_flash
    python tests/text_vs_image/run_evaluation.py --case tc01 --phase 1
    python tests/text_vs_image/run_evaluation.py --force
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

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent

# ---------------------------------------------------------------------------
# API client setup
# ---------------------------------------------------------------------------

GEMINI_MODELS = {
    "gemini_3_flash": "gemini-3-flash-preview",
    "gemini_31_flash_lite": "gemini-3.1-flash-lite-preview",
}
GPT_MODEL = "gpt-5.4"
BATCH_SIZE = 10
RATE_LIMIT_SLEEP = 0.2


def _load_env() -> None:
    env_path = WORKSPACE / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set in .env or environment")
    return key


def _openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set in .env or environment")
    return key


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

def _extract_answer_text(response) -> str:
    """Extract answer text, filtering out thinking-mode parts."""
    try:
        candidates = response.candidates or []
        if not candidates:
            return (getattr(response, "text", "") or "").strip()
        parts = candidates[0].content.parts or []
        chunks: list[str] = []
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


def gemini_vision(prompt: str, image_bytes: bytes, mime: str,
                  model_name: str) -> str:
    """Image + prompt Gemini call."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_gemini_api_key())
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
    response = client.models.generate_content(
        model=model_name, contents=[prompt, image_part],
    )
    text = _extract_answer_text(response)
    if not text:
        raise RuntimeError("Gemini returned empty vision response")
    return text


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------

def _openai_client():
    from openai import OpenAI
    return OpenAI(api_key=_openai_api_key())


def gpt_text(prompt: str) -> str:
    """Text-only GPT call."""
    client = _openai_client()
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def gpt_vision(prompt: str, image_bytes: bytes, mime: str) -> str:
    """Image + prompt GPT Vision call."""
    client = _openai_client()
    b64 = base64.b64encode(image_bytes).decode()
    response = client.chat.completions.create(
        model=GPT_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# YAML I/O
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dump_yaml(data: dict, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False,
                  default_flow_style=False, width=120)


def _guess_mime(path: Path) -> str:
    return {
        ".png": "image/png", ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")


# ---------------------------------------------------------------------------
# Judge prompt (extraction — batch scoring)
# ---------------------------------------------------------------------------

JUDGE_BATCH_PROMPT = """\
あなたは厳密な事実チェック採点者です。
以下の「確認したい事実リスト」のそれぞれが「与えられたテキスト」に含まれているかを個別に判定してください。

判定基準:
- present: 事実が明確に、正確な値・名前・関係で含まれている
- partial: 部分的に言及されているが、細部 (数値・名前・方向など) が欠けている / ずれている
- missing: 事実が全く言及されていない、または明確に間違っている

出力は次の形式の **JSON 配列のみ** を返してください。説明文・前置き・コードフェンスは一切付けないでください。
配列の順序と要素数は入力の事実リストと完全に一致させてください。

[
  {{"id": "f01", "verdict": "present", "reason": "簡潔な根拠 (日本語 30 文字以内)"}},
  ...
]

=== 確認したい事実リスト (id と本文) ===
{facts}

=== 与えられたテキスト ===
{text}"""

# (Self-score instruction removed — self-scoring always returns 5/5/5/5.
#  Judgment cases now use: C = reasoning_points fact check + A = Gemini cross-score)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_judge_batch(raw: str, expected_ids: list[str]) -> dict:
    """Parse batched judge output -> {fact_id: {"verdict": ..., "reason": ...}}."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return {fid: {"verdict": "missing", "reason": "unparseable"}
                for fid in expected_ids}
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {fid: {"verdict": "missing", "reason": "invalid-json"}
                for fid in expected_ids}
    out: dict[str, dict] = {}
    if isinstance(arr, list):
        for item in arr:
            if not isinstance(item, dict):
                continue
            fid = str(item.get("id", "")).strip()
            verdict = str(item.get("verdict", "")).strip().lower()
            reason = str(item.get("reason", "")).strip()
            if fid and verdict in {"present", "partial", "missing"}:
                out[fid] = {"verdict": verdict, "reason": reason}
    for fid in expected_ids:
        if fid not in out:
            out[fid] = {"verdict": "missing", "reason": "not-returned-by-judge"}
    return out




# ---------------------------------------------------------------------------
# Score one batch of facts via GPT-5.4
# ---------------------------------------------------------------------------

def _score_fact_batch(facts: list[dict], subject_text: str) -> dict:
    """Score up to BATCH_SIZE facts. Returns {id: {verdict, reason}}."""
    facts_section = "\n".join(f"- {f['id']}: {f['text']}" for f in facts)
    prompt = JUDGE_BATCH_PROMPT.format(facts=facts_section, text=subject_text)
    expected_ids = [f["id"] for f in facts]
    try:
        raw = gpt_text(prompt)
    except Exception as exc:  # noqa: BLE001
        return {fid: {"verdict": "missing", "reason": f"api-error:{exc}"}
                for fid in expected_ids}
    return _parse_judge_batch(raw, expected_ids)


def _score_all_facts(facts: list[dict], subject_text: str,
                     label: str) -> dict:
    """Score all facts in batches, printing progress. Returns merged dict."""
    if not subject_text or subject_text.startswith("ERROR"):
        print(f"    score {label}: SKIP (empty/error)")
        return {}
    num_batches = (len(facts) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"    score {label}: {len(facts)} facts in {num_batches} batch(es)")
    merged: dict = {}
    for i in range(num_batches):
        batch = facts[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        results = _score_fact_batch(batch, subject_text)
        counts = {"present": 0, "partial": 0, "missing": 0}
        for v in results.values():
            counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
        merged.update(results)
        print(f"      batch {i+1}/{num_batches}: "
              f"P={counts['present']} A={counts['partial']} M={counts['missing']}")
        time.sleep(RATE_LIMIT_SLEEP)
    return merged


# ---------------------------------------------------------------------------
# Phase 1: Describe + Score descriptions
# ---------------------------------------------------------------------------

def _call_gemini_describe(label: str, prompt: str, image_bytes: bytes,
                          mime: str, model_name: str,
                          target: dict, field: str, force: bool) -> None:
    """Call Gemini Vision for one description slot, with skip/error handling."""
    if target.get(field) and not force:
        print(f"    {label}: SKIP (exists)")
        return
    print(f"    {label}: calling {model_name} ...")
    try:
        text = gemini_vision(prompt, image_bytes, mime, model_name)
        target[field] = text
        print(f"      OK ({len(text)} chars)")
    except Exception as exc:  # noqa: BLE001
        print(f"      FAIL: {exc}", file=sys.stderr)
        target[field] = f"ERROR: {exc}"
    time.sleep(RATE_LIMIT_SLEEP)


def _generate_descriptions(case: dict, image_bytes: bytes, mime: str,
                           force: bool) -> None:
    """Generate D1-D4 descriptions for one case."""
    generic_prompt = (ROOT / "prompts" / "generic.md").read_text(encoding="utf-8")
    spec_rel = case.get("specialized_prompt")
    spec_prompt = (ROOT / spec_rel).read_text(encoding="utf-8") if spec_rel else ""

    descs = case.setdefault("descriptions", {})
    for model_key, model_name in GEMINI_MODELS.items():
        model_descs = descs.setdefault(model_key, {"generic": "", "specialized": ""})
        _call_gemini_describe(f"{model_key}/generic", generic_prompt,
                              image_bytes, mime, model_name,
                              model_descs, "generic", force)
        if not spec_prompt:
            print(f"    {model_key}/specialized: SKIP (no prompt)")
            continue
        _call_gemini_describe(f"{model_key}/specialized", spec_prompt,
                              image_bytes, mime, model_name,
                              model_descs, "specialized", force)


def _score_descriptions(case: dict, force: bool) -> None:
    """Score D1-D4 descriptions against ground_truth_facts (extraction only)."""
    if case.get("test_type") != "extraction":
        return
    facts = case.get("ground_truth_facts") or []
    if not facts:
        print("    description scoring: SKIP (no facts)")
        return

    desc_scores = case.setdefault("description_scores", {})
    descs = case.get("descriptions") or {}

    for model_key in GEMINI_MODELS:
        model_scores = desc_scores.setdefault(
            model_key, {"generic": {}, "specialized": {}})
        model_descs = descs.get(model_key) or {}

        for variant in ("generic", "specialized"):
            label = f"{model_key}/{variant}"
            existing = model_scores.get(variant) or {}
            if existing and not force:
                print(f"    score {label}: SKIP (exists)")
                continue
            text = model_descs.get(variant) or ""
            result = _score_all_facts(facts, text, label)
            model_scores[variant] = result


def _run_phase1(case: dict, image_bytes: bytes, mime: str,
                force: bool) -> None:
    """Phase 1 for one case: describe + score (extraction only)."""
    cid = case["id"]
    print(f"  -- Phase 1: describe ({cid}) --")
    _generate_descriptions(case, image_bytes, mime, force)
    print(f"  -- Phase 1: score descriptions ({cid}) --")
    _score_descriptions(case, force)


def _verdict_to_score(v) -> float:
    """Convert a verdict (dict or string) to a numeric score."""
    verdict = v.get("verdict", "missing") if isinstance(v, dict) else v
    return {"present": 1.0, "partial": 0.5}.get(verdict, 0.0)


def _avg_score_across_cases(cases: list[dict], model_key: str,
                            variant: str) -> float | None:
    """Compute average fact score (present=1, partial=0.5, missing=0)."""
    totals: list[float] = []
    for case in cases:
        scores = (case.get("description_scores") or {}).get(
            model_key, {}).get(variant, {})
        if not scores:
            continue
        totals.extend(_verdict_to_score(v) for v in scores.values())
    return round(sum(totals) / len(totals), 4) if totals else None


def _default_phase1() -> dict:
    return {
        "selected_model": None, "selection_reason": "",
        "scores_summary": {
            "gemini_3_flash": {"avg_generic": None, "avg_specialized": None},
            "gemini_31_flash_lite": {"avg_generic": None, "avg_specialized": None},
        },
    }


def _compute_phase1_result(data: dict, force: bool) -> None:
    """Compute average scores per model across extraction cases, select best."""
    phase1 = data.setdefault("phase1_result", _default_phase1())
    if phase1.get("selected_model") and not force:
        print(f"\nPhase 1 result: already selected "
              f"'{phase1['selected_model']}' (use --force to recompute)")
        return

    extraction_cases = [c for c in data["test_cases"]
                        if c.get("test_type") == "extraction"]
    summary = phase1.setdefault("scores_summary", {})

    best_model = None
    best_avg = -1.0
    for model_key in GEMINI_MODELS:
        avg_g = _avg_score_across_cases(extraction_cases, model_key, "generic")
        avg_s = _avg_score_across_cases(extraction_cases, model_key, "specialized")
        model_summary = summary.setdefault(
            model_key, {"avg_generic": None, "avg_specialized": None})
        model_summary["avg_generic"] = avg_g
        model_summary["avg_specialized"] = avg_s
        if avg_g is not None and avg_s is not None:
            combined = (avg_g + avg_s) / 2
            if combined > best_avg:
                best_avg = combined
                best_model = model_key
        print(f"  {model_key}: avg_generic={avg_g}, avg_specialized={avg_s}")

    if best_model:
        phase1["selected_model"] = best_model
        phase1["selection_reason"] = (
            f"Highest combined avg score ({best_avg:.4f}) across extraction cases")
        print(f"\n  Selected model: {best_model} (combined avg={best_avg:.4f})")
    else:
        print("\n  WARNING: Could not determine best model (no scores available)")


# ---------------------------------------------------------------------------
# Phase 2: Answer + Score answers
# ---------------------------------------------------------------------------

def _get_selected_model(data: dict, override: str | None) -> str:
    """Determine which describe model to use for Phase 2."""
    if override:
        if override not in GEMINI_MODELS:
            raise RuntimeError(
                f"Unknown model '{override}'. Choose from: {list(GEMINI_MODELS)}")
        return override
    selected = (data.get("phase1_result") or {}).get("selected_model")
    if not selected:
        raise RuntimeError(
            "No model selected. Run --phase 1 first, or pass --describe-model")
    return selected


def _build_text_prompt(case: dict, model_key: str) -> str:
    """Build the text-only answer prompt using descriptions from model_key."""
    descs = (case.get("descriptions") or {}).get(model_key) or {}
    d_generic = descs.get("generic") or ""
    d_specialized = descs.get("specialized") or ""
    question = case["question"].strip()

    prompt = (
        "以下は、ある画像を別の Vision LLM が文字化した記述です（汎用記述 + 専用記述）。\n"
        "この記述を画像の代わりとして使い、後ろの質問に日本語で答えてください。\n"
        "画像に関する事実（要素、数値、配置など）はこの記述を根拠にし、\n"
        "判断や推論には一般的なドメイン知識を自由に使って構いません。\n\n"
        f"=== 汎用記述 ===\n{d_generic}\n\n"
        f"=== 専用記述 ===\n{d_specialized}\n\n"
        f"=== 質問 ===\n{question}"
    )
    return prompt


def _init_answer_slot(answer: dict, slot: str) -> dict:
    """Ensure answer[slot] exists with the right structure."""
    return answer.setdefault(slot, {"response": "", "fact_scores": {}})


def _call_gpt_answer(label: str, prompt: str, ans_dict: dict,
                     force: bool,
                     image_bytes: bytes | None = None,
                     mime: str = "") -> None:
    """Generate one GPT answer (text or vision)."""
    if ans_dict.get("response") and not force:
        print(f"    {label}: SKIP (exists)")
        return
    use_vision = image_bytes is not None
    mode = "Vision" if use_vision else "text"
    print(f"    {label}: calling GPT-5.4 {mode} ...")
    try:
        resp = gpt_vision(prompt, image_bytes, mime) if use_vision else gpt_text(prompt)
        ans_dict["response"] = resp
        print(f"      OK ({len(resp)} chars)")
    except Exception as exc:  # noqa: BLE001
        print(f"      FAIL: {exc}", file=sys.stderr)
        ans_dict["response"] = f"ERROR: {exc}"
    time.sleep(RATE_LIMIT_SLEEP)


def _score_answer_facts(facts: list[dict], ans_dict: dict,
                        label: str, force: bool) -> None:
    """Score an answer's response against ground_truth_facts."""
    existing = ans_dict.get("fact_scores") or {}
    if existing and not force:
        print(f"    score {label}: SKIP (exists)")
        return
    resp_text = ans_dict.get("response") or ""
    ans_dict["fact_scores"] = _score_all_facts(facts, resp_text, label)



def _run_phase2_case(case: dict, image_bytes: bytes, mime: str,
                     model_key: str, force: bool) -> None:
    """Phase 2 for one case: generate answers + score them."""
    cid = case["id"]
    question = case["question"].strip()
    is_judgment = case.get("test_type") == "judgment"

    answer = case.setdefault("answer", {})
    text_ans = _init_answer_slot(answer, "text_via_gpt")
    image_ans = _init_answer_slot(answer, "image_via_gpt")

    # A1: text_via_gpt
    text_prompt = _build_text_prompt(case, model_key)
    _call_gpt_answer(f"A1 text_via_gpt ({cid})", text_prompt,
                     text_ans, force)

    # A2: image_via_gpt
    img_prompt = f"添付の画像を参照して、以下の質問に日本語で答えてください。\n\n{question}"
    _call_gpt_answer(f"A2 image_via_gpt ({cid})", img_prompt,
                     image_ans, force,
                     image_bytes=image_bytes, mime=mime)

    # Score answers against facts (extraction) or reasoning_points (judgment)
    if is_judgment:
        reasoning = case.get("reasoning_points") or []
        if reasoning:
            _score_answer_facts(reasoning, text_ans, f"text_via_gpt/{cid}", force)
            _score_answer_facts(reasoning, image_ans, f"image_via_gpt/{cid}", force)
    else:
        facts = case.get("ground_truth_facts") or []
        if facts:
            _score_answer_facts(facts, text_ans, f"text_via_gpt/{cid}", force)
            _score_answer_facts(facts, image_ans, f"image_via_gpt/{cid}", force)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_image(case: dict) -> tuple[bytes, str] | None:
    """Load image bytes and mime type for a case. Returns None on error."""
    image_path = (WORKSPACE / case["image"]).resolve()
    if not image_path.exists():
        print(f"  ERROR: image not found: {image_path}", file=sys.stderr)
        return None
    return image_path.read_bytes(), _guess_mime(image_path)


def _run_phase1_loop(cases: list[dict], data: dict,
                     yaml_path: Path, force: bool) -> None:
    """Run Phase 1 across all cases, then compute result."""
    print("\n===== PHASE 1: Describe model comparison =====")
    for case in cases:
        print(f"\n[{case['id']}] {case.get('title', '')}")
        loaded = _load_image(case)
        if not loaded:
            continue
        image_bytes, mime = loaded
        _run_phase1(case, image_bytes, mime, force)
        _dump_yaml(data, yaml_path)
    print("\n--- Phase 1 summary ---")
    _compute_phase1_result(data, force)
    _dump_yaml(data, yaml_path)


def _run_phase2_loop(cases: list[dict], data: dict, yaml_path: Path,
                     describe_model: str | None, force: bool) -> int:
    """Run Phase 2 across all cases. Returns non-zero on fatal error."""
    print("\n===== PHASE 2: Answer comparison (GPT-5.4) =====")
    try:
        model_key = _get_selected_model(data, describe_model)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    print(f"Using descriptions from: {model_key}")
    for case in cases:
        print(f"\n[{case['id']}] {case.get('title', '')}")
        loaded = _load_image(case)
        if not loaded:
            continue
        image_bytes, mime = loaded
        _run_phase2_case(case, image_bytes, mime, model_key, force)
        _dump_yaml(data, yaml_path)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", choices=["1", "2", "all"], default="all",
                        help="Which phase to run (default: all)")
    parser.add_argument("--case", help="Only run a specific case id (e.g. tc01)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing non-empty fields")
    parser.add_argument("--auto-select", action="store_true",
                        help="Auto-select best model after Phase 1")
    parser.add_argument("--describe-model", choices=list(GEMINI_MODELS),
                        help="Override describe model for Phase 2")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run_p1 = args.phase in ("1", "all")
    run_p2 = args.phase in ("2", "all")

    _load_env()

    yaml_path = ROOT / "test_cases.yaml"
    data = _load_yaml(yaml_path)

    cases = data["test_cases"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"ERROR: case '{args.case}' not found", file=sys.stderr)
            return 2

    print(f"Phase(s): {'1' if run_p1 else ''}"
          f"{'+ ' if run_p1 and run_p2 else ''}"
          f"{'2' if run_p2 else ''}")
    print(f"Cases: {[c['id'] for c in cases]}")
    print(f"Force: {args.force}")

    if run_p1:
        _run_phase1_loop(cases, data, yaml_path, args.force)

    if run_p2:
        rc = _run_phase2_loop(cases, data, yaml_path,
                              args.describe_model, args.force)
        if rc:
            return rc

    print(f"\nDone. Results written to {yaml_path.relative_to(WORKSPACE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
