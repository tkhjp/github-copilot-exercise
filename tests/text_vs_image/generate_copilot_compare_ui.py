#!/usr/bin/env python
"""Generate the 3-column Copilot comparison UI.

Unlike `generate_human_eval_ui.py` (which switches quants via dropdown), this UI
pins the 3 Copilot variants (copilot_png / copilot_pptx / copilot_docx) as
side-by-side columns — each reasoning point has 3 score widgets in the same row,
so the reviewer can see all 3 format responses and score them together.

localStorage is compatible with the main UI: same key, same
`{quant: {tc: {fact_id: verdict}}}` schema, so Export JSON merges cleanly with
any scores already given on `human_eval.html`.

Run:
    python tests/text_vs_image/generate_copilot_compare_ui.py
    open tests/text_vs_image/human_eval_copilot_compare.html
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse data-loading helpers from the main generator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_human_eval_ui import build_dataset  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_QUALITY_DIR = REPO_ROOT / "benchmarks" / "out" / "phase4" / "quality"
DEFAULT_CASES_YAML = REPO_ROOT / "tests" / "text_vs_image" / "test_cases.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "tests" / "text_vs_image" / "human_eval_copilot_compare.html"

PINNED_QUANTS = ["copilot_png", "copilot_pptx", "copilot_docx"]
DEFAULT_TCS = ["tc02_judge", "tc03_judge"]

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Copilot PNG vs PPTX vs DOCX — Judgment Compare</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; font-family: "Yu Gothic UI", "Meiryo", system-ui, sans-serif; color: #1a1a1a; background: #f7f3fb; }
  body { min-height: 100vh; display: flex; flex-direction: column; }
  header { padding: 10px 18px; background: #460073; color: #fff; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  header .sub { font-size: 11px; opacity: 0.8; }
  header .progress { font-size: 12px; margin-left: auto; }
  header button { font: inherit; padding: 4px 10px; border-radius: 4px; border: none; cursor: pointer; background: #A100FF; color: #fff; }
  header button.secondary { background: #fff; color: #460073; }
  header button:hover { filter: brightness(1.1); }
  .tabs { display: flex; gap: 0; background: #2d0050; }
  .tab { padding: 8px 18px; color: #d5b4ef; cursor: pointer; font-size: 13px; border-bottom: 3px solid transparent; }
  .tab.active { color: #fff; border-bottom-color: #A100FF; background: #3a0063; }
  .tab .tc-kind { display: inline-block; font-size: 9px; padding: 1px 5px; border-radius: 3px; margin-right: 6px; letter-spacing: 0.06em; font-weight: 700; background: #e67e22; color: #fff; }
  .tab .tc-done { opacity: 0.7; font-size: 11px; margin-left: 6px; }
  .prompt-bar { background: #fff; border-bottom: 1px solid #e2d5ee; padding: 8px 18px; font-size: 12.5px; display: grid; grid-template-columns: 100px 1fr; gap: 12px; align-items: start; }
  .prompt-bar .label { color: #A100FF; font-weight: 700; font-size: 10px; letter-spacing: 0.04em; padding-top: 2px; }
  .prompt-bar .value { color: #1a1a1a; line-height: 1.5; white-space: pre-wrap; }
  .rubric { background: #f7f3fb; border-bottom: 1px solid #e2d5ee; padding: 6px 18px; font-size: 11.5px; }
  .rubric summary { cursor: pointer; color: #460073; font-weight: 600; user-select: none; outline: none; }
  .rubric pre { margin: 6px 0 0; white-space: pre-wrap; color: #333; background: #fff; padding: 8px 10px; border-radius: 4px; border: 1px solid #e2d5ee; font: inherit; }

  main { flex: 1; padding: 12px 18px; display: flex; flex-direction: column; gap: 12px; }

  /* --- Image reference --- */
  .image-ref { background: #fff; border: 1px solid #e2d5ee; border-radius: 6px; }
  .image-ref summary { padding: 8px 12px; font-size: 12px; font-weight: 600; color: #460073; cursor: pointer; user-select: none; text-transform: uppercase; letter-spacing: 0.02em; }
  .image-ref[open] summary { border-bottom: 1px solid #e2d5ee; }
  .image-ref img { display: block; max-width: 100%; height: auto; margin: 0 auto; padding: 10px; }

  /* --- 3-column output panels --- */
  .outputs { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .out-panel { background: #fff; border: 1px solid #e2d5ee; border-radius: 6px; display: flex; flex-direction: column; min-height: 0; }
  .out-panel h3 { margin: 0; padding: 8px 12px; font-size: 12px; font-weight: 600; color: #460073; border-bottom: 1px solid #e2d5ee; background: #f7f3fb; letter-spacing: 0.02em; text-transform: uppercase; display: flex; align-items: center; justify-content: space-between; }
  .out-panel h3 .avg { font-size: 10.5px; color: #6b7280; font-weight: 500; text-transform: none; letter-spacing: 0; }
  .out-panel h3 .avg strong { color: #A100FF; }
  .out-body { padding: 10px 12px; font-size: 12.5px; line-height: 1.5; overflow-y: auto; max-height: 420px; white-space: pre-wrap; word-break: break-word; }

  /* --- Summary card --- */
  .summary-card { background: #fff; border: 1px solid #e2d5ee; border-radius: 6px; overflow: hidden; }
  .summary-card h3 { margin: 0; padding: 8px 12px; font-size: 12px; font-weight: 600; color: #460073; border-bottom: 1px solid #e2d5ee; background: #f7f3fb; letter-spacing: 0.02em; text-transform: uppercase; display: flex; justify-content: space-between; align-items: center; }
  .summary-card h3 .sum-tc { color: #A100FF; font-family: Consolas, monospace; text-transform: none; font-size: 11px; }
  .summary-card table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  .summary-card th, .summary-card td { padding: 6px 12px; text-align: center; font-variant-numeric: tabular-nums; }
  .summary-card thead th { background: #f7f3fb; font-weight: 700; color: #460073; font-size: 11px; letter-spacing: 0.02em; text-transform: uppercase; border-bottom: 1px solid #e2d5ee; }
  .summary-card thead th:first-child { background: #f7f3fb; }
  .summary-card tbody th { text-align: left; font-weight: 600; color: #4a4a4a; font-size: 11px; width: 200px; background: #faf7fd; }
  .summary-card tbody tr { border-top: 1px solid #f0e8fa; }
  .summary-card tbody tr:first-child { border-top: none; }
  .summary-card .delta.pos { color: #1a873b; font-weight: 700; }
  .summary-card .delta.neg { color: #b93a3a; font-weight: 700; }
  .summary-card .delta.zero { color: #8a8a8a; }

  /* --- LLM verdict badge (shared with human_eval.html styling) --- */
  .j-badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 7px; border-radius: 99px; font-weight: 700; font-size: 10px; line-height: 1.3; }
  .j-badge .j-score { font-weight: 500; opacity: 0.85; }
  .j-badge.vp { background: #e3f3e7; color: #136a2f; }
  .j-badge.vpa { background: #fdecd8; color: #9f5a1c; }
  .j-badge.vm { background: #f7dcdc; color: #8c2d2d; }
  .j-badge.vn { background: #f1edf7; color: #8a8a8a; }
  .j-agree { font-weight: 700; padding: 1px 4px; border-radius: 3px; font-size: 9px; background: rgba(185, 58, 58, 0.15); color: #b93a3a; margin-left: 2px; }
  .j-agree.stable { background: rgba(19, 106, 47, 0.12); color: #136a2f; }

  /* --- Scoring grid --- */
  .score-section { background: #fff; border: 1px solid #e2d5ee; border-radius: 6px; }
  .score-section h3 { margin: 0; padding: 8px 12px; font-size: 12px; font-weight: 600; color: #460073; border-bottom: 1px solid #e2d5ee; background: #f7f3fb; letter-spacing: 0.02em; text-transform: uppercase; }
  .score-header, .score-row { display: grid; grid-template-columns: 46px minmax(260px, 2fr) 1.1fr 1.1fr 1.1fr; gap: 8px; align-items: center; padding: 8px 12px; }
  .score-header { background: #f7f3fb; font-size: 10px; color: #8a8a8a; letter-spacing: 0.05em; text-transform: uppercase; font-weight: 700; border-bottom: 1px solid #e2d5ee; position: sticky; top: 0; }
  .score-header div { text-align: center; }
  .score-header .col-id, .score-header .col-text { text-align: left; }
  .score-row { border-bottom: 1px solid #f0e8fa; align-items: start; }
  .score-row:nth-child(even) { background: #faf7fd; }
  .score-row.done { background: #f3eefa; }
  .score-row .col-id { font-size: 10px; color: #8a8a8a; font-weight: 700; padding-top: 10px; }
  .score-row .col-text { font-size: 12.5px; line-height: 1.45; padding-top: 6px; }
  .col-cell { display: flex; flex-direction: column; gap: 5px; align-items: center; }
  .col-cell .col-llm { min-height: 18px; display: flex; justify-content: center; }
  .col-score { display: flex; gap: 4px; justify-content: center; }
  .col-score input[type=radio] { display: none; }
  .col-score label { font-size: 11px; padding: 3px 9px; border: 1px solid #cfc6d6; border-radius: 3px; cursor: pointer; user-select: none; background: #fff; font-weight: 600; font-variant-numeric: tabular-nums; min-width: 28px; text-align: center; }
  .col-score input[type=radio]:checked + label { color: #fff; border-color: transparent; }
  .col-score input[value=present]:checked + label { background: #1a873b; }
  .col-score input[value=partial]:checked + label { background: #e67e22; }
  .col-score input[value=missing]:checked + label { background: #b93a3a; }

  footer { background: #fff; padding: 10px 18px; font-size: 12px; border-top: 1px solid #e2d5ee; display: flex; gap: 24px; align-items: center; flex-wrap: wrap; position: sticky; bottom: 0; }
  footer .metric { display: inline-flex; flex-direction: column; line-height: 1.25; }
  footer .metric .k { font-size: 9px; color: #8a8a8a; letter-spacing: 0.04em; text-transform: uppercase; }
  footer .metric .v { color: #460073; font-weight: 600; font-size: 13px; font-variant-numeric: tabular-nums; }
  footer .spacer { flex: 1; }
  footer .hint { color: #8a8a8a; font-size: 11px; }
  footer button { font: inherit; padding: 6px 12px; border-radius: 4px; border: none; cursor: pointer; background: #A100FF; color: #fff; }
  footer button.secondary { background: #fff; color: #460073; border: 1px solid #cfc6d6; }
  footer button:hover { filter: brightness(1.1); }

  @media (max-width: 1100px) {
    .outputs { grid-template-columns: 1fr; }
    .score-header, .score-row { grid-template-columns: 40px minmax(200px, 1.5fr) 1fr 1fr 1fr; gap: 4px; padding: 6px 8px; }
  }
</style>
</head>
<body>

<header>
  <h1>Copilot PNG vs PPTX vs DOCX — 横並び採点</h1>
  <span class="sub">Phase 4 judgment — Microsoft Copilot Web</span>
  <span class="progress" id="progress"></span>
</header>

<div class="tabs" id="tc-tabs"></div>

<section class="prompt-bar">
  <div class="label">PROMPT</div>
  <div class="value" id="tc-question"></div>
</section>

<details class="rubric">
  <summary>Judge rubric (present 1.0 / partial 0.5 / missing 0.0)</summary>
  <pre id="rubric-text"></pre>
</details>

<main>
  <details class="image-ref" open>
    <summary>画像参照 (3 フォーマット共通の元画像)</summary>
    <img id="tc-image" alt="">
  </details>

  <section class="outputs" id="outputs"></section>

  <section class="summary-card">
    <h3>サマリー <span class="sum-tc" id="sum-tc"></span></h3>
    <table>
      <thead>
        <tr>
          <th></th>
          <th>copilot_png</th>
          <th>copilot_pptx</th>
          <th>copilot_docx</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th>Gemini judge avg (n_runs=3)</th>
          <td id="s-llm-png">—</td>
          <td id="s-llm-pptx">—</td>
          <td id="s-llm-docx">—</td>
        </tr>
        <tr>
          <th>Gemini agreement (mean per fact)</th>
          <td id="s-agree-png">—</td>
          <td id="s-agree-pptx">—</td>
          <td id="s-agree-docx">—</td>
        </tr>
        <tr>
          <th>あなたの採点 avg</th>
          <td id="s-human-png">—</td>
          <td id="s-human-pptx">—</td>
          <td id="s-human-docx">—</td>
        </tr>
        <tr>
          <th>Δ (あなた − Gemini)</th>
          <td id="s-delta-png" class="delta">—</td>
          <td id="s-delta-pptx" class="delta">—</td>
          <td id="s-delta-docx" class="delta">—</td>
        </tr>
      </tbody>
    </table>
  </section>

  <section class="score-section">
    <h3>Reasoning point × 3 format スコアリング (LLM 判定を参考にあなたが最終判定)</h3>
    <div class="score-header">
      <div class="col-id">ID</div>
      <div class="col-text">Reasoning point</div>
      <div>copilot_png</div>
      <div>copilot_pptx</div>
      <div>copilot_docx</div>
    </div>
    <div id="score-body"></div>
  </section>
</main>

<footer>
  <div class="metric"><span class="k">PNG avg</span><span class="v" id="m-png">—</span></div>
  <div class="metric"><span class="k">PPTX avg</span><span class="v" id="m-pptx">—</span></div>
  <div class="metric"><span class="k">DOCX avg</span><span class="v" id="m-docx">—</span></div>
  <div class="metric"><span class="k">Progress</span><span class="v" id="m-progress">—</span></div>
  <span class="spacer"></span>
  <span class="hint">auto-saves to localStorage (shared with human_eval.html)</span>
  <button class="secondary" id="btn-clear">Clear this tc</button>
  <button id="btn-export">Export JSON</button>
</footer>

<script>
const DATA = /*__DATA__*/;
const STORE_KEY = "phase4_human_scores_v1";
const VERDICTS = ["present", "partial", "missing"];
const VERDICT_SCORE = { present: 1.0, partial: 0.5, missing: 0.0 };
const BUTTON_LABEL = { present: "1.0", partial: "0.5", missing: "0.0" };
const VERDICT_CLASS = { present: "vp", partial: "vpa", missing: "vm" };
const QUANTS = DATA.quants;
const SHORT = q => q.replace("copilot_", "");

let state = loadState();
let currentTc = DATA.test_cases[0]?.id;

function loadState() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; }
  catch (e) { return {}; }
}
function saveState() {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); }
  catch (e) { console.error(e); }
}
function getVerdict(q, t, f) { return state?.[q]?.[t]?.[f] ?? null; }
function setVerdict(q, t, f, v) {
  state[q] ??= {}; state[q][t] ??= {}; state[q][t][f] = v;
  saveState();
}
function clearTc(t) {
  for (const q of QUANTS) if (state[q]) delete state[q][t];
  saveState();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function countDoneForTc(t) {
  const tc = DATA.test_cases.find(x => x.id === t);
  if (!tc) return { done: 0, total: 0 };
  let done = 0;
  for (const q of QUANTS) {
    for (const f of tc.facts) {
      if (state?.[q]?.[t]?.[f.id]) done++;
    }
  }
  return { done, total: QUANTS.length * tc.facts.length };
}

function renderTabs() {
  const host = document.getElementById("tc-tabs");
  host.innerHTML = "";
  for (const tc of DATA.test_cases) {
    const { done, total } = countDoneForTc(tc.id);
    const el = document.createElement("div");
    el.className = "tab" + (tc.id === currentTc ? " active" : "");
    el.innerHTML = `<span class="tc-kind">JUDGE</span>${tc.id} — ${escapeHtml(tc.title)} <span class="tc-done">${done}/${total}</span>`;
    el.onclick = () => { currentTc = tc.id; render(); };
    host.appendChild(el);
  }
}

function renderPrompt() {
  const tc = DATA.test_cases.find(x => x.id === currentTc);
  document.getElementById("tc-question").textContent = tc?.question ?? "";
  document.getElementById("rubric-text").textContent = DATA.judge_rubric || "";
}

function renderImage() {
  const tc = DATA.test_cases.find(x => x.id === currentTc);
  const img = document.getElementById("tc-image");
  if (tc) {
    img.src = `data:image/png;base64,${tc.image_b64}`;
    img.alt = tc.image_name;
  }
}

function computeAvg(q, t) {
  const tc = DATA.test_cases.find(x => x.id === t);
  if (!tc) return null;
  const vals = [];
  for (const f of tc.facts) {
    const v = state?.[q]?.[t]?.[f.id];
    if (v in VERDICT_SCORE) vals.push(VERDICT_SCORE[v]);
  }
  return vals.length ? vals.reduce((a,b) => a+b, 0) / vals.length : null;
}

function llmVerdicts(q, t) { return DATA.runs[q]?.[t]?.llm_verdicts ?? {}; }
function llmAvg(q, t)      { return DATA.runs[q]?.[t]?.llm_score_avg ?? null; }
function llmAgreement(q, t) {
  const vd = llmVerdicts(q, t);
  const ags = Object.values(vd).map(x => x.agreement ?? 1.0);
  return ags.length ? ags.reduce((a,b) => a+b, 0) / ags.length : null;
}

// Render a small colored pill showing the Gemini verdict + per-run agreement.
// info shape (from {quant}_{tc}_scores.json via build_dataset):
//   {verdict, verdicts:[...], agreement}  or missing => n/a badge
function verdictBadge(info) {
  if (!info || !info.verdict || !(info.verdict in VERDICT_SCORE)) {
    return '<span class="j-badge vn">— <span class="j-score">n/a</span></span>';
  }
  const v = info.verdict;
  const verdicts = info.verdicts || [v];
  const agreement = typeof info.agreement === "number" ? info.agreement : 1.0;
  const n = verdicts.length;
  const agreeN = Math.round(agreement * n);
  const cls = VERDICT_CLASS[v] || "vn";
  const score = VERDICT_SCORE[v].toFixed(1);
  let agreeTag = "";
  if (n > 1) {
    const stable = agreement >= 1.0;
    agreeTag = ` <span class="j-agree${stable ? " stable" : ""}">${agreeN}/${n}</span>`;
  }
  return `<span class="j-badge ${cls}">${v} <span class="j-score">${score}</span>${agreeTag}</span>`;
}

function renderOutputs() {
  const host = document.getElementById("outputs");
  host.innerHTML = "";
  for (const q of QUANTS) {
    const run = DATA.runs[q]?.[currentTc] ?? {};
    const desc = run.description || "(回答が登録されていません)";
    const avg = computeAvg(q, currentTc);
    const avgStr = avg == null ? "—" : avg.toFixed(3);
    const panel = document.createElement("div");
    panel.className = "out-panel";
    panel.innerHTML = `
      <h3><span>${escapeHtml(q)}</span><span class="avg">avg <strong>${avgStr}</strong></span></h3>
      <div class="out-body">${escapeHtml(desc)}</div>
    `;
    host.appendChild(panel);
  }
}

function renderScoring() {
  const tc = DATA.test_cases.find(x => x.id === currentTc);
  const host = document.getElementById("score-body");
  host.innerHTML = "";
  if (!tc) return;
  for (const f of tc.facts) {
    const row = document.createElement("div");
    row.className = "score-row";
    const verdicts = QUANTS.map(q => getVerdict(q, currentTc, f.id));
    if (verdicts.every(v => v)) row.classList.add("done");
    const scoreCells = QUANTS.map(q => {
      const cur = getVerdict(q, currentTc, f.id);
      const llmInfo = llmVerdicts(q, currentTc)[f.id] ?? null;
      const buttons = VERDICTS.map(v => {
        const inputId = `v__${q}__${f.id}__${v}`;
        const name = `v__${q}__${f.id}`;
        return `
          <input type="radio" name="${name}" id="${inputId}" value="${v}"
                 data-quant="${q}" data-fid="${f.id}" data-verdict="${v}"
                 ${cur === v ? "checked" : ""}>
          <label for="${inputId}" title="${v}">${BUTTON_LABEL[v]}</label>
        `;
      }).join("");
      return `
        <div class="col-cell">
          <div class="col-llm">${verdictBadge(llmInfo)}</div>
          <div class="col-score">${buttons}</div>
        </div>
      `;
    }).join("");
    row.innerHTML = `
      <div class="col-id">${escapeHtml(f.id)}</div>
      <div class="col-text">${escapeHtml(f.text)}</div>
      ${scoreCells}
    `;
    row.querySelectorAll("input[type=radio]").forEach(input => {
      input.onchange = () => {
        setVerdict(input.dataset.quant, currentTc, input.dataset.fid, input.dataset.verdict);
        renderTabs();
        renderOutputs();   // update per-column avg
        renderSummary();   // update Human avg + Δ in the summary card
        renderProgress();
        // update row "done" class without full re-render
        const ok = QUANTS.every(q => getVerdict(q, currentTc, input.dataset.fid));
        row.classList.toggle("done", ok);
      };
    });
    host.appendChild(row);
  }
}

function renderProgress() {
  // Footer metrics: per-quant avg + total progress
  for (const q of QUANTS) {
    const avg = computeAvg(q, currentTc);
    const el = document.getElementById(`m-${SHORT(q)}`);
    if (el) el.textContent = avg == null ? "—" : avg.toFixed(3);
  }
  const { done, total } = countDoneForTc(currentTc);
  document.getElementById("m-progress").textContent = `${done}/${total}`;
  document.getElementById("progress").textContent =
    `${currentTc}: ${done}/${total}`;
}

function renderSummary() {
  const tcEl = document.getElementById("sum-tc");
  if (tcEl) tcEl.textContent = currentTc;
  for (const q of QUANTS) {
    const short = SHORT(q);
    const llm = llmAvg(q, currentTc);
    const agree = llmAgreement(q, currentTc);
    const human = computeAvg(q, currentTc);
    const setText = (id, txt) => { const e = document.getElementById(id); if (e) e.textContent = txt; };
    setText(`s-llm-${short}`,   llm   == null ? "—" : llm.toFixed(3));
    setText(`s-agree-${short}`, agree == null ? "—" : agree.toFixed(2));
    setText(`s-human-${short}`, human == null ? "—" : human.toFixed(3));
    const deltaEl = document.getElementById(`s-delta-${short}`);
    if (!deltaEl) continue;
    deltaEl.classList.remove("pos", "neg", "zero");
    if (llm != null && human != null) {
      const delta = human - llm;
      const sign = delta > 0 ? "+" : "";
      deltaEl.textContent = `${sign}${delta.toFixed(3)}`;
      deltaEl.classList.add(delta > 0.001 ? "pos" : (delta < -0.001 ? "neg" : "zero"));
    } else {
      deltaEl.textContent = "—";
    }
  }
}

function render() {
  renderTabs();
  renderPrompt();
  renderImage();
  renderOutputs();
  renderSummary();
  renderScoring();
  renderProgress();
}

document.getElementById("btn-clear").onclick = () => {
  if (!confirm(`Clear all 3 Copilot scores for ${currentTc}?`)) return;
  clearTc(currentTc);
  render();
};

document.getElementById("btn-export").onclick = () => {
  const payload = {
    schema: "phase4_human_scores_v1",
    exported_at: new Date().toISOString(),
    scores: state,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "human_scores.json";
  a.click();
};

render();
</script>

</body>
</html>
"""


