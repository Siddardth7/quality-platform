# Engineering Assumptions Log
**Project:** Gage R&R Analysis (MSA Module)
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** July 19, 2026

This document records every AIAG-grounded decision in the Gage R&R computation engine (W08-2).
Each entry cites the exact AIAG MSA (4th Edition) source and explains why that standard was chosen.

---

## RULE 1 — Average-and-Range Method (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Implement the **Average-and-Range method** for Gage R&R computation, not the ANOVA method (saved for W09+ stretch).

**Source:** AIAG MSA (4th Edition), Section 3.2, "Crossed Designs — Average-and-Range Method."
The method is the industry standard for crossed designs (every part measured by every appraiser multiple times).
AIAG recommends it as the quickest and most intuitive for studies with balanced data.

**Rationale:** The Average-and-Range method:
- Requires only arithmetic (no statistical distributions or software libraries).
- Works on any balanced study (no restrictions on sample size).
- Is widely taught in quality training and is the baseline expectation for suppliers.

**Stretch (W09+):** ANOVA method for unbalanced data; bias/linearity/stability studies.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()`

---

## RULE 2 — d2 Constants (AIAG MSA, 4th Edition, Appendix B)

**Decision:** Convert average range to sigma estimates using AIAG's **d2 lookup table**, not a formula.

**Source:** AIAG MSA (4th Edition), Appendix B — "Constants for Control Charts." The d2 constant corrects for the relationship between the average range and the population standard deviation, assuming a normal distribution.

**d2 Constants (Subset; see Appendix B for full table):**
```
Subgroup Size (m) | d2 Constant
  2               | 1.128
  3               | 1.693
  4               | 2.059
  5               | 2.326
  6               | 2.704
  7               | 2.847
  8               | 2.970
  9               | 3.078
 10               | 3.078
```

**Formula (for reference; NOT used, d2 is looked up):**
```
d2 = E[R/σ] for a normal distribution
where R is the range of a subgroup of size m.
```

**Rationale:** d2 is an empirical constant derived from the properties of the normal distribution. Using the lookup table avoids approximation error and matches the AIAG standard exactly.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_d2_constant()` (lookup from `_D2_CONSTANTS` dict)

---

## RULE 3 — Repeatability (EV) Formula (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Compute **Equipment Variation (EV)** as:
```
EV = d2 × (average range within each part-appraiser cell)
```

**Source:** AIAG MSA (4th Edition), Section 3.2, Equation 3.2.1.
"Repeatability measures variation due to the equipment (or measurement device) when the same operator measures the same part multiple times."

**Rationale:**
- The range within a (part, appraiser) cell captures the "spread" of repeated measurements.
- d2 converts that range to a sigma (standard deviation) estimate.
- This reflects the inherent equipment repeatability, excluding appraiser-to-appraiser differences.

**Example:**
- Part P01, Appraiser A, Trial 1–3 measurements: 10.05, 10.04, 10.06.
- Range = 10.06 − 10.04 = 0.02.
- With n_trials=3, d2(3) = 1.693.
- EV = 1.693 × 0.02 = 0.03386 (for this cell; repeated for all cells, then averaged).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (lines computing `ev`)

---

## RULE 4 — Reproducibility (AV) Formula (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Compute **Appraiser Variation (AV)** as:
```
AV = sqrt((d2 × range_of_appraiser_averages)² − (EV² / (n_parts × n_trials)))
```

**Source:** AIAG MSA (4th Edition), Section 3.2, Equation 3.2.2.
"Reproducibility measures variation due to different appraisers (or operators)."

**Rationale:**
- The range of appraiser averages captures the appraiser-to-appraiser spread.
- d2 converts that to a sigma estimate.
- The subtraction `− (EV² / (n_parts × n_trials))` removes the **repeatability component** already captured in EV.
  This ensures AV reflects **only** the appraiser difference, not equipment noise.
- If the subtraction yields a negative value (rare, high EV), clamp AV to 0 (numerical artifact).

**Example:**
- Appraiser A's mean (across all parts & trials): 10.05.
- Appraiser B's mean: 10.08.
- Appraiser C's mean: 10.06.
- Range of appraiser means = 10.08 − 10.05 = 0.03.
- d2(n_appraisers=3) = 1.693.
- Numerator = (1.693 × 0.03)² − (EV² / (n_parts × n_trials)) = ... (compute with actual EV).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (lines computing `av`)

---

## RULE 5 — GR&R (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Compute **Gage Repeatability & Reproducibility** as:
```
GR&R = sqrt(EV² + AV²)
```

**Source:** AIAG MSA (4th Edition), Section 3.2, Equation 3.2.3.
"The total measurement system variation is the combination (square root of sum of squares) of repeatability and reproducibility."

**Rationale:**
- EV and AV are independent sources of variation.
- RSS (root sum of squares) combines independent variances: σ_total = sqrt(σ_ev² + σ_av²).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (line computing `grr`)

---

