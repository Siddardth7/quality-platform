"""
tests/test_rating_scales.py
Tests for fmea_app/rating_scales.py — data-driven S/O/D rating scales (W03-4).

Coverage:
    RS-01  Bundled AIAG default loads with all three factors, ratings 1–10
    RS-02  to_frame returns a 10→1 ordered table for each factor
    RS-03  A valid custom mapping loads
    RS-04  Valid custom JSON text loads
    RS-05  Missing a rating is rejected
    RS-06  Out-of-range / extra rating is rejected
    RS-07  Blank description is rejected
    RS-08  Malformed JSON is rejected with a clear ValueError
    RS-09  Non-object payload is rejected
"""

import json

import pytest

from fmea_app.rating_scales import (
    FACTORS,
    RatingScaleSet,
    load_default_scales,
    load_scales_from_json,
    load_scales_from_mapping,
)


def _full_scale() -> dict[str, str]:
    return {str(i): f"level {i}" for i in range(1, 11)}


def _valid_mapping() -> dict:
    return {
        "name": "Acme PFMEA",
        "severity": _full_scale(),
        "occurrence": _full_scale(),
        "detection": _full_scale(),
    }


# ---------------------------------------------------------------------------
# RS-01 / RS-02 — bundled default
# ---------------------------------------------------------------------------

def test_rs01_default_scales_load_complete():
    scales = load_default_scales()
    assert scales.name == "AIAG FMEA-4 (default)"
    assert scales.source  # citation preserved
    for factor in FACTORS:
        scale = getattr(scales, factor)
        assert set(scale) == set(range(1, 11))
    assert getattr(scales, "severity")[10] == "Safety hazard — no warning"


def test_rs02_to_frame_orders_10_to_1():
    scales = load_default_scales()
    frame = scales.to_frame("detection")
    assert list(frame["Score"]) == list(range(10, 0, -1))
    assert frame.iloc[0]["Meaning"] == "No detection control exists"   # score 10
    assert frame.iloc[-1]["Meaning"] == "Almost certain detection"      # score 1
    assert len(frame) == 10


# ---------------------------------------------------------------------------
# RS-03 / RS-04 — valid custom scales
# ---------------------------------------------------------------------------

def test_rs03_valid_custom_mapping_loads():
    scales = load_scales_from_mapping(_valid_mapping())
    assert isinstance(scales, RatingScaleSet)
    assert scales.name == "Acme PFMEA"
    assert scales.severity[1] == "level 1"


def test_rs04_valid_custom_json_text_loads():
    scales = load_scales_from_json(json.dumps(_valid_mapping()))
    assert scales.occurrence[5] == "level 5"


# ---------------------------------------------------------------------------
# RS-05..RS-07 — validation failures
# ---------------------------------------------------------------------------

def test_rs05_missing_rating_rejected():
    bad = _valid_mapping()
    del bad["severity"]["3"]
    with pytest.raises(ValueError, match="ratings 1–10"):
        load_scales_from_mapping(bad)


def test_rs06_out_of_range_rating_rejected():
    bad = _valid_mapping()
    bad["detection"]["11"] = "too high"
    with pytest.raises(ValueError, match="ratings 1–10"):
        load_scales_from_mapping(bad)


def test_rs07_blank_description_rejected():
    bad = _valid_mapping()
    bad["occurrence"]["4"] = "   "
    with pytest.raises(ValueError, match="blank description"):
        load_scales_from_mapping(bad)


# ---------------------------------------------------------------------------
# RS-08 / RS-09 — bad input shapes
# ---------------------------------------------------------------------------

def test_rs08_malformed_json_rejected():
    with pytest.raises(ValueError, match="parse rating-scale JSON"):
        load_scales_from_json("{not valid json")


def test_rs09_non_object_payload_rejected():
    with pytest.raises(ValueError, match="must be a JSON object"):
        load_scales_from_mapping(["not", "a", "dict"])  # type: ignore[arg-type]
