# Engineering Assumptions Log
**Project:** `quality-core` — the shared, UI-free core
**Last Updated:** August 13, 2026

This document records design decisions made **in the shared core itself**, as opposed to in one
app. Entries are of two kinds and each says which it is:

- **Standards-grounded** — the decision follows a published standard (AIAG / ISO / SAE). The entry
  names the manual and section and quotes it verbatim.
- **Not in a standard** — an internal design choice. The entry says so in its `**Source:**` line
  and claims no standard behind it.

An entry with no primary source is acceptable. An entry that *implies* one is not: a wrong number
is falsifiable by recomputation, but a fabricated quotation looks like verified evidence and every
decision downstream of it inherits unearned confidence.

Constants that already have a home stay there. `quality_core.spc`'s AIAG SPC constants are cited in
[`apps/spc/docs/ASSUMPTIONS_LOG.md`](../../../apps/spc/docs/ASSUMPTIONS_LOG.md) (they were promoted
out of `spc_app` verbatim by #205), and the chart-selection rule table behind `SPCChart` is RULE 1 of
[`apps/controlplan/docs/ASSUMPTIONS_LOG.md`](../../../apps/controlplan/docs/ASSUMPTIONS_LOG.md).
This log does not re-cite them.

---

## RULE 1 — Files hold current state; git is the history (#276)

**Decision:** A project directory holds the **current** state of each artifact and nothing else.
`project.yaml`'s `project_id` is a stable, human-chosen slug (in practice the directory name), not a
UUID minted per run. Every artifact carries `generated_at` (ISO-8601 UTC) and `generated_by`
(`"<tool>==<version>"`) so a reader can judge freshness without consulting git. A re-run
**overwrites** its own artifact file in place, and `spc/results/<slug>.json` is one file per
monitored characteristic, **not** one per run. There is no run-id and no history array.

**Source:** Not in a standard — an internal design choice, resolved by the SME on 2026-08-13 against
the alternative of an embedded run history. Rationale: the issue's acceptance framing is
"git-versionable, human-inspectable", and an embedded history duplicates what git already provides
while making the JSON noisy to read by hand. The consequence is deliberate: a consumer that wants
"what did this look like last week" reads `git show`, not the file.

## RULE 2 — One envelope for all five artifacts, including `fmea.json` (#276)

**Decision:** Every artifact file — including `fmea/fmea.json` — is
`{schema_version, generated_at, generated_by, <payload>}`. `fmea.json` therefore wraps
`quality_core.schema.relational.RelationalFMEA` under the key `fmea` rather than being a bare dump
of that model.

**Source:** Not in a standard — an internal design choice, resolved by the SME on 2026-08-13.
Rationale: `RelationalFMEA` is a shared **domain** model; `schema_version` / `generated_at` /
`generated_by` are **file-format** concerns. Adding them to the domain model would push file
metadata into every in-memory FMEA in the platform. A single envelope also gives the loader one
uniform code path for all five artifacts instead of a special case for one.

## RULE 3 — Versioning is an explicit `schema_version` integer, checked on load (#276)

**Decision:** Each file declares `schema_version: int` (currently `1`,
`quality_core.project.schema.SCHEMA_VERSION`). The loader rejects any other value with a
`ProjectError` naming expected vs found, rather than coercing or ignoring it. There is no JSON
Schema file, no schema registry, and no additional validation dependency — pydantic models are the
one source of truth, exactly as for every other schema in this repo.

**Source:** Not in a standard — an internal design choice. Rationale: schema drift between an old
artifact and a newer loader must fail loud; a silent coercion would surface later as a wrong number
in a downstream arrow. `model_json_schema()` can emit a JSON-Schema document on demand for
documentation, which is output, not a second source of truth.

## RULE 4 — `tolerance_source` on a project characteristic (#276)

**Decision:** `ProjectCharacteristic.tolerance_source` is one of `"fmea"`, `"control_plan"`,
`"manual"`. It records where that characteristic's unit/LSL/USL/target came from.

**Source:** Not in a standard — a new field with no equivalent in AIAG's Control Plan column
structure or in any existing app schema. Rationale: M3's purpose is provenance across files, so a
reader of `project.yaml` alone must be able to tell a connector-derived spec from a hand-entered
one. The tolerance *rule* it guards (`usl > lsl`, `lsl <= target <= usl`) is not new — it is the
same rule `controlplan_app.schema.ControlPlanRow.check_tolerance` already applies, written once in
`quality_core.project.schema._check_tolerance` so the two cannot drift.

## RULE 5 — Four of the five artifact models mirror app types instead of importing them (#276)

**Decision:** Only `fmea.json` reuses a live type (`RelationalFMEA`, which `quality-core` owns). The
Control Plan, SPC result, Gage R&R and SPC->FMEA feedback models are **independent** pydantic models
whose field names and types mirror `controlplan_app.schema.ControlPlanRow`,
`spc_app.exporter.ControlChartReport`/`CapabilityReport`, `msa_app.gage_rr_engine.compute_gage_rr`'s
return dict and `spc_app.fmea_feedback.build_occurrence_feedback`'s return dict.

**Source:** Not in a standard — forced by the repo's import-direction rule ("imports go downward
only"; CI audit A11, #202). `quality_core` is the bottom of the stack and must never import an app.
The duplication is the price of that contract and is deliberate; a future contributor "fixing" it by
importing an app into the core would break CI's core dependency contract. Keeping the mirrors
faithful is the job of the M3 arrow issues (#277+), which own the adaptation glue in both directions.

Where JSON has no equivalent of a Python tuple, the mirror uses a small named model instead of a
positional array (`ChartMetric` for `metrics: Sequence[tuple[str, str]]`, `SecondarySeries` for
`secondary_points: tuple[str, Sequence[float]] | None`), so the file stays readable by hand. The
capability study block is stored as a free-form JSON object, mirroring the `Mapping[str, Any]` the
SPC report itself declares; its keys are `quality_core.spc.capability.CapabilityStudy`, whose CI
tuples land as two-element JSON arrays.

## RULE 6 — `project.yaml` is YAML; the artifacts are JSON (#276)

**Decision:** `project.yaml` is YAML (via `pyyaml`, a new hard dependency of `quality-core`); the
five artifact files are JSON.

**Source:** Not in a standard — an internal design choice. Rationale: `project.yaml` is the one file
a human is expected to author and edit by hand (comments, no quoting noise); the artifacts are
tool-written and only read by hand, where JSON's exactness and universal tooling win. `pyyaml` is a
pure-python parser, was already in the workspace lock, and is not on the Streamlit chain the core
dependency contract forbids (#202).
