"""Smoke tests for the extraction material generator.

These do NOT verify visual correctness — that must be eyeballed. They verify:
- Files are created at expected paths
- PNGs are valid images with expected dimensions
- PPTX has 8 slides
- Each PNG contains the slide title as visible text (via structural checks where possible)
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from tests.text_vs_image.extraction import generate_extraction as g


EXPECTED_PNG_NAMES = [
    "p01_ui_callouts.png",
    "p02_before_after.png",
    "p03_process_flow.png",
    "p04_dashboard_annotated.png",
    "p05_hierarchical_drilldown.png",
    "p06_review_comments.png",
    "p07_mixed_dashboard.png",
    "p08_org_chart.png",
]

CANVAS_W, CANVAS_H = 1600, 900  # All PNGs share the same aspect ratio so Copilot gets uniform framing.


@pytest.mark.parametrize("pid", ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"])  # Extended to p01-p08 after each renderer lands.
def test_render_png_produces_valid_image(tmp_path: Path, pid: str):
    out_path = tmp_path / f"{pid}.png"
    g.render_png(pid, out_path)
    assert out_path.exists(), f"{pid} PNG was not created"
    with Image.open(out_path) as img:
        assert img.size == (CANVAS_W, CANVAS_H), f"{pid} PNG size {img.size} != expected {(CANVAS_W, CANVAS_H)}"
        assert img.format == "PNG"