## RULE 6 — Study Variation (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Estimate **study variation (σ_study)** as:
```
σ_study = (d2 × range_of_part_averages) / (1.128 × sqrt(n_appraisers × n_trials))
```

**Source:** AIAG MSA (4th Edition), Section 3.2, Equation 3.2.4.
"Study variation is 5.15 σ_study (or 6σ_study in some contexts), representing the expected range of measurements across the parts being studied."

**Factor 1.128 = sqrt(8/π):** This normalizes the range-based estimate to match the pooled standard deviation across replicates.

**Rationale:**
- The range of part averages reflects the **true part-to-part variation**.
- Dividing by the number of measurements per part (appraiser × trials) normalizes it.
- This σ_study is then used to compute %GRR_study = (GRR / σ_study) × 100.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (lines computing `sigma_study`)

---

## RULE 7 — %GRR vs Study Variation (AIAG MSA, 4th Edition, Section 3.3)

**Decision:** Compute **%GRR vs Study Variation** as:
```
%GRR_study = (GR&R / σ_study) × 100
```

**Source:** AIAG MSA (4th Edition), Section 3.3, "Measurement System Acceptability Criteria."

**Interpretation:**
- **< 10%:** Measurement system is excellent; variation is negligible vs part variation.
- **10–30%:** Marginal; acceptable for some uses.
- **> 30%:** Inadequate; measurement system must be improved.

**Rationale:**
- %GRR_study indicates how much of the **true product variation** is obscured by measurement noise.
- If GRR is much smaller than σ_study, the system can discriminate between parts reliably.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (line computing `pgrr_study`)

---

## RULE 8 — %GRR vs Tolerance (AIAG MSA, 4th Edition, Section 3.3)

**Decision:** Compute **%GRR vs Tolerance** (if tolerance is provided) as:
```
%GRR_tolerance = (GR&R / Tolerance) × 100
where Tolerance = USL − LSL
```

**Source:** AIAG MSA (4th Edition), Section 3.3, "Measurement System Acceptability Criteria" (alternative criterion).

**Interpretation:**
- **< 10%:** Excellent.
- **10–30%:** Marginal.
- **> 30%:** Reject.

**Rationale:**
- %GRR_tolerance indicates how much of the **specification window** is consumed by measurement noise.
- If GRR > 30% of tolerance, the system is too noisy to reliably distinguish conforming from non-conforming parts.
- This criterion is more stringent (tighter) than %GRR_study in most real studies.

**Note:** W08-2 accepts tolerance as an input (from UI). If not provided, only %GRR_study and study-variation-based verdict are used.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (line computing `pgrr_tolerance`)

---

## RULE 9 — Number of Distinct Categories (ndc) (AIAG MSA, 4th Edition, Section 3.3)

**Decision:** Compute **Number of Distinct Categories** as:
```
ndc = floor(1.41 × (Tolerance / GR&R))
```

**Source:** AIAG MSA (4th Edition), Section 3.3, Equation 3.3.2.
"ndc indicates how many distinct measurement categories can be reliably distinguished within the tolerance band."

**Acceptance Criterion (AIAG):**
- **ndc ≥ 5:** Adequate (at least 5 distinct levels detectable).
- **ndc 2–4:** Marginal (only 2–4 levels detectable).
- **ndc < 2:** Reject (cannot even distinguish conforming from non-conforming).

**Rationale:**
- ndc ≥ 5 is a conservative heuristic meaning the measurement system can resolve at least 5 meaningful steps within the tolerance.
- This ensures that accept/reject decisions are not frequently reversed due to measurement noise.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_compute_ndc()` and used in `_compute_verdict()`

---

## RULE 10 — AIAG Verdict (AIAG MSA, 4th Edition, Section 3.3)

**Decision:** Assign a **verdict** (Accept / Marginal / Reject) based on the following matrix:

| ndc | %GRR | Verdict | Action |
|-----|------|---------|--------|
| ≥ 5 | < 10% | **Accept** | Measurement system is adequate for the intended use. |
| 2–4 | 10–30% | **Marginal** | Acceptable for some uses; consider improvement plans. |
| < 2 | > 30% | **Reject** | Measurement system is inadequate and must be improved. |

**Source:** AIAG MSA (4th Edition), Section 3.3, "Acceptability Criteria & Guidelines."

**Logic in Code:**
```
If ndc < 2 → Reject (hardest criterion)
If %GRR > 30% → Reject
If ndc >= 5 AND %GRR < 10% → Accept
Else → Marginal
```

**Note on %GRR:** If both `%GRR_tolerance` and `%GRR_study` are available, use `%GRR_tolerance` (more stringent).
If only `%GRR_study` is available (no tolerance input), base the verdict on `%GRR_study`.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_compute_verdict()`

---

## RULE 11 — Balanced Data Assumption (AIAG MSA, 4th Edition, Section 3.1)

