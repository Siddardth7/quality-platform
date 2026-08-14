"""
quality_core/project/schema.py
The M3 on-disk data contract: `project.yaml` plus the five artifact files a
Quality Platform project directory holds (#276).

**Files hold current state only — git is the history** (SME resolution, #276).
`project.yaml.project_id` is a stable human-chosen slug (the directory name in
practice), not a per-run UUID; every artifact carries `generated_at` /
`generated_by` so a reader can tell how fresh it is; a re-run *overwrites* its
own artifact file in place, and `spc/results/<slug>.json` is one file per
monitored characteristic, not per run. There is deliberately no run-id or
history array — prior states live in git commits.

Every artifact shares one :class:`ArtifactEnvelope` header
(`schema_version` / `generated_at` / `generated_by`), including `fmea.json`,
which wraps :class:`~quality_core.schema.relational.RelationalFMEA` rather than
being a bare dump of it (SME resolution, #276) — `RelationalFMEA` stays a pure
domain model with no file-format fields.

**Import direction (do not "fix" this).** `quality_core` is the bottom of the
stack: apps import from it, it never imports from `apps/*` (CLAUDE.md; CI audit
A11, #202). So of the five artifacts only `fmea.json` reuses a live type —
`RelationalFMEA`, which quality-core already owns. The models for the Control
Plan, SPC result, Gage R&R and SPC->FMEA feedback artifacts are **independent
mirrors** of `controlplan_app.schema.ControlPlanRow`,
`spc_app.exporter.ControlChartReport`/`CapabilityReport`,
`msa_app.gage_rr_engine.compute_gage_rr`'s return dict and
`spc_app.fmea_feedback.build_occurrence_feedback`'s return dict: same field
names and types, no import. Importing an app here would break the core
dependency contract. The adaptation glue in both directions is the job of the
M3 arrow issues (#277+), not of this module.

JSON has no tuple: where an app type uses a pair (`metrics: Sequence[tuple[str,
str]]`, `secondary_points: tuple[str, Sequence[float]] | None`) the artifact
uses a small named model instead, so the file stays self-describing by hand.
"""
from __future__ import annotations

from typing import Annotated, Literal

import pydantic
from pydantic import JsonValue

from quality_core.schema._base import StrictModel, find_duplicates
from quality_core.schema.relational import RelationalFMEA
from quality_core.spc.constants import SPCChart

#: Current version of every file shape in this module. Bump on a breaking field
#: change; `quality_core.project.io` refuses any other value rather than coercing.
SCHEMA_VERSION = 1

#: A short label (characteristic name, stream, chart label, unit, ...).
Label = Annotated[str, pydantic.Field(min_length=1, max_length=200)]
#: Free prose (reaction plan, CAPA prompt, method note).
Text = Annotated[str, pydantic.Field(min_length=1, max_length=2000)]

#: Where a characteristic's tolerance came from. Not an AIAG concept — M3's point
#: is provenance across files, so a reader of `project.yaml` alone can tell a
#: connector-derived spec from a hand-entered one (see
#: `packages/quality-core/docs/ASSUMPTIONS_LOG.md`).
ToleranceSource = Literal["fmea", "control_plan", "manual"]


def _check_tolerance(lsl: float | None, usl: float | None, target: float | None) -> None:
    """Apply the platform's one tolerance rule: `usl > lsl`, `lsl <= target <= usl`.

    Same rule as `controlplan_app.schema.ControlPlanRow.check_tolerance`; written
    once here so `project.yaml` and the Control Plan artifact cannot drift apart.
    """
    if lsl is not None and usl is not None and usl <= lsl:
        raise ValueError("usl must be greater than lsl")
    if lsl is not None and usl is not None and target is not None and not lsl <= target <= usl:
        raise ValueError("target must be within [lsl, usl]")


# ===========================================================================
# Common envelope
# ===========================================================================


class ArtifactEnvelope(StrictModel):
    """The header every artifact file shares.

    `generated_at` / `generated_by` are plain strings (ISO-8601 UTC, e.g.
    ``"2026-08-13T12:00:00Z"``, and ``"<tool>==<version>"``, e.g.
    ``"spc_app==0.14.0"``) — the file is meant to be read and diffed by hand, so
    the timestamp is stored exactly as written rather than re-formatted on a
    round trip.
    """

    schema_version: int
    generated_at: Label
    generated_by: Label


# ===========================================================================
# project.yaml
# ===========================================================================


class ProjectCharacteristic(StrictModel):
    """One monitored characteristic: its unit, tolerance, and where they came from."""

    name: Label
    unit: Label | None = None
    lsl: float | None = None
    usl: float | None = None
    target: float | None = None
    tolerance_source: ToleranceSource

    @pydantic.model_validator(mode="after")
    def check_tolerance(self) -> "ProjectCharacteristic":
        _check_tolerance(self.lsl, self.usl, self.target)
        return self


