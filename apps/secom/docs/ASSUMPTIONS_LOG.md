# Engineering Assumptions Log
**Project:** SECOM Dataset Ingest + Signal Selection (W09-1) + SPC Control Charts (W09-2)
+ Capability (W09-3) + MSA Applicability (W09-4)
**Last Updated:** July 23, 2026

This document records every screening decision in the SECOM ingest/selection engine
and its source, with an explicit **standard vs heuristic** label — SECOM signal
selection is a data-screening step from statistical practice, not a published
quality standard (unlike AIAG SPC/MSA math elsewhere in this platform).

---

## RULE 1 — Preserve missingness at ingest (definitional)

**Decision:** `load_secom()` never imputes and never drops rows/columns for missing
cells. NaN survives into `SecomDataset.features` unchanged. The only hard failures
are structural: a row-count mismatch between `secom.data`/`secom_labels.data`, or a
label outside `{-1, +1}`.

**Source:** SECOM's defining trait is heavy, honest missingness across ~590 sensor
columns (UCI dataset 179). The platform's shared `quality_core.io.load_table` path
validates one Pydantic row per row with `allow_inf_nan=False`, which would *reject*
a row with a missing required float — the wrong tool for this dataset. `IngestError`
(from `quality_core.io`) is reused for the friendly structural-failure path only.

**Rationale:** Imputation, if ever wanted, is an explicit downstream decision made by
a later issue, not baked into ingest. Surfacing missingness (`secom_missingness()`)
and screening it (`select_signals()`) keeps every exclusion visible and auditable.

**Applied In:** `apps/secom/secom_app/ingest.py` -> `load_secom()`, `secom_missingness()`

---

## RULE 2 — Missingness cutoff: `MIN_NON_MISSING = 100` (heuristic, SME-set)

**Decision:** A signal is kept only if it has at least 100 present (non-NaN) values;
retained signals are analyzed on present values only (no imputation).

**Source:** AIAG SPC Reference Manual, capability sample-size guidance (~100
individual points / ~25 subgroups) motivates the floor. General data-screening
practice for the "keep only signals with enough data" idea. **Flagged: the numeric
threshold (100) is SME-set for this platform, not itself an AIAG-published table —
AIAG motivates the order of magnitude, not this exact cutoff.**

**Rationale:** A signal with too few present values cannot support a meaningful
control chart or capability estimate regardless of its variance. SME resolution
(2026-07-21) selected `>= 100 non-missing` over the more common ">50% missing"
screening default, to anchor the floor to AIAG's SPC sample-size guidance rather
than an arbitrary fraction.

**Applied In:** `apps/secom/secom_app/selection.py` -> `MIN_NON_MISSING`,
`SelectionCriteria.min_non_missing`, `select_signals()` (rule 1, reason `"too_missing"`)

---

## RULE 3 — Zero-variance drop (definitional, not tunable)

**Decision:** A signal with zero variance on its present values (including an
all-NaN column, which has zero present values) is dropped unconditionally.

**Source:** AIAG SPC Reference Manual, 4th ed. (2005), capability indices:
Cp = (USL-LSL)/6*sigma is undefined at sigma=0; `compute_capability` in this
platform (`apps/spc/spc_app/spc_engine/capability.py`) raises on `sigma_hat<=0`.

**Rationale:** A control chart and Cp/Cpk both require variation to be meaningful.
This is definitional, not a tunable threshold — there is no SME choice to make.

**Applied In:** `apps/secom/secom_app/selection.py` -> `select_signals()`
(rule 2, reason `"constant"`)

---

## RULE 4 — Near-zero-variance drop (third-party heuristic, NOT a quality standard)

**Decision:** Drop a signal if `freq_ratio >= 19` AND `percent_unique <= 10%`, where
`freq_ratio` = (count of most-common present value) / (count of 2nd-most-common
present value), and `percent_unique` = n_distinct / n_present.

