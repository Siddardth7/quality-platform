# Engineering Assumptions Log
**Project:** SECOM Dataset Ingest + Signal Selection (W09-1)
**Last Updated:** July 21, 2026

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

## Summary of Files & Code Pointers

| Assumption | Implemented In |
|-----------|---------------|
| Preserve missingness at ingest | `ingest.py` -> `load_secom()`, `secom_missingness()` |
| Missingness cutoff (100) | `selection.py` -> `MIN_NON_MISSING` |
| Zero-variance drop | `selection.py` -> `select_signals()` rule 2 |
| Near-zero-variance drop | `selection.py` -> `NZV_FREQ_RATIO`, `NZV_PERCENT_UNIQUE` |
| Filter order / reason precedence | `selection.py` -> `select_signals()` |
| No spec limits / no Cp/Cpk here | (deferred; not implemented in W09-1) |