def build_html(dataset: dict) -> str:
    payload = json.dumps(dataset, ensure_ascii=False)
    return _HTML_TEMPLATE.replace("/*__DATA__*/", payload)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate 3-column Copilot compare UI")
    ap.add_argument("--quality-dir", default=str(DEFAULT_QUALITY_DIR))
    ap.add_argument("--cases-yaml", default=str(DEFAULT_CASES_YAML))
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument(
        "--tcs",
        default=",".join(DEFAULT_TCS),
        help="Comma-separated test case id whitelist (default: tc02_judge,tc03_judge)",
    )
    args = ap.parse_args()

    only_tcs = [t.strip() for t in args.tcs.split(",") if t.strip()]
    dataset = build_dataset(
        Path(args.quality_dir),
        Path(args.cases_yaml),
        only_quants=PINNED_QUANTS,
        only_tcs=only_tcs,
    )

    if len(dataset["test_cases"]) == 0:
        print(f"WARNING: no test cases matched {only_tcs}", file=sys.stderr)

    html = build_html(dataset)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    n_tcs = len(dataset["test_cases"])
    n_facts = sum(len(tc["facts"]) for tc in dataset["test_cases"])
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    print(f"  quants: {', '.join(dataset['quants'])}")
    print(f"  test cases: {n_tcs}  |  total reasoning points: {n_facts}  |  scores to give: {n_tcs and len(dataset['quants']) * n_facts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
