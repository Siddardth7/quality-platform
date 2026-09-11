# Worked example — the SECOM quality loop

A complete project directory that one call to `run_project_loop` takes all the way around the
loop: FMEA → Control Plan → SPC monitoring config → measurement-system gate → SPC-to-FMEA
occurrence feedback → a candidate action back on the FMEA.

Source:
[`examples/secom-quality-loop/`](https://github.com/Siddardth7/quality-platform/tree/main/examples/secom-quality-loop).

!!! danger "Read this first: what is real and what is not"
    This example is a **hybrid, and it is labelled that way deliberately.**

| File | Provenance |
|---|---|
| `spc/results/etch-chamber-chamber-parameter-drift.json` | **REAL.** Sensor 220 of the UCI SECOM dataset, run once through the existing `secom_app.charts` I-MR engine by `scripts/seed_spc_results.py`. Every point, limit and rule violation in it came out of that data. |
| `fmea/fmea.json` | **ILLUSTRATIVE — not derived from SECOM.** Hand-authored. |
| `msa/gage-rr.json` | **ILLUSTRATIVE — not derived from SECOM.** Hand-authored. |
| `project.yaml` | **ILLUSTRATIVE — not derived from SECOM.** Hand-authored. |
| `control-plan/plan.json`, `spc/config.json`, `spc/msa-gate.json`, `feedback/spc-to-fmea.json` | Produced by the loop when you run it. Not committed — they are gitignored so the demo is provably the orchestrator's own work rather than a hand-edited stand-in. |

Why the split, rather than a fully "SECOM" example:

- **SECOM ships no FMEA and no Control Plan.** It is 590 anonymous sensor columns and a
  pass/fail label. Deriving a failure mode, a severity or a cause from it would be an
  invention presented as an analysis.
- **SECOM cannot support a Gage R&R at all.** Not "we did not run one" — it *structurally
  cannot*: there is no part / appraiser / trial axis, and different sensors measure different
  physical characteristics, not repeat appraisals of one measurand.
- **SECOM ships no tolerances**, so `project.yaml` declares none and **no Cp/Cpk appears
  anywhere in this example, on purpose.**

Nothing in this directory should be read as "SECOM's FMEA" or "SECOM's Gage R&R", because no
such thing exists.

## Why signal 220

The demo needs a characteristic that is genuinely, visibly out of statistical control —
otherwise the last leg of the loop has nothing to feed back and the example silently proves
nothing. Signal 220 was chosen **empirically**, by running the shipped engines over the whole
dataset, not by picking a story and finding data for it:

- `secom_app.selection.select_signals()` keeps it (463 of 590 signals survive the
  missingness, near-zero-variance and outlier screens).
- Its I-MR chart trips **three violations under three distinct Western Electric rules** over
  226 charted points — Rule 1 (index 115), Rule 2 (index 96), Rule 3 (index 58).
- Its lag-1 autocorrelation is 0.025, below the sample-size-adjusted bound, so the I-MR
  independence assumption is not visibly violated.
- Three violating points in 226 is a ~1.3% out-of-control rate, landing mid-band in the
  occurrence table rather than at a clamp — the candidate rating is a real mapping result,
  not a saturated edge case.

`apps/mcp/tests/test_project_loop.py::test_committed_example_spc_result_is_really_out_of_control`
asserts that violation is still there, so a wrong or stale signal choice fails CI instead of
shipping quietly broken.

## Reproducing it

```bash
uv run python -c "from mcp_app.server import run_project_loop; \
    run_project_loop('examples/secom-quality-loop')"
```

Or, from an agent host with the MCP server configured, use the `project-loop` skill and let
it call `run_project_loop` with this directory.

## What changes in `fmea/fmea.json` — the acceptance criterion

Before the loop, the etch failure mode's one link carries no action:

```json
{ "row_id": 1, "effect_id": "ETCH-M1-E1", "cause_id": "ETCH-M1-C1",
  "control_id": "ETCH-M1-CT1", "action": null }
```

After one loop it carries a provenance-tracked candidate:

```json
{ "row_id": 1, "effect_id": "ETCH-M1-E1", "cause_id": "ETCH-M1-C1",
  "control_id": "ETCH-M1-CT1",
  "action": { "owner": "SPC feedback arrow (feedback/spc-to-fmea.json)",
              "status": "Open", "due": null,
              "s_after": null, "o_after": 7, "d_after": null } }
```

Read it as: *the FMEA rated this cause's occurrence 3; the SPC chart says it is happening at
a rate the AIAG-4 / SAE J1739 occurrence table calls a 7; here is an open action pointing at
the evidence.*

Three properties of that diff matter more than the numbers:

1. **`Cause.occurrence` is still 3.** The loop never overwrites a rating. It attaches a
   proposal and waits for a human. The `owner` field is the pointer to the evidence file.
2. **Only the characteristic with SPC data is touched.** The second characteristic appears in
   the plan, the SPC config and the gate, but has no committed chart result, so it gets no
   feedback row and no action — the loop reports on what it has, and nothing more.
3. **Running the loop again changes nothing.** The candidate is recomputed from the same
   chart and plan, matches what is on disk, and `fmea/fmea.json` is not rewritten — not even
   its timestamp.

## Files in the example

```
project.yaml                       project identity + characteristic registry  (illustrative)
fmea/fmea.json                     relational FMEA, 2 functions                (illustrative)
msa/gage-rr.json                   Gage R&R study                              (illustrative)
spc/results/etch-...-drift.json    I-MR control chart                          (REAL SECOM)
scripts/seed_spc_results.py        one-time seeder for the file above
```

!!! note "Recordings coming soon"
    No screen recording or terminal capture of this run is published yet. When one exists it
    will be linked here — this callout is a deliberate placeholder, not a missing asset.
