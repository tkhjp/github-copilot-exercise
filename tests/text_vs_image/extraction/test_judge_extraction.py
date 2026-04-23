"""Tests for the extraction judge pipeline (mocked Gemini calls)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from tests.text_vs_image.extraction import judge_extraction as je


def _write_response_md(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# extraction — example\n\n## Output\n\n{body}\n",
        encoding="utf-8",
    )


def test_extract_output_section_strips_header(tmp_path: Path):
    p = tmp_path / "r.md"
    _write_response_md(p, "Hello world")
    assert je.extract_output_section(p) == "Hello world"


def test_extract_output_section_handles_missing_header(tmp_path: Path):
    p = tmp_path / "r.md"
    p.write_text("No header at all\njust body", encoding="utf-8")
    # Falls back to the whole file stripped.
    assert "No header at all" in je.extract_output_section(p)


def test_load_ground_truth_returns_8_patterns(tmp_path: Path):
    from tests.text_vs_image.extraction.extraction_spec import emit_ground_truth_yaml
    gt_path = tmp_path / "gt.yaml"
    emit_ground_truth_yaml(gt_path)
    gt = je.load_ground_truth(gt_path)
    assert set(gt.keys()) == {"p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"}
    assert all("facts" in v for v in gt.values())


def test_hallucination_prompt_template_has_required_slots():
    tmpl = je.JUDGE_PROMPT_HALLUCINATION
    assert "{description}" in tmpl
    assert "{facts_json}" in tmpl


def test_split_pptx_response_heuristic_uses_slide_headers():
    response = """
## Slide 1
Line A for p01.

## Slide 2
Line B for p02.

## Slide 3
Line C for p03.
""".strip()
    segments = je.split_pptx_response_heuristic(response, n_slides=8)
    assert len(segments) == 8
    assert "Line A for p01" in segments[0]
    assert "Line B for p02" in segments[1]
    assert "Line C for p03" in segments[2]
    # Slides 4-8 have no header match; should be empty strings.
    for i in range(3, 8):
        assert segments[i] == "", f"slide {i+1} should be empty when no header present"


def test_split_pptx_response_heuristic_no_headers_returns_whole_as_slide_1():
    response = "Free-form text, no slide headers at all"
    segments = je.split_pptx_response_heuristic(response, n_slides=8)
    assert segments[0] == response
    for i in range(1, 8):
        assert segments[i] == ""


def test_extract_output_section_empty_body_returns_empty_string(tmp_path: Path):
    """A response file with `## Output` followed only by an HTML-comment placeholder
    should extract to an empty string (caller can then skip judge calls)."""
    p = tmp_path / "empty.md"
    p.write_text("# x\n\n## Output\n\n<!-- paste here -->\n", encoding="utf-8")
    assert je.extract_output_section(p) == ""


def test_split_pptx_response_heuristic_oob_slide_number_is_ignored():
    """`## Slide 9` (out of range for n_slides=8) should be silently ignored and
    its content dropped, NOT crash or land in an unrelated segment."""
    response = """
## Slide 1
Legit p01 content.

## Slide 9
Hallucinated slide — should be dropped.
""".strip()
    segments = je.split_pptx_response_heuristic(response, n_slides=8)
    assert "Legit p01 content" in segments[0]
    for i in range(1, 8):
        assert "Hallucinated" not in segments[i]


def test_split_pptx_response_heuristic_duplicate_header_last_wins():
    """Duplicate `## Slide N` headers: the last match's content overwrites earlier —
    documenting current behavior so future maintainers don't accidentally change it."""
    response = """
## Slide 1
First p01 block.

## Slide 1
Second p01 block (replaces first).
""".strip()
    segments = je.split_pptx_response_heuristic(response, n_slides=8)
    assert "Second p01 block" in segments[0]
    assert "First p01 block" not in segments[0]