class ProjectMeta(StrictModel):
    """`project.yaml` — project identity plus the characteristic registry.

    `project_id` is the stable slug the directory is known by (git is the
    history, so it is not minted per run).
    """

    schema_version: int
    project_id: Label
    name: Label
    created_at: Label
    characteristics: list[ProjectCharacteristic]

    @pydantic.model_validator(mode="after")
    def check_unique_characteristic_names(self) -> "ProjectMeta":
        dupes = find_duplicates(char.name for char in self.characteristics)
        if dupes:
            raise ValueError(f"duplicate characteristic names found: {dupes}")
        return self


# ===========================================================================
# fmea/fmea.json
# ===========================================================================


class FMEAArtifact(ArtifactEnvelope):
    """`fmea/fmea.json` — the relational FMEA under the shared envelope."""

    fmea: RelationalFMEA


# ===========================================================================
# control-plan/plan.json
# ===========================================================================


class ControlPlanArtifactRow(StrictModel):
    """Mirrors `controlplan_app.schema.ControlPlanRow` field-for-field (no import)."""

    characteristic: Label
    lsl: float | None = None
    usl: float | None = None
    target: float | None = None
    measurement_method: Label
    sample_size: Annotated[int, pydantic.Field(ge=1)]
    frequency: Label
    recommended_chart: SPCChart | None = None
    reaction_plan: Text
    source_cause_id: Annotated[str | None, pydantic.Field(max_length=300)] = None
    sample_plan_is_placeholder: bool = False

    @pydantic.model_validator(mode="after")
    def check_tolerance(self) -> "ControlPlanArtifactRow":
        _check_tolerance(self.lsl, self.usl, self.target)
        return self


class ControlPlanArtifact(ArtifactEnvelope):
    """`control-plan/plan.json` — one row per characteristic."""

    rows: list[ControlPlanArtifactRow]

    @pydantic.model_validator(mode="after")
    def check_unique_characteristics(self) -> "ControlPlanArtifact":
        dupes = find_duplicates(row.characteristic for row in self.rows)
        if dupes:
            raise ValueError(f"duplicate characteristic rows found: {dupes}")
        return self


# ===========================================================================
# spc/config.json
# ===========================================================================


class SPCConfigRow(StrictModel):
    """Mirrors `spc_app.control_plan_config.SPCViewConfig` field-for-field (no import).

    `chart_key` is the Control Plan's `recommended_chart` carried through; `None`
    means no chart was preselected, which the SPC layer treats as "the user picks"
    — never a fabricated chart type.
    """

    characteristic: Label
    chart_key: SPCChart | None = None
    lsl: float | None = None
    usl: float | None = None
    target: float | None = None
    sample_size: Annotated[int, pydantic.Field(ge=1)] | None = None
    frequency: Label | None = None

    @pydantic.model_validator(mode="after")
    def check_tolerance(self) -> "SPCConfigRow":
        _check_tolerance(self.lsl, self.usl, self.target)
        return self


class SPCConfigArtifact(ArtifactEnvelope):
    """`spc/config.json` — which characteristics SPC watches and with which chart.

    A *pre*-run selection derived from `control-plan/plan.json`, not a result:
    `spc/results/<characteristic>.json` holds what a chart run produced.
    """

    rows: list[SPCConfigRow]

    @pydantic.model_validator(mode="after")
    def check_unique_characteristics(self) -> "SPCConfigArtifact":
        dupes = find_duplicates(row.characteristic for row in self.rows)
        if dupes:
            raise ValueError(f"duplicate characteristic rows found: {dupes}")
        return self


# ===========================================================================
# spc/results/<characteristic>.json
# ===========================================================================


class ControlChartViolation(StrictModel):
    """One rule hit: the point index and the rule that fired."""

    index: Annotated[int, pydantic.Field(ge=0)]
    rule: Label


class ChartMetric(StrictModel):
    """One `summarize_metrics()` entry — the JSON form of a `(label, value)` pair."""

    label: Label
    value: Label


class SecondarySeries(StrictModel):
    """An optional second per-point series (e.g. CUSUM's lower arm), `(label, values)`."""

    label: Label
    values: list[float]


class ControlChartPayload(StrictModel):
    """Mirrors `spc_app.exporter.ControlChartReport` (no import).

    `ucl`/`lcl` are a scalar for the fixed-limit charts and a per-point list for
    the p- and u-charts, exactly as the report dataclass declares them.
    """

    chart_label: Label
    stream: Label
    rule_set: Label
    points: list[float]
    cl: float
    ucl: float | list[float]
    lcl: float | list[float]
    violations: list[ControlChartViolation]
    metrics: list[ChartMetric]
    secondary_points: SecondarySeries | None = None


class NormalityPayload(StrictModel):
    """The Shapiro-Wilk result a capability report carries."""

    w_stat: float
    p_value: float
    is_normal: bool


