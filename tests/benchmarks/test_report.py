"""Tests for benchmarks.report."""
from __future__ import annotations

import csv
from pathlib import Path

from benchmarks.metrics import RunMetrics
from benchmarks.report import write_csv, write_markdown


def _sample_runs() -> list[RunMetrics]:
    return [
        RunMetrics("s2", "ollama", "qwen2.5-vl:7b",
                   3.5, 128, 42, 0.8, 6200.0, 82.1, True, None),
        RunMetrics("s2", "ollama", "qwen2.5-vl:7b",
                   4.1, 128, 50, 0.9, 6400.0, 85.0, True, None),
    ]


def test_write_csv_produces_header_and_rows(tmp_path: Path):
    out = tmp_path / "runs.csv"
    write_csv(_sample_runs(), out)
    with out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["scenario"] == "s2"
    assert rows[0]["tool"] == "ollama"
    assert float(rows[0]["wall_seconds"]) == 3.5
    assert rows[0]["ok"] == "True"


def test_write_markdown_contains_summary_and_table(tmp_path: Path):
    out = tmp_path / "runs.md"
    write_markdown(_sample_runs(), out, title="Phase 3 — Ollama S2")
    text = out.read_text(encoding="utf-8")
    assert "# Phase 3 — Ollama S2" in text
    assert "median_wall_seconds" in text
    assert "| scenario | tool | model |" in text
    assert "ollama" in text
