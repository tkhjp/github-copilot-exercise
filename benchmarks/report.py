"""CSV and Markdown report writers for benchmark runs."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from benchmarks.metrics import RunMetrics, aggregate

_CSV_FIELDS = [
    "scenario",
    "tool",
    "model",
    "wall_seconds",
    "prompt_tokens",
    "completion_tokens",
    "completion_tok_per_sec",
    "ttft_seconds",
    "rss_peak_mb",
    "cpu_percent_avg",
    "ok",
    "error",
]


def write_csv(runs: Sequence[RunMetrics], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for r in runs:
            writer.writerow({
                "scenario": r.scenario,
                "tool": r.tool,
                "model": r.model,
                "wall_seconds": r.wall_seconds,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "completion_tok_per_sec": f"{r.completion_tok_per_sec:.4f}",
                "ttft_seconds": r.ttft_seconds,
                "rss_peak_mb": r.rss_peak_mb,
                "cpu_percent_avg": r.cpu_percent_avg,
                "ok": r.ok,
                "error": r.error or "",
            })


def write_markdown(
    runs: Sequence[RunMetrics], out_path: Path, title: str
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    agg = aggregate(runs)
    lines: list[str] = [f"# {title}", ""]
    lines.append("## Summary")
    for key, value in agg.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")
    lines.append("## Runs")
    lines.append("")
    lines.append(
        "| scenario | tool | model | wall_s | tok/s | ttft_s | rss_mb | ok | error |"
    )
    lines.append(
        "|---|---|---|---|---|---|---|---|---|"
    )
    for r in runs:
        lines.append(
            f"| {r.scenario} | {r.tool} | {r.model} | {r.wall_seconds:.2f} | "
            f"{r.completion_tok_per_sec:.2f} | {r.ttft_seconds:.2f} | "
            f"{r.rss_peak_mb:.0f} | {r.ok} | {r.error or ''} |"
        )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
