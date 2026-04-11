#!/usr/bin/env python
"""Generate report.html (v2) from test_cases.yaml.

Renders a single self-contained HTML page with:
- Phase 1: Gemini model comparison (describe matrix, per-case detail)
- Phase 2: GPT-5.4 text vs image answer comparison
- Mermaid blocks rendered live via mermaid.js CDN
- Markdown blocks rendered via marked.js CDN

Run:
    python tests/text_vs_image/generate_report.py
"""
from __future__ import annotations

import base64
import html as html_mod
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent

# ---------------------------------------------------------------------------
# Score helpers
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {"present": 1.0, "partial": 0.5, "missing": 0.0}

DESCRIBE_COLUMNS = [
    # (model_key, prompt_key, short_label, css_class)
    ("gemini_3_flash", "generic", "D1", "flash"),
    ("gemini_3_flash", "specialized", "D2", "flash"),
    ("gemini_31_flash_lite", "generic", "D3", "lite"),
    ("gemini_31_flash_lite", "specialized", "D4", "lite"),
]

ANSWER_COLUMNS = [
    # (answer_key, short_label)
    ("text_via_gpt", "A1"),
    ("image_via_gpt", "A2"),
]

PROMPT_FILES = [
    ("generic.md", "Generic (汎用)", "All image types", "全画像タイプ共通の構造的記述プロンプト。OCR・図表構造・色・レイアウトを網羅的に記述させる。"),
    ("mixed_slide.md", "Mixed Slide", "mixed_slide", "pptxスライド画像用。フロー・グラフ・表・コードなど複数情報種別を漏れなく抽出するステップ式プロンプト。"),
    ("ui_change.md", "UI Change Request", "ui_change_request", "UIモックアップ+変更要求吹き出し画像用。既存要素と変更要求を分離して構造化するプロンプト。"),
    ("architecture_mermaid.md", "Architecture / Mermaid", "cloud_architecture", "システム構成図用。Mermaid flowchart形式でノード・接続・グルーピングを再現するプロンプト。"),
    ("text_document.md", "Text Document", "text_document", "文書スクリーンショット用。Markdown形式で完全転写するプロンプト。"),
]


def _img_to_data_uri(image_path: Path) -> str:
    suffix = image_path.suffix.lower().lstrip(".")
    mime = "png" if suffix == "png" else "jpeg"
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def _get_describe_scores(case: dict, model_key: str, prompt_key: str) -> dict:
    """Return {fact_id: {verdict, reason}} for a describe column."""
    return (
        (case.get("description_scores") or {})
        .get(model_key, {})
        .get(prompt_key, {})
    )


def _get_describe_text(case: dict, model_key: str, prompt_key: str) -> str:
    return (
        (case.get("descriptions") or {})
        .get(model_key, {})
        .get(prompt_key, "")
    )


def _get_answer_scores(case: dict, answer_key: str) -> dict:
    """Return {fact_id: {verdict, reason}} for an answer column."""
    return (case.get("answer") or {}).get(answer_key, {}).get("fact_scores", {})


def _get_answer_text(case: dict, answer_key: str) -> str:
    return (case.get("answer") or {}).get(answer_key, {}).get("response", "")


def _calc_score_pct(scores: dict, fact_ids: list[str]) -> float | None:
    """Calculate percentage score. Returns None if no facts."""
    if not fact_ids:
        return None
    total = 0.0
    for fid in fact_ids:
        entry = scores.get(fid, {})
        verdict = entry.get("verdict") if isinstance(entry, dict) else entry
        total += SCORE_WEIGHTS.get(verdict, 0.0)
    return total / len(fact_ids) * 100


def _fact_ids_for(case: dict) -> list[str]:
    """Get fact IDs -- ground_truth_facts for extraction, reasoning_points for judgment."""
    if case.get("test_type") == "judgment":
        return [f["id"] for f in (case.get("reasoning_points") or [])]
    return [f["id"] for f in (case.get("ground_truth_facts") or [])]


def _facts_for(case: dict) -> list[dict]:
    if case.get("test_type") == "judgment":
        return case.get("reasoning_points") or []
    return case.get("ground_truth_facts") or []


def _read_prompt_file(filename: str) -> str:
    p = ROOT / "prompts" / filename
    if p.exists():
        return p.read_text(encoding="utf-8")
    return f"(file not found: {filename})"


def _safe_avg(values: list[float]) -> float:
    """Return average of values, or 0.0 if empty."""
    return round(sum(values) / len(values), 1) if values else 0.0


def _round_pct(pct: float | None) -> float | None:
    return round(pct, 1) if pct is not None else None


# ---------------------------------------------------------------------------
# Build JSON payload -- split into focused helpers
# ---------------------------------------------------------------------------

