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

## RULE 2 — K1/K2/K3 Constants (AIAG MSA, 4th Edition, Gage R&R Report Form / Appendix C)

**Decision:** Convert average ranges directly to sigma estimates using AIAG's published **K1/K2/K3
lookup tables** (`K = 1/d2*`), not a plain d2 lookup.

**Source:** AIAG MSA (4th Edition), Gage R&R report form and Appendix C. Verified directly against
the primary manual (`MSA_Reference_Manual_4th_Edition.md`) on 2026-07-19 (SME: Sid). K1 uses the
many-subgroup d2* (≈ plain d2); K2 and K3 use the single-subgroup d2*, which differs materially
from plain d2 — using the K tables verbatim sidesteps that ambiguity and matches AIAG's published
forms exactly.

**K1 by number of trials (r):**
```
r | K1
2 | 0.8862
3 | 0.5908
```

**K2 by number of appraisers (k):**
```
k | K2
2 | 0.7071
3 | 0.5231
```

**K3 by number of parts (n):**
```
n  | K3
 2 | 0.7071
 3 | 0.5231
 4 | 0.4467
 5 | 0.4030
 6 | 0.3742
 7 | 0.3534
 8 | 0.3375
 9 | 0.3249
10 | 0.3146
```

**Rationale:** Each K is an empirical constant (`1/d2*`) derived from the properties of the normal
distribution for the relevant subgroup layout. Using the published tables avoids re-deriving d2*
and matches the AIAG standard exactly. Sizes outside these tables are **not** defined by AIAG's
published range-method tables: `_k_constant()` raises `ValueError` rather than clamping or
extrapolating.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_K1`/`_K2`/`_K3` dicts, `_k_constant()`

---

## RULE 3 — Repeatability (EV) Formula (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Compute **Equipment Variation (EV)** as:
```
EV = Rbar × K1(trials)
where Rbar = mean of the within-(part, appraiser)-cell ranges
```

**Source:** AIAG MSA (4th Edition), Section 3.2, Equation 3.2.1.
"Repeatability measures variation due to the equipment (or measurement device) when the same operator measures the same part multiple times."

**Rationale:**
- The range within a (part, appraiser) cell captures the "spread" of repeated measurements.
- K1 converts that mean range to a sigma (standard deviation) estimate.
- This reflects the inherent equipment repeatability, excluding appraiser-to-appraiser differences.

**Worked example (AIAG canonical 10×3×3 study):**
- Rbar = 0.342, trials = 3, K1(3) = 0.5908.
- EV = 0.342 × 0.5908 = 0.20206 ≈ 0.202 (AIAG-published EV = 0.20188).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (lines computing `ev`)

---

## RULE 4 — Reproducibility (AV) Formula (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Compute **Appraiser Variation (AV)** as:
```
AV = sqrt((Xdiff × K2(appraisers))² − (EV² / (n_parts × n_trials)))
where Xdiff = range of appraiser grand means
```

**Source:** AIAG MSA (4th Edition), Section 3.2, Equation 3.2.2.
"Reproducibility measures variation due to different appraisers (or operators)."

**Rationale:**
- The range of appraiser averages (Xdiff) captures the appraiser-to-appraiser spread.
- K2 converts that to a sigma estimate.
- The subtraction `− (EV² / (n_parts × n_trials))` removes the **repeatability component** already captured in EV.
  This ensures AV reflects **only** the appraiser difference, not equipment noise.
- If the subtraction yields a negative value (rare, high EV), clamp AV to 0 (numerical artifact).

**Worked example (AIAG canonical 10×3×3 study):**
- Xdiff = 0.445, appraisers = 3, K2(3) = 0.5231, EV = 0.202, n_parts = 10, n_trials = 3.
- AV = sqrt((0.445 × 0.5231)² − 0.202² / 30) = sqrt(0.054186 − 0.001360) ≈ 0.230
  (AIAG-published AV = 0.22963).

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

## RULE 6 — Part Variation / Total Variation (AIAG MSA, 4th Edition, Section 3.2)

**Decision:** Estimate **Part Variation (PV)** and **Total Variation (TV)** as:
```
PV = Rp × K3(parts)
where Rp = range of part means
TV = sqrt(GRR² + PV²)
```

**Source:** AIAG MSA (4th Edition), Section 3.2, Equation 3.2.4, and the Gage R&R report form.
"Part variation represents the true part-to-part spread; total variation combines measurement
system variation (GRR) with part variation."

**Note (correction, W08-2):** The previous version of this document described a malformed
`σ_study = (d2 × Rp) / (1.128 × sqrt(n_appraisers × n_trials))` and cited "1.128 = sqrt(8/π)" as
the reason. That factor and formula do not appear in AIAG MSA and have been removed; AIAG's
published form is the simple `PV = Rp × K3(n)` above.

**σ-units cancellation note:** EV, AV, PV, GRR, and TV are all reported in bare sigma units
(K = 1/d2*), with no 5.15/6-sigma "study variation" multiplier applied. That multiplier would
scale all five components identically, so it cancels exactly out of `%GRR = 100 × GRR / TV` and
`ndc = 1.41 × PV / GRR` — omitting it is mathematically equivalent and simpler.

**Rationale:**
- The range of part averages (Rp) reflects the **true part-to-part variation**.
- K3 converts that to a sigma estimate (PV).
- TV combines GRR and PV via RSS, giving the total observed variation in the study.
- TV is then used to compute %GRR_study = (GRR / TV) × 100.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (lines computing `pv`), `compute_gage_rr()` (line computing `tv`)

---

## RULE 7 — %GRR vs Study Variation (AIAG MSA, 4th Edition, Section 3.3)

**Decision:** Compute **%GRR vs Study Variation** as:
```
%GRR_study = (GR&R / TV) × 100
```

**Source:** AIAG MSA (4th Edition), Section 3.3, "Measurement System Acceptability Criteria."

**Interpretation:**
- **< 10%:** Measurement system is excellent; variation is negligible vs part variation.
- **10–30%:** Marginal; acceptable for some uses.
- **> 30%:** Inadequate; measurement system must be improved.

**Rationale:**
- %GRR_study indicates how much of the **total observed variation** is measurement noise.
- If GRR is much smaller than TV, the system can discriminate between parts reliably.
- If `TV <= 0` (degenerate zero-variation study), %GRR_study is `inf`.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (line computing `pgrr_study`)

---

## RULE 8 — %GRR vs Tolerance (AIAG MSA, 4th Edition, Section 3.3)

**Decision:** Compute **%GRR vs Tolerance** (if tolerance is provided) as:
```
%GRR_tolerance = (6 × GR&R / Tolerance) × 100      where Tolerance = USL − LSL
```

**Source:** AIAG MSA (4th Edition), Section 3.3, "Measurement System Acceptability Criteria" (alternative criterion).

**Why the 6 is here and not in %GRR_study:** EV/AV/GRR/PV/TV are all carried in bare 1-sigma units
(`K = 1/d2*`) inside this engine (see RULE 6/7 and `_average_and_range_method()`'s docstring). The
6-sigma "study variation" multiplier cancels out of `%GRR_study = GRR/TV` and of
`ndc = 1.41 × PV/GRR` because it would scale numerator and denominator identically — so it is
correctly omitted there. It does **not** cancel here: the denominator is a fixed spec width
(`USL − LSL`), not another bare-sigma quantity, so the numerator must first be put on the same
6-sigma "study variation" basis before dividing. Skipping this step understates %GRR_tolerance by
exactly 6× (audit finding A07 / issue #190).

**Provenance of the 6 — PRIMARY-SOURCE VERIFIED (upgraded 2026-07-30, issue #217).** This was
previously carried with a ⚠ "verified against a third-party reproduction, not the paywalled manual
itself" caveat. That caveat is now **withdrawn**: AIAG MSA 4th Ed., **Chapter III, Section B**
states the tolerance basis outright —

> "In that case, *%EV*, *%AV*, *%GRR* and *%PV* are calculated by substituting the value of
> tolerance *divided by six* in the denominator of the calculations in place of the total
> variation (*TV*). **Either or both approaches can be taken depending on the intended use of the
> measurement system and the desires of the customer.**"

`tolerance / 6` in the denominator is algebraically identical to `6 × GRR / tolerance` in the
numerator, so the manual itself pins **6.00** (not 5.15) for the 4th edition. Verified against the
primary manual (`MSA_Reference_Manual_4th_Edition.md`) on 2026-07-30 — the same copy RULE 2 and
RULE 9 cite.

The RTX / United Technologies PPAP toolbox "Study Case 1 — AIAG MSA Manual 4th Edition
(pag 118-119)" form — built from the same reference dataset as
`apps/msa/data/aiag_reference_study.csv` — computes
`100 × (6.00 × SMV) / Eng. Tolerance = 100 × 1.847522 / 4.4200 = 41.80%`, labelled
`% Tolerance (SV/Toler)`. That form is now only a **numeric cross-check** of the primary source,
not the source of the constant. (Note: that form is a Hamilton Sundstrand / UTC customer document,
not an AIAG reproduction — see the acceptance-band note below.)

**5.15 is the superseded 3rd-edition convention** (99.0% coverage vs. 6σ's 99.73%) and is not used
here; there is no config knob to select it — see `_STUDY_VARIATION_SIGMA` in `gage_rr_engine.py`.

**Interpretation — ONE band set applies to BOTH bases:**
- **< 10%:** Excellent.
- **10–30%:** Marginal.
- **> 30%:** Reject.

**The tolerance basis uses the SAME acceptance bands as the study-variation basis (10 / 30).**
This is stated here explicitly rather than left to inference; RULE 8's earlier silence on the point
is what let audit finding A07 hide, and an explicit statement is what makes a future attempt to
introduce a *second*, tolerance-only band set visibly wrong. Two primary passages settle it:

1. **Chapter II, Section D, Table II-D 1 "GRR Criteria"** — a single table with **no
   study-variation-vs-tolerance basis qualifier**: `Under 10 percent` → "Generally considered to
   be an acceptable measurement system"; `10 percent to 30 percent` → "May be acceptable for
   some applications"; `Over 30 percent` → "Considered to be unacceptable".
   (Precision note, so a future auditor does not re-raise it: the table's lead-in *does* carry a
   **purpose** qualifier — "For measurement systems whose purpose is to analyze a process". That
   is a different axis from the basis, and passage 2 below closes the tolerance case explicitly.)
2. **Chapter III, Section B**, in the same passage as the tolerance-basis text quoted above
   (separated from it only by the intervening paragraph defining *ndc*):
   *"Given that the graphical analysis has not indicated any special cause variation, the rule of
   thumb for gage repeatability and reproducibility (%GRR) may be found in Chapter II,
   Section D."* — i.e. the tolerance basis is a **denominator swap only**, and it redirects to the
   very same Table II-D 1 for its acceptance rule of thumb.

**Rejected alternative (issue #217, audit A07-b, 2026-07-30):** a proposed `0–19%` Accept /
`20–30%` Marginal / `>30%` Reject band set *for the tolerance basis only*. **Refuted, not merely
unverified.** Those figures come from the RTX / Hamilton Sundstrand PPAP form's own
"Gage R&R Study Evaluation Guideline" — a **customer-specific** criterion whose *study-variation*
row also disagrees with AIAG's published 10/30, so it cannot be an AIAG reproduction. A full-text
search of the primary manual for `19 percent`, `0-19` and `20-30` returns no match. Minitab,
SPC for Excel and QI Macros — all independent of that form — likewise apply one band set to
%Study Var and %Tolerance alike. Adopting it would have implemented a third-party customer's
criterion under an AIAG label, and loosened the product in the falsely-optimistic direction.
**Do not reintroduce a per-basis band set without a primary-source citation that overrides
Table II-D 1.**

**Caution (AIAG MSA 4th Ed., Ch. II §D):** *"The use of the GRR guidelines as threshold criteria
alone is NOT an acceptable practice for determining the acceptability of a measurement system."*
The verdict this engine emits is a guideline flag, not a release decision.

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
ndc = trunc(1.41 × (PV / GR&R))
```

