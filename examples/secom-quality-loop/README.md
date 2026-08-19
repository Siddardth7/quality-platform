# SECOM quality loop — the worked example

A complete Quality Platform **project directory** that one call to the `run_project_loop`
MCP tool takes all the way around the loop: FMEA → Control Plan → SPC monitoring config →
measurement-system gate → SPC-to-FMEA occurrence feedback → a candidate action back on the
FMEA.

---

## ⚠️ Read this first: what is real and what is not

This example is a **hybrid, and it is labelled that way deliberately.**

| File | Provenance |
|---|---|
| `spc/results/etch-chamber-chamber-parameter-drift.json` | **REAL.** Sensor 220 of the UCI SECOM dataset (`apps/secom/data/secom.data`), run once through the existing `secom_app.charts` I-MR engine by `scripts/seed_spc_results.py`. Every point, limit and rule violation in it came out of that data. |
| `fmea/fmea.json` | **ILLUSTRATIVE — not derived from SECOM.** Hand-authored. |
| `msa/gage-rr.json` | **ILLUSTRATIVE — not derived from SECOM.** Hand-authored. |
| `project.yaml` | **ILLUSTRATIVE — not derived from SECOM.** Hand-authored. |
| `control-plan/plan.json`, `spc/config.json`, `spc/msa-gate.json`, `feedback/spc-to-fmea.json` | Produced by the loop when you run it. Not committed — see "Reproducing it" below. |

Why the split, rather than a fully "SECOM" example:

- **SECOM ships no FMEA and no Control Plan.** It is 590 anonymous sensor columns and a
  pass/fail label. Deriving a failure mode, a severity or a cause from it would be an
  invention presented as an analysis.
- **SECOM cannot support a Gage R&R at all.** Not "we did not run one" — it *structurally
  cannot*: there is no part / appraiser / trial axis, and different sensors measure
  different physical characteristics, not repeat appraisals of one measurand. That refusal
  is documented and enforced in `apps/secom/docs/MSA_APPLICABILITY.md` and
  `secom_app.msa`. `msa/gage-rr.json` here is a plausible study a fab *would* run,
  standing in for one; it describes no real gauge and no SECOM sensor.