class CapabilityPayload(StrictModel):
    """Mirrors `spc_app.exporter.CapabilityReport` (no import).

    `capability` is the `compute_capability` / `compute_capability_study`
    dict stored verbatim (the app types it `Mapping[str, Any]` too) — its keys are
    `quality_core.spc.capability.CapabilityStudy`, whose CI tuples land as
    two-element JSON arrays.
    """

    stream_label: Label
    values: list[float]
    capability: dict[str, JsonValue]
    lsl: float | None = None
    usl: float | None = None
    normality: NormalityPayload
    oos_signal_count: Annotated[int, pydantic.Field(ge=0)]


class SPCResultArtifact(ArtifactEnvelope):
    """`spc/results/<characteristic>.json` — one file per monitored characteristic.

    A re-run overwrites this file (git is the history), so it holds the current
    control-chart *or* capability result for that characteristic, tagged by `kind`.
    """

    kind: Literal["control_chart", "capability"]
    characteristic: Label
    control_chart: ControlChartPayload | None = None
    capability: CapabilityPayload | None = None

    @pydantic.model_validator(mode="after")
    def check_payload_matches_kind(self) -> "SPCResultArtifact":
        present: StrictModel | None
        absent: StrictModel | None
        if self.kind == "control_chart":
            present, absent = self.control_chart, self.capability
        else:
            present, absent = self.capability, self.control_chart
        if present is None:
            raise ValueError(f"kind '{self.kind}' requires a matching '{self.kind}' payload")
        if absent is not None:
            raise ValueError(f"kind '{self.kind}' must not carry the other payload")
        return self


# ===========================================================================
# msa/gage-rr.json
# ===========================================================================


class MSAGageRRArtifact(ArtifactEnvelope):
    """`msa/gage-rr.json` — mirrors `msa_app.gage_rr_engine.compute_gage_rr`'s
    return dict field-for-field (no import).

    The `*_tolerance` percentages are `None` when the study was run without a
    tolerance; the `interaction*` fields are `None` for the Average-and-Range
    method, which has no interaction term.
    """

    ev: float
    av: float
    grr: float
    pev_study: float
    pav_study: float
    pgrr_study: float
    ppv_study: float
    pev_tolerance: float | None = None
    pav_tolerance: float | None = None
    pgrr_tolerance: float | None = None
    ppv_tolerance: float | None = None
    ndc: Annotated[int, pydantic.Field(ge=0)]
    verdict: Label
    tv: float
    pv: float
    mean: float
    n_parts: Annotated[int, pydantic.Field(ge=1)]
    n_appraisers: Annotated[int, pydantic.Field(ge=1)]
    n_trials: Annotated[int, pydantic.Field(ge=1)]
    is_balanced: bool
    method: Label
    method_note: Text
    interaction: float | None = None
    interaction_f: float | None = None
    interaction_significant: bool | None = None


# ===========================================================================
# feedback/spc-to-fmea.json
# ===========================================================================


class SPCToFMEAFeedbackRow(StrictModel):
    """One out-of-control characteristic's feedback — mirrors
    `spc_app.fmea_feedback.build_occurrence_feedback`'s return dict (no import).

    The `source_*` / `component` / `current_occurrence` fields are `None` when the
    out-of-control signal has no Control-Plan row tying it back to an FMEA cause.
    The suggested occurrence is a *candidate* for review, never an applied change.
    """

    characteristic: Label
    stream: Label
    rule_set: Label
    ooc: bool
    violating_points: Annotated[int, pydantic.Field(ge=0)]
    rules: list[Label]
    ooc_rate: float
    source_failure_mode_id: Label | None = None
    source_cause_id: Label | None = None
    source_cause_description: Text | None = None
    current_occurrence: Annotated[int, pydantic.Field(ge=1, le=10)] | None = None
    suggested_occurrence: Annotated[int, pydantic.Field(ge=1, le=10)]
    component: Label | None = None
    capa_prompt: Text


class SPCToFMEAFeedbackArtifact(ArtifactEnvelope):
    """`feedback/spc-to-fmea.json` — one row per out-of-control characteristic.

    A single run can find several characteristics out of control at once, and there
    is one feedback file per project (not one per characteristic), so the rows live
    in a list exactly like `ControlPlanArtifact` / `SPCConfigArtifact`. An empty
    `rows` list is a valid (if uninformative) file; the SPC->FMEA arrow deletes the
    file outright when nothing is out of control, since files hold current state only.
    """

    rows: list[SPCToFMEAFeedbackRow]

    @pydantic.model_validator(mode="after")
    def check_unique_characteristics(self) -> "SPCToFMEAFeedbackArtifact":
        dupes = find_duplicates(row.characteristic for row in self.rows)
        if dupes:
            raise ValueError(f"duplicate characteristic rows found: {dupes}")
        return self
