"""
tests/test_project_schema.py
Model validation for the M3 project-file contract (`quality_core.project.schema`, #276).

One valid-construction and one per-rule rejection for every model, plus the
model-level cross-field rules (tolerance ordering, unique characteristic names,
the SPC-result kind/payload discriminator both ways). The two SME-resolved design
calls (git-is-history: no run-id field; fmea.json is an envelope wrapper, not a
bare RelationalFMEA) are pinned here as explicit structural assertions.
"""
from __future__ import annotations

import json
from pathlib import Path

import pydantic
import pytest
from quality_core.project.schema import (
    SCHEMA_VERSION,
    ArtifactEnvelope,
    CapabilityPayload,
    ControlChartPayload,
    ControlPlanArtifact,
    ControlPlanArtifactRow,
    FMEAArtifact,
    MSAGageRRArtifact,
    NormalityPayload,
    ProjectCharacteristic,
    ProjectMeta,
    SPCConfigArtifact,
    SPCConfigRow,
    SPCResultArtifact,
    SPCToFMEAFeedbackArtifact,
)
from quality_core.schema.relational import RelationalFMEA

FIXTURES = Path(__file__).parent / "fixtures" / "project"


def _load_json(*parts: str) -> dict:
    return json.loads((FIXTURES.joinpath(*parts)).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# ArtifactEnvelope
# ---------------------------------------------------------------------------


def test_envelope_valid() -> None:
    env = ArtifactEnvelope(
        schema_version=SCHEMA_VERSION,
        generated_at="2026-08-13T12:00:00Z",
        generated_by="spc_app==0.14.0",
    )
    assert env.schema_version == 1


def test_envelope_rejects_blank_generated_by() -> None:
    with pytest.raises(pydantic.ValidationError):
        ArtifactEnvelope(
            schema_version=1, generated_at="2026-08-13T12:00:00Z", generated_by="   "
        )


def test_schema_version_constant_is_one() -> None:
    # Load path rejects any other value; the current shape is version 1.
    assert SCHEMA_VERSION == 1


# ---------------------------------------------------------------------------
# ProjectCharacteristic + tolerance rule
# ---------------------------------------------------------------------------


def _characteristic(**overrides: object) -> dict:
    base: dict = {
        "name": "Bore diameter",
        "unit": "mm",
        "lsl": 9.5,
        "usl": 10.5,
        "target": 10.0,
        "tolerance_source": "control_plan",
    }
    base.update(overrides)
    return base


def test_characteristic_valid() -> None:
    char = ProjectCharacteristic(**_characteristic())
    assert char.name == "Bore diameter"


def test_characteristic_tolerance_all_none_is_allowed() -> None:
    # None guards in _check_tolerance take the no-raise path.
    char = ProjectCharacteristic(name="x", lsl=None, usl=None, target=None, tolerance_source="manual")
    assert char.lsl is None


def test_characteristic_usl_not_greater_than_lsl_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match="usl must be greater than lsl"):
        ProjectCharacteristic(**_characteristic(lsl=10.5, usl=10.5, target=None))


def test_characteristic_target_outside_limits_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match=r"target must be within"):
        ProjectCharacteristic(**_characteristic(lsl=9.5, usl=10.5, target=20.0))


def test_characteristic_rejects_unknown_tolerance_source() -> None:
    with pytest.raises(pydantic.ValidationError):
        ProjectCharacteristic(**_characteristic(tolerance_source="guess"))


# ---------------------------------------------------------------------------
# ProjectMeta + unique-name rule
# ---------------------------------------------------------------------------


def test_project_meta_valid() -> None:
    meta = ProjectMeta(
        schema_version=1,
        project_id="example-project",
        name="Example",
        created_at="2026-08-13T12:00:00Z",
        characteristics=[ProjectCharacteristic(**_characteristic())],
    )
    assert meta.project_id == "example-project"


def test_project_meta_rejects_duplicate_characteristic_names() -> None:
    with pytest.raises(pydantic.ValidationError, match="duplicate characteristic names"):
        ProjectMeta(
            schema_version=1,
            project_id="p",
            name="P",
            created_at="2026-08-13T12:00:00Z",
            characteristics=[
                ProjectCharacteristic(**_characteristic(name="Dup")),
                ProjectCharacteristic(**_characteristic(name="Dup")),
            ],
        )


def test_project_meta_has_no_run_id_or_history_field() -> None:
    # SME resolution #1 (git is history): no run-id / history array anywhere.
    fields = set(ProjectMeta.model_fields)
    for banned in ("run_id", "run_uuid", "history", "runs", "revision"):
        assert banned not in fields
    for banned in ("run_id", "history", "runs"):
        assert banned not in set(ArtifactEnvelope.model_fields)