**Source:** Kuhn & Johnson, *Applied Predictive Modeling* (2013), Section 3.5;
`caret::nearZeroVar` default thresholds (`freqCut = 19`, `uniqueCut = 10`).
**Flagged: this is a third-party statistical-software reproduction, not a quality
standard (no AIAG/ISO table defines "near-zero variance").** SME accepted the caret
defaults as-is (2026-07-21) rather than setting bespoke cutoffs.

**Rationale:** A signal that is almost always one value (highly skewed frequency,
few distinct present values) offers little discriminating information for a control
chart even though its variance is technically nonzero — mirrors a standard predictive-
modeling screening step, applied here to the SPC-suitability question instead.

**Applied In:** `apps/secom/secom_app/selection.py` -> `NZV_FREQ_RATIO`,
`NZV_PERCENT_UNIQUE`, `_freq_ratio()`, `_percent_unique()`, `select_signals()`
(rule 3, reason `"near_zero_variance"`)

---

## RULE 5 — Filter order and reason precedence

**Decision:** The three rules run in a fixed order per signal; the first failing
rule is reported as `reason` (a signal cannot be both `"too_missing"` and
`"constant"` in the audit table, even if it satisfies both conditions):
1. `n_present < MIN_NON_MISSING` -> drop `"too_missing"`
2. variance == 0 on present values -> drop `"constant"`
3. NZV (`freq_ratio >= 19` AND `percent_unique <= 10%`) -> drop `"near_zero_variance"`
4. else -> keep `"ok"`

**Source:** Platform convention (not a standard) — matches the "return an audit
table with an explainable single reason per row" discipline used elsewhere in this
codebase (e.g. FMEA/Control Plan validation messages).

**Rationale:** An all-NaN column would technically be both "too missing" (0 present
values) and "constant" (undefined/zero variance); reporting `"too_missing"` first is
the more informative diagnosis (the real problem is absent data, not a lack of
spread in the data that does exist).

**Applied In:** `apps/secom/secom_app/selection.py` -> `select_signals()`

---

## NOTE — Normality / stability are downstream, not selection gates here

Cp/Cpk validity needs a stable, ~normal process; SPC already runs a stability gate +
`normality_test` at chart time. W09-1 selects *candidate* signals only — it does not
pre-filter on normality, to avoid discarding a signal that a later transform (e.g.
Box-Cox) could rescue.

## NOTE — No spec limits ship with SECOM (deferred seam, OQ #4)

SECOM ships raw sensor readings + pass/fail + timestamp only — no USL/LSL/tolerances.
"Suitable for capability" in this module means "has usable variation and enough
present data," **not** "has limits." `select_signals()` does not fabricate limits and
does not compute Cp/Cpk. The limits-source decision (engineering spec vs
percentile-derived vs SME-supplied) belongs to a later capability issue.

---

## RULE 6 — W09-2 (#66): I-MR is the reused, standard chart type (standard)

**Decision:** Every SECOM sensor is charted with Individuals + Moving Range
(I-MR, MR window = 2) via the existing, already-tested SPC engine
(`compute_imr`, `detect_we_violations`/`detect_nelson_violations` in
`apps/spc/spc_app/spc_engine/`), reused read-only through a `sys.path` shim
in `apps/secom/conftest.py`. No control-limit math or rule-detection logic is
re-derived in `secom_app/charts.py`.

**Source:** AIAG SPC Reference Manual, 4th ed. (2005); Montgomery,
*Introduction to Statistical Quality Control*, individuals-chart chapter.
SECOM is one reading per production run per sensor — individual measurements,
no rational subgroup — so I-MR is the standard choice, not a heuristic one.

**Applied In:** `apps/secom/secom_app/charts.py` -> `control_chart_for_signal()`

---

## RULE 7 — W09-2 (#66): lag-1 autocorrelation flag (SME-set, rigorous option)

