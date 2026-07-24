# SECOM Case Study

A short, honest read of what the W09 SECOM series analyzed and what it does — and
does not — show. This condenses `README.md` and the two deep docs below; it does
not restate them.

## What SECOM is

SECOM (UCI ML Repository, dataset 179) is real semiconductor fab process-monitoring
data: **1567 wafers x 590 sensor signals**, one reading per wafer per sensor, plus a
pass/fail label and a timestamp per wafer. It is vendored unchanged under `data/`;
see [`../data/LICENSE_SECOM.txt`](../data/LICENSE_SECOM.txt) for UCI
provenance and the CC BY 4.0 citation.

## What was analyzed

Five views, each reusing an existing engine rather than re-deriving math:

- **Ingest + selection (W09-1).** `load_secom()` in
  [`../secom_app/ingest.py`](../secom_app/ingest.py) reads the two raw files into an
  aligned, NaN-preserving dataset — missing cells are never imputed.
  `select_signals()` in [`../secom_app/selection.py`](../secom_app/selection.py)
  screens the 590 sensor columns for SPC/capability suitability (present-count
  floor, zero/near-zero variance). Every inclusion/exclusion is recorded in an
  audit table; see `ASSUMPTIONS_LOG.md` RULE 1–2 for the standard-vs-heuristic
  labelling of each rule.
- **SPC control charts (W09-2).** `control_chart_for_signal()` /
  `control_charts_for_selection()` in
  [`../secom_app/charts.py`](../secom_app/charts.py) run every kept signal through
  the existing SPC I-MR engine, breaking the moving range across missing-data gaps
  and flagging WE/Nelson violations. No spec limits, no Cp/Cpk here.
- **Capability (W09-3).** `capability_for_signal()` in
  [`../secom_app/capability.py`](../secom_app/capability.py) computes Cp/Cpk/Pp/Ppk
  against **caller-supplied** limits — SECOM ships no tolerances — and is
  stability-gated, flagging (not suppressing) results on an unstable process.
- **MSA applicability (W09-4).** [`../secom_app/msa.py`](../secom_app/msa.py)
  refuses to fabricate a Gage R&R study: SECOM has no part x appraiser x trial
  structure. See `MSA_APPLICABILITY.md` for the full argument.
- **Yield / DPPM + Pareto (W09-5).** `yield_summary()` and
  `failing_signal_pareto()` in
  [`../secom_app/yield_dppm.py`](../secom_app/yield_dppm.py) compute wafer-level
  yield and DPPM, and rank kept signals by how often their control-chart
  violations coincide with failed wafers — an association, not root-cause, Pareto.

## What the numbers are

Verified, test-locked figures only — every other statistic in the series (e.g.
missingness rate, exact count of signals kept by selection) is intentionally left
out of this table; see Limitations.

| Metric | Value | Source |
|---|---|---|
| Dataset shape | 1567 wafers x 590 signals | `apps/secom/tests/test_ingest.py:38` |
| Pass / fail split | 1463 pass / 104 fail | `test_ingest.py:43`; `test_yield_dppm.py:51-52` |
| Yield | 93.363 % | `test_yield_dppm.py:55` |
| DPPM (defective **units** per million — not DPMO) | 66,368.86 | `test_yield_dppm.py:56` |

DPPM is not DPMO: SECOM carries one pass/fail verdict per wafer, not a
defects-and-opportunities count, so only a units-based metric is defensible (see
[`../secom_app/yield_dppm.py`](../secom_app/yield_dppm.py)).

## Limitations

- **Missingness is real and unresolved by design.** The 590 sensors carry heavy,
  honest missingness across the dataset. NaNs are preserved end to end — never
  imputed. Every SPC/capability view runs on *present values only*, and signals
  falling below the present-count floor are screened out by
  [`../secom_app/selection.py`](../secom_app/selection.py) before any chart or
  index is computed. No result here silently fills a gap.
- **SECOM is observational, not a designed experiment.** Concretely:
  - **MSA / Gage R&R cannot be run.** No part x appraiser x trial structure
    exists in this data, and none can be honestly constructed from it — see
    [`MSA_APPLICABILITY.md`](MSA_APPLICABILITY.md).
  - **Capability limits are caller-supplied, not intrinsic.** SECOM ships no
    tolerances, so Cp/Cpk/Pp/Ppk here describe the data against *whatever limits a
    user provides* — they are not a property of the process itself.
  - **The failing-signal Pareto is association, not causation.** It ranks which
    kept signals were most often flagged out-of-control on failed wafers. It does
    not prove any signal caused any failure — SECOM's label is a single
    wafer-level verdict that attributes failure to nothing.
- **What no view here claims:** control charts flag statistical signals, not
  defects; yield/DPPM are definitional arithmetic with no acceptance threshold
  implied; nothing in this series is a validated root-cause analysis or a
  certified capability claim about the fab.

## Where to go deeper

- [`../README.md`](../README.md) — per-feature summary of W09-1..W09-5.
- [`ASSUMPTIONS_LOG.md`](ASSUMPTIONS_LOG.md) — every screening rule, labelled
  standard vs. heuristic.
- [`MSA_APPLICABILITY.md`](MSA_APPLICABILITY.md) — the full "MSA does not apply"
  argument.
- [`../data/LICENSE_SECOM.txt`](../data/LICENSE_SECOM.txt) — UCI
  provenance and license.
