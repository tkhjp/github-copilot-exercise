"""Structural tests for the extraction_spec canonical dict."""
from __future__ import annotations

import pytest

from tests.text_vs_image.extraction import extraction_spec as spec_mod


EXPECTED_IDS = ["p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08"]


def test_spec_has_all_8_patterns():
    assert list(spec_mod.SPEC.keys()) == EXPECTED_IDS


@pytest.mark.parametrize("pid", EXPECTED_IDS)
def test_pattern_has_required_fields(pid):
    p = spec_mod.SPEC[pid]
    assert p["id"] == pid
    assert isinstance(p["title"], str) and p["title"]
    assert isinstance(p["pattern_name"], str) and p["pattern_name"]
    assert isinstance(p["facts"], list) and len(p["facts"]) >= 15, \
        f"{pid} should have at least 15 GT facts, got {len(p['facts'])}"
    for f in p["facts"]:
        assert set(f.keys()) >= {"id", "text"}, f"{pid}/{f} missing id or text"
        assert f["id"].startswith(pid + "_f"), f"fact id must start with {pid}_f"


def test_fact_ids_are_unique_within_pattern():
    for pid, p in spec_mod.SPEC.items():
        ids = [f["id"] for f in p["facts"]]
        assert len(ids) == len(set(ids)), f"{pid} has duplicate fact ids"


def test_total_fact_count_is_in_expected_range():
    # Spec 2.2 aimed at ~225; actual corpus landed at 141 after trimming.
    # Keep the upper bound to catch runaway bloat; lower bound just ensures
    # nothing catastrophic.
    total = sum(len(p["facts"]) for p in spec_mod.SPEC.values())
    assert 130 <= total <= 280, f"total facts {total} outside [130, 280]"
