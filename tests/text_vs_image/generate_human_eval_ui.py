#!/usr/bin/env python
"""Generate a self-contained HTML page for manual human scoring of Phase 4 outputs.

Loads test_cases.yaml + every `{quant}_{tc}_description.md` + `{quant}_{tc}_scores.json`
under `benchmarks/out/phase4/quality/`, embeds images as base64, and writes one HTML
file you open in a browser. Radio buttons let you mark each fact as present/partial/
missing; the LLM judge's verdict is shown beside each fact as reference only.
Progress persists in localStorage; "Export JSON" downloads your scores.

Usage:
    python tests/text_vs_image/generate_human_eval_ui.py \
        --quality-dir benchmarks/out/phase4/quality \
        --output tests/text_vs_image/human_eval.html

Then merge the exported JSON back into per-quant summaries:
    python tests/text_vs_image/import_human_scores.py \
        --scores-json ~/Downloads/human_scores.json \
        --quality-dir benchmarks/out/phase4/quality
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from html import escape
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_QUALITY_DIR = REPO_ROOT / "benchmarks" / "out" / "phase4" / "quality"
DEFAULT_CASES_YAML = REPO_ROOT / "tests" / "text_vs_image" / "test_cases.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "tests" / "text_vs_image" / "human_eval.html"


_SCORES_RE = re.compile(r"^(?P<quant>[^_]+)_(?P<tc>tc\d+)_scores\.json$")


def _discover_quants(quality_dir: Path) -> list[str]:
    quants: set[str] = set()
    for p in quality_dir.glob("*_scores.json"):
        m = _SCORES_RE.match(p.name)
        if m:
            quants.add(m.group("quant"))
    # Stable order: q4, q5, q8, e2b, then any other alphabetically.
    preferred = ["q4", "q5", "q8", "e2b"]
    ordered = [q for q in preferred if q in quants]
    ordered += sorted(q for q in quants if q not in preferred)
    return ordered


def _b64_image(path: Path) -> str:
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def _load_description(quality_dir: Path, quant: str, tc: str) -> str:
    md = quality_dir / f"{quant}_{tc}_description.md"
    if not md.exists():
        return ""
    text = md.read_text(encoding="utf-8")
    # Keep only the "## Output" section for the UI (drop the question echo).
    if "## Output" in text:
        text = text.split("## Output", 1)[1].lstrip("\n")
    return text.strip()


def _load_scores(quality_dir: Path, quant: str, tc: str) -> dict[str, dict]:
    """Return {fact_id: {verdict, verdicts, agreement}}.

    For single-run data (old format) verdicts is a 1-element list and agreement=1.0.
    For multi-run data verdicts holds each run's verdict and agreement is the fraction
    of runs matching the mode.
    """
    f = quality_dir / f"{quant}_{tc}_scores.json"
    if not f.exists():
        return {}
    data = json.loads(f.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for fact in data.get("facts", []):
        verdict = fact.get("verdict_mode") or fact.get("verdict") or "missing"
        verdicts = fact.get("verdicts") or [verdict]
        agreement = fact.get("agreement")
        if agreement is None:
            # derive from verdicts if not stored
            if verdicts:
                counts = {v: verdicts.count(v) for v in set(verdicts)}
                agreement = max(counts.values()) / len(verdicts)
            else:
                agreement = 1.0
        out[fact["id"]] = {
            "verdict": verdict,
            "verdicts": verdicts,
            "agreement": agreement,
        }
    return out


def _load_case_stats(quality_dir: Path, quant: str) -> dict[str, dict]:
    """Return {tc_id: {score_avg, describe_seconds}} from both
    {quant}_summary.json (extraction) and {quant}_judgment_summary.json (judgment).
    """
    out: dict[str, dict] = {}
    for suffix in ("", "_judgment"):
        p = quality_dir / f"{quant}{suffix}_summary.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        for c in data.get("cases", []):
            out[c["case_id"]] = {
                "score_avg": c.get("score_avg"),
                "describe_seconds": c.get("describe_seconds"),
            }
    return out


def build_dataset(
    quality_dir: Path,
    cases_yaml: Path,
    extra_quants: list[str] = (),
    only_quants: list[str] = (),
    only_tcs: list[str] = (),
) -> dict:
    cases_data = yaml.safe_load(cases_yaml.read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in cases_data["test_cases"]}
    if only_quants:
        quants = [q.strip() for q in only_quants if q.strip()]
    else:
        quants = _discover_quants(quality_dir)
        for q in extra_quants:
            q = q.strip()
            if q and q not in quants:
                quants.append(q)
    if not quants:
        raise SystemExit(f"no *_scores.json files under {quality_dir} and no --extra-quants/--only-quants given")

    only_tcs_set = {t.strip() for t in only_tcs if t.strip()}

    tcs: list[dict] = []
    for tc_id, case in sorted(cases.items()):
        if only_tcs_set and tc_id not in only_tcs_set:
            continue
        items = case.get("ground_truth_facts") or case.get("reasoning_points")
        if not items:
            continue  # neither extraction facts nor judgment reasoning points
        image_path = REPO_ROOT / case["image"]
        if not image_path.exists():
            print(f"WARNING: image missing for {tc_id}: {image_path}", file=sys.stderr)
            continue
        test_type = case.get("test_type", "extraction")
        tcs.append(
            {
                "id": tc_id,
                "title": case.get("title", tc_id),
                "test_type": test_type,
                "question": case.get("question", "").strip(),
                "facts": [{"id": f["id"], "text": f["text"]} for f in items],
                "image_b64": _b64_image(image_path),
                "image_name": image_path.name,
            }
        )

    runs: dict[str, dict[str, dict]] = {}
    for q in quants:
        case_stats = _load_case_stats(quality_dir, q)
        runs[q] = {}
        for tc in tcs:
            stats = case_stats.get(tc["id"], {})
            runs[q][tc["id"]] = {
                "description": _load_description(quality_dir, q, tc["id"]),
                "llm_verdicts": _load_scores(quality_dir, q, tc["id"]),
                "llm_score_avg": stats.get("score_avg"),
                "llm_describe_seconds": stats.get("describe_seconds"),
            }

    # Judge rubric — same wording as phase4_quality_eval.py so the human reviewer
    # sees the rules the LLM judge was given. Two variants depending on test_type.
    judge_rubric = (
        "【抽出テスト (extraction: tc01〜tc04)】各 fact に対して以下を付ける。\n"
        "・present (1.0) — fact の内容が description にほぼそのまま、あるいは明確に含まれている\n"
        "・partial (0.5) — fact の一部のみ（ラベルは合っているが値が微妙に違う、など）\n"
        "・missing (0.0) — fact に対応する言及が description に全くない、または明らかに誤っている\n"
        "\n"
        "【判断テスト (judgment: tcXX_judge)】各 reasoning point に対して以下を付ける。\n"
        "・present (1.0) — reasoning point の主張がモデルの判断として明確に述べられている（言い換えも可）\n"
        "・partial (0.5) — 近い結論だが規模・方向性・理由が微妙に違う\n"
        "・missing (0.0) — 対応する判断が reasoning に全く出ていない、または明確に矛盾\n"
        "\n"
        "case score = sum(各 item のスコア) / item 件数。test_type ごとに別 summary に集計される。"
    )

    return {
        "quants": quants,
        "test_cases": tcs,
        "runs": runs,
        "judge_rubric": judge_rubric,
    }


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Phase 4 Human Eval</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; height: 100%; font-family: "Yu Gothic UI", "Meiryo", system-ui, sans-serif; color: #1a1a1a; background: #f7f3fb; }
  body { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
  header { padding: 10px 18px; background: #460073; color: #fff; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  header label { font-size: 12px; }
  header select, header button { font: inherit; padding: 4px 10px; border-radius: 4px; border: 1px solid #8a8a8a; }
  header button { background: #A100FF; color: #fff; border: none; cursor: pointer; }
  header button.secondary { background: #fff; color: #460073; }
  header button:hover { filter: brightness(1.1); }
  .progress { font-size: 12px; opacity: 0.85; margin-left: auto; }
  .tabs { display: flex; gap: 0; background: #2d0050; }
  .tab { padding: 8px 18px; color: #d5b4ef; cursor: pointer; font-size: 13px; border-bottom: 3px solid transparent; }
  .tab.active { color: #fff; border-bottom-color: #A100FF; background: #3a0063; }
  .tab .tc-done { opacity: 0.7; font-size: 11px; margin-left: 6px; }
  .tab .tc-kind { display: inline-block; font-size: 9px; padding: 1px 5px; border-radius: 3px; margin-right: 6px; letter-spacing: 0.06em; font-weight: 700; }
  .tab .tc-kind.extraction { background: #3a0063; color: #d5b4ef; border: 1px solid #4a0078; }
  .tab .tc-kind.judgment   { background: #e67e22; color: #fff; }
  .prompt-bar { background: #fff; border-bottom: 1px solid #e2d5ee; padding: 8px 18px; font-size: 12.5px; display: grid; grid-template-columns: 88px 1fr; gap: 12px; align-items: start; }
  .prompt-bar .label { color: #A100FF; font-weight: 700; font-size: 10px; letter-spacing: 0.04em; padding-top: 2px; }
  .prompt-bar .value { color: #1a1a1a; line-height: 1.5; }
  .rubric { background: #f7f3fb; border-bottom: 1px solid #e2d5ee; padding: 6px 18px; font-size: 11.5px; }
  .rubric summary { cursor: pointer; color: #460073; font-weight: 600; user-select: none; outline: none; }
  .rubric pre { margin: 6px 0 0; white-space: pre-wrap; color: #333; background: #fff; padding: 8px 10px; border-radius: 4px; border: 1px solid #e2d5ee; font: inherit; }
  main { flex: 1; display: grid; grid-template-columns: minmax(280px, 22%) minmax(360px, 38%) minmax(360px, 40%); gap: 12px; padding: 12px; overflow: hidden; }
  .panel { background: #fff; border: 1px solid #e2d5ee; border-radius: 6px; display: flex; flex-direction: column; min-height: 0; }
  .panel h2 { margin: 0; padding: 8px 12px; font-size: 12px; font-weight: 600; color: #460073; border-bottom: 1px solid #e2d5ee; background: #f7f3fb; letter-spacing: 0.02em; text-transform: uppercase; }
  .panel-body { padding: 10px 12px; overflow-y: auto; font-size: 13px; line-height: 1.55; }
  img.tc-image { max-width: 100%; height: auto; display: block; border: 1px solid #e2d5ee; }
  .desc { white-space: pre-wrap; word-break: break-word; font-size: 12.5px; }
  .facts { display: flex; flex-direction: column; gap: 6px; }
  .fact { border: 1px solid #e2d5ee; border-radius: 4px; padding: 8px 10px; background: #fff; display: grid; grid-template-columns: 36px 1fr auto; gap: 6px 10px; align-items: start; }
  .fact.done { background: #f3eefa; }
  .fact-id { font-size: 10px; color: #8a8a8a; font-weight: 700; padding-top: 3px; }
  .fact-text { font-size: 12.5px; line-height: 1.45; }
  .fact-controls { display: flex; gap: 4px; align-items: center; margin-top: 2px; }
  .fact-controls label { font-size: 11px; padding: 3px 9px; border: 1px solid #cfc6d6; border-radius: 3px; cursor: pointer; user-select: none; background: #fff; font-weight: 600; font-variant-numeric: tabular-nums; min-width: 28px; text-align: center; }
  .fact-controls input[type=radio] { display: none; }
  .fact-controls input[type=radio]:checked + label { color: #fff; border-color: transparent; }
  .fact-controls input[value=present]:checked + label { background: #1a873b; }
  .fact-controls input[value=partial]:checked + label { background: #e67e22; }
  .fact-controls input[value=missing]:checked + label { background: #b93a3a; }
  .fact-controls-wrap { display: flex; flex-direction: column; gap: 4px; align-items: flex-end; }
  .fact-controls-wrap .row-label { font-size: 9px; color: #8a8a8a; letter-spacing: 0.04em; text-transform: uppercase; }
  .judgement { grid-column: 2 / -1; display: flex; align-items: center; gap: 8px; margin-top: 4px; font-size: 10.5px; }
  .judgement .j-label { color: #8a8a8a; letter-spacing: 0.03em; text-transform: uppercase; font-size: 9.5px; }
  .j-badge { display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border-radius: 999px; font-weight: 700; font-size: 10.5px; line-height: 1.4; }
  .j-badge .j-score { font-weight: 500; opacity: 0.85; }
  .j-badge.vp { background: #e3f3e7; color: #136a2f; }
  .j-badge.vpa { background: #fdecd8; color: #9f5a1c; }
  .j-badge.vm { background: #f7dcdc; color: #8c2d2d; }
  .j-badge.vn { background: #f1edf7; color: #8a8a8a; }
  .j-agree { font-weight: 700; padding: 1px 5px; border-radius: 3px; background: rgba(185, 58, 58, 0.15); color: #b93a3a; font-size: 9.5px; }
  .j-agree.stable { background: rgba(19, 106, 47, 0.12); color: #136a2f; }
  .j-runs { font-family: Consolas, "Yu Gothic UI", monospace; font-size: 9.5px; color: #555; letter-spacing: 0.1em; padding: 1px 4px; border: 1px solid #cfc6d6; border-radius: 3px; background: #fff; }
  footer { background: #fff; padding: 8px 18px; font-size: 12px; border-top: 1px solid #e2d5ee; display: flex; gap: 20px; align-items: center; flex-wrap: wrap; }
  footer .metric { display: inline-flex; flex-direction: column; line-height: 1.25; }
  footer .metric .k { font-size: 9px; color: #8a8a8a; letter-spacing: 0.04em; text-transform: uppercase; }
  footer .metric .v { color: #460073; font-weight: 600; font-size: 13px; }
  footer .metric.delta .v.pos { color: #1a873b; }
  footer .metric.delta .v.neg { color: #b93a3a; }
  .hint { color: #8a8a8a; font-size: 11px; }
</style>
</head>
<body>

<header>
  <h1>Phase 4 Human Eval</h1>
  <label>quant
    <select id="quant-select"></select>
  </label>
  <span class="progress" id="progress"></span>
</header>

<div class="tabs" id="tc-tabs"></div>

<section class="prompt-bar">
  <div class="label">PROMPT → LOCAL LLM</div>
  <div class="value" id="tc-question"></div>
</section>

<details class="rubric">
  <summary>Judge rubric (present 1.0 / partial 0.5 / missing 0.0)</summary>
  <pre id="rubric-text"></pre>
</details>

<main>
  <section class="panel">
    <h2>Image</h2>
    <div class="panel-body">
      <img id="tc-image" class="tc-image" alt="">
    </div>
  </section>

  <section class="panel">
    <h2>Model Output</h2>
    <div class="panel-body">
      <div class="desc" id="desc"></div>
    </div>
  </section>

  <section class="panel">
    <h2>Facts — your verdict (LLM verdict shown in gray)</h2>
    <div class="panel-body">
      <div class="facts" id="facts"></div>
    </div>
  </section>
</main>

<footer>
  <div class="metric"><span class="k">LLM avg</span><span class="v" id="m-llm">—</span></div>
  <div class="metric"><span class="k">Human avg</span><span class="v" id="m-human">—</span></div>
  <div class="metric delta"><span class="k">Δ (human − LLM)</span><span class="v" id="m-delta">—</span></div>
  <div class="metric"><span class="k">Progress</span><span class="v" id="m-progress">—</span></div>
  <div class="metric"><span class="k">Describe time (LLM)</span><span class="v" id="m-desc-time">—</span></div>
  <span style="flex:1"></span>
  <span class="hint">auto-saves to localStorage</span>
  <button class="secondary" id="btn-clear">Clear this (quant×tc)</button>
  <button id="btn-export">Export JSON</button>
</footer>

<script>
const DATA = /*__DATA__*/;
const STORE_KEY = "phase4_human_scores_v1";
const VERDICTS = ["present", "partial", "missing"];
const VERDICT_SCORE = { present: 1.0, partial: 0.5, missing: 0.0 };

let state = loadState();
let currentQuant = DATA.quants[0];
let currentTc = DATA.test_cases[0].id;

function loadState() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    console.error("localStorage load failed", e);
    return {};
  }
}

function saveState() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch (e) {
    console.error("localStorage save failed", e);
  }
}

function getVerdict(quant, tc, fid) {
  return state?.[quant]?.[tc]?.[fid] ?? null;
}

function setVerdict(quant, tc, fid, verdict) {
  state[quant] ??= {};
  state[quant][tc] ??= {};
  state[quant][tc][fid] = verdict;
  saveState();
}

function clearQuantTc(quant, tc) {
  if (state[quant]) delete state[quant][tc];
  saveState();
}

function renderQuantSelect() {
  const sel = document.getElementById("quant-select");
  sel.innerHTML = "";
  for (const q of DATA.quants) {
    const o = document.createElement("option");
    o.value = q;
    o.textContent = q;
    sel.appendChild(o);
  }
  sel.value = currentQuant;
  sel.onchange = () => { currentQuant = sel.value; render(); };
}

function countDone(quant, tc) {
  const n = DATA.test_cases.find(x => x.id === tc).facts.length;
  const d = state?.[quant]?.[tc] ?? {};
  return { done: Object.keys(d).length, total: n };
}

function renderTabs() {
  const host = document.getElementById("tc-tabs");
  host.innerHTML = "";
  for (const tc of DATA.test_cases) {
    const { done, total } = countDone(currentQuant, tc.id);
    const kind = tc.test_type === "judgment" ? "judgment" : "extraction";
    const kindShort = tc.test_type === "judgment" ? "JUDGE" : "EXTRACT";
    const div = document.createElement("div");
    div.className = "tab" + (tc.id === currentTc ? " active" : "");
    div.innerHTML = `<span class="tc-kind ${kind}">${kindShort}</span>${tc.id} — ${escapeHtml(tc.title)} <span class="tc-done">${done}/${total}</span>`;
    div.onclick = () => { currentTc = tc.id; render(); };
    host.appendChild(div);
  }
}

function renderImage() {
  const tc = DATA.test_cases.find(x => x.id === currentTc);
  document.getElementById("tc-image").src = `data:image/png;base64,${tc.image_b64}`;
  document.getElementById("tc-image").alt = tc.image_name;
  document.getElementById("tc-question").textContent = tc.question;
}

function renderRubric() {
  document.getElementById("rubric-text").textContent = DATA.judge_rubric || "";
}

function renderDesc() {
  const run = DATA.runs[currentQuant]?.[currentTc];
  document.getElementById("desc").textContent = run?.description ?? "(no output)";
}

const VERDICT_CLASS = { present: "vp", partial: "vpa", missing: "vm" };
const BUTTON_LABEL = { present: "1.0", partial: "0.5", missing: "0.0" };

function verdictBadge(info) {
  // info may be null, a legacy string, or {verdict, verdicts, agreement}.
  if (!info) {
    return `<span class="j-badge vn">— <span class="j-score">n/a</span></span>`;
  }
  const v = typeof info === "string" ? info : info.verdict;
  const verdicts = (typeof info === "object" && info.verdicts) || [v];
  const agreement = (typeof info === "object" && typeof info.agreement === "number") ? info.agreement : 1.0;
  const n = verdicts.length;
  const agreeN = Math.round(agreement * n);
  const cls = VERDICT_CLASS[v] || "vn";
  if (!VERDICT_CLASS[v]) {
    return `<span class="j-badge vn">— <span class="j-score">n/a</span></span>`;
  }
  const score = VERDICT_SCORE[v].toFixed(1);
  const agreementMark = (n > 1 && agreement < 1.0)
    ? ` <span class="j-agree">${agreeN}/${n}</span>`
    : (n > 1 ? ` <span class="j-agree stable">${n}/${n}</span>` : "");
  // If there's disagreement, append a small "runs" string with each verdict letter.
  const runsRibbon = (n > 1 && agreement < 1.0)
    ? ` <span class="j-runs">[${verdicts.map(x => (x||"")[0] || "?").join("")}]</span>`
    : "";
  return `<span class="j-badge ${cls}">${v} <span class="j-score">${score}</span>${agreementMark}${runsRibbon}</span>`;
}

function renderFacts() {
  const tc = DATA.test_cases.find(x => x.id === currentTc);
  const llm = DATA.runs[currentQuant]?.[currentTc]?.llm_verdicts ?? {};
  const host = document.getElementById("facts");
  host.innerHTML = "";
  for (const f of tc.facts) {
    const cur = getVerdict(currentQuant, currentTc, f.id);
    const div = document.createElement("div");
    div.className = "fact" + (cur ? " done" : "");
    const llmV = llm[f.id] ?? null;
    div.innerHTML = `
      <div class="fact-id">${escapeHtml(f.id)}</div>
      <div>
        <div class="fact-text">${escapeHtml(f.text)}</div>
      </div>
      <div class="fact-controls-wrap">
        <span class="row-label">Your score</span>
        <div class="fact-controls">
          ${VERDICTS.map(v => `
            <input type="radio" name="v_${f.id}" id="v_${f.id}_${v}" value="${v}" ${cur === v ? "checked" : ""}>
            <label for="v_${f.id}_${v}" title="${v}">${BUTTON_LABEL[v]}</label>
          `).join("")}
        </div>
      </div>
      <div class="judgement">
        <span class="j-label">LLM judgement</span>
        ${verdictBadge(llmV)}
      </div>
    `;
    div.querySelectorAll("input[type=radio]").forEach(input => {
      input.onchange = () => {
        setVerdict(currentQuant, currentTc, f.id, input.value);
        div.classList.add("done");
        renderTabs();
        renderProgress();
      };
    });
    host.appendChild(div);
  }
}

function renderProgress() {
  const run = DATA.runs[currentQuant]?.[currentTc] ?? {};
  const { done, total } = countDone(currentQuant, currentTc);

  document.getElementById("progress").textContent = `${currentQuant} / ${currentTc}: ${done}/${total}`;
  document.getElementById("m-progress").textContent = `${done}/${total}`;

  // LLM avg for this (quant, tc), from {quant}_summary.json
  const llmAvg = typeof run.llm_score_avg === "number" ? run.llm_score_avg : null;
  document.getElementById("m-llm").textContent = llmAvg !== null ? llmAvg.toFixed(3) : "—";

  // Human avg computed live
  const d = state?.[currentQuant]?.[currentTc] ?? {};
  const vals = Object.values(d).map(v => VERDICT_SCORE[v] ?? 0);
  const humanAvg = vals.length ? (vals.reduce((a,b) => a+b, 0) / vals.length) : null;
  document.getElementById("m-human").textContent = humanAvg !== null ? humanAvg.toFixed(3) : "—";

  // Delta: only meaningful when the human has scored every fact (partial subsets skew average)
  const deltaEl = document.getElementById("m-delta");
  deltaEl.classList.remove("pos", "neg");
  if (llmAvg !== null && humanAvg !== null && done === total) {
    const delta = humanAvg - llmAvg;
    const sign = delta >= 0 ? "+" : "";
    deltaEl.textContent = `${sign}${delta.toFixed(3)}`;
    deltaEl.classList.add(delta >= 0 ? "pos" : "neg");
  } else if (llmAvg !== null && humanAvg !== null) {
    deltaEl.textContent = `(partial ${done}/${total})`;
  } else {
    deltaEl.textContent = "—";
  }

  const dt = run.llm_describe_seconds;
  document.getElementById("m-desc-time").textContent =
    typeof dt === "number" ? `${dt.toFixed(1)} s` : "—";
}

function render() {
  renderQuantSelect();
  renderTabs();
  renderImage();
  renderRubric();
  renderDesc();
  renderFacts();
  renderProgress();
}

function escapeHtml(s) {
  const map = {"&":"&amp;", "<":"&lt;", ">":"&gt;", "'":"&#39;"};
  map['"'] = "&quot;";
  return String(s).replace(/[&<>"']/g, c => map[c]);
}

document.getElementById("btn-clear").onclick = () => {
  if (!confirm(`Clear ${currentQuant} / ${currentTc}?`)) return;
  clearQuantTc(currentQuant, currentTc);
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
    ap = argparse.ArgumentParser(description="Generate the Phase 4 human eval UI")
    ap.add_argument("--quality-dir", default=str(DEFAULT_QUALITY_DIR))
    ap.add_argument("--cases-yaml", default=str(DEFAULT_CASES_YAML))
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    ap.add_argument(
        "--extra-quants",
        default="",
        help="Comma-separated quant labels to include even without *_scores.json "
             "(e.g. copilot_png,copilot_pptx,copilot_docx for human-only scoring)",
    )
    ap.add_argument(
        "--only-quants",
        default="",
        help="Comma-separated quant whitelist. If set, skips auto-discovery and "
             "--extra-quants, using ONLY the given labels (e.g. copilot-only page)",
    )
    ap.add_argument(
        "--only-tcs",
        default="",
        help="Comma-separated test case id whitelist. If set, UI shows only these "
             "tabs (e.g. tc02_judge,tc03_judge to focus on judgment cases)",
    )
    args = ap.parse_args()

    extras = [q for q in args.extra_quants.split(",") if q.strip()]
    only_q = [q for q in args.only_quants.split(",") if q.strip()]
    only_t = [t for t in args.only_tcs.split(",") if t.strip()]
    dataset = build_dataset(
        Path(args.quality_dir), Path(args.cases_yaml),
        extra_quants=extras, only_quants=only_q, only_tcs=only_t,
    )
    html = build_html(dataset)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    n_tcs = len(dataset["test_cases"])
    n_q = len(dataset["quants"])
    n_facts = sum(len(tc["facts"]) for tc in dataset["test_cases"])
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    print(f"  quants: {', '.join(dataset['quants'])}")
    print(f"  test cases: {n_tcs}  |  total facts: {n_facts}  |  pairs to score: {n_q * n_facts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