def _build_describe_matrix(extraction_cases: list[dict]) -> dict:
    """Average describe score per D1/D2/D3/D4 across extraction cases."""
    matrix = {}
    for model_key, prompt_key, label, _ in DESCRIBE_COLUMNS:
        pcts = [
            _calc_score_pct(
                _get_describe_scores(c, model_key, prompt_key),
                _fact_ids_for(c),
            )
            for c in extraction_cases
        ]
        matrix[label] = _safe_avg([p for p in pcts if p is not None])
    return matrix


def _build_model_avgs(extraction_cases: list[dict]) -> dict:
    """Per-model average for generic and specialized prompts."""
    avgs: dict = {}
    for model_key in ("gemini_3_flash", "gemini_31_flash_lite"):
        gen, spec = [], []
        for case in extraction_cases:
            fids = _fact_ids_for(case)
            gp = _calc_score_pct(_get_describe_scores(case, model_key, "generic"), fids)
            sp = _calc_score_pct(_get_describe_scores(case, model_key, "specialized"), fids)
            if gp is not None:
                gen.append(gp)
            if sp is not None:
                spec.append(sp)
        avgs[model_key] = {"generic": _safe_avg(gen), "specialized": _safe_avg(spec)}
    return avgs


def _build_case_payload(case: dict) -> dict:
    """Build the JSON-serialisable payload for a single test case."""
    image_path = WORKSPACE / case["image"]
    fids = _fact_ids_for(case)
    facts = _facts_for(case)

    describe_cols = {
        label: {
            "text": (text := _get_describe_text(case, mk, pk)),
            "char_count": len(text),
            "scores": _get_describe_scores(case, mk, pk),
            "pct": _round_pct(_calc_score_pct(_get_describe_scores(case, mk, pk), fids)),
            "tint": tint,
        }
        for mk, pk, label, tint in DESCRIBE_COLUMNS
    }

    answer_cols = {
        label: {
            "text": (text := _get_answer_text(case, ak)),
            "char_count": len(text),
            "scores": _get_answer_scores(case, ak),
            "pct": _round_pct(_calc_score_pct(_get_answer_scores(case, ak), fids)),
        }
        for ak, label in ANSWER_COLUMNS
    }

    return {
        "id": case["id"],
        "title": case["title"],
        "test_type": case.get("test_type", "extraction"),
        "image": case["image"],
        "image_data_uri": _img_to_data_uri(image_path) if image_path.exists() else "",
        "image_type": case.get("image_type", ""),
        "specialized_prompt": case.get("specialized_prompt", ""),
        "question": case.get("question", "").strip(),
        "facts": [{"id": f["id"], "text": f["text"]} for f in facts],
        "describe_cols": describe_cols,
        "answer_cols": answer_cols,
    }


def _build_prompts_payload() -> list[dict]:
    return [
        {
            "filename": fn,
            "display_name": dn,
            "applies_to": at,
            "intent": intent,
            "content": _read_prompt_file(fn),
        }
        for fn, dn, at, intent in PROMPT_FILES
    ]


def _build_phase2_summary(extraction_cases: list[dict]) -> dict:
    a1_all, a2_all = [], []
    for case in extraction_cases:
        fids = _fact_ids_for(case)
        a1p = _calc_score_pct(_get_answer_scores(case, "text_via_gpt"), fids)
        a2p = _calc_score_pct(_get_answer_scores(case, "image_via_gpt"), fids)
        if a1p is not None:
            a1_all.append(a1p)
        if a2p is not None:
            a2_all.append(a2p)
    return {"a1_avg": _safe_avg(a1_all), "a2_avg": _safe_avg(a2_all)}


def _build_payload(data: dict) -> dict:
    cases = data.get("test_cases") or []
    extraction_cases = [c for c in cases if c.get("test_type") == "extraction"]
    judgment_cases = [c for c in cases if c.get("test_type") == "judgment"]

    return {
        "cases": [_build_case_payload(c) for c in cases],
        "extraction_ids": [c["id"] for c in extraction_cases],
        "judgment_ids": [c["id"] for c in judgment_cases],
        "describe_matrix": _build_describe_matrix(extraction_cases),
        "model_avgs": _build_model_avgs(extraction_cases),
        "phase1_result": data.get("phase1_result") or {},
        "phase2_summary": _build_phase2_summary(extraction_cases),
        "prompts": _build_prompts_payload(),
    }


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>Text vs Image Fidelity Report v2</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg: #f8fafc;
  --card: #ffffff;
  --border: #e2e8f0;
  --text: #1e293b;
  --muted: #64748b;
  --accent: #2563eb;
  --present: #16a34a;
  --partial: #ca8a04;
  --missing: #dc2626;
  --na: #9ca3af;
  --flash-bg: #eff6ff;
  --flash-border: #93c5fd;
  --lite-bg: #f5f3ff;
  --lite-border: #c4b5fd;
  --answer-bg: #f0fdf4;
  --answer-border: #86efac;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", "Hiragino Sans", "Yu Gothic UI", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
  margin: 0;
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
h1 { font-size: 28px; margin-top: 0; color: var(--text); }
h2 { font-size: 22px; margin-top: 32px; color: var(--text); }
h3 { font-size: 16px; color: var(--text); }
.subtitle { color: var(--muted); font-size: 14px; margin-bottom: 24px; }
.section {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}
.muted { color: var(--muted); font-size: 13px; }