# ---------------------------------------------------------------------------
# FMEAArtifact — envelope wrapper over RelationalFMEA (SME resolution #2)
# ---------------------------------------------------------------------------


def test_fmea_artifact_wraps_relational_fmea() -> None:
    art = FMEAArtifact.model_validate(_load_json("fmea", "fmea.json"))
    assert isinstance(art.fmea, RelationalFMEA)
    assert art.schema_version == 1


def test_fmea_artifact_is_envelope_not_bare_relational_fmea() -> None:
    # The wrapper must carry the envelope fields AND a nested `fmea`; it must not
    # BE a RelationalFMEA (which would mean the bare-dump shape the SME rejected).
    assert issubclass(FMEAArtifact, ArtifactEnvelope)
    assert not issubclass(FMEAArtifact, RelationalFMEA)
    assert "fmea" in FMEAArtifact.model_fields
    assert "functions" not in FMEAArtifact.model_fields  # would leak if it were bare
    # RelationalFMEA itself must have gained no file-format fields.
    for banned in ("schema_version", "generated_at", "generated_by"):
        assert banned not in set(RelationalFMEA.model_fields)


# ---------------------------------------------------------------------------
# ControlPlanArtifact
# ---------------------------------------------------------------------------


def _cp_row(**overrides: object) -> dict:
    base: dict = {
        "characteristic": "Bore diameter",
        "lsl": 9.5,
        "usl": 10.5,
        "target": 10.0,
        "measurement_method": "Bore gauge",
        "sample_size": 5,
        "frequency": "per shift",
        "recommended_chart": "Xbar-R",
        "reaction_plan": "Quarantine the lot.",
        "source_cause_id": "F1-M1-C1",
        "sample_plan_is_placeholder": True,
    }
    base.update(overrides)
    return base


def test_control_plan_row_valid() -> None:
    row = ControlPlanArtifactRow(**_cp_row())
    assert row.sample_size == 5


def test_control_plan_row_rejects_sample_size_below_one() -> None:
    with pytest.raises(pydantic.ValidationError):
        ControlPlanArtifactRow(**_cp_row(sample_size=0))


def test_control_plan_row_enforces_tolerance_rule() -> None:
    with pytest.raises(pydantic.ValidationError, match="usl must be greater than lsl"):
        ControlPlanArtifactRow(**_cp_row(lsl=11.0, usl=10.0, target=None))


def test_control_plan_artifact_valid() -> None:
    art = ControlPlanArtifact.model_validate(_load_json("control-plan", "plan.json"))
    assert len(art.rows) == 1


def test_control_plan_artifact_rejects_duplicate_characteristics() -> None:
    with pytest.raises(pydantic.ValidationError, match="duplicate characteristic rows"):
        ControlPlanArtifact(
            schema_version=1,
            generated_at="2026-08-13T12:00:00Z",
            generated_by="controlplan_app==0.14.0",
            rows=[
                ControlPlanArtifactRow(**_cp_row(characteristic="Dup")),
                ControlPlanArtifactRow(**_cp_row(characteristic="Dup")),
            ],
        )


# ---------------------------------------------------------------------------
# SPCConfigArtifact — the Control Plan → SPC monitoring selection (#278)
# ---------------------------------------------------------------------------


def _spc_config_row(**overrides: object) -> dict:
    base: dict = {
        "characteristic": "Bore diameter",
        "chart_key": "Xbar-R",
        "lsl": 9.5,
        "usl": 10.5,
        "target": 10.0,
        "sample_size": 5,
        "frequency": "per shift",
    }
    base.update(overrides)
    return base


def test_spc_config_row_valid() -> None:
    row = SPCConfigRow(**_spc_config_row())
    assert row.chart_key == "Xbar-R"
    assert row.sample_size == 5


def test_spc_config_row_chart_key_none_allowed() -> None:
    # `None` means "no chart preselected" — the SPC layer lets the user pick.
    row = SPCConfigRow(**_spc_config_row(chart_key=None))
    assert row.chart_key is None


def test_spc_config_row_tolerance_all_none_is_allowed() -> None:
    row = SPCConfigRow(**_spc_config_row(lsl=None, usl=None, target=None))
    assert row.lsl is None and row.usl is None and row.target is None


def test_spc_config_row_usl_not_greater_than_lsl_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match="usl must be greater than lsl"):
        SPCConfigRow(**_spc_config_row(lsl=11.0, usl=10.0, target=None))


def test_spc_config_row_target_outside_limits_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match="target must be within"):
        SPCConfigRow(**_spc_config_row(lsl=9.5, usl=10.5, target=12.0))