**Decision:** Each charted signal gets a diagnostic-only lag-1 (Pearson)
autocorrelation statistic (`lag1_autocorr`) and a boolean flag
(`autocorr_flag`) attached to its `SignalControlChart`. The flag threshold is
`1.96 / sqrt(n)` — Bartlett's large-sample approximate 95% white-noise
confidence bound for a lag-1 autocorrelation estimate — evaluated per signal
against that signal's own `n_used` (present-value count), so the threshold
scales with sample size rather than using one fixed cutoff for every signal.

**Source:** Box, Jenkins & Reinsel, *Time Series Analysis: Forecasting and
Control* (Bartlett's formula for the standard error of an autocorrelation
estimate under a white-noise null); Montgomery's SPC text discusses the same
autocorrelation diagnostic when checking the I-MR chart's independence
assumption (fab sensor streams are frequently autocorrelated from drift/
thermal cycles, which inflates false special-cause signals if ignored).

**Rationale:** SME resolution (2026-07-21) chose the rigorous option over a
caption-only caveat: flag every charted signal individually rather than
leaving the independence-assumption caveat unverified. This is a
**diagnostic flag only** — it never filters, models/deautocorrelates, or
gates which signals are charted or how their limits are computed. It is
computed gap-spanning over the dropna'd series (not run-broken like the
moving range) because it is not part of the control-limit math that OQ5
governs.

**Applied In:** `apps/secom/secom_app/charts.py` ->
`_lag1_autocorrelation()`, `AUTOCORR_Z`, `control_chart_for_signal()`

---

## RULE 8 — W09-2 (#66): moving range broken at gaps, not gap-spanning (SME-set)

**Decision:** Before any moving-range math, a signal's present values are
split into maximal contiguous (NaN-free) runs (`_present_runs()`). The moving
range is computed only within a run (reusing `compute_imr`'s own diff logic
per run via `_pooled_moving_ranges()`), never across a missing cell. A run of
length 1 contributes no moving range. All within-run moving ranges are pooled
into a single `mrbar` -> `sigma_hat` -> one set of I-MR control limits per
signal, so the chart still has one UCL/LCL (only the *moving-range
computation*, not the limit-combination step, is run-broken). If every run in
a signal happens to have length 1 (pooled MR empty), `mrbar` and `sigma_hat`
collapse to 0 and `detect_*` raises — the same degenerate-signal error path
as a constant series.

**Source:** SME resolution (2026-07-21), the time-faithful option over
gap-spanning drop-NaN. A moving range spanning a gap would compare two points
that were not actually adjacent production runs, which is not a meaningful
moving range for a process-monitoring chart.

**Rationale:** SECOM's NaN cells are honest missingness (RULE 1), preserved
through ingest and selection; W09-2 must not silently treat two
non-adjacent-in-time present values as if they were consecutive.

**Applied In:** `apps/secom/secom_app/charts.py` -> `_present_runs()`,
`_pooled_moving_ranges()`, `control_chart_for_signal()`

---

## NOTE — W09-2: normality still deferred, no gate (applied default, unchanged)

Same stance as the W09-1 note above: the Individuals chart is moderately
robust to non-normality, the MR chart less so, but SECOM signals are not
verified normal. `charts.py` does not run or attach a normality flag — this
mirrors deferring the same call SPC's own Capability page makes explicit
(`normality_test`), left to a later issue if a normality diagnostic is wanted
here too. No filter, no gate.

## NOTE — W09-2: still no spec limits / no Cp/Cpk (RED LINE, lifted in W09-3 below)

