---
name: control-plan
description: Derive a Control Plan from a relational FMEA by calling the quality-platform Control Plan MCP tools — one control-plan row per failure mode (characteristic, measurement method, reaction plan, source-cause traceability) plus an AIAG SPC chart recommendation per characteristic. Use for control-plan, reaction-plan, sample-plan or FMEA-to-control-plan requests, not FMEA risk scoring or SPC chart computation itself.
---

# control-plan — derive a Control Plan from an FMEA

Turn a relational FMEA into a Control Plan by calling the quality-platform MCP tools. The
engine owns every field; this skill decides which tool to call and how to present the
traceability and the provenance flags that come back with it. See `skills/CONVENTIONS.md`
for the rules this skill is written to.

## When to use

The user has an FMEA and wants the control plan that follows from it, or has a control plan
and wants a chart type or a trace back to the failure mode that justified a row. Pick the
tool by what they already have:

| What the user has | Tool |
|---|---|
| A relational FMEA, wants a control plan derived from it | `controlplan_build` |
| A characteristic's data type + subgroup size, wants the right chart | `controlplan_recommend_chart` |
| A control plan already built, wants to trace a row back to its FMEA cause | `controlplan_source_index` |
| A project directory on disk (`fmea/fmea.json`), wants `control-plan/plan.json` written | `controlplan_build_from_project` |

This is **not** the skill for scoring or ranking failure modes — that is the `fmea` skill's
`fmea_score` / `fmea_run` / `fmea_run_relational`. It is also not the skill for *running* the
recommended chart or computing capability — that is the `spc` skill. `controlplan_recommend_chart`
names a chart type; it does not compute one.

## Shared input contract

`fmea_model` for `controlplan_build` and `controlplan_source_index` is the exact same
`RelationalFMEA` JSON object the `fmea` skill's `fmea_run_relational` tool takes — the
connector consumes it directly, with no separate Control Plan input schema. For the field set,
see [`skills/fmea/references/mcp-tool-contract.md`](../fmea/references/mcp-tool-contract.md).
This skill does not redefine it, and neither should any answer built from it.

## Steps

1. Connect to the quality-platform MCP server over stdio. The host normally has it configured
   already; if not, it launches as `python -m mcp_app.server` from the workspace root.
2. If starting from an FMEA, confirm it is already a valid `RelationalFMEA` object. If it is
   not — a flat table, a spreadsheet, loose prose — send the user to the `fmea` skill's intake
   guidance first; do not re-validate or reshape the model here.
3. Call `controlplan_build(fmea_model)`. Report every row **verbatim** — all eleven keys,
   including `sample_plan_is_placeholder` and `source_cause_id`. The rows come back
   highest-risk first; the tool does that ordering (by Action Priority, then Risk Priority
   Number), and where a failure mode has several links the tool also picks which link to score.
   Neither choice is the user's or the skill's to make.
