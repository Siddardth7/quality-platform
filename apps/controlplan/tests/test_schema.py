"""Tests for controlplan_app/schema.py — validated Control Plan upload ingest (W06-1).

Two layers: ``lsl``/``usl``/``target``/``recommended_chart`` are deliberately
excluded from ``CONTROL_PLAN_SCHEMA.required_columns`` (SME resolution 2) so a
CSV that omits them is still the valid "not SPC-monitored" shape. They are
declared as ``optional_columns`` instead (#200), so ``quality_core.io`` validates
any of them the upload *does* carry through ``ControlPlanRow``'s own validators in
the normal ingest pass — so the tolerance/target-range/chart-enum rules are
exercised both by constructing ``ControlPlanRow`` directly (fast, isolated) and
through the real CSV path (below, proving the upload-time rejection actually
fires). Mirrors ``apps/msa/tests/test_schema.py`` structurally.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pydantic
import pytest
from controlplan_app.schema import (
    CONTROL_PLAN_SCHEMA,
    ControlPlanDataset,
    ControlPlanRow,
    IngestError,
    load_control_plan_csv,
)

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "data" / "control_plan_template.csv"

GOOD_ROW_KWARGS = dict(
    characteristic="Bore Diameter",
    measurement_method="Bore gauge",
    sample_size=5,
    frequency="per shift",
    reaction_plan="Stop line; notify quality engineer.",
)


def _csv(rows, name: str = "upload.csv") -> io.BytesIO:
    buf = io.BytesIO(pd.DataFrame(rows).to_csv(index=False).encode())
    buf.name = name  # mimic a Streamlit UploadedFile
    return buf


def _csv_from_frame(frame: pd.DataFrame, name: str = "upload.csv") -> io.BytesIO:
    buf = io.BytesIO(frame.to_csv(index=False).encode())
    buf.name = name
    return buf


def _good_csv_row() -> dict:
    return {
        "characteristic": "Bore Diameter",
        "measurement_method": "Bore gauge",
        "sample_size": 5,
        "frequency": "per shift",
        "reaction_plan": "Stop line; notify quality engineer.",
    }


# --- schema wiring -------------------------------------------------------------


def test_required_columns_are_the_five_always_required_fields():
    assert CONTROL_PLAN_SCHEMA.required_columns == (
        "characteristic",
        "measurement_method",
        "sample_size",
        "frequency",
        "reaction_plan",
    )


def test_ingest_error_is_value_error():
    assert issubclass(IngestError, ValueError)


# --- ControlPlanRow: direct construction (tolerance / target / chart rules) ----
# lsl/usl/target/recommended_chart never reach ControlPlanRow via the CSV path
# (see module docstring), so these rules are exercised at the model level.


def test_row_valid_full_tolerance_and_chart():
    row = ControlPlanRow(
        lsl=24.90, usl=25.10, target=25.00, recommended_chart="Xbar-R", **GOOD_ROW_KWARGS
    )
    assert row.lsl == 24.90
    assert row.usl == 25.10
    assert row.recommended_chart == "Xbar-R"


def test_row_usl_equal_to_lsl_rejected():
    with pytest.raises(pydantic.ValidationError, match="usl must be greater than lsl"):
        ControlPlanRow(lsl=25.0, usl=25.0, **GOOD_ROW_KWARGS)


def test_row_usl_below_lsl_rejected():
    with pytest.raises(pydantic.ValidationError, match="usl must be greater than lsl"):
        ControlPlanRow(lsl=25.0, usl=24.0, **GOOD_ROW_KWARGS)


def test_row_target_below_lsl_rejected():
    with pytest.raises(pydantic.ValidationError, match="target must be within"):
        ControlPlanRow(lsl=25.0, usl=26.0, target=24.0, **GOOD_ROW_KWARGS)


def test_row_target_above_usl_rejected():
    with pytest.raises(pydantic.ValidationError, match="target must be within"):
        ControlPlanRow(lsl=25.0, usl=26.0, target=27.0, **GOOD_ROW_KWARGS)


def test_row_target_at_bounds_accepted():
    # boundary values are inclusive ([lsl, usl])
    assert ControlPlanRow(lsl=25.0, usl=26.0, target=25.0, **GOOD_ROW_KWARGS).target == 25.0
    assert ControlPlanRow(lsl=25.0, usl=26.0, target=26.0, **GOOD_ROW_KWARGS).target == 26.0


def test_row_one_sided_spec_lsl_only_accepted():
    row = ControlPlanRow(lsl=24.90, **GOOD_ROW_KWARGS)
    assert row.lsl == 24.90
    assert row.usl is None


def test_row_one_sided_spec_usl_only_accepted():
    row = ControlPlanRow(usl=3.2, **GOOD_ROW_KWARGS)
    assert row.usl == 3.2
    assert row.lsl is None


def test_row_target_without_bounds_accepted():
    # target present but lsl/usl missing -> the cross-check does not fire.
    row = ControlPlanRow(target=25.0, **GOOD_ROW_KWARGS)
    assert row.target == 25.0


def test_row_optional_fields_default_to_none():
    row = ControlPlanRow(**GOOD_ROW_KWARGS)
    assert row.lsl is None
    assert row.usl is None
    assert row.target is None
    assert row.recommended_chart is None
    assert row.source_cause_id is None


# --- ControlPlanRow.source_cause_id (OQ1 join key, W07-2 #89) -----------------


def test_row_source_cause_id_round_trips():
    row = ControlPlanRow(source_cause_id="F1::F1-M1::F1-M1-C1", **GOOD_ROW_KWARGS)
    assert row.source_cause_id == "F1::F1-M1::F1-M1-C1"


def test_row_source_cause_id_blank_coerced_to_none():
    row = ControlPlanRow(source_cause_id="   ", **GOOD_ROW_KWARGS)
    assert row.source_cause_id is None


def test_row_source_cause_id_stripped():
    row = ControlPlanRow(source_cause_id="  F1::F1-M1::F1-M1-C1  ", **GOOD_ROW_KWARGS)
    assert row.source_cause_id == "F1::F1-M1::F1-M1-C1"


def test_row_source_cause_id_none_passes_through():
    row = ControlPlanRow(source_cause_id=None, **GOOD_ROW_KWARGS)
    assert row.source_cause_id is None


def test_row_recommended_chart_accepts_every_spc_chart_key():
    for chart in ("Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"):
        assert ControlPlanRow(recommended_chart=chart, **GOOD_ROW_KWARGS).recommended_chart == chart


def test_row_recommended_chart_none_accepted():
    assert ControlPlanRow(recommended_chart=None, **GOOD_ROW_KWARGS).recommended_chart is None


def test_row_recommended_chart_unknown_string_rejected():
    with pytest.raises(pydantic.ValidationError, match="recommended_chart"):
        ControlPlanRow(recommended_chart="Bogus-Chart", **GOOD_ROW_KWARGS)


def test_row_lsl_infinite_rejected():
    with pytest.raises(pydantic.ValidationError, match="lsl"):
        ControlPlanRow(lsl=float("inf"), **GOOD_ROW_KWARGS)


def test_row_usl_infinite_rejected():
    with pytest.raises(pydantic.ValidationError, match="usl"):
        ControlPlanRow(usl=float("-inf"), **GOOD_ROW_KWARGS)


def test_row_target_infinite_rejected():
    with pytest.raises(pydantic.ValidationError, match="target"):
        ControlPlanRow(target=float("nan"), **GOOD_ROW_KWARGS)


def test_row_float_field_coerces_numeric_string():
    row = ControlPlanRow(lsl="24.90", **GOOD_ROW_KWARGS)
    assert row.lsl == 24.90


# --- ControlPlanRow: required string fields (reject_blank + type coercion) ----


def test_row_characteristic_blank_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["characteristic"] = "   "
    with pytest.raises(pydantic.ValidationError, match="characteristic"):
        ControlPlanRow(**kwargs)


def test_row_measurement_method_blank_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["measurement_method"] = ""
    with pytest.raises(pydantic.ValidationError, match="measurement_method"):
        ControlPlanRow(**kwargs)


def test_row_frequency_blank_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["frequency"] = "\t"
    with pytest.raises(pydantic.ValidationError, match="frequency"):
        ControlPlanRow(**kwargs)


def test_row_reaction_plan_blank_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["reaction_plan"] = "  \n  "
    with pytest.raises(pydantic.ValidationError, match="reaction_plan"):
        ControlPlanRow(**kwargs)


def test_row_string_fields_are_stripped():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["characteristic"] = "  Bore Diameter  "
    row = ControlPlanRow(**kwargs)
    assert row.characteristic == "Bore Diameter"


def test_row_non_string_characteristic_rejected():
    # Exercises the non-str branch of reject_blank (returned unchanged), then
    # pydantic's own str-type check rejects the coerced-through int.
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["characteristic"] = 123
    with pytest.raises(pydantic.ValidationError, match="characteristic"):
        ControlPlanRow(**kwargs)


def test_row_sample_size_below_one_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["sample_size"] = 0
    with pytest.raises(pydantic.ValidationError, match="sample_size"):
        ControlPlanRow(**kwargs)


def test_row_sample_size_non_integer_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["sample_size"] = 1.5
    with pytest.raises(pydantic.ValidationError, match="sample_size"):
        ControlPlanRow(**kwargs)


def test_row_sample_size_coerces_numeric_string():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["sample_size"] = "5"
    assert ControlPlanRow(**kwargs).sample_size == 5


def test_row_characteristic_too_long_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["characteristic"] = "x" * 201
    with pytest.raises(pydantic.ValidationError, match="characteristic"):
        ControlPlanRow(**kwargs)


def test_row_reaction_plan_too_long_rejected():
    kwargs = dict(GOOD_ROW_KWARGS)
    kwargs["reaction_plan"] = "x" * 2001
    with pytest.raises(pydantic.ValidationError, match="reaction_plan"):
        ControlPlanRow(**kwargs)


# --- ControlPlanDataset: duplicate characteristic uniqueness ------------------


def test_dataset_accepts_unique_characteristics():
    ds = ControlPlanDataset(
        rows=[
            ControlPlanRow(**GOOD_ROW_KWARGS),
            ControlPlanRow(**{**GOOD_ROW_KWARGS, "characteristic": "Surface Finish"}),
        ]
    )
    assert len(ds.rows) == 2


def test_dataset_rejects_duplicate_characteristic():
    with pytest.raises(pydantic.ValidationError, match="duplicate characteristic"):
        ControlPlanDataset(
            rows=[
                ControlPlanRow(**GOOD_ROW_KWARGS),
                ControlPlanRow(**GOOD_ROW_KWARGS),
            ]
        )


def test_dataset_accepts_empty_rows():
    assert ControlPlanDataset(rows=[]).rows == []


# --- load_control_plan_csv: happy paths ---------------------------------------


def test_valid_upload_passes_and_returns_frame():
    out = load_control_plan_csv(_csv([_good_csv_row()]))
    assert len(out) == 1
    assert list(out["characteristic"]) == ["Bore Diameter"]


def test_valid_upload_multiple_rows():
    rows = [_good_csv_row(), {**_good_csv_row(), "characteristic": "Surface Finish"}]
    out = load_control_plan_csv(_csv(rows))
    assert len(out) == 2


def test_template_validates_as_the_documented_shape():
    out = load_control_plan_csv(str(TEMPLATE_PATH))
    assert len(out) == 3
    assert sorted(out["characteristic"]) == [
        "Bore Diameter",
        "Surface Finish",
        "Visual Inspection",
    ]


# --- load_control_plan_csv: malformed paths (only the 5 required columns) -----


def test_blank_characteristic_rejected():
    rows = [{**_good_csv_row(), "characteristic": "   "}]
    with pytest.raises(IngestError, match="characteristic"):
        load_control_plan_csv(_csv(rows))


def test_blank_measurement_method_rejected():
    rows = [{**_good_csv_row(), "measurement_method": ""}]
    with pytest.raises(IngestError, match="measurement_method"):
        load_control_plan_csv(_csv(rows))


def test_blank_frequency_rejected():
    rows = [{**_good_csv_row(), "frequency": "   "}]
    with pytest.raises(IngestError, match="frequency"):
        load_control_plan_csv(_csv(rows))


def test_blank_reaction_plan_rejected():
    rows = [{**_good_csv_row(), "reaction_plan": "   "}]
    with pytest.raises(IngestError, match="reaction_plan"):
        load_control_plan_csv(_csv(rows))


def test_sample_size_below_one_rejected_via_csv():
    rows = [{**_good_csv_row(), "sample_size": 0}]
    with pytest.raises(IngestError, match="sample_size"):
        load_control_plan_csv(_csv(rows))


def test_non_numeric_sample_size_row_addressed():
    rows = [
        _good_csv_row(),
        {**_good_csv_row(), "characteristic": "Surface Finish", "sample_size": "oops"},
    ]
    with pytest.raises(IngestError) as exc:
        load_control_plan_csv(_csv(rows))
    msg = str(exc.value)
    assert "Row 3" in msg  # header is row 1
    assert "sample_size" in msg


def test_missing_required_column_is_friendly():
    rows = [
        {k: v for k, v in _good_csv_row().items() if k != "reaction_plan"}
    ]  # no reaction_plan
    with pytest.raises(
        IngestError, match=r"Missing required column\(s\): \['reaction_plan'\]"
    ):
        load_control_plan_csv(_csv(rows))


def test_empty_upload_is_friendly():
    empty = pd.DataFrame(
        columns=[
            "characteristic",
            "measurement_method",
            "sample_size",
            "frequency",
            "reaction_plan",
        ]
    )
    with pytest.raises(IngestError, match="at least one"):
        load_control_plan_csv(_csv_from_frame(empty))


def test_duplicate_characteristic_rejected_via_csv():
    rows = [_good_csv_row(), _good_csv_row()]  # same characteristic twice
    with pytest.raises(IngestError, match="duplicate characteristic"):
        load_control_plan_csv(_csv(rows))


# --- load_control_plan_csv: optional tolerance/chart columns, when present ----
# lsl/usl/target/recommended_chart stay out of required_columns (nullable) but are
# declared in optional_columns, so quality_core.io validates them whenever the
# uploaded CSV carries the column (#200) — these prove that happens through the
# real CSV path, not just ControlPlanRow(...).


def test_usl_below_lsl_rejected_via_csv():
    rows = [{**_good_csv_row(), "lsl": 25.0, "usl": 24.0}]
    with pytest.raises(IngestError, match="usl must be greater than lsl"):
        load_control_plan_csv(_csv(rows))


def test_target_below_lsl_rejected_via_csv():
    rows = [{**_good_csv_row(), "lsl": 25.0, "usl": 26.0, "target": 24.0}]
    with pytest.raises(IngestError, match="target must be within"):
        load_control_plan_csv(_csv(rows))


def test_target_above_usl_rejected_via_csv():
    rows = [{**_good_csv_row(), "lsl": 25.0, "usl": 26.0, "target": 27.0}]
    with pytest.raises(IngestError, match="target must be within"):
        load_control_plan_csv(_csv(rows))


def test_unknown_recommended_chart_rejected_via_csv():
    rows = [{**_good_csv_row(), "recommended_chart": "Not-A-Real-Chart"}]
    with pytest.raises(IngestError, match="recommended_chart") as exc:
        load_control_plan_csv(_csv(rows))
    assert "Not-A-Real-Chart" in str(exc.value)


def test_bad_optional_value_error_is_row_addressed():
    # second row is the offender -> message must name row 3 (header is row 1).
    rows = [
        _good_csv_row(),
        {**_good_csv_row(), "characteristic": "Surface Finish", "usl": 24.0, "lsl": 25.0},
    ]
    with pytest.raises(IngestError, match="Row 3"):
        load_control_plan_csv(_csv(rows))


def test_omitted_optional_columns_load_clean_via_csv():
    # no lsl/usl/target/recommended_chart columns at all -> no-op, no false reject.
    out = load_control_plan_csv(_csv([_good_csv_row()]))
    assert len(out) == 1


def test_valid_optional_values_load_clean_via_csv():
    rows = [
        {
            **_good_csv_row(),
            "lsl": 24.90,
            "usl": 25.10,
            "target": 25.00,
            "recommended_chart": "Xbar-R",
        }
    ]
    out = load_control_plan_csv(_csv(rows))
    assert len(out) == 1
    assert out["recommended_chart"].iloc[0] == "Xbar-R"


def test_one_sided_spec_lsl_only_loads_clean_via_csv():
    rows = [{**_good_csv_row(), "lsl": 24.90, "usl": None, "target": None}]
    out = load_control_plan_csv(_csv(rows))
    assert len(out) == 1


def test_one_sided_spec_usl_only_loads_clean_via_csv():
    rows = [{**_good_csv_row(), "usl": 3.2, "lsl": None, "target": None}]
    out = load_control_plan_csv(_csv(rows))
    assert len(out) == 1


def test_optional_columns_are_the_six_declared_ones():
    assert CONTROL_PLAN_SCHEMA.optional_columns == (
        "lsl",
        "usl",
        "target",
        "recommended_chart",
        "source_cause_id",
        "sample_plan_is_placeholder",
    )


def test_placeholder_flag_is_optional_never_required():
    # F-10 (#196) is additive: an upload predating the column must still validate.
    assert "sample_plan_is_placeholder" not in CONTROL_PLAN_SCHEMA.required_columns


# ---------------------------------------------------------------------------
# sample_plan_is_placeholder (F-10, #196)
# ---------------------------------------------------------------------------


def test_placeholder_flag_defaults_to_false():
    # A hand-authored row asserts its own sample plan — it is not a placeholder.
    assert ControlPlanRow(**GOOD_ROW_KWARGS).sample_plan_is_placeholder is False


def test_placeholder_flag_explicit_true_round_trips():
    row = ControlPlanRow(**GOOD_ROW_KWARGS, sample_plan_is_placeholder=True)
    assert row.sample_plan_is_placeholder is True
    assert ControlPlanRow(**row.model_dump()).sample_plan_is_placeholder is True


def test_placeholder_flag_explicit_false_round_trips():
    # The other direction of the same choice: an engineered row can carry False
    # and it must not be silently upgraded to True.
    row = ControlPlanRow(**GOOD_ROW_KWARGS, sample_plan_is_placeholder=False)
    assert row.sample_plan_is_placeholder is False
    assert ControlPlanRow(**row.model_dump()).sample_plan_is_placeholder is False


@pytest.mark.parametrize("blank", [None, "", "   ", "\t\n"])
def test_placeholder_flag_missing_or_blank_coerces_to_false(blank):
    # The before-validator's coercion arm: a NaN->None cell from the ingest
    # boundary, or a blank CSV cell, means "not flagged" — not a validation error.
    row = ControlPlanRow(**GOOD_ROW_KWARGS, sample_plan_is_placeholder=blank)
    assert row.sample_plan_is_placeholder is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("True", True), (1, True), ("false", False), ("False", False), (0, False)],
)
def test_placeholder_flag_non_blank_values_pass_through_to_coercion(raw, expected):
    # The before-validator's passthrough arm: a non-blank value is handed to
    # pydantic's non-strict bool coercion untouched (both directions).
    row = ControlPlanRow(**GOOD_ROW_KWARGS, sample_plan_is_placeholder=raw)
    assert row.sample_plan_is_placeholder is expected


def test_placeholder_flag_rejects_uninterpretable_value():
    with pytest.raises(pydantic.ValidationError):
        ControlPlanRow(**GOOD_ROW_KWARGS, sample_plan_is_placeholder="maybe")


def test_dataset_preserves_placeholder_flag_per_row():
    rows = [
        ControlPlanRow(**{**GOOD_ROW_KWARGS, "characteristic": "A"}, sample_plan_is_placeholder=True),
        ControlPlanRow(**{**GOOD_ROW_KWARGS, "characteristic": "B"}, sample_plan_is_placeholder=False),
    ]
    dataset = ControlPlanDataset(rows=rows)
    assert [r.sample_plan_is_placeholder for r in dataset.rows] == [True, False]


def test_csv_without_placeholder_column_validates_and_reads_false():
    out = load_control_plan_csv(_csv([_good_csv_row()]))
    assert len(out) == 1
    assert "sample_plan_is_placeholder" not in out.columns
    # The column is absent from the narrowed frame, but the model default holds.
    assert ControlPlanRow(**out.iloc[0].to_dict()).sample_plan_is_placeholder is False


@pytest.mark.parametrize(("cell", "expected"), [(True, True), (False, False)])
def test_csv_with_placeholder_column_parses_both_values(cell, expected):
    rows = [{**_good_csv_row(), "sample_plan_is_placeholder": cell}]
    out = load_control_plan_csv(_csv(rows))
    assert len(out) == 1
    assert bool(out["sample_plan_is_placeholder"].iloc[0]) is expected


def test_csv_with_blank_placeholder_cell_validates_as_false():
    rows = [
        {**_good_csv_row(), "characteristic": "A", "sample_plan_is_placeholder": True},
        {**_good_csv_row(), "characteristic": "B", "sample_plan_is_placeholder": None},
    ]
    out = load_control_plan_csv(_csv(rows))
    assert len(out) == 2
    flags = [
        ControlPlanRow(
            **{k: (None if pd.isna(v) else v) for k, v in rec.items()}
        ).sample_plan_is_placeholder
        for rec in out.to_dict("records")
    ]
    assert flags == [True, False]


def test_undeclared_column_dropped_and_declared_ones_survive_via_csv():
    # #200: the narrowed return is the five required columns plus the present
    # optional ones, in schema order — an undeclared column cannot ride through.
    rows = [
        {
            **_good_csv_row(),
            "lsl": 24.90,
            "usl": 25.10,
            "target": 25.00,
            "recommended_chart": "Xbar-R",
            "operator_notes": "third shift",
        }
    ]
    out = load_control_plan_csv(_csv(rows))
    assert list(out.columns) == [
        "characteristic",
        "measurement_method",
        "sample_size",
        "frequency",
        "reaction_plan",
        "lsl",
        "usl",
        "target",
        "recommended_chart",
    ]
    assert "operator_notes" not in out.columns


@pytest.mark.parametrize(
    ("extra", "sentence"),
    [
        ({"lsl": 25.0, "usl": 24.0}, "usl must be greater than lsl"),
        ({"lsl": 25.0, "usl": 26.0, "target": 27.0}, "target must be within [lsl, usl]"),
    ],
)
def test_model_level_error_shape_row_addressed_with_truncated_row_echo(extra, sentence):
    # #200 known message change, asserted deliberately rather than by accident: a
    # model-validator error has no `loc`, so the message carries no column name,
    # and the core formatter (_format_row_error) *always* echoes the offending
    # input — here the whole row dict, truncated at 50 chars. The deleted app-local
    # _reject_bad_optional_values used to suppress that echo.
    with pytest.raises(IngestError) as exc:
        load_control_plan_csv(_csv([{**_good_csv_row(), **extra}]))
    msg = str(exc.value)
    # #207: the core formatter now routes msg through clean_pydantic_message, so
    # pydantic's "Value error, " prefix is stripped here too. Everything else about
    # the shape (no column clause, truncated echo) is #200's and is unchanged below.
    assert msg.startswith(f"Row 2: {sentence} (got {{'characteristic': ")
    assert "Value error" not in msg
    assert "column" not in msg.split(" (got ")[0]  # no column name on a model-level error
    assert "...)" in msg  # the row dict is truncated, not echoed whole


def test_field_level_optional_error_still_names_the_column():
    # Contrast with the model-level shape above: a field error keeps its `loc`.
    rows = [{**_good_csv_row(), "recommended_chart": "Bogus"}]
    with pytest.raises(IngestError) as exc:
        load_control_plan_csv(_csv(rows))
    assert str(exc.value).startswith("Row 2, column 'recommended_chart': ")


def test_mixed_recommended_chart_presence_only_bad_row_rejected():
    # one row has no chart (None), one has a valid chart, one has a bad chart —
    # only the bad row should raise, proving per-row (not per-column) checking.
    rows = [
        {**_good_csv_row(), "recommended_chart": None},
        {**_good_csv_row(), "characteristic": "Surface Finish", "recommended_chart": "Xbar-R"},
        {**_good_csv_row(), "characteristic": "Bore Taper", "recommended_chart": "Bogus"},
    ]
    with pytest.raises(IngestError, match="Row 4"):  # header + 2 good rows before it
        load_control_plan_csv(_csv(rows))