def test_spc_config_row_rejects_sample_size_below_one() -> None:
    with pytest.raises(pydantic.ValidationError):
        SPCConfigRow(**_spc_config_row(sample_size=0))


def test_spc_config_row_sample_size_none_allowed() -> None:
    row = SPCConfigRow(**_spc_config_row(sample_size=None))
    assert row.sample_size is None


def test_spc_config_row_rejects_unknown_chart_key() -> None:
    # chart_key is the SPCChart Literal — EWMA/CUSUM are not valid config keys.
    with pytest.raises(pydantic.ValidationError):
        SPCConfigRow(**_spc_config_row(chart_key="EWMA"))


def test_spc_config_row_requires_characteristic() -> None:
    # StrictModel does not forbid extra fields (pydantic's default is to ignore them),
    # so the mirror-integrity guarantee is carried by required fields + strict typing,
    # not by extra-rejection: dropping `characteristic` fails loud.
    payload = _spc_config_row()
    del payload["characteristic"]
    with pytest.raises(pydantic.ValidationError):
        SPCConfigRow(**payload)


def test_spc_config_row_enforces_strict_typing() -> None:
    # strict=True: a stringly-typed sample_size is rejected, not coerced.
    with pytest.raises(pydantic.ValidationError):
        SPCConfigRow(**_spc_config_row(sample_size="5"))


def test_spc_config_artifact_valid_from_fixture() -> None:
    art = SPCConfigArtifact.model_validate(_load_json("spc", "config.json"))
    assert len(art.rows) == 1
    assert art.rows[0].characteristic == "Example Characteristic"
    assert art.rows[0].chart_key == "Xbar-R"


def test_spc_config_artifact_empty_rows_allowed() -> None:
    art = SPCConfigArtifact(
        schema_version=1,
        generated_at="2026-08-13T12:00:00Z",
        generated_by="spc_app==0.14.0",
        rows=[],
    )
    assert art.rows == []


def test_spc_config_artifact_rejects_duplicate_characteristics() -> None:
    with pytest.raises(pydantic.ValidationError, match="duplicate characteristic rows"):
        SPCConfigArtifact(
            schema_version=1,
            generated_at="2026-08-13T12:00:00Z",
            generated_by="spc_app==0.14.0",
            rows=[
                SPCConfigRow(**_spc_config_row(characteristic="Dup")),
                SPCConfigRow(**_spc_config_row(characteristic="Dup")),
            ],
        )


# ---------------------------------------------------------------------------
# SPCResultArtifact — kind/payload discriminator, all four branches
# ---------------------------------------------------------------------------


def _control_chart_payload(**overrides: object) -> dict:
    base: dict = {
        "chart_label": "Xbar-R",
        "stream": "Bore diameter",
        "rule_set": "Western Electric",
        "points": [10.02, 9.98, 10.11],
        "cl": 10.0,
        "ucl": 10.3,
        "lcl": 9.7,
        "violations": [{"index": 2, "rule": "Rule 1"}],
        "metrics": [{"label": "Subgroup size", "value": "5"}],
        "secondary_points": None,
    }
    base.update(overrides)
    return base


def _capability_payload(**overrides: object) -> dict:
    base: dict = {
        "stream_label": "Bore diameter",
        "values": [10.0, 10.1, 9.9],
        "capability": {"cp": 1.3, "cpk": 1.1, "ci": [1.0, 1.2]},
        "lsl": 9.5,
        "usl": 10.5,
        "normality": {"w_stat": 0.98, "p_value": 0.5, "is_normal": True},
        "oos_signal_count": 0,
    }
    base.update(overrides)
    return base


def _spc_result(**overrides: object) -> dict:
    base: dict = {
        "schema_version": 1,
        "generated_at": "2026-08-13T12:00:00Z",
        "generated_by": "spc_app==0.14.0",
        "kind": "control_chart",
        "characteristic": "Bore diameter",
        "control_chart": _control_chart_payload(),
        "capability": None,
    }
    base.update(overrides)
    return base


def test_spc_result_control_chart_valid() -> None:
    art = SPCResultArtifact.model_validate(_spc_result())
    assert art.control_chart is not None and art.capability is None


def test_spc_result_capability_valid() -> None:
    art = SPCResultArtifact.model_validate(
        _spc_result(kind="capability", control_chart=None, capability=_capability_payload())
    )
    assert art.capability is not None and art.control_chart is None


def test_spc_result_kind_requires_matching_payload() -> None:
    with pytest.raises(pydantic.ValidationError, match="requires a matching"):
        SPCResultArtifact.model_validate(_spc_result(control_chart=None, capability=None))


