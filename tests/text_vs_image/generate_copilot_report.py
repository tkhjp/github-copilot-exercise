#!/usr/bin/env python
"""Generate the Japanese comparison report for the Copilot PNG/PPTX/DOCX arm.

Input: the `human_scores.json` exported from `human_eval.html`, which carries
every reviewer verdict as {quant: {tc: {fact_id: "present"|"partial"|"missing"}}}.

Output: a Markdown report in Japanese that puts local Gemma4 quants side-by-side
with the three copilot variants for the 2 judgment cases, plus a breakdown of
tc03_judge per reasoning point (so the visual-dependency signal j07/j08/j09 is
visible at a glance).

Run (after scoring in the UI and exporting human_scores.json):
    python tests/text_vs_image/generate_copilot_report.py \\
        --human-scores ~/Downloads/human_scores.json \\
        --out tests/text_vs_image/copilot_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
DEFAULT_CASES_YAML = ROOT / "test_cases.yaml"
DEFAULT_OUT = ROOT / "copilot_report.md"

SCORE_MAP = {"present": 1.0, "partial": 0.5, "missing": 0.0}

# Fixed display order for the comparison table.
DEFAULT_QUANTS = ["q4", "q5", "q8", "e2b", "copilot_png", "copilot_pptx", "copilot_docx"]
DEFAULT_TCS = ["tc02_judge", "tc03_judge"]

# Localized labels for column headers and per-case footnotes.
QUANT_LABELS = {
    "q4":            "q4 (Gemma4 E2B Q4)",
    "q5":            "q5 (Gemma4 E2B Q5)",
    "q8":            "q8 (Gemma4 E2B Q8)",
    "e2b":           "e2b (BF16)",
    "copilot_png":   "copilot_png (PNG 入力)",
    "copilot_pptx":  "copilot_pptx (PPTX 入力)",
    "copilot_docx":  "copilot_docx (DOCX+PNG 埋込)",
}

TC_LABELS = {
    "tc02_judge": "tc02_judge (UI 変更工数判断)",
    "tc03_judge": "tc03_judge (AWS 構成図 視覚読解)",
}


def _load_cases(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["test_cases"]}


def _load_scores(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scores = payload.get("scores") if isinstance(payload, dict) and "scores" in payload else payload
    if not isinstance(scores, dict):
        raise SystemExit("human_scores.json must contain a 'scores' dict of {quant: {tc: {fact_id: verdict}}}")
    return scores


def _avg(verdicts: dict[str, str], fact_ids: list[str]) -> float | None:
    """Return mean score over the fact_ids, treating missing entries as un-scored.

    If **no** fact is scored returns None (rendered as 'n/a')."""
    vals = []
    for fid in fact_ids:
        v = verdicts.get(fid)
        if v in SCORE_MAP:
            vals.append(SCORE_MAP[v])
    if not vals:
        return None
    return sum(vals) / len(vals)


def _coverage(verdicts: dict[str, str], fact_ids: list[str]) -> tuple[int, int]:
    scored = sum(1 for fid in fact_ids if verdicts.get(fid) in SCORE_MAP)
    return scored, len(fact_ids)


def _fmt_score(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def _fmt_verdict_ja(v: str | None) -> str:
    if v == "present":
        return "present (1.0)"
    if v == "partial":
        return "partial (0.5)"
    if v == "missing":
        return "missing (0.0)"
    return "未採点"


def _build_summary_table(
    scores: dict,
    cases: dict,
    quants: list[str],
    tcs: list[str],
) -> str:
    header = ["ケース"] + [QUANT_LABELS.get(q, q) for q in quants]
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join(sep) + " |"]
    for tc in tcs:
        case = cases.get(tc)
        if not case:
            continue
        fact_ids = [f["id"] for f in (case.get("reasoning_points") or case.get("ground_truth_facts") or [])]
        row = [TC_LABELS.get(tc, tc)]
        for q in quants:
            verdicts = scores.get(q, {}).get(tc, {})
            avg = _avg(verdicts, fact_ids)
            done, total = _coverage(verdicts, fact_ids)
            cell = _fmt_score(avg)
            if avg is not None and done < total:
                cell += f" ({done}/{total})"
            row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _build_per_point_table(
    scores: dict,
    case: dict,
    quants: list[str],
) -> str:
    reasoning = case.get("reasoning_points") or case.get("ground_truth_facts") or []
    header = ["rp_id", "内容"] + [QUANT_LABELS.get(q, q) for q in quants]
    sep = ["---"] * len(header)
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join(sep) + " |"]
    for f in reasoning:
        fid = f["id"]
        text = f["text"].replace("|", "\\|").replace("\n", " ")
        row = [fid, text]
        for q in quants:
            verdicts = scores.get(q, {}).get(case["id"], {})
            row.append(_fmt_verdict_ja(verdicts.get(fid)))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _build_report(
    scores: dict,
    cases: dict,
    quants: list[str],
    tcs: list[str],
    today: str,
) -> str:
    copilot_quants = [q for q in quants if q.startswith("copilot")]
    local_quants = [q for q in quants if not q.startswith("copilot")]

    parts: list[str] = []
    parts.append("# Microsoft Copilot Web — 入力フォーマット別 判断品質比較レポート")
    parts.append("")
    parts.append(f"_生成日: {today}_")
    parts.append("")

    # ---- 実験概要 ----
    parts.append("## 実験概要")
    parts.append("")
    parts.append(
        "本レポートは、Phase 4 text-vs-image 実験の延長として、**Microsoft Copilot Web 版** に対し "
        "同一内容を 3 種のフォーマット (PNG / PPTX / DOCX) で入力した場合の、判断タスク品質の変化を計測したものである。"
    )
    parts.append("")
    parts.append("- 対象ケース: `tc02_judge` (UI 変更工数判断) / `tc03_judge` (AWS 構成図 視覚読解)")
    parts.append("- 採点方式: `human_eval.html` 上で人手で **present / partial / missing** の 3 値を付与、スコアは 1.0 / 0.5 / 0.0 にマップして平均")
    parts.append("- 比較ベースライン: 既存のローカル LLM (Gemma4 E2B 量子化スイープ q4 / q5 / q8 / e2b)")
    parts.append("- **注記**: ローカル LLM は `n_runs=3` の多数決スコア、Copilot は `n_runs=1` の単発回答。一致率 (agreement) の比較は非対称になるため、本レポートではスコア平均のみ比較する。")
    parts.append("")

    # ---- 評価対象 ----
    parts.append("## 評価対象 quant 一覧")
    parts.append("")
    parts.append("| quant | 説明 | n_runs |")
    parts.append("| --- | --- | --- |")
    nruns_map = {"q4": 3, "q5": 3, "q8": 3, "e2b": 3,
                 "copilot_png": 1, "copilot_pptx": 1, "copilot_docx": 1}
    for q in quants:
        parts.append(f"| `{q}` | {QUANT_LABELS.get(q, q)} | {nruns_map.get(q, '?')} |")
    parts.append("")

    # ---- サマリーテーブル ----
    parts.append("## ケース別スコアサマリー")
    parts.append("")
    parts.append("各セルは該当 (quant, ケース) における全 reasoning point の平均スコア (0.0〜1.0)。括弧内は「採点済み件数 / 全件」で、部分採点のケースを示す。")
    parts.append("")
    parts.append(_build_summary_table(scores, cases, quants, tcs))
    parts.append("")

    # ---- tc03 per-point table ----
    tc03 = cases.get("tc03_judge")
    if tc03 and "tc03_judge" in tcs:
        parts.append("## tc03_judge における reasoning point 別 verdict")
        parts.append("")
        parts.append(
            "tc03_judge の `j07` / `j08` / `j09` は図中の線色や凡例の色分けに依存する。"
            "PNG → PPTX → DOCX の順に、どのフォーマットでこれらの色情報が保持・伝達されたかを可視化する。"
        )
        parts.append("")
        parts.append("### 全 quant 横並び")
        parts.append("")
        parts.append(_build_per_point_table(scores, tc03, quants))
        parts.append("")
        if copilot_quants:
            parts.append("### Copilot フォーマット別 (視覚依存項のハイライト)")
            parts.append("")
            parts.append(_build_per_point_table(scores, tc03, copilot_quants))
            parts.append("")

    # ---- 考察テンプレート ----
    parts.append("## 考察")
    parts.append("")
    parts.append("以下は分析の観点テンプレート。実数値を確認の上、該当する結論を選択・記述する。")
    parts.append("")
    parts.append("1. **PNG vs PPTX (Copilot)**: PPTX は native shape と text を保持するため、LLM は OCR を経由せず構造を直接読める可能性がある。スコア差が大きければ「構造保持による精度向上」を示唆する。")
    parts.append("2. **PNG vs DOCX (Copilot)**: DOCX は PNG を埋め込んだだけで、追加の構造情報は無い。スコア差が大きい場合、Copilot の docx 添付処理パイプライン (MIME 判定・OCR パスの違いなど) が効いている可能性がある。")
    parts.append("3. **tc03_judge の色依存項 (j07 / j08 / j09)**: これらは図中の線色に直接依存する。DOCX 版で全て `missing` なら「テキスト化で視覚手がかりが脱落」の研究シグナル。PPTX 版で保持されれば「native shape 経由で色情報が text として読み取れている」ことを示唆する。")
    parts.append("4. **ローカル LLM との比較**: q4 / q5 / q8 / e2b はいずれも 3 回の多数決スコア。Copilot は 1 回のみなので、上下幅が大きい可能性がある。数値が近い場合でも Copilot のばらつきを考慮する必要がある。")
    parts.append("")

    # ---- 付録 ----
    parts.append("## 付録 — 素材と生成物")
    parts.append("")
    parts.append("### 入力素材")
    parts.append("- PNG: `tests/text_vs_image/images/02_ui_change.png` / `03_complex_arch.png`")
    parts.append("- PPTX: `tests/text_vs_image/inputs/02_ui_change.pptx` / `03_complex_arch.pptx`")
    parts.append("  - 生成スクリプト: `tests/text_vs_image/generate_test_pptx.py`")
    parts.append("- DOCX: `tests/text_vs_image/inputs/02_ui_change.docx` / `03_complex_arch.docx`")
    parts.append("  - 生成スクリプト: `tests/text_vs_image/generate_test_docx.py`")
    parts.append("")
    parts.append("### Copilot 回答原文")
    for q in copilot_quants:
        for tc in tcs:
            parts.append(f"- `benchmarks/out/phase4/quality/{q}_{tc}_description.md`")
    parts.append("")
    parts.append("### 採点データ")
    parts.append("- UI エクスポート: `~/Downloads/human_scores.json`")
    parts.append("- 取り込み後のサマリー: `benchmarks/out/phase4/quality/{quant}_human_summary.json`")
    parts.append("")

    return "\n".join(parts) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the Japanese Copilot comparison report")
    ap.add_argument("--human-scores", required=True, help="Path to human_scores.json exported by the UI")
    ap.add_argument("--cases-yaml", default=str(DEFAULT_CASES_YAML))
    ap.add_argument("--quants", default=",".join(DEFAULT_QUANTS),
                    help="Comma-separated quants to include, in column order")
    ap.add_argument("--tcs", default=",".join(DEFAULT_TCS),
                    help="Comma-separated test case ids (row order)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--date", default=date.today().isoformat(),
                    help="Override the date shown in the report header")
    args = ap.parse_args()

    scores = _load_scores(Path(args.human_scores))
    cases = _load_cases(Path(args.cases_yaml))
    quants = [q.strip() for q in args.quants.split(",") if q.strip()]
    tcs = [t.strip() for t in args.tcs.split(",") if t.strip()]

    missing_cases = [t for t in tcs if t not in cases]
    if missing_cases:
        print(f"WARNING: unknown test cases: {missing_cases}", file=sys.stderr)

    report = _build_report(scores, cases, quants, tcs, args.date)
    out = Path(args.out)
    out.write_text(report, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    print(f"  quants: {', '.join(quants)}")
    print(f"  test cases: {', '.join(tcs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