/* Model info table */
.model-table { border-collapse: collapse; font-size: 13px; margin: 12px 0; }
.model-table th, .model-table td { padding: 6px 12px; border: 1px solid var(--border); }
.model-table th { background: var(--bg); font-weight: 600; }

/* Describe matrix */
.matrix-table { border-collapse: collapse; font-size: 14px; margin: 16px 0; }
.matrix-table th, .matrix-table td { padding: 10px 20px; border: 1px solid var(--border); text-align: center; }
.matrix-table th { background: var(--bg); font-weight: 600; }
.matrix-table .winner { background: #dcfce7; font-weight: 700; }
.matrix-table .model-name { text-align: left; font-weight: 600; }

/* Fact table */
.fact-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
.fact-table th, .fact-table td { padding: 6px 8px; border: 1px solid var(--border); text-align: left; vertical-align: top; }
.fact-table th { background: var(--bg); font-weight: 600; font-size: 12px; }
.fact-table td.score { text-align: center; font-weight: 700; font-size: 18px; cursor: default; }
.score-present { color: var(--present); }
.score-partial { color: var(--partial); }
.score-missing { color: var(--missing); }
.score-na { color: var(--na); }

/* Case card */
.case-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}
.case-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 12px;
}
.case-header h3 { margin: 0; }
.tag {
  display: inline-block;
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--muted);
  margin-left: 8px;
}
.case-body {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
  margin-bottom: 16px;
}
.case-image img { max-width: 100%; border: 1px solid var(--border); border-radius: 8px; }
.question-block {
  background: var(--bg);
  border-left: 4px solid var(--accent);
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 13px;
  white-space: pre-wrap;
}

/* Description cards grid */
.desc-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px; }
.desc-card {
  border: 2px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  position: relative;
  display: flex;
  flex-direction: column;
}
.desc-card.flash { background: var(--flash-bg); border-color: var(--flash-border); }
.desc-card.lite { background: var(--lite-bg); border-color: var(--lite-border); }
.desc-card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.desc-card-label { font-weight: 700; font-size: 14px; }
.desc-card-meta { font-size: 11px; color: var(--muted); }
.desc-card-score { font-size: 14px; font-weight: 700; color: var(--accent); }
.desc-card-content {
  font-size: 11px;
  white-space: pre-wrap;
  background: white;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px;
  max-height: 200px;
  overflow-y: auto;
  flex-grow: 1;
}
.desc-card-content.rendered { white-space: normal; }

/* Answer cards */
.answer-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 12px; }
.answer-card {
  border: 2px solid var(--answer-border);
  background: var(--answer-bg);
  border-radius: 8px;
  padding: 12px;
  position: relative;
  display: flex;
  flex-direction: column;
}
.answer-card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.answer-card-label { font-weight: 700; font-size: 14px; }
.answer-card-score { font-size: 14px; font-weight: 700; color: var(--accent); }
.answer-card-content {
  font-size: 11px;
  white-space: pre-wrap;
  background: white;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px;
  max-height: 300px;
  overflow-y: auto;
  flex-grow: 1;
}
.answer-card-content.rendered { white-space: normal; }

/* Expand button */
.expand-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: pointer;
  color: var(--muted);
  z-index: 2;
}
.expand-btn:hover { color: var(--accent); border-color: var(--accent); }

/* Modal */
.modal-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  z-index: 1000;
  align-items: center;
  justify-content: center;
  padding: 32px;
}
.modal-overlay.open { display: flex; }
.modal-box {
  background: white;
  border-radius: 12px;
  max-width: 1000px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.modal-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h3 { margin: 0; }
.modal-close { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--muted); }
.modal-body { padding: 24px; overflow-y: auto; flex-grow: 1; }
.modal-body .rendered-md { white-space: normal; }
.modal-body .rendered-md pre { white-space: pre-wrap; word-wrap: break-word; }
.modal-body .mermaid { background: white; text-align: center; margin: 8px 0; }

