#!/usr/bin/env python
"""Aggregate all prompt-trial scores under benchmarks/out/extraction/ into one
Japanese Markdown comparison report.

Usage:
    python tests/text_vs_image/extraction/extraction_report.py \\
        --out tests/text_vs_image/extraction/extraction_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_OUT_ROOT = REPO_ROOT / "benchmarks" / "out" / "extraction"
DEFAULT_REPORT = Path(__file__).resolve().parent / "extraction_report.md"
ALL_PIDS = ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]


def _load_prompt_scores(prompt_dir: Path) -> dict[str, dict] | None:
    """Return {channel: {pid: {recall_avg, hallucination_count, ...}}} or None if no scores."""
    scores_dir = prompt_dir / "scores"
    if not scores_dir.exists():
        return None
    out = {"png": {}, "pptx": {}}
    for pid in ALL_PIDS:
        png_path = scores_dir / f"png_{pid}_scores.json"
        if png_path.exists():
            out["png"][pid] = json.loads(png_path.read_text(encoding="utf-8"))
    pptx_path = scores_dir / "pptx_scores.json"
    if pptx_path.exists():
        for entry in json.loads(pptx_path.read_text(encoding="utf-8")):
            out["pptx"][entry["pattern_id"]] = entry
    return out


def _fmt(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}"


def build_report(out_root: Path, today: str) -> str:
    trials: list[tuple[str, dict]] = []
    for prompt_dir in sorted(out_root.glob("*/")):
        if not prompt_dir.is_dir():
            continue
        scores = _load_prompt_scores(prompt_dir)
        if scores:
            trials.append((prompt_dir.name, scores))
    if not trials:
        return f"# Copilot 抽出プロンプト 比較レポート\n\n_生成日: {today}_\n\n採点済みのプロンプト試行はまだありません。\n"

    lines: list[str] = []
    lines.append("# Copilot 抽出プロンプト 比較レポート")
    lines.append("")
    lines.append(f"_生成日: {today}_")
    lines.append("")
    lines.append(f"対象プロンプト: {len(trials)} 種類")
    lines.append("")
    lines.append("## 概要 (プロンプト × フォーマット 平均)")
    lines.append("")
    lines.append("| prompt_id | PNG recall avg | PNG hallu total | PPTX recall avg | PPTX hallu total |")
    lines.append("| --- | --- | --- | --- | --- |")
    for name, sc in trials:
        png_vals = [v["recall_avg"] for v in sc["png"].values()]
        pptx_vals = [v["recall_avg"] for v in sc["pptx"].values()]
        png_hallu = sum(v.get("hallucination_count", 0) for v in sc["png"].values())
        pptx_hallu = sum(v.get("hallucination_count", 0) for v in sc["pptx"].values())
        png_avg = sum(png_vals) / len(png_vals) if png_vals else None
        pptx_avg = sum(pptx_vals) / len(pptx_vals) if pptx_vals else None
        lines.append(f"| `{name}` | {_fmt(png_avg)} | {png_hallu} | {_fmt(pptx_avg)} | {pptx_hallu} |")
    lines.append("")

    lines.append("## パターン別 recall (PNG)")
    lines.append("")
    header = ["prompt_id"] + ALL_PIDS
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            v = sc["png"].get(pid)
            row.append(_fmt(v["recall_avg"]) if v else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## パターン別 recall (PPTX)")
    lines.append("")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            v = sc["pptx"].get(pid)
            row.append(_fmt(v["recall_avg"]) if v else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## ハルシネーション件数 (パターン別、PNG / PPTX 合計)")
    lines.append("")
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for name, sc in trials:
        row = [f"`{name}`"]
        for pid in ALL_PIDS:
            png_h = sc["png"].get(pid, {}).get("hallucination_count", 0)
            pptx_h = sc["pptx"].get(pid, {}).get("hallucination_count", 0)
            row.append(str(png_h + pptx_h))
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## ハルシネーション具体例 (プロンプト別、最初の 3 件)")
    lines.append("")
    for name, sc in trials:
        lines.append(f"### `{name}`")
        shown = 0
        for channel in ("png", "pptx"):
            for pid, v in sc[channel].items():
                for ex in v.get("hallucination_examples", [])[:3]:
                    lines.append(f"- **[{channel}/{pid}]** {ex}")
                    shown += 1
                    if shown >= 3:
                        break
                if shown >= 3:
                    break
            if shown >= 3:
                break
        if shown == 0:
            lines.append("- ハルシネーションなし")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    ap.add_argument("--out", default=str(DEFAULT_REPORT))
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()
    report = build_report(Path(args.out_root), args.date)
    out = Path(args.out)
    out.write_text(report, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