def test_spc_result_rejects_both_payloads() -> None:
    with pytest.raises(pydantic.ValidationError, match="must not carry the other payload"):
        SPCResultArtifact.model_validate(
            _spc_result(control_chart=_control_chart_payload(), capability=_capability_payload())
        )


def test_spc_result_per_point_limits_and_secondary_series() -> None:
    # Exercises the list-valued ucl/lcl union arm and the SecondarySeries model.
    art = SPCResultArtifact.model_validate(
        _spc_result(
            control_chart=_control_chart_payload(
                ucl=[10.3, 10.3, 10.3],
                lcl=[9.7, 9.7, 9.7],
                secondary_points={"label": "Range", "values": [0.1, 0.2, 0.05]},
            )
        )
    )
    assert isinstance(art.control_chart.ucl, list)  # type: ignore[union-attr]
    assert art.control_chart.secondary_points is not None  # type: ignore[union-attr]


def test_control_chart_payload_rejects_negative_violation_index() -> None:
    with pytest.raises(pydantic.ValidationError):
        ControlChartPayload(**_control_chart_payload(violations=[{"index": -1, "rule": "Rule 1"}]))


def test_capability_payload_rejects_negative_oos_count() -> None:
    with pytest.raises(pydantic.ValidationError):
        CapabilityPayload(**_capability_payload(oos_signal_count=-1))


def test_normality_payload_valid() -> None:
    n = NormalityPayload(w_stat=0.99, p_value=0.4, is_normal=True)
    assert n.is_normal


# ---------------------------------------------------------------------------
# MSAGageRRArtifact
# ---------------------------------------------------------------------------


def test_msa_artifact_valid() -> None:
    art = MSAGageRRArtifact.model_validate(_load_json("msa", "gage-rr.json"))
    assert art.verdict == "Acceptable"
    assert art.pev_tolerance == 12.4


def test_msa_artifact_tolerance_and_interaction_optional() -> None:
    data = _load_json("msa", "gage-rr.json")
    for key in ("pev_tolerance", "pav_tolerance", "pgrr_tolerance", "ppv_tolerance"):
        data[key] = None
    for key in ("interaction", "interaction_f", "interaction_significant"):
        data[key] = None
    art = MSAGageRRArtifact.model_validate(data)
    assert art.pev_tolerance is None and art.interaction is None


def test_msa_artifact_rejects_zero_parts() -> None:
    with pytest.raises(pydantic.ValidationError):
        MSAGageRRArtifact.model_validate({**_load_json("msa", "gage-rr.json"), "n_parts": 0})


def test_msa_artifact_rejects_negative_ndc() -> None:
    with pytest.raises(pydantic.ValidationError):
        MSAGageRRArtifact.model_validate({**_load_json("msa", "gage-rr.json"), "ndc": -1})


# ---------------------------------------------------------------------------
# SPCToFMEAFeedbackArtifact
# ---------------------------------------------------------------------------


def test_feedback_artifact_valid() -> None:
    art = SPCToFMEAFeedbackArtifact.model_validate(_load_json("feedback", "spc-to-fmea.json"))
    assert [row.ooc for row in art.rows] == [True]
    assert art.rows[0].suggested_occurrence == 6


def test_feedback_artifact_source_fields_optional() -> None:
    data = _load_json("feedback", "spc-to-fmea.json")
    for key in (
        "source_failure_mode_id",
        "source_cause_id",
        "source_cause_description",
        "current_occurrence",
        "component",
    ):
        data["rows"][0][key] = None
    art = SPCToFMEAFeedbackArtifact.model_validate(data)
    assert art.rows[0].source_cause_id is None and art.rows[0].current_occurrence is None


def test_feedback_artifact_rejects_occurrence_above_ten() -> None:
    data = _load_json("feedback", "spc-to-fmea.json")
    data["rows"][0]["suggested_occurrence"] = 11
    with pytest.raises(pydantic.ValidationError):
        SPCToFMEAFeedbackArtifact.model_validate(data)


def test_feedback_artifact_rejects_duplicate_characteristics() -> None:
    data = _load_json("feedback", "spc-to-fmea.json")
    data["rows"] = [data["rows"][0], dict(data["rows"][0])]
    with pytest.raises(pydantic.ValidationError, match="duplicate characteristic rows"):
        SPCToFMEAFeedbackArtifact.model_validate(data)


def test_feedback_artifact_accepts_empty_rows() -> None:
    data = {**_load_json("feedback", "spc-to-fmea.json"), "rows": []}
    assert SPCToFMEAFeedbackArtifact.model_validate(data).rows == []