/* Phase 1 result banner */
.phase1-banner {
  background: #dcfce7;
  border: 2px solid #86efac;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
}
.phase1-banner strong { color: #15803d; }

/* Prompt details */
details { margin: 8px 0; }
details summary { cursor: pointer; font-weight: 600; font-size: 14px; color: var(--accent); padding: 4px 0; }
details summary:hover { text-decoration: underline; }
details .prompt-content {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 12px;
  white-space: pre-wrap;
  margin-top: 8px;
  max-height: 400px;
  overflow-y: auto;
}
.prompt-meta { font-size: 12px; color: var(--muted); margin: 4px 0 0 0; }

/* Phase 2 flow diagram */
.flow-diagram {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 13px;
  line-height: 1.8;
  margin: 16px 0;
  white-space: pre;
  overflow-x: auto;
}

/* Legend */
.legend {
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  margin: 16px 0 8px;
  padding: 8px 12px;
  background: var(--bg);
  border-radius: 6px;
}
.legend span { font-weight: 700; font-size: 16px; margin-right: 4px; }

/* TOC */
.toc { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px 24px; margin-bottom: 24px; }
.toc ol { margin: 8px 0 0 0; padding-left: 20px; }
.toc a { color: var(--accent); text-decoration: none; }
.toc a:hover { text-decoration: underline; }

/* Summary comparison table */
.cmp-table { border-collapse: collapse; font-size: 14px; margin: 16px 0; }
.cmp-table th, .cmp-table td { padding: 8px 16px; border: 1px solid var(--border); text-align: center; }
.cmp-table th { background: var(--bg); font-weight: 600; }
.cmp-table .better { background: #dcfce7; font-weight: 700; }

/* Future work */
.future-list { list-style: none; padding: 0; }
.future-list li { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
.future-list li:last-child { border-bottom: none; }
.future-list .future-tag {
  display: inline-block;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  margin-right: 8px;
}

@media (max-width: 1100px) {
  .case-body { grid-template-columns: 1fr; }
  .desc-grid { grid-template-columns: 1fr 1fr; }
  .answer-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<!-- ===================== HEADER ===================== -->
<h1>Text vs Image Fidelity Report v2</h1>
<p class="subtitle">
  <strong>Phase 1</strong> = Gemini model comparison (which model produces better image descriptions)<br>
  <strong>Phase 2</strong> = GPT-5.4 text vs image (does GPT perform better with text descriptions or direct image input?)
</p>

<table class="model-table">
  <tr><th>Role</th><th>Model</th><th>Purpose</th></tr>
  <tr><td>Describe</td><td>gemini-3-flash / gemini-3.1-flash-lite</td><td>Generate text descriptions from images (Phase 1)</td></tr>
  <tr><td>Answer</td><td>GPT-5.4</td><td>Answer questions using text or image (Phase 2)</td></tr>
  <tr><td>Judge</td><td>GPT-5.4</td><td>Score answers against ground truth facts</td></tr>
</table>

<div class="legend">
  <span class="score-present">&#10003;</span> present (1.0)
  <span class="score-partial">&#9651;</span> partial (0.5)
  <span class="score-missing">&#10007;</span> missing (0.0)
  <span class="score-na">&mdash;</span> not scored
</div>

<div class="toc">
  <strong>Table of Contents</strong>
  <ol>
    <li><a href="#phase1">Phase 1: Describe Model Comparison</a></li>
    <li><a href="#phase1-detail">Phase 1: Per-Case Detail (extraction)</a></li>
    <li><a href="#phase2">Phase 2: Answer Comparison (extraction)</a></li>
    <li><a href="#phase2-judgment">Phase 2: Answer Comparison (judgment)</a></li>
    <li><a href="#future">Future Work</a></li>
  </ol>
</div>

<!-- ===================== PHASE 1 ===================== -->
<div class="section" id="phase1">
  <h2>Phase 1: Describe Model Comparison</h2>
  <p class="muted">Two Gemini models each produce two descriptions (generic + specialized prompt) per image. Scored against ground truth facts. Extraction cases only.</p>

  <div id="mermaid-flow" style="margin:16px 0;">
    <div class="mermaid">
flowchart LR
    IMG["Image"] --> GF["gemini-3-flash"]
    IMG --> GL["gemini-3.1-flash-lite"]
    GF -->|generic.md| D1["D1"]
    GF -->|specialized| D2["D2"]
    GL -->|generic.md| D3["D3"]
    GL -->|specialized| D4["D4"]
    D1 & D2 -->|text| GPT["GPT-5.4"]
    IMG -->|vision| GPT
    GPT --> A1["A1 text answer"]
    GPT --> A2["A2 image answer"]
    </div>
  </div>

  <!-- Prompt documentation -->
  <h3>Prompt Documentation</h3>
  <div id="prompts-section"></div>

  <!-- Describe matrix -->
  <h3>Describe Matrix Summary (extraction cases)</h3>
  <div id="matrix-section"></div>
</div>

<!-- ===================== PHASE 1 DETAIL ===================== -->
<div id="phase1-detail">
  <h2>Phase 1: Per-Case Detail (extraction)</h2>
  <div id="phase1-cases"></div>
</div>

<!-- ===================== PHASE 2 ===================== -->
<div class="section" id="phase2">
  <h2>Phase 2: Answer Comparison (extraction)</h2>
  <p class="muted">GPT-5.4 answers questions via two paths: A1 = text descriptions (D_generic + D_specialized from Phase 1 winner), A2 = direct image input.</p>

  <div class="flow-diagram">A1 (text via GPT): D_generic + D_specialized + question  -->  GPT-5.4 text   --> answer
A2 (image via GPT):              image + question  -->  GPT-5.4 vision --> answer</div>

  <div id="phase2-summary-table"></div>
  <div id="phase2-cases"></div>
</div>

<!-- ===================== PHASE 2 JUDGMENT ===================== -->
<div id="phase2-judgment">
  <h2>Phase 2: Answer Comparison (judgment)</h2>
  <p class="muted">Judgment cases test reasoning quality rather than factual extraction. Scored against reasoning_points.</p>
  <div id="judgment-cases"></div>
</div>

<!-- ===================== FUTURE WORK ===================== -->
<div class="section" id="future">
  <h2>Future Work</h2>
  <ul class="future-list">
    <li><span class="future-tag">Pipeline</span> pptx image extraction pipeline &mdash; automated slide-to-image conversion for batch processing</li>
    <li><span class="future-tag">Quality</span> Image preprocessing &mdash; contrast enhancement, denoising, resolution normalization before description</li>
    <li><span class="future-tag">Routing</span> Image type auto-detection dispatch layer &mdash; automatically select specialized prompt based on image content</li>
    <li><span class="future-tag">Integration</span> Copilot Chat integration &mdash; plug the describe-then-answer pipeline into GitHub Copilot Chat</li>
  </ul>
</div>

<!-- ===================== MODAL ===================== -->
<div id="modal" class="modal-overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal-box">
    <div class="modal-header">
      <h3 id="modal-title"></h3>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;

mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });

function esc(str) {
  return (str || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function renderMd(text) {
  if (!text || !text.trim()) return '<em class="muted">(empty)</em>';
  let html;
  try { html = marked.parse(text, { breaks: true, gfm: true }); }
  catch(e) { html = '<pre>' + esc(text) + '</pre>'; }
  html = html.replace(
    /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g,
    (m, code) => '<div class="mermaid">' + code.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'") + '</div>'
  );
  return html;
}

function verdictIcon(v) {
  if (!v) return {icon: '\u2014', cls: 'score-na'};
  const map = {present: {icon: '\u2713', cls: 'score-present'}, partial: {icon: '\u25B3', cls: 'score-partial'}, missing: {icon: '\u2717', cls: 'score-missing'}};
  return map[v] || {icon: '\u2014', cls: 'score-na'};
}

function getVerdict(scores, fid) {
  const entry = scores[fid];
  if (!entry) return {verdict: null, reason: ''};
  if (typeof entry === 'string') return {verdict: entry, reason: ''};
  return {verdict: entry.verdict || null, reason: entry.reason || ''};
}

// =========================================================================
// Phase 1: Prompts
// =========================================================================
function renderPrompts() {
  const el = document.getElementById('prompts-section');
  let html = '';
  for (const p of DATA.prompts) {
    html += `<details>
      <summary>${esc(p.display_name)} <span class="muted" style="font-weight:normal;font-size:12px;">(${esc(p.applies_to)})</span></summary>
      <p class="prompt-meta">${esc(p.intent)}</p>
      <div class="prompt-content">${esc(p.content)}</div>
    </details>`;
  }
  el.innerHTML = html;
}

// =========================================================================
// Phase 1: Matrix
// =========================================================================
function renderMatrix() {
  const el = document.getElementById('matrix-section');
  const ma = DATA.model_avgs;
  const p1 = DATA.phase1_result;

  // Find best scores for highlighting
  const flash_avg = (ma.gemini_3_flash.generic + ma.gemini_3_flash.specialized) / 2;
  const lite_avg = (ma.gemini_31_flash_lite.generic + ma.gemini_31_flash_lite.specialized) / 2;

  let html = '<table class="matrix-table"><thead><tr><th></th><th>generic</th><th>specialized</th><th>avg</th></tr></thead><tbody>';

  // Flash row
  const flashIsWinner = flash_avg >= lite_avg;
  html += '<tr>';
  html += '<td class="model-name">gemini-3-flash</td>';
  html += `<td${ma.gemini_3_flash.generic >= ma.gemini_31_flash_lite.generic ? ' class="winner"' : ''}>${ma.gemini_3_flash.generic.toFixed(1)}%</td>`;
  html += `<td${ma.gemini_3_flash.specialized >= ma.gemini_31_flash_lite.specialized ? ' class="winner"' : ''}>${ma.gemini_3_flash.specialized.toFixed(1)}%</td>`;
  html += `<td${flashIsWinner ? ' class="winner"' : ''}>${flash_avg.toFixed(1)}%</td>`;
  html += '</tr>';

  // Lite row
  html += '<tr>';
  html += '<td class="model-name">gemini-3.1-flash-lite</td>';
  html += `<td${ma.gemini_31_flash_lite.generic > ma.gemini_3_flash.generic ? ' class="winner"' : ''}>${ma.gemini_31_flash_lite.generic.toFixed(1)}%</td>`;
  html += `<td${ma.gemini_31_flash_lite.specialized > ma.gemini_3_flash.specialized ? ' class="winner"' : ''}>${ma.gemini_31_flash_lite.specialized.toFixed(1)}%</td>`;
  html += `<td${!flashIsWinner ? ' class="winner"' : ''}>${lite_avg.toFixed(1)}%</td>`;
  html += '</tr>';

  html += '</tbody></table>';

  // Phase 1 result banner
  if (p1.selected_model) {
    html += `<div class="phase1-banner">
      <strong>Selected model: ${esc(p1.selected_model)}</strong><br>
      <span class="muted">${esc(p1.selection_reason)}</span>
    </div>`;
  }

  el.innerHTML = html;
}

// =========================================================================
// Phase 1: Per-case detail (extraction only)
// =========================================================================
function renderPhase1Cases() {
  const container = document.getElementById('phase1-cases');
  const extCases = DATA.cases.filter(c => c.test_type === 'extraction');

  for (const c of extCases) {
    const div = document.createElement('div');
    div.className = 'case-card';
    div.id = 'p1-' + c.id;

    // Fact table with D1-D4 columns
    let factHtml = '<table class="fact-table"><thead><tr><th>#</th><th>Ground Truth Fact</th>';
    factHtml += '<th style="width:60px;text-align:center;background:var(--flash-bg);">D1</th>';
    factHtml += '<th style="width:60px;text-align:center;background:var(--flash-bg);">D2</th>';
    factHtml += '<th style="width:60px;text-align:center;background:var(--lite-bg);">D3</th>';
    factHtml += '<th style="width:60px;text-align:center;background:var(--lite-bg);">D4</th>';
    factHtml += '</tr></thead><tbody>';

    for (let i = 0; i < c.facts.length; i++) {
      const f = c.facts[i];
      factHtml += `<tr><td>${i+1}</td><td>${esc(f.text)}</td>`;
      for (const label of ['D1','D2','D3','D4']) {
        const col = c.describe_cols[label];
        const {verdict, reason} = getVerdict(col.scores, f.id);
        const vi = verdictIcon(verdict);
        const tip = reason ? ` title="${esc(reason)}"` : '';
        factHtml += `<td class="score ${vi.cls}"${tip}>${vi.icon}</td>`;
      }
      factHtml += '</tr>';
    }
    factHtml += '</tbody></table>';

    // Description cards
    let descCards = '';
    for (const label of ['D1','D2','D3','D4']) {
      const col = c.describe_cols[label];
      const pctStr = col.pct !== null ? col.pct.toFixed(1) + '%' : '\u2014';
      descCards += `
        <div class="desc-card ${col.tint}">
          <button class="expand-btn" onclick="openModal('${c.id}','describe','${label}')">&#9974; expand</button>
          <div class="desc-card-header">
            <span class="desc-card-label">${label}</span>
            <span><span class="desc-card-meta">${col.char_count.toLocaleString()} chars</span> <span class="desc-card-score">${pctStr}</span></span>
          </div>
          <div class="desc-card-content rendered">${renderMd(col.text)}</div>
        </div>`;
    }

    div.innerHTML = `
      <div class="case-header">
        <h3>${esc(c.id)} &mdash; ${esc(c.title)}
          <span class="tag">${esc(c.image_type)}</span>
          <span class="tag">${esc(c.specialized_prompt)}</span>
        </h3>
      </div>
      <div class="case-body">
        <div class="case-image">
          ${c.image_data_uri ? `<img src="${c.image_data_uri}" alt="${esc(c.title)}" />` : '<em>(image missing)</em>'}
          <p class="muted" style="font-size:11px;">${esc(c.image)}</p>
        </div>
        <div>
          <h3>Question</h3>
          <div class="question-block">${esc(c.question)}</div>
          <h3>Ground Truth Facts &mdash; D1/D2/D3/D4 Scores</h3>
          ${factHtml}
        </div>
      </div>
      <h3>Description Cards
        <span class="muted" style="font-size:12px;">&mdash;
          <span style="color:#1d4ed8;">blue = flash (D1/D2)</span>,
          <span style="color:#7c3aed;">purple = lite (D3/D4)</span>
        </span>
      </h3>
      <div class="desc-grid">${descCards}</div>
    `;
    container.appendChild(div);
  }
}

// =========================================================================
// Phase 2: Extraction cases
// =========================================================================
function renderPhase2() {
  // Summary table
  const summaryEl = document.getElementById('phase2-summary-table');
  const extCases = DATA.cases.filter(c => c.test_type === 'extraction');

  let sumHtml = '<table class="cmp-table"><thead><tr><th>Case</th><th>A1 (text via GPT)</th><th>A2 (image via GPT)</th><th>D1+D2 ref</th></tr></thead><tbody>';
  for (const c of extCases) {
    const a1 = c.answer_cols['A1'];
    const a2 = c.answer_cols['A2'];
    const d1pct = c.describe_cols['D1'].pct;
    const d2pct = c.describe_cols['D2'].pct;
    const refPct = (d1pct !== null && d2pct !== null) ? ((d1pct + d2pct)/2).toFixed(1)+'%' : '\u2014';
    const a1str = a1.pct !== null ? a1.pct.toFixed(1)+'%' : '\u2014';
    const a2str = a2.pct !== null ? a2.pct.toFixed(1)+'%' : '\u2014';
    const a1better = (a1.pct || 0) > (a2.pct || 0);
    const a2better = (a2.pct || 0) > (a1.pct || 0);
    sumHtml += `<tr><td style="text-align:left;font-weight:600;">${esc(c.id)}</td>`;
    sumHtml += `<td${a1better?' class="better"':''}>${a1str}</td>`;
    sumHtml += `<td${a2better?' class="better"':''}>${a2str}</td>`;
    sumHtml += `<td>${refPct}</td></tr>`;
  }
  // Average row
  const ps = DATA.phase2_summary;
  const a1avg = ps.a1_avg, a2avg = ps.a2_avg;
  sumHtml += `<tr style="font-weight:700;border-top:2px solid var(--border);">`;
  sumHtml += `<td style="text-align:left;">Average</td>`;
  sumHtml += `<td${a1avg > a2avg?' class="better"':''}>${a1avg.toFixed(1)}%</td>`;
  sumHtml += `<td${a2avg > a1avg?' class="better"':''}>${a2avg.toFixed(1)}%</td>`;
  sumHtml += `<td>\u2014</td></tr>`;
  sumHtml += '</tbody></table>';
  summaryEl.innerHTML = sumHtml;

  // Per-case detail
  const container = document.getElementById('phase2-cases');
  for (const c of extCases) {
    const div = document.createElement('div');
    div.className = 'case-card';
    div.id = 'p2-' + c.id;

    // Fact table with A1/A2
    let factHtml = '<table class="fact-table"><thead><tr><th>#</th><th>Ground Truth Fact</th>';
    factHtml += '<th style="width:80px;text-align:center;background:var(--answer-bg);">A1 (text)</th>';
    factHtml += '<th style="width:80px;text-align:center;background:var(--answer-bg);">A2 (image)</th>';
    factHtml += '</tr></thead><tbody>';

    for (let i = 0; i < c.facts.length; i++) {
      const f = c.facts[i];
      factHtml += `<tr><td>${i+1}</td><td>${esc(f.text)}</td>`;
      for (const label of ['A1','A2']) {
        const col = c.answer_cols[label];
        const {verdict, reason} = getVerdict(col.scores, f.id);
        const vi = verdictIcon(verdict);
        const tip = reason ? ` title="${esc(reason)}"` : '';
        factHtml += `<td class="score ${vi.cls}"${tip}>${vi.icon}</td>`;
      }
      factHtml += '</tr>';
    }
    factHtml += '</tbody></table>';

    // Answer cards
    let answerCards = '';
    for (const label of ['A1','A2']) {
      const col = c.answer_cols[label];
      const pctStr = col.pct !== null ? col.pct.toFixed(1)+'%' : '\u2014';
      const fullLabel = label === 'A1' ? 'A1: text via GPT' : 'A2: image via GPT';
      answerCards += `
        <div class="answer-card">
          <button class="expand-btn" onclick="openModal('${c.id}','answer','${label}')">&#9974; expand</button>
          <div class="answer-card-header">
            <span class="answer-card-label">${fullLabel}</span>
            <span><span class="desc-card-meta">${col.char_count.toLocaleString()} chars</span> <span class="answer-card-score">${pctStr}</span></span>
          </div>
          <div class="answer-card-content rendered">${renderMd(col.text)}</div>
        </div>`;
    }

    div.innerHTML = `
      <div class="case-header">
        <h3>${esc(c.id)} &mdash; ${esc(c.title)} <span class="tag">extraction</span></h3>
      </div>
      <h3>Fact Scores: A1 vs A2</h3>
      ${factHtml}
      <h3>Answer Cards</h3>
      <div class="answer-grid">${answerCards}</div>
    `;
    container.appendChild(div);
  }
}

// =========================================================================
// Phase 2: Judgment cases
// =========================================================================
function renderJudgmentCases() {
  const container = document.getElementById('judgment-cases');
  const judgCases = DATA.cases.filter(c => c.test_type === 'judgment');

  for (const c of judgCases) {
    const div = document.createElement('div');
    div.className = 'case-card';
    div.id = 'j-' + c.id;

    // Fact table with A1/A2
    let factHtml = '<table class="fact-table"><thead><tr><th>#</th><th>Reasoning Point</th>';
    factHtml += '<th style="width:80px;text-align:center;background:var(--answer-bg);">A1 (text)</th>';
    factHtml += '<th style="width:80px;text-align:center;background:var(--answer-bg);">A2 (image)</th>';
    factHtml += '</tr></thead><tbody>';

    for (let i = 0; i < c.facts.length; i++) {
      const f = c.facts[i];
      factHtml += `<tr><td>${i+1}</td><td>${esc(f.text)}</td>`;
      for (const label of ['A1','A2']) {
        const col = c.answer_cols[label];
        const {verdict, reason} = getVerdict(col.scores, f.id);
        const vi = verdictIcon(verdict);
        const tip = reason ? ` title="${esc(reason)}"` : '';
        factHtml += `<td class="score ${vi.cls}"${tip}>${vi.icon}</td>`;
      }
      factHtml += '</tr>';
    }
    factHtml += '</tbody></table>';

    // Answer cards
    let answerCards = '';
    for (const label of ['A1','A2']) {
      const col = c.answer_cols[label];
      const pctStr = col.pct !== null ? col.pct.toFixed(1)+'%' : '\u2014';
      const fullLabel = label === 'A1' ? 'A1: text via GPT' : 'A2: image via GPT';
      answerCards += `
        <div class="answer-card">
          <button class="expand-btn" onclick="openModal('${c.id}','answer','${label}')">&#9974; expand</button>
          <div class="answer-card-header">
            <span class="answer-card-label">${fullLabel}</span>
            <span><span class="desc-card-meta">${col.char_count.toLocaleString()} chars</span> <span class="answer-card-score">${pctStr}</span></span>
          </div>
          <div class="answer-card-content rendered">${renderMd(col.text)}</div>
        </div>`;
    }

    // Question block
    div.innerHTML = `
      <div class="case-header">
        <h3>${esc(c.id)} &mdash; ${esc(c.title)} <span class="tag">judgment</span></h3>
      </div>
      <h3>Question</h3>
      <div class="question-block">${esc(c.question)}</div>
      <h3>Reasoning Points: A1 vs A2</h3>
      ${factHtml}
      <h3>Answer Cards</h3>
      <div class="answer-grid">${answerCards}</div>
    `;
    container.appendChild(div);
  }
}

// =========================================================================
// Modal
// =========================================================================
function openModal(caseId, kind, label) {
  const c = DATA.cases.find(x => x.id === caseId);
  if (!c) return;
  const titleEl = document.getElementById('modal-title');
  const bodyEl = document.getElementById('modal-body');

  let text = '';
  let subtitle = '';
  if (kind === 'describe') {
    const col = c.describe_cols[label];
    text = col.text;
    subtitle = `${label} (${col.char_count.toLocaleString()} chars, ${col.pct !== null ? col.pct.toFixed(1)+'%' : '\u2014'})`;
  } else {
    const col = c.answer_cols[label];
    text = col.text;
    const fullLabel = label === 'A1' ? 'A1: text via GPT' : 'A2: image via GPT';
    subtitle = `${fullLabel} (${col.char_count.toLocaleString()} chars, ${col.pct !== null ? col.pct.toFixed(1)+'%' : '\u2014'})`;
  }

  titleEl.textContent = `${c.id} ${c.title} \u2014 ${subtitle}`;
  bodyEl.innerHTML = '<div class="rendered-md">' + renderMd(text) + '</div>';
  document.getElementById('modal').classList.add('open');
  setTimeout(() => mermaid.run({ querySelector: '#modal-body .mermaid' }), 50);
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// =========================================================================
// Init
// =========================================================================
function init() {
  renderPrompts();
  renderMatrix();
  renderPhase1Cases();
  renderPhase2();
  renderJudgmentCases();
  // Render mermaid after DOM is populated
  setTimeout(() => mermaid.run({ querySelector: '.mermaid' }), 200);
}

init();
</script>
</body>
</html>
"""


def _render_html(data: dict) -> str:
    payload = _build_payload(data)
    payload_json = json.dumps(payload, ensure_ascii=False)
    return _HTML_TEMPLATE.replace("__DATA_JSON__", payload_json)


def main() -> int:
    yaml_path = ROOT / "test_cases.yaml"
    if not yaml_path.exists():
        print(f"ERROR: {yaml_path} not found", file=sys.stderr)
        return 2
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    html_text = _render_html(data)
    out = ROOT / "report.html"
    out.write_text(html_text, encoding="utf-8")
    print(f"wrote {out.relative_to(WORKSPACE)} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
