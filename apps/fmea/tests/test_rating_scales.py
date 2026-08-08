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
    DEFAULT_SCALES_PATH,
    FACTORS,
    LEGACY_FMEA4_SCALES_PATH,
    RatingScaleSet,
    load_default_scales,
    load_legacy_fmea4_scales,
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
# RS-01 / RS-02 — bundled default (now AIAG & VDA 2019 PFMEA, #256)
# ---------------------------------------------------------------------------

# The 2019 PFMEA anchors these tests pin. Verbatim from the shipped JSON; the
# handbook provenance of every string lives in CITATIONS.tsv (test_citations.py).
_SEV10_2019 = (
    "Affects safe operation of the vehicle and/or other vehicles, the health of "
    "driver or passenger(s) or road users or pedestrians."
)
_DET10_2019 = "The failure mode will not or cannot be detected."
_DET1_2019 = (
    "Failure mode cannot be physically produced as-designed or processed, or "
    "detection methods proven to always detect the failure mode or failure cause."
)


def test_rs01_default_scales_load_complete():
    scales = load_default_scales()
    assert scales.name == "AIAG & VDA 2019 PFMEA (default)"
    assert scales.source  # citation preserved
    for factor in FACTORS:
        scale = getattr(scales, factor)
        assert set(scale) == set(range(1, 11))
    assert getattr(scales, "severity")[10] == _SEV10_2019


def test_rs02_to_frame_orders_10_to_1():
    scales = load_default_scales()
    frame = scales.to_frame("detection")
    assert list(frame["Score"]) == list(range(10, 0, -1))
    assert frame.iloc[0]["Meaning"] == _DET10_2019  # score 10
    assert frame.iloc[-1]["Meaning"] == _DET1_2019  # score 1
    assert len(frame) == 10


# ---------------------------------------------------------------------------
# RS-01b / RS-02b — legacy AIAG FMEA-4 scale (moved from old RS-01/RS-02, #256).
# Losing this coverage would silently drop the FMEA-4 anchors that still ship.
# ---------------------------------------------------------------------------

def test_rs01b_legacy_fmea4_scales_load_complete():
    scales = load_legacy_fmea4_scales()
    assert scales.name == "AIAG FMEA-4 (legacy)"
    assert scales.source  # citation preserved
    for factor in FACTORS:
        scale = getattr(scales, factor)
        assert set(scale) == set(range(1, 11))
    assert getattr(scales, "severity")[10] == "Safety hazard — no warning"


def test_rs02b_legacy_fmea4_to_frame_orders_10_to_1():
    scales = load_legacy_fmea4_scales()
    frame = scales.to_frame("detection")
    assert list(frame["Score"]) == list(range(10, 0, -1))
    assert frame.iloc[0]["Meaning"] == "No detection control exists"   # score 10
    assert frame.iloc[-1]["Meaning"] == "Almost certain detection"      # score 1
    assert len(frame) == 10


# ---------------------------------------------------------------------------
# Both bundled JSON files independently satisfy RatingScaleSet validation.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [DEFAULT_SCALES_PATH, LEGACY_FMEA4_SCALES_PATH])
def test_bundled_json_files_validate(path):
    scales = load_scales_from_json(path.read_text(encoding="utf-8"))
    assert scales.name  # a name field is present
    for factor in FACTORS:
        scale = getattr(scales, factor)
        assert set(scale) == set(range(1, 11))  # ratings 1–10 complete
        assert all(str(desc).strip() for desc in scale.values())  # none blank


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


def test_rs07b_pydantic_prefix_stripped_from_surfaced_message():
    """#207: `_build` runs the model-validator message through
    `clean_pydantic_message`, so the pydantic `Value error, ` / `Assertion failed, `
    prefix must NOT leak into the user-facing ValueError. The existing RS-07
    `match=` passes with or without the strip, so it does not pin this — this does.
    A no-op `clean_pydantic_message` fails here by leaking the raw prefix."""
    bad = _valid_mapping()
    bad["occurrence"]["4"] = "   "  # blank description -> model-validator error
    with pytest.raises(ValueError) as excinfo:
        load_scales_from_mapping(bad)
    msg = str(excinfo.value)
    assert "blank description" in msg  # the real content survives the strip
    assert "Value error" not in msg  # pydantic raise-prefix stripped
    assert "Assertion failed" not in msg  # pydantic assert-prefix stripped


# ---------------------------------------------------------------------------
# RS-08 / RS-09 — bad input shapes
# ---------------------------------------------------------------------------

def test_rs08_malformed_json_rejected():
    with pytest.raises(ValueError, match="parse rating-scale JSON"):
        load_scales_from_json("{not valid json")


def test_rs09_non_object_payload_rejected():
    with pytest.raises(ValueError, match="must be a JSON object"):
        load_scales_from_mapping(["not", "a", "dict"])  # type: ignore[arg-type]


def test_rs10_int_coercion_key_collision_rejected():
    """Keys '1' and '1.0' both coerce to int 1 — must fail loudly, not shadow."""
    bad = _valid_mapping()
    bad["severity"]["1.0"] = "duplicate of rating 1"
    with pytest.raises(ValueError, match="collide on rating"):
        load_scales_from_json(json.dumps(bad))


# ---------------------------------------------------------------------------
# #199 — fail-closed: byte ceiling + JSON-bomb hardening
# ---------------------------------------------------------------------------


def test_r3_deeply_nested_json_bomb_raises_value_error_not_recursion_error():
    """R3 (#199, MEDIUM): a deeply nested JSON payload must raise ValueError
    (caught by ui/filters.py's `except ValueError`), never an uncaught
    RecursionError."""
    bomb = "[" * 200_000 + "]" * 200_000
    with pytest.raises(ValueError, match="parse rating-scale JSON"):
        load_scales_from_json(bomb)


def test_oversized_json_payload_rejected_before_parsing():
    """The byte-length ceiling is checked before json.loads ever runs."""
    huge = json.dumps(_valid_mapping()) + " " * (21 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds the 20 MB limit"):
        load_scales_from_json(huge)


def test_oversized_json_payload_rejected_before_parsing_bytes():
    # bytes branch of the length check (len(text) rather than .encode()).
    huge = (json.dumps(_valid_mapping()) + " " * (21 * 1024 * 1024)).encode("utf-8")
    with pytest.raises(ValueError, match="exceeds the 20 MB limit"):
        load_scales_from_json(huge)


def test_json_payload_just_under_ceiling_still_loads():
    scales = load_scales_from_json(json.dumps(_valid_mapping()))
    assert scales.severity[1] == "level 1"


def test_bytes_with_invalid_utf8_still_raises_value_error():
    with pytest.raises(ValueError, match="parse rating-scale JSON"):
        load_scales_from_json(b"\xff\xfe not valid utf-8 or json")
