#!/usr/bin/env python
"""Generate report.html from test_cases.yaml.

Renders a single self-contained HTML page with:
- Aggregate fidelity scores across 4 columns (Generic / Specialized / Case1 / Case2)
- Per-test-case detail with image, ground truth fact table, and 4 columns of evaluation
- Mermaid blocks rendered live via mermaid.js CDN
- Markdown blocks rendered via marked.js CDN

Run:
    python tests/text_vs_image/generate_report.py
"""
from __future__ import annotations

import base64
import html
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parent.parent

EVAL_COLUMNS = [
    # (key, label, kind, source, badge_label)
    # The "source" field now distinguishes:
    #   - "describe": the LLM's raw description of the image
    #   - "answer":   the LLM's answer to the user question (using either
    #                 the specialized description or the image directly)
    ("generic", "① Generic 記述", "description", "describe", "記述 (generic)"),
    ("specialized", "② Specialized 記述", "description", "describe", "記述 (specialized)"),
    ("case1", "③ Case 1: text→LLM 回答", "case", "answer", "回答 (text 経由)"),
    ("case2", "④ Case 2: image→LLM 回答", "case", "answer", "回答 (image 直接)"),
]

SCORE_VALUES = ("present", "partial", "missing")
SCORE_WEIGHTS = {"present": 1.0, "partial": 0.5, "missing": 0.0}
SCORE_ICONS = {"present": "✓", "partial": "△", "missing": "✗", None: "—"}
SCORE_COLORS = {
    "present": "#16a34a",
    "partial": "#ca8a04",
    "missing": "#dc2626",
    None: "#9ca3af",
}


def _img_to_data_uri(image_path: Path) -> str:
    suffix = image_path.suffix.lower().lstrip(".")
    mime = "png" if suffix == "png" else "jpeg"
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{b64}"


def _scores_for(case: dict, column_key: str, column_kind: str) -> dict:
    """Return {fact_id: score} dict for a given column."""
    if column_kind == "description":
        return (case.get("description_scores") or {}).get(column_key) or {}
    return (case.get(column_key) or {}).get("fact_scores") or {}


def _content_for(case: dict, column_key: str, column_kind: str) -> str:
    if column_kind == "description":
        return (case.get("descriptions") or {}).get(column_key) or ""
    return (case.get(column_key) or {}).get("copilot_answer") or ""


def _per_case_score(case: dict, column_key: str, column_kind: str) -> tuple[float, int, int]:
    """Return (weighted_sum, total_facts, num_scored)."""
    facts = case.get("ground_truth_facts") or []
    total = len(facts)
    scores = _scores_for(case, column_key, column_kind)
    weighted = 0.0
    scored = 0
    for fact in facts:
        s = scores.get(fact["id"])
        if s in SCORE_WEIGHTS:
            scored += 1
            weighted += SCORE_WEIGHTS[s]
    return weighted, total, scored


def _aggregate(cases: list, column_key: str, column_kind: str) -> dict:
    total_weighted = 0.0
    total_facts = 0
    total_scored = 0
    for case in cases:
        w, t, s = _per_case_score(case, column_key, column_kind)
        total_weighted += w
        total_facts += t
        total_scored += s
    return {
        "weighted": total_weighted,
        "total": total_facts,
        "scored": total_scored,
        "percent": (total_weighted / total_facts * 100) if total_facts else 0.0,
        "coverage": (total_scored / total_facts * 100) if total_facts else 0.0,
    }


def _render_html(data: dict) -> str:
    cases = data.get("test_cases") or []

    aggregates = {
        key: _aggregate(cases, key, kind)
        for key, _, kind, _, _ in EVAL_COLUMNS
    }

    payload = {
        "cases": [],
        "columns": [
            {
                "key": k,
                "label": label,
                "kind": kind,
                "source": source,
                "badge": badge,
            }
            for k, label, kind, source, badge in EVAL_COLUMNS
        ],
        "aggregates": aggregates,
    }

    for case in cases:
        image_path = WORKSPACE / case["image"]
        case_payload = {
            "id": case["id"],
            "title": case["title"],
            "image": case["image"],
            "image_data_uri": _img_to_data_uri(image_path) if image_path.exists() else "",
            "image_type": case.get("image_type", ""),
            "specialized_prompt": case.get("specialized_prompt", ""),
            "question": case.get("question", "").strip(),
            "facts": case.get("ground_truth_facts") or [],
            "columns": {},
            "scores_per_column": {},
        }
        score_reasons = case.get("score_reasons") or {}
        for key, _label, kind, source, _badge in EVAL_COLUMNS:
            content = _content_for(case, key, kind)
            reasons_key = f"descriptions.{key}" if kind == "description" else f"{key}.copilot_answer"
            case_payload["columns"][key] = {
                "kind": kind,
                "source": source,
                "content": content,
                "char_count": len(content),
                "scores": _scores_for(case, key, kind),
                "reasons": score_reasons.get(reasons_key, {}),
            }
            w, t, s = _per_case_score(case, key, kind)
            case_payload["scores_per_column"][key] = {
                "weighted": w,
                "total": t,
                "scored": s,
                "percent": (w / t * 100) if t else 0.0,
            }
        payload["cases"].append(case_payload)

    payload_json = json.dumps(payload, ensure_ascii=False)

    return _HTML_TEMPLATE.replace("__DATA_JSON__", payload_json)


_HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>Text vs Image Fidelity Report</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
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
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", "Hiragino Sans", "Yu Gothic UI", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
  margin: 0;
  padding: 24px;
}
h1, h2, h3 { color: var(--text); margin-top: 0; }
h1 { font-size: 28px; }
h2 { font-size: 22px; margin-top: 32px; }
h3 { font-size: 16px; }
.muted { color: var(--muted); font-size: 14px; }
.summary {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-top: 16px;
}
.summary-card {
  background: var(--bg);
  border: 2px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  position: relative;
}
.summary-card.source-describe {
  background: #eff6ff;
  border-color: #93c5fd;
}
.summary-card.source-answer {
  background: #f0fdf4;
  border-color: #86efac;
}
.badge-mini {
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid currentColor;
  background: white;
  white-space: nowrap;
}
.badge-mini.source-describe { color: #1d4ed8; }
.badge-mini.source-answer { color: #15803d; }
.summary-card .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.summary-card .pct { font-size: 32px; font-weight: 700; margin: 8px 0; color: var(--accent); }
.summary-card .detail { font-size: 12px; color: var(--muted); }
.bar {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
  margin-top: 8px;
}
.bar > div { height: 100%; background: var(--accent); transition: width 0.3s; }
.case {
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
.case-header h2 { margin: 0; }
.tag {
  display: inline-block;
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--muted);
  margin-left: 8px;
}
.case-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  margin-bottom: 16px;
}
.case-image img {
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.question-block {
  background: var(--bg);
  border-left: 4px solid var(--accent);
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 14px;
  white-space: pre-wrap;
}
.fact-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 12px;
}
.fact-table th, .fact-table td {
  padding: 6px 8px;
  border: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
.fact-table th {
  background: var(--bg);
  font-weight: 600;
  font-size: 12px;
}
.fact-table td.score {
  text-align: center;
  font-weight: 700;
  font-size: 18px;
}
.score-present { color: var(--present); }
.score-partial { color: var(--partial); }
.score-missing { color: var(--missing); }
.score-na { color: var(--na); }
.eval-section-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-top: 24px;
  margin-bottom: 8px;
}
.eval-section-title h3 { margin: 0; font-size: 16px; }
.eval-section-title .hint { font-size: 12px; color: var(--muted); }
.eval-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 8px;
}
.eval-col {
  border: 2px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  position: relative;
}
.eval-col.source-describe {
  background: #eff6ff;
  border-color: #93c5fd;
}
.eval-col.source-answer {
  background: #f0fdf4;
  border-color: #86efac;
}
.eval-col-badge {
  position: absolute;
  top: -10px;
  left: 12px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: 10px;
  border: 1px solid currentColor;
  background: white;
}
.eval-col.source-describe .eval-col-badge {
  color: #1d4ed8;
}
.eval-col.source-answer .eval-col-badge {
  color: #15803d;
}
.eval-col-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
  margin-top: 6px;
}
.eval-col-header .col-name {
  font-weight: 600;
  font-size: 13px;
}
.eval-col-header .col-meta {
  display: flex;
  gap: 8px;
  align-items: baseline;
}
.eval-col-header .col-chars {
  font-size: 11px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.eval-col-header .col-score {
  font-size: 14px;
  font-weight: 700;
  color: var(--accent);
}
.eval-col-expand {
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
}
.eval-col-expand:hover { color: var(--accent); border-color: var(--accent); }
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
.modal {
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
.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--muted);
}
.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex-grow: 1;
}
.eval-content {
  font-size: 12px;
  white-space: pre-wrap;
  background: white;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 10px;
  max-height: 360px;
  overflow-y: auto;
  flex-grow: 1;
  min-height: 120px;
}
.eval-content.empty {
  color: var(--muted);
  font-style: italic;
}
.eval-content pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; }
.eval-content .mermaid {
  background: white;
  text-align: center;
  margin: 8px 0;
}
.legend {
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  margin-top: 16px;
  padding: 8px 12px;
  background: var(--bg);
  border-radius: 6px;
}
.legend span { font-weight: 700; font-size: 16px; margin-right: 4px; }
.toc {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 24px;
  margin-bottom: 24px;
}
.toc ol { margin: 8px 0 0 0; padding-left: 20px; }
.toc a { color: var(--accent); text-decoration: none; }
.toc a:hover { text-decoration: underline; }
@media (max-width: 1100px) {
  .case-body { grid-template-columns: 1fr; }
  .eval-grid { grid-template-columns: 1fr 1fr; }
  .summary-grid { grid-template-columns: 1fr 1fr; }
}
</style>
</head>
<body>