`charts.py` produces I-MR control limits (UCL/LCL derived from the moving
range) — these are legitimate, data-computed chart limits, not spec limits.
It never fabricates USL/LSL, never calls `compute_capability`, and never
computes Cp/Cpk/Pp/Ppk. SECOM still ships no tolerances. **Update (W09-3,
#67): this red line is lifted, but only via caller-supplied limits — see
RULE 9.** `charts.py` itself is untouched and remains pure control-chart;
the new capability code lives in a separate module (`capability.py`).

---

## RULE 9 — W09-3 (#67): capability = caller-supplied limits, no fabrication (standard math, no-fabrication policy is SME-set)

**Decision:** `capability_for_signal(features, signal, lsl, usl, ruleset)` in
`secom_app/capability.py` takes `lsl`/`usl` as explicit caller-supplied
arguments (either may be `None` for a one-sided characteristic). The module
never derives, defaults, or fabricates a limit — e.g. it does NOT compute a
percentile/mean±k·sigma "tolerance" from the data. Both `None` raises
`ValueError` (no capability without at least one limit); both given with
`lsl >= usl` also raises.

**Source:** AIAG SPC Reference Manual, 4th ed. (2005) — Cp/Cpk/Pp/Ppk
formulas are reused unchanged from `apps/spc/spc_app/spc_engine/capability.py`
(`compute_capability`), which already handles `lsl`/`usl == None` correctly
(one-sided / two-sided / neither -> index `None`). **Flagged: the
no-fabrication *policy* (reject a derived-limit shortcut) is an SME
resolution for this platform, not itself an AIAG-published rule — AIAG
defines the Cp/Cpk math, not where a limit must come from.** SME resolution
(2026-07-23) confirmed caller-supplied limits over any percentile/nominal-
derived alternative, because deriving a "tolerance" from the process's own
data would inflate Cpk toward whatever the process already does and is not
a real capability claim.

**Rationale:** Continues RULE 3/NOTE "No spec limits ship with SECOM" — the
limits-source decision (engineering spec vs SME-supplied) still belongs to a
later UI/limits issue; this module only computes once a limit is supplied,
it never invents one.

**Applied In:** `apps/secom/secom_app/capability.py` -> `capability_for_signal()`

---

## RULE 10 — W09-3 (#67): capability coupled to the W09-2 stability gate — compute + flag, not suppress (standard requirement, SME-set response)

**Decision:** `capability_for_signal()` always computes Cp/Cpk/Pp/Ppk (via
`compute_capability`, fed `chart.imr["values"]` and the within-process
`chart.imr["sigma_hat"]` = MR̄/d₂ from the W09-2 I-MR chart). If the signal's
control chart has any special-cause `violations` (Western Electric or
Nelson, per the `ruleset` argument), the result carries `stable=False` and a
non-`None` `stability_warning` naming the violation count and ruleset and
stating the indices are not a valid capability claim until the process is
stabilized. The indices are never hard-suppressed (returned `None`) for
instability — an in-control signal produces `stable=True`,
`stability_warning=None`.

**Source:** AIAG SPC Reference Manual, 4th ed. (2005) — capability indices
are only meaningful on a process in statistical control; this is the AIAG
requirement already implemented as the precedent
`apps/spc/spc_app/pages/process_capability.py:156` ("if oos_signals:" ->
prominent warning, values still shown). **Flagged: "compute + flag" vs. hard-
suppress is an SME resolution matching that existing precedent — AIAG states
the stability *requirement*, not which of the two enforcement mechanics a
tool must pick.** SME resolution (2026-07-23) chose compute + flag, per DoD
#67 "no Cpk on an out-of-control process without a warning" (a warning, not
a withhold).

**Rationale:** Mirrors the platform's existing SPC Capability page exactly,
so a SECOM signal and an SPC stream get identically-shaped stability
guidance rather than two divergent behaviors for the same AIAG requirement.

**Applied In:** `apps/secom/secom_app/capability.py` -> `capability_for_signal()`

---

## RULE 11 — W09-4 (#68): MSA not applicable to SECOM (standard)