- **SECOM ships no tolerances** (`apps/secom/docs/ASSUMPTIONS_LOG.md`, the #65 red line).
  So `project.yaml` declares none — every limit is `null` and `tolerance_source` is
  `manual`, meaning "a human would have to supply these". No Cp/Cpk appears anywhere in
  this example, on purpose.

The same discipline `secom_app/selection.py` and `secom_app/doe_screening.py` keep in their
module docstrings — say what has no standard behind it, rather than implying one — applies
here. Nothing in this directory should be read as "SECOM's FMEA" or "SECOM's Gage R&R",
because no such thing exists.

Background on the dataset and what the platform legitimately does with it:
[`apps/secom/docs/CASE_STUDY.md`](../../apps/secom/docs/CASE_STUDY.md).

---

## Why signal 220

The demo needs a characteristic that is genuinely, visibly out of statistical control —
otherwise the last leg of the loop has nothing to feed back and the example silently proves
nothing. Signal 220 was chosen **empirically**, by running the shipped engines over the
whole dataset, not by picking a story and finding data for it:

- `secom_app.selection.select_signals()` **keeps** it (it survives the missingness,
  near-zero-variance and outlier screens; 463 of 590 signals do).
- Its I-MR chart trips **three violations under three distinct Western Electric rules** over
  226 charted points — Rule 1 (point beyond 3σ, index 115), Rule 2 (index 96) and Rule 3
  (index 58). Not one borderline hit: three different special-cause patterns.
- Its lag-1 autocorrelation is 0.025, **below** the sample-size-adjusted bound, so the I-MR
  independence assumption is not visibly violated — the signals are not an artifact of
  serial correlation. (That diagnostic is `secom_app.charts`' OQ2; it is advisory and gates
  nothing.)
- Three violating points in 226 is an out-of-control rate of ~1.3%, which lands cleanly in
  the middle of the occurrence band table rather than at a clamp — so the candidate rating
  the loop produces is a real mapping result, not a saturated edge case.

`apps/mcp/tests/test_project_loop.py::test_committed_example_spc_result_is_really_out_of_control`
asserts that violation is still there, so a wrong or stale signal choice fails CI instead of
shipping quietly broken.

---

## The loop, file by file

```
fmea/fmea.json                          hand-authored input
   └─► control-plan/plan.json           (1) controlplan_build_from_project
          └─► spc/config.json           (2) spc_config_from_project
                 └─► spc/msa-gate.json  (3) spc_msa_gate_from_project  ◄── msa/gage-rr.json
spc/results/*.json                      seeded precondition — NOT produced by the loop
   └─► feedback/spc-to-fmea.json        (4) spc_fmea_feedback_from_project
          └─► candidate Action on fmea/fmea.json
```

Two things worth understanding before reading the output:

**`spc/results/*.json` is an input.** No arrow writes it. Running a control chart against
live process data and persisting the result is not any M3 arrow's contract, so the loop
treats whatever is on disk as a precondition — the trace of a prior charting session. That
is what `scripts/seed_spc_results.py` produced, once, and why its output is committed here.

**Step 3 is not a gate the loop enforces.** `spc/msa-gate.json` records how far each
characteristic's SPC numbers may be trusted; nothing stops a `warn`- or `block`-gated
characteristic from producing feedback. Read the two files together. This example gates
`pass` on the monitored characteristic (an illustrative `Accept` study) and `warn` on the
other (no study on file — silence is never an accept).

---

## Reproducing it

From the workspace root, with the MCP server's tools available in-process:

```bash
uv run python -c "from mcp_app.server import run_project_loop; \
    run_project_loop('examples/secom-quality-loop')"
```

or, from an agent host with the quality-platform MCP server configured, use the
[`project-loop` skill](../../skills/project-loop/SKILL.md) and let it call
`run_project_loop` with this directory.

Either way the four derived files appear (they are `.gitignore`d here precisely so the demo
is provably the orchestrator's own work rather than a hand-edited stand-in), and
`fmea/fmea.json` gains one action. To reset, `git checkout` this directory's `fmea/fmea.json`
and delete the generated files.

Re-seeding the SPC leg from the raw dataset (not normally needed — its output is committed):

```bash
uv run python examples/secom-quality-loop/scripts/seed_spc_results.py
```

---

## What changes in `fmea/fmea.json` — the acceptance criterion, concretely

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
2. **Only the characteristic with SPC data is touched.** `Wet bench — Residue left after
   clean` appears in the plan, the SPC config and the gate, but has no committed chart
   result, so it gets no feedback row and no action — the loop reports on what it has, and
   nothing more.
3. **Running the loop again changes nothing.** The candidate is recomputed from the same
   chart and the same plan, matches what is already on disk, and `fmea/fmea.json` is not
   rewritten — not even its timestamp. (`spc-to-fmea.json`'s `generated_at` does move; its
   rows do not.) Asserted in
   `apps/mcp/tests/test_project_loop.py::test_run_project_loop_twice_leaves_the_fmea_byte_identical`.

The full evidence for the proposal — chart, rule set, violating points, out-of-control rate,
current and candidate occurrence, and a CAPA prompt — lands in `feedback/spc-to-fmea.json`.

---

## Files

```
project.yaml                       project identity + characteristic registry  (illustrative)
fmea/fmea.json                     relational FMEA, 2 functions                (illustrative)
msa/gage-rr.json                   Gage R&R study                              (illustrative)
spc/results/etch-...-drift.json    I-MR control chart                          (REAL SECOM)
scripts/seed_spc_results.py        one-time seeder for the file above
```