<h1>Text vs Image Fidelity Report (全自動 LLM 評価版)</h1>
<p class="muted">画像を LLM に渡す 2 通りの経路（specialized 記述を経由 vs 画像を直接渡す）でどの程度の情報損失が起きるか、またプロンプト工夫で記述の質をどれだけ改善できるかを LLM (Gemini) を使って完全自動で評価。Copilot Chat の代替として同じ Gemini モデルを使用しているため、同一モデル内の自己参照バイアスがあり得ることに留意。</p>

<div class="summary">
  <h2>集計サマリー</h2>
  <p class="muted">各列の Ground Truth fact カバー率（present=1.0、partial=0.5、missing=0）。未採点は除外。</p>
  <div id="summary-grid" class="summary-grid"></div>
  <div class="legend">
    <span class="score-present">✓</span> present (1.0)
    <span class="score-partial">△</span> partial (0.5)
    <span class="score-missing">✗</span> missing (0.0)
    <span class="score-na">—</span> 未採点
  </div>
</div>

<div class="toc">
  <strong>テストケース一覧</strong>
  <ol id="toc-list"></ol>
</div>

<div id="cases"></div>

<div id="modal" class="modal-overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <div class="modal-header">
      <h3 id="modal-title"></h3>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;

mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });

function escapeHtml(str) {
  return (str || "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}

function renderContent(text) {
  if (!text || !text.trim()) {
    return '<div class="eval-content empty">（未入力）</div>';
  }
  // Use marked to render Markdown, then post-process Mermaid blocks
  let html;
  try {
    html = marked.parse(text, { breaks: true, gfm: true });
  } catch (e) {
    html = '<pre>' + escapeHtml(text) + '</pre>';
  }
  // Replace mermaid code blocks: marked outputs <pre><code class="language-mermaid">...</code></pre>
  html = html.replace(
    /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g,
    (m, code) => '<div class="mermaid">' + code.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'") + '</div>'
  );
  return '<div class="eval-content">' + html + '</div>';
}

function renderSummary() {
  const grid = document.getElementById('summary-grid');
  grid.innerHTML = '';
  for (const col of DATA.columns) {
    const agg = DATA.aggregates[col.key];
    const card = document.createElement('div');
    card.className = 'summary-card source-' + col.source;
    const pct = agg.total ? agg.percent.toFixed(1) : '—';
    const cov = agg.total ? agg.coverage.toFixed(0) : '0';
    card.innerHTML = `
      <div class="badge-mini source-${col.source}">${escapeHtml(col.badge)}</div>
      <div class="label">${escapeHtml(col.label)}</div>
      <div class="pct">${pct}<small style="font-size:14px;color:var(--muted);">%</small></div>
      <div class="detail">採点済 ${agg.scored}/${agg.total} facts (${cov}%)</div>
      <div class="bar"><div style="width:${agg.total ? agg.percent : 0}%;"></div></div>
    `;
    grid.appendChild(card);
  }
}

function renderToc() {
  const ol = document.getElementById('toc-list');
  ol.innerHTML = '';
  for (const c of DATA.cases) {
    const li = document.createElement('li');
    li.innerHTML = `<a href="#${c.id}">${escapeHtml(c.title)}</a> <span class="muted">(${escapeHtml(c.image_type)})</span>`;
    ol.appendChild(li);
  }
}

function renderFactTable(c) {
  let html = '<table class="fact-table"><thead><tr><th style="width:30px;">#</th><th>Ground Truth Fact</th>';
  for (const col of DATA.columns) {
    html += `<th style="width:80px;text-align:center;">${escapeHtml(col.label)}</th>`;
  }
  html += '</tr></thead><tbody>';
  for (let i = 0; i < c.facts.length; i++) {
    const f = c.facts[i];
    html += `<tr><td>${i + 1}</td><td>${escapeHtml(f.text)}</td>`;
    for (const col of DATA.columns) {
      const score = (c.columns[col.key].scores || {})[f.id] || null;
      const reason = (c.columns[col.key].reasons || {})[f.id] || '';
      const cls = score ? `score-${score}` : 'score-na';
      const icon = score === 'present' ? '✓' : score === 'partial' ? '△' : score === 'missing' ? '✗' : '—';
      const tip = reason ? ` title="${escapeHtml(reason)}"` : '';
      html += `<td class="score ${cls}"${tip}>${icon}</td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  return html;
}

function renderCase(c) {
  const div = document.createElement('div');
  div.className = 'case';
  div.id = c.id;

  let evalCols = '';
  for (const col of DATA.columns) {
    const score = c.scores_per_column[col.key];
    const pct = score.total && score.scored ? score.percent.toFixed(0) + '%' : '—';
    const colData = c.columns[col.key];
    const charText = colData.content ? `${colData.char_count.toLocaleString()} 文字` : '0 文字';
    evalCols += `
      <div class="eval-col source-${col.source}" data-case="${c.id}" data-col="${col.key}">
        <span class="eval-col-badge">${escapeHtml(col.badge)}</span>
        <button class="eval-col-expand" onclick="openModal('${c.id}','${col.key}')">⛶ 拡大</button>
        <div class="eval-col-header">
          <span class="col-name">${escapeHtml(col.label)}</span>
          <span class="col-meta">
            <span class="col-chars">${charText}</span>
            <span class="col-score">${pct}</span>
          </span>
        </div>
        ${renderContent(colData.content)}
      </div>
    `;
  }

  div.innerHTML = `
    <div class="case-header">
      <h2>${escapeHtml(c.id)} — ${escapeHtml(c.title)}
        <span class="tag">type: ${escapeHtml(c.image_type)}</span>
        <span class="tag">prompt: ${escapeHtml(c.specialized_prompt)}</span>
      </h2>
    </div>
    <div class="case-body">
      <div class="case-image">
        ${c.image_data_uri ? `<img src="${c.image_data_uri}" alt="${escapeHtml(c.title)}" />` : '<em>(image missing)</em>'}
        <p class="muted" style="font-size:12px;">${escapeHtml(c.image)}</p>
      </div>
      <div>
        <h3>質問</h3>
        <div class="question-block">${escapeHtml(c.question)}</div>
        <h3>Ground Truth ファクト採点</h3>
        ${renderFactTable(c)}
      </div>
    </div>
    <div class="eval-section-title">
      <h3>各評価対象の出力</h3>
      <span class="hint">← <strong style="color:#1d4ed8;">青枠 ①② = 画像 → LLM 記述 (describe)</strong> ／ <strong style="color:#15803d;">緑枠 ③④ = LLM 記述/画像 → LLM 回答 (answer)</strong> →</span>
    </div>
    <div class="eval-grid">${evalCols}</div>
  `;
  return div;
}

function renderAll() {
  renderSummary();
  renderToc();
  const container = document.getElementById('cases');
  for (const c of DATA.cases) {
    container.appendChild(renderCase(c));
  }
  // run mermaid after content is in the DOM
  setTimeout(() => mermaid.run({ querySelector: '.mermaid' }), 100);
}

function openModal(caseId, colKey) {
  const c = DATA.cases.find(x => x.id === caseId);
  if (!c) return;
  const col = DATA.columns.find(x => x.key === colKey);
  const colData = c.columns[colKey];
  const titleEl = document.getElementById('modal-title');
  const bodyEl = document.getElementById('modal-body');
  titleEl.innerText = `${c.id} ${c.title} — ${col.label} (${col.badge}, ${colData.char_count.toLocaleString()} 文字)`;
  bodyEl.innerHTML = renderContent(colData.content);
  document.getElementById('modal').classList.add('open');
  setTimeout(() => mermaid.run({ querySelector: '#modal-body .mermaid' }), 50);
}
function closeModal() {
  document.getElementById('modal').classList.remove('open');
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

renderAll();
</script>
</body>
</html>
"""


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
    print(f"wrote {out.relative_to(WORKSPACE)} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