**Source:** AIAG MSA (4th Edition), Section 3.3, Equation 3.3.2. Verified directly against the
primary manual on 2026-07-19 (SME: Sid): `ndc = 1.41 × PV / GRR`.
"ndc indicates how many distinct measurement categories can be reliably distinguished across the
observed part variation."

**Note (correction, W08-2):** ndc is driven by **Part Variation (PV)**, not tolerance. It is
computed unconditionally, whether or not a tolerance is supplied — a study with no tolerance can
still report a real ndc and reach Accept/Marginal, not just Reject.

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

**Note on %GRR (SME resolution, 2026-07-19, Sid — supersedes prior tolerance-preferred convention):**
If both `%GRR_tolerance` and `%GRR_study` are available, the verdict is driven by
`max(%GRR_tolerance, %GRR_study)` — the more conservative (worse) of the two. AIAG reports both
numbers and does not mandate which single number drives the verdict; using the max avoids a study
that looks acceptable against tolerance while actually failing against study variation (or vice
versa). If only `%GRR_study` is available (no tolerance input), base the verdict on `%GRR_study`.
`ndc` and each individual `%GRR` value are still reported separately regardless of this choice.

**Note on the band set (issue #217, 2026-07-30):** `_compute_verdict(ndc, pgrr)` takes **one**
%GRR and judges it against **one** band set (10 / 30) on purpose. Per RULE 8, AIAG MSA 4th Ed.
applies Table II-D 1 (Ch. II §D) to the tolerance basis and the study-variation basis alike —
Ch. III §B makes the tolerance basis a denominator swap and redirects to Ch. II §D for the rule of
thumb. So the two-argument signature is not a simplification of the standard: there is no second
band set to carry, and adding an accept-threshold parameter per basis would encode a
customer-specific criterion, not AIAG's. Because both bases share the bands, `max()` above is a
straight comparison of like with like.

Where this *does* deviate from AIAG is the choice of basis, not the bands: **Ch. II §C** picks the
basis by purpose (product control → assess %GRR to *tolerance*; process control → assess %GRR to
*process variation*). The engine has no purpose input, so it takes the worse of the two — a
deliberate conservative deviation, documented in the SME note above.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` computes the effective
`verdict_pgrr` (the `max()` above) and passes it as the sole `pgrr` argument to
`_compute_verdict(ndc, pgrr)`, which applies only the ndc/threshold logic.

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

## RULE 13 — Edge Case: All Measurements Identical (TV = 0)

**Decision:** If all part averages are identical (e.g., all measurements = 10.05):
- PV = 0, GRR = 0 (EV = AV = 0), so TV = sqrt(GRR² + PV²) = 0.
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

## RULE 15 — CSV Export Payload: Both Study and Results (W08-3, SME resolution)

**Decision:** Offer **two** CSV downloads on the Gage R&R page, not one:
1. **Study CSV** — the validated study frame (`part, appraiser, trial, measurement`),
   round-trippable input, matching Control Plan's `export_csv(validated)`.
2. **Results CSV** — a flat, one-row table of the computed metrics (EV, AV, GRR, PV,
   TV, %GRR study, %GRR tolerance, ndc, verdict, verdict interpretation).

**Source:** Not an AIAG requirement; a platform UX decision (SME resolution, W08-3,
2026-07-19, Sid — overrides the single-CSV default researched for #56). The Excel/PDF
exports remain the full results report; the results CSV is a lightweight machine-readable
companion to it.

**Rationale:** A study CSV alone forces a spreadsheet user to recompute %GRR/ndc/verdict by
hand to get them into a flat table; a results CSV alone loses the raw measurements needed to
audit or re-run the study. Both are one call each over the same `GageStudyReport` and the
same verdict→sentence map, so the marginal cost of the second button is a few lines, not a
new export path.

**Applied In:** `apps/msa/msa_app/exporter.py` → `export_csv()`, `export_results_csv()`;
`apps/msa/msa_app/pages/gage_study.py` → the "Download Report" section (two CSV buttons).

---

## Summary of Files & Code Pointers

| Assumption | Implemented In |
|-----------|---------------|
| Average-and-Range method | `_average_and_range_method()` |
| K1/K2/K3 constants | `_K1`/`_K2`/`_K3` dicts, `_k_constant()` |
| EV formula | `_average_and_range_method()`, lines: `ev = avg_range_within * k1` |
| AV formula | `_average_and_range_method()`, lines: `av_squared = ...` |
| GR&R formula | `compute_gage_rr()`, lines: `grr = sqrt(ev² + av²)` |
| Part / Total variation | `_average_and_range_method()`, lines: `pv = range_parts * k3`; `compute_gage_rr()`, lines: `tv = sqrt(grr² + pv²)` |
| %GRR_study | `compute_gage_rr()`, lines: `pgrr_study = (grr / tv) * 100` |
| %GRR_tolerance | `compute_gage_rr()`, lines: `pgrr_tolerance = (grr * _STUDY_VARIATION_SIGMA / tolerance) * 100` |
| ndc | `_compute_ndc()` |
| Verdict logic | `_compute_verdict()`, `verdict_pgrr = max(pgrr_tolerance, pgrr_study)` in `compute_gage_rr()` |
| Balance check | `compute_gage_rr()`, lines: `is_balanced = ...` |
| Minimum study size | `compute_gage_rr()`, validation checks |
| Edge cases | `compute_gage_rr()`, error handling + `_compute_verdict()` |