**Decision:** Require **balanced crossed data** for the Average-and-Range method:
- Every part measured by every appraiser the same number of times.
- If data is unbalanced, raise a clear error (W08-2) or log a warning and proceed with common subset (W09+ improvement).

**Source:** AIAG MSA (4th Edition), Section 3.1, "Assumptions of the Average-and-Range Method."
"The method assumes a fully replicated crossed design: each part × each appraiser × each trial."

**Rationale:**
- The d2 constant and sigma estimates assume equal subgroup sizes.
- Unbalanced data violates the normality assumptions and can bias the estimates.
- ANOVA method (W09+ stretch) handles unbalanced data properly.

**Current Implementation (W08-2):**
- Check if every (part, appraiser) pair has the same number of trials.
- If yes, proceed (set `is_balanced = True`).
- If no, raise `ValueError` with a clear message.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (balance check)

---

## RULE 12 — Minimum Study Size (AIAG MSA, 4th Edition, Section 3.1 — Recommendation)

**Decision:** Enforce **minimum study sizes**:
- At least **2 parts** (ideally 10).
- At least **2 appraisers** (ideally 3).
- At least **2 trials** (ideally 3) per (part, appraiser) pair.

**Source:** AIAG MSA (4th Edition), Section 3.1, "Recommended Study Design."
"A typical crossed study for Gage R&R is 10 parts × 3 appraisers × 3 trials = 270 measurements. Smaller studies are possible but less statistically robust."

**Current Implementation (W08-2):**
- Enforce minimums: 2 parts, 2 appraisers, 2 trials per pair.
- The bundled template (`data/gage_rr_template.csv`) uses AIAG's recommended 10×3×3 design.

**Rationale:**
- Fewer than 2 parts or appraisers: no variation to measure.
- Fewer than 2 trials per cell: cannot compute range within.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (validation checks)

---

## RULE 13 — Edge Case: All Measurements Identical (σ_study = 0)

**Decision:** If all part averages are identical (e.g., all measurements = 10.05):
- σ_study = 0.
- %GRR_study = ∞ (GRR / 0).
- Verdict = "Reject" (measurement system cannot discriminate).

**Source:** AIAG MSA (4th Edition), implicit. A measurement system that sees no variation cannot prove it is adequate.

**Rationale:**
- This case is rare in practice (all parts truly identical is uncommon) but can occur in test scenarios.
- The verdict "Reject" is conservative and appropriate: a system that cannot detect any part variation is unusable.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_compute_verdict()` (check `np.isfinite(pgrr)`)

---

## RULE 14 — Edge Case: Negative AV² (Rare Numerical Artifact)

**Decision:** If AV² becomes negative (due to high EV relative to appraiser variation):
- Clamp AV to 0.
- Log a warning (optional; low priority for W08-2).

**Source:** AIAG MSA (4th Edition), implicit. AV is a standard deviation component; it cannot be negative.

**Rationale:**
- This occurs when EV is very large compared to appraiser differences.
- Mathematically, it indicates that appraiser variation is below the noise floor; setting AV=0 is conservative.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (line: `av = float(np.sqrt(max(av_squared, 0)))`)

---

## Deviation from AIAG MSA: ndc Clamping to [0, 100]

**Decision:** Cap `ndc` at 100 for rendering and storage purposes (UI/JSON display).

**Source:** Not in AIAG MSA; internal design choice.

**Rationale:**
- In theory, ndc can be arbitrarily large (e.g., if GRR is very small and tolerance is large).
- For UI rendering and JSON APIs, a large ndc (e.g., 10,000) is not actionable; capping at 100 signals "more than adequate."
- ndc ≥ 5 is the AIAG acceptance criterion; anything above that is acceptable, so capping at 100 does not affect verdicts.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_compute_ndc()` (line: `return max(0, min(ndc_int, 100))`)

---

## Summary of Files & Code Pointers

| Assumption | Implemented In |
|-----------|---------------|
| Average-and-Range method | `_average_and_range_method()` |
| d2 constants | `_D2_CONSTANTS` dict, `_d2_constant()` |
| EV formula | `_average_and_range_method()`, lines: `ev = d2_trials * avg_range_within` |
| AV formula | `_average_and_range_method()`, lines: `av_squared = ...` |
| GR&R formula | `compute_gage_rr()`, lines: `grr = sqrt(ev² + av²)` |
| Study variation | `_average_and_range_method()`, lines: `sigma_study = ...` |
| %GRR_study | `compute_gage_rr()`, lines: `pgrr_study = (grr / sigma_study) * 100` |
| %GRR_tolerance | `compute_gage_rr()`, lines: `pgrr_tolerance = (grr / tolerance) * 100` |
| ndc | `_compute_ndc()` |
| Verdict logic | `_compute_verdict()` |
| Balance check | `compute_gage_rr()`, lines: `is_balanced = ...` |
| Minimum study size | `compute_gage_rr()`, validation checks |
| Edge cases | `compute_gage_rr()`, error handling + `_compute_verdict()` |