4. **Flag every row's placeholder fields explicitly.** When `sample_plan_is_placeholder` is
   `true` — which is every row `controlplan_build` emits — `sample_size`, `frequency` and
   `reaction_plan` are connector defaults with no FMEA source (F-10, #196). Say so plainly:
   these three need engineering judgment before the plan is used, and they are not
   AIAG-derived. Never author a replacement value yourself; that is the user's and the
   reviewer's call.
5. `recommended_chart` comes back `null` on every `controlplan_build` row **by design** — the
   relational FMEA carries no data type or subgroup size, so the engine does not guess one.
   That is not a gap for the skill to fill. If the user wants a chart recommendation for a
   characteristic, ask for its data type and subgroup size, then call
   `controlplan_recommend_chart` **separately** and report `recommended_chart` verbatim as its
   own cited output. Tolerance does not enter into it: the tool takes no LSL/USL, and under the
   AIAG rule table tolerance never affects chart *type* — it matters for capability, which is
   the `spc` skill's territory.
6. For traceability, call `controlplan_source_index(fmea_model)` with the **same** `fmea_model`
   used for `controlplan_build` — a different model produces different keys. Match a row to its
   index entry by exact `characteristic` string, or by the row's `source_cause_id` against the
   entry's `cause_id`. Report the five index fields verbatim: `failure_mode_id`, `cause_id`,
   `cause_description`, `occurrence`, `component`.
7. On a tool error — a malformed `RelationalFMEA` (duplicate IDs, a link pointing at an ID that
   does not exist), a `subgroup_size` below 1 or above 12 for variable data, an unknown
   `data_type` — surface the message verbatim and ask for corrected input. An **empty**
   `functions` list is not an error: `controlplan_build` returns `[]`, which means "no failure
   modes to control", and should be reported as such rather than as a failure.

Two shapes that read as bugs and are not:

- A characteristic name with an appended failure-mode ID or a `#2` suffix. Two failure modes
  that would produce the same `component — description` name get a deterministic
  disambiguating suffix. The naming rule lives in
  `apps/controlplan/controlplan_app/connector.py`; do not re-derive or "clean up" the name.
- `lsl`, `usl` and `target` coming back `null`. The FMEA carries no tolerances. Ask the user
  for them if the plan needs them; never infer them from the failure-mode text.

## No compute here

The skill never selects a chart itself — `controlplan_recommend_chart` owns that rule table.
It never authors a reaction plan, a sample size or a frequency. It never re-derives the Risk
Priority Number or the Action Priority the engine used to order the rows; those are named in
prose and reported, never recomputed. A second opinion calculated in this layer is a defect,
not a safeguard.

## Worked example

User: *"Here's my weld FMEA — what should the control plan look like?"*

The model, one function with one failure mode and one link:

```python
fmea_model = {
    "functions": [{
        "id": "F1", "process_step": "Weld station 10", "component": "Bracket weld",
        "description": "Join bracket to frame",
        "failure_modes": [{
            "id": "M1", "description": "Incomplete weld",
            "effects": [{"id": "E1", "description": "Joint failure in service", "severity": 9}],
            "causes": [{"id": "C1", "description": "Insufficient weld time", "occurrence": 5}],
            "controls": [{"id": "CT1", "description": "Visual weld inspection", "detection": 6}],
            "links": [{"row_id": 1, "effect_id": "E1", "cause_id": "C1", "control_id": "CT1"}],
        }],
    }],
}
```

`controlplan_build(fmea_model)` returns:

```json
[{
  "characteristic": "Bracket weld — Incomplete weld",
  "lsl": null, "usl": null, "target": null,
  "measurement_method": "Visual weld inspection",
  "sample_size": 1,
  "frequency": "per shift",
  "recommended_chart": null,
  "reaction_plan": "Contain and investigate; failure effect: Joint failure in service.",
  "source_cause_id": "F1::M1::C1",
  "sample_plan_is_placeholder": true
}]
```

Report that row as engine output, and say what the flag means: `sample_plan_is_placeholder`
is `true`, so `sample_size: 1`, `frequency: "per shift"` and that `reaction_plan` sentence are
connector defaults awaiting engineering judgment — not values the FMEA supplied.

`controlplan_source_index(fmea_model)` returns:

```json
{
  "Bracket weld — Incomplete weld": {
    "failure_mode_id": "M1", "cause_id": "F1::M1::C1",
    "cause_description": "Insufficient weld time", "occurrence": 5,
    "component": "Bracket weld"
  }
}
```

The index key is character-for-character the row's `characteristic`, and its `cause_id`
(`"F1::M1::C1"`) is exactly the row's `source_cause_id`. That round trip is what
`controlplan_source_index` exists to prove — call it out to the user as the traceability
guarantee, because it is the evidence that the control-plan row and the FMEA cause are the
same finding.

If the user then says *"this is a variable measurement, sample size 5"*, call
`controlplan_recommend_chart(data_type="variable", subgroup_size=5)`:

```json
{"recommended_chart": "Xbar-R"}
```

Present that as a separate, cited output alongside the row. Never merge it into the build row
yourself — `controlplan_build` leaves `recommended_chart` null deliberately, and a row that
carries a chart the engine did not put there is no longer engine output.

`scripts/call_controlplan_build.py` is the same build call as a runnable script, for when a
shell call is cheaper than a tool call.

## Reference

- [`references/mcp-tool-contract.md`](references/mcp-tool-contract.md) — the tool namespace
  convention, the request/response shape of all three Control Plan tools, the key-parity
  guarantee, the error contract and transport.
- [`references/controlplan-method-notes.md`](references/controlplan-method-notes.md) — the
  chart-selection table's provenance and its open primary-source flag, why the sample plan and
  reaction plan are placeholders with no published standard, why subgroup sizes above 12 raise,
  and which mapping decisions are SME-locked — each cited to
  `apps/controlplan/docs/ASSUMPTIONS_LOG.md`.