**Decision:** MSA / Gage R&R does not apply to SECOM. SECOM carries no
`part`/`appraiser`/`trial` structure and none can be legitimately constructed
from it (different sensors measure different characteristics, not repeat
appraisals of one measurand; successive wafers are different parts, not
re-measurements of the same part). Rather than fabricate a crossed-study
structure or skip the issue silently, this platform ships a standards-
anchored non-applicability document plus an executable refusal guard:
`gage_rr_applicability()` / `assert_gage_rr_applicable()` in
`secom_app/msa.py` detect the missing dimensions and raise/return a verdict
pointing at the documentation. No Gage R&R math (EV/AV/%GRR/ndc/verdict) is
added to SECOM — a real study is run through the existing `apps/msa` app.

**Source:** AIAG MSA (4th Edition) Section 3.1 (designed crossed study: n
parts x k appraisers x r>=2 trials; recommended study size) and Section 3.2
(Average-and-Range method assumptions — repeatability estimated within a
(part, appraiser) cell, reproducibility estimated across appraisers). Already
SME-verified in-repo against the primary manual: `apps/msa/docs/ASSUMPTIONS_LOG.md`
RULE 1 (Average-and-Range method), RULE 11 (balanced crossed data), RULE 12
(minimum study size) — verified 2026-07-19 (SME: Sid). This entry cites those
in-repo, verified rules rather than introducing new AIAG section numbers,
tables, or thresholds — the finding here is structural (SECOM lacks the axes
a Gage R&R needs), not a new numeric criterion. **Labelled standard**: the
AIAG structural requirement (a Gage R&R needs a crossed part x appraiser x
trial design) is not a platform heuristic — it is what makes a Gage R&R a
Gage R&R.

**Rationale:** `apps/secom/secom_app/ingest.py:52` (`SecomDataset`) carries
exactly `features`/`labels`/`timestamps` — one reading per wafer per sensor,
no re-measurement axis and no appraiser axis. Treating different sensors as
appraisers or successive wafers as trials would be exactly the kind of
invention this issue forbids; the honest answer is refusal, not a fabricated
computation. Full argument: `apps/secom/docs/MSA_APPLICABILITY.md`.

**Applied In:** `apps/secom/secom_app/msa.py` ->
`gage_rr_applicability()`, `assert_gage_rr_applicable()`;
`apps/secom/docs/MSA_APPLICABILITY.md`

---

## Summary of Files & Code Pointers

| Assumption | Implemented In |
|-----------|---------------|
| Preserve missingness at ingest | `ingest.py` -> `load_secom()`, `secom_missingness()` |
| Missingness cutoff (100) | `selection.py` -> `MIN_NON_MISSING` |
| Zero-variance drop | `selection.py` -> `select_signals()` rule 2 |
| Near-zero-variance drop | `selection.py` -> `NZV_FREQ_RATIO`, `NZV_PERCENT_UNIQUE` |
| Filter order / reason precedence | `selection.py` -> `select_signals()` |
| No spec limits / no Cp/Cpk here | (deferred; not implemented in W09-1) |
| I-MR via reused SPC engine (standard) | `charts.py` -> `control_chart_for_signal()` |
| Lag-1 autocorrelation flag (SME-set) | `charts.py` -> `_lag1_autocorrelation()`, `AUTOCORR_Z` |
| Gap-broken moving range (SME-set) | `charts.py` -> `_present_runs()`, `_pooled_moving_ranges()` |
| Normality still deferred (no gate) | (deferred; not implemented in W09-2) |
| No spec limits / no Cp/Cpk here | RED LINE lifted in W09-3 via caller-supplied limits only (RULE 9) |
| Caller-supplied limits, no fabrication (standard math, SME policy) | `capability.py` -> `capability_for_signal()` |
| Compute + flag stability coupling (SME resolution) | `capability.py` -> `capability_for_signal()` |
| MSA not applicable to SECOM (standard) | `msa.py` -> `gage_rr_applicability()`, `assert_gage_rr_applicable()` |
