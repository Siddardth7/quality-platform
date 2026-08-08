# Engineering Assumptions Log
**Project:** Gage R&R Analysis (MSA Module)
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** August 7, 2026

This document records every decision in the Gage R&R computation engine (W08-2) and explains why it
was made. Entries are of two kinds and each says which it is:

- **AIAG-grounded** — the decision follows AIAG MSA (4th Edition). The entry names a
  `Chapter <roman> – Section <letter>` locator and quotes the manual verbatim.
- **Not in AIAG MSA** — an internal design choice, a platform relaxation, or a deliberate
  deviation. The entry says so in its `**Source:**` line and claims no standard behind it.

An entry with no primary source is acceptable. An entry that *implies* one is not: a wrong number is
falsifiable by recomputation, but a fabricated quotation looks like verified evidence and every
decision downstream of it inherits unearned confidence.

**Citation integrity (#223, audit A10-a).** Every quotation below is registered in
[`CITATIONS.tsv`](CITATIONS.tsv) with the line of `MSA_Reference_Manual_4th_Edition.md` it came from,
and `apps/msa/tests/test_citations.py` re-asserts each one — quote **and** line number — against the
manual. A quotation in this file without a manifest row is a review failure. The manual is licensed
and is not in the repo, so those tests skip unless `MSA_MANUAL_PATH` points at a local copy.

**Note on locators.** The 4th Edition numbers its headings `Chapter <roman> – Section <letter>`.
It has no `Section 3.x` / `Equation 3.x.y` scheme; citations in that form (removed by #223) pointed
at nothing.

**Blockquote convention.** Every `>` blockquote in this file is a verbatim passage from the manual
with a `CITATIONS.tsv` row — including the manual's own grammar errors, which are reproduced
unaltered and marked `[sic]`. Text that was **withdrawn** as fabricated is exhibited in a fenced
code block, never in a blockquote, so a skim can never mistake a retracted quote for a live one.

The manual prints footnote *markers* inline, mid-sentence (e.g. `…10 parts ⁴⁴ that represent…`).
Quotations here drop the marker and quote the footnote separately where it is load-bearing; the
words are otherwise unaltered. A quotation spanning a dropped marker is registered in
`CITATIONS.tsv` as two rows — one per side — so both halves are still line-checked.

---

## RULE 1 — Average-and-Range Method, the DEFAULT (AIAG MSA, 4th Edition, Ch. III Sec. B)

**Decision:** The **Average-and-Range method** is the **default** — no longer the only — Gage R&R
computation. Since **#195** the ANOVA method exists alongside it and is opt-in via
`compute_gage_rr(..., method="anova")`; see **RULE 17** for its decomposition and citations. The
default did not change (SME decision, 2026-08-07): every existing call site keeps Average-and-Range
behaviour, and every computed value it returns is unchanged. Which method actually ran is declared
in the computed payload (`method` / `method_note`) and in every export, so a consumer can never
mistake an Average-and-Range `%GRR` for an ANOVA one.

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Variable Measurement System Study
Guidelines." Under "Guidelines for Determining Repeatability and Reproducibility" the manual names
three acceptable techniques:

> "The Variable Gage Study can be performed using a number of differing techniques. Three
> acceptable methods will be discussed in detail in this section. These are: Range method /
> Average and Range method (including the Control Chart method) / ANOVA method"

and states the trade-off between them directly:

> "Except for the Range method, the study data design is very similar for each of these methods.
> The ANOVA method is preferred because it measures the operator to part interaction gauge error,
> whereas the Range and the Average and Range methods does not include this variation." [sic —
> the manual's own grammar, quoted unaltered]

The same passage is why Average-and-Range remains *acceptable* rather than merely tolerated:

> "The ANOVA approach can identify appraiser-part interaction but it can also evaluate other
> sources of variation which is the reason why it was included. Historically, the assumption is
> made that the interaction is zero, in which case the results of both approaches are equivalent."

The manual's own "Average and Range Method" subsection repeats the limitation:

> "Unlike the Range method, this approach will allow the measurement system's variation to be
> decomposed into two separate components, repeatability and reproducibility. However, variation
> due to the interaction between the appraiser and the part/gage is not accounted for in the
> analysis."

with footnote 43: *"The ANOVA method can be used to determine the interaction between the gage and
appraisers, if such exists."* AIAG also states the zero-interaction assumption as a **precondition**
of these procedures — Chapter III, Section A, "Example Test Procedures" lists *"There is no
statistical interaction between appraisers and parts"* among the conditions under which they apply.

**Rationale:** The Average-and-Range method:
- Requires only arithmetic (no statistical distributions or software libraries).
- Works on any balanced study (no restrictions on sample size).
- Is widely taught in quality training and is the baseline expectation for suppliers.
- Is equivalent to ANOVA under AIAG's own stated precondition that the interaction is zero.

**Limitation of this method (declared, not hidden):** the part × appraiser interaction is **not
estimated** by Average-and-Range. It is absorbed into the reported EV/AV/PV components rather than
separated out, so `%GRR` is **biased low** whenever the interaction is non-zero — exactly the case
AIAG's precondition excludes and this method cannot detect. The computed payload therefore carries
`method = "average_and_range"` and a `method_note` stating the limitation, and both reach the results
CSV, the Excel Summary sheet and the PDF detail table ("Method" / "Method Limitation"). The remedy is
to run the same study through `method="anova"` (**RULE 17**), which separates and tests the
interaction term; `interaction` / `interaction_f` / `interaction_significant` are `None` under
Average-and-Range precisely because it cannot see them.

**Still outstanding:** unbalanced-data support (RULE 11) and bias/linearity/stability studies. #195
delivered the ANOVA interaction term for **balanced** studies only; ANOVA's ability to handle
unbalanced designs is not exercised here (both methods share the balance precondition).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()`;
`compute_gage_rr()` → the `method` dispatch and the `method` / `method_note` return keys; module
constants `METHOD` / `METHOD_NOTE` (and `METHOD_ANOVA` / `METHOD_NOTE_ANOVA`, RULE 17).
`apps/msa/msa_app/exporter.py` → `_detail_rows()` (Excel + PDF) and
`export_results_csv()` "Method" / "Method Limitation" rows/columns.
`apps/msa/msa_app/pages/gage_study.py` → the caption under "Gage R&R Results".
**Forward requirement:** the API response model for a Gage R&R study (#178 / #195-era endpoints)
must expose these two fields — `apps/api` does not exist yet, so it is carried by #178, not done here.

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-07-31 (SME: Sid). Note the 4th Edition uses
`Chapter <roman> – Section <letter>` headings; the "Section 3.2" locator previously cited here does
not exist in it.

---

## RULE 2 — K1/K2/K3 Constants (AIAG MSA, 4th Edition, Gage R&R Report Form / Appendix C)

**Decision:** Convert average ranges directly to sigma estimates using AIAG's published **K1/K2/K3
lookup tables** (`K = 1/d2*`), not a plain d2 lookup.

**Source:** AIAG MSA (4th Edition), Gage R&R report form and Appendix C. Chapter III, Section B,
"Analysis of Results — Numerical" states the `K = 1/d2*` relationship and where the table lives:

> "*K1* depends upon the number of trials used in the gage study and is equal to the inverse of
> *d*2\* which is obtained from Appendix C."

(the *K2* and *K3* paragraphs say the same for appraisers and parts, and fix `g = 1` for both —
"since there is only one range calculation" — which is why K2/K3 use the single-subgroup `d2*`).
Verified directly against
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

## RULE 3 — Repeatability (EV) Formula (AIAG MSA, 4th Edition, Ch. III Sec. B)

**Decision:** Compute **Equipment Variation (EV)** as:
```
EV = Rbar × K1(trials)
where Rbar = mean of the within-(part, appraiser)-cell ranges
```

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Analysis of Results — Numerical."
The formula is stated there directly:

> "The repeatability or equipment variation (*EV* or σ*E*) is determined by multiplying the average
> range (*R̄*) by a constant (*K1*). *K1* depends upon the number of trials used in the gage study
> and is equal to the inverse of *d*2\* which is obtained from Appendix C."

and the quantity it estimates is defined in Chapter I, Section E, "Repeatability":

> "Repeatability is the variation in measurements obtained with **one measurement instrument** when
> used several times by **one appraiser** while measuring the identical characteristic on the
> **same part.**"

**Correction (#223, audit A10-a):** this entry previously cited "Section 3.2, Equation 3.2.1" and
quoted *"Repeatability measures variation due to the equipment (or measurement device) when the same
operator measures the same part multiple times."* Neither the locator scheme nor that sentence exists
in the 4th Edition — the quotation was **fabricated** and has been replaced with the two passages
above. The formula it was offered in support of was, and remains, correct.

**Rationale:**
- The range within a (part, appraiser) cell captures the "spread" of repeated measurements.
- K1 converts that mean range to a sigma (standard deviation) estimate.
- This reflects the inherent equipment repeatability, excluding appraiser-to-appraiser differences.

**Worked example (AIAG canonical 10×3×3 study):**
- Rbar = 0.342, trials = 3, K1(3) = 0.5908.
- EV = 0.342 × 0.5908 = 0.20206 ≈ 0.202 (AIAG-published EV = 0.20188).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (lines computing `ev`)

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 4 — Reproducibility (AV) Formula (AIAG MSA, 4th Edition, Ch. III Sec. B)

**Decision:** Compute **Appraiser Variation (AV)** as:
```
AV = sqrt((Xdiff × K2(appraisers))² − (EV² / (n_parts × n_trials)))
where Xdiff = range of appraiser grand means
```

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Analysis of Results — Numerical," which
gives both the multiplication and — this is the part that matters — the reason for the subtraction:

> "The reproducibility or appraiser variation (*AV* or σ*A*) is determined by multiplying the maximum
> average appraiser difference (*X̄*DIFF) by a constant (*K2*). ... Since the appraiser variation is
> contaminated by the equipment variation, it must be adjusted by subtracting a fraction of the
> equipment variation."

with *"where n = number of parts and r = number of trials"* fixing the divisor of that fraction as
`n × r`. The quantity being estimated is defined in Chapter I, Section E, "Reproducibility":

> "Reproducibility is typically defined as the variation in the average of the measurements made by
> **different appraisers** using the **same measuring instrument** when measuring the identical
> characteristic on the **same part**."

**Correction (#223, audit A10-a):** this entry previously cited "Section 3.2, Equation 3.2.2" and
quoted *"Reproducibility measures variation due to different appraisers (or operators)."* — a
**fabricated** quotation under a locator scheme the 4th Edition does not use. The replacement above
is strictly better evidence than the sentence it removes: the old quote did not mention the
`− EV²/(nr)` adjustment at all, so it never actually supported the formula it was attached to.

**Rationale:**
- The range of appraiser averages (Xdiff) captures the appraiser-to-appraiser spread.
- K2 converts that to a sigma estimate.
- The subtraction `− (EV² / (n_parts × n_trials))` removes the **repeatability component** already captured in EV.
  This ensures AV reflects **only** the appraiser difference, not equipment noise — AIAG's
  "contaminated by the equipment variation" sentence above is the justification for it.
- If the subtraction yields a negative value (rare, high EV), clamp AV to 0 (numerical artifact) —
  AIAG states this clamp explicitly; see RULE 14.

**Worked example (AIAG canonical 10×3×3 study):**
- Xdiff = 0.445, appraisers = 3, K2(3) = 0.5231, EV = 0.202, n_parts = 10, n_trials = 3.
- AV = sqrt((0.445 × 0.5231)² − 0.202² / 30) = sqrt(0.054186 − 0.001360) ≈ 0.230
  (AIAG-published AV = 0.22963).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (lines computing `av`)

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 5 — GR&R (AIAG MSA, 4th Edition, Ch. III Sec. B)

**Decision:** Compute **Gage Repeatability & Reproducibility** as:
```
GR&R = sqrt(EV² + AV²)
```

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Analysis of Results — Numerical":

> "The measurement system variation for repeatability and reproducibility (*GRR* or σ*M*) is
> calculated by adding the square of the equipment variation and the square of the appraiser
> variation, and taking the square root as follows:"

Chapter I, Section E states the same thing in variance terms: *"GRR is the variance equal to the sum
of within-system and between-system variances."*

**Correction (#223, audit A10-a):** previously cited "Section 3.2, Equation 3.2.3" with the
**fabricated** quotation *"The total measurement system variation is the combination (square root of
sum of squares) of repeatability and reproducibility."* The phrase "square root of sum of squares"
does not occur anywhere in the manual. The formula is unchanged and is now quoted from the manual's
own wording.

**Rationale:**
- EV and AV are independent sources of variation.
- RSS (root sum of squares) combines independent variances: σ_total = sqrt(σ_ev² + σ_av²).

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (line computing `grr`)

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 6 — Part Variation / Total Variation (AIAG MSA, 4th Edition, Ch. III Sec. B)

**Decision:** Estimate **Part Variation (PV)** and **Total Variation (TV)** as:
```
PV = Rp × K3(parts)
where Rp = range of part means
TV = sqrt(GRR² + PV²)
```

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Analysis of Results — Numerical," and
the Gage R&R report form:

> "The part variation (part-to-part; part variation without measurement variation) (*PV* or σ*P*)
> is determined by multiplying the range of part averages (*Rp*) by a constant (*K3*)."

> "The total variation (*TV* or σ*T*) from the study is then calculated by summing the square of both
> the repeatability and reproducibility variation and the part variation (*PV*) and taking the square
> root as follows:"

**Correction (#223, audit A10-a):** previously cited "Section 3.2, Equation 3.2.4" with the
**fabricated** quotation *"Part variation represents the true part-to-part spread; total variation
combines measurement system variation (GRR) with part variation."* Both formulas were correct; only
the evidence for them was invented. They are now quoted from the manual.

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

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 7 — %GRR vs Study Variation (AIAG MSA, 4th Edition, Ch. III Sec. B / Ch. II Sec. D)

**Decision:** Compute **%GRR vs Study Variation** as:
```
%GRR_study = (GR&R / TV) × 100
```

**Source — the index:** AIAG MSA (4th Edition), Chapter III, Section B, "Indices," which gives the
`100[component/TV]` form and extends it to the other components:

> "The percent the equipment variation (*%EV*) consumes of the total variation (*TV*) is calculated
> by 100[*EV/TV*]. The percent that the other factors consume of the total variation can be
> similarly calculated as follows:"

Since #225 that "similarly calculated as follows" is carried out in full: the study basis is computed
for **all four** components (%EV, %AV, %GRR, %PV), not %GRR alone. The per-component formulas and
their locator in the completed Gage R&R report form are recorded in **RULE 16**.

**Source — the bands:** Chapter II, Section D, **Table II-D 1 "GRR Criteria."** Its lead-in reads
*"For measurement systems whose purpose is to analyze a process, a general guidelines [sic — the
manual's own grammar] for measurement system acceptability is as follows:"*, and the table gives:

| GRR | Decision |
|---|---|
| "Under 10 percent" | "Generally considered to be an acceptable measurement system." |
| "10 percent to 30 percent" | "May be acceptable for some applications" |
| "Over 30 percent" | "Considered to be unacceptable" |

**Correction (#223, audit A10-a):** previously cited "Section 3.3, 'Measurement System Acceptability
Criteria.'" That locator scheme does not exist in the 4th Edition and no section carries that title;
the interpretation bands below were left unlocated. Both are now pinned to the real passages above.

**Interpretation:**
- **< 10%:** Measurement system is excellent; variation is negligible vs part variation.
- **10–30%:** Marginal; acceptable for some uses.
- **> 30%:** Inadequate; measurement system must be improved.

**Rationale:**
- %GRR_study indicates how much of the **total observed variation** is measurement noise.
- If GRR is much smaller than TV, the system can discriminate between parts reliably.
- If `TV <= 0` (degenerate zero-variation study), %GRR_study is `inf`.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (the `tv > 0` block computing
`pev_study` / `pav_study` / `pgrr_study` / `ppv_study`)

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 8 — %GRR vs Tolerance (AIAG MSA, 4th Edition, Ch. III Sec. B)

**Decision:** Compute **%GRR vs Tolerance** (if tolerance is provided) as:
```
%GRR_tolerance = (6 × GR&R / Tolerance) × 100      where Tolerance = USL − LSL
```

**Source:** AIAG MSA (4th Edition), Chapter III, Section B — the tolerance-basis paragraph quoted
verbatim under "Provenance of the 6" below (alternative criterion).

**Locator correction (#223, audit A10-a):** this line previously read "Section 3.3, 'Measurement
System Acceptability Criteria' (alternative criterion)" — a stale locator left behind when #217
upgraded the body of this rule to the primary source. The 4th Edition has no `Section 3.x` scheme
and no section by that title; the body's Chapter III, Section B citation was already correct.

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

## RULE 9 — Number of Distinct Categories (ndc) (AIAG MSA, 4th Edition, Ch. III Sec. B / Ch. II Sec. D)

**Decision:** Compute **Number of Distinct Categories** as:
```
ndc = trunc(1.41 × (PV / GR&R))
```

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Analysis of Results — Numerical," which
defines what ndc *is*:

> "The final step in the numerical analysis is to determine the number of distinct categories that
> can be reliably distinguished by the measurement system. This is the number of non-overlapping 97%
> confidence intervals that will span the expected product variation."

and, immediately after the formula, how it is reduced to an integer:

> "For analysis, the *ndc* is the maximum of one or the calculated value truncated to the integer.
> This result should be greater than or equal to 5."

Chapter II, Section D, under "Additional Width Error Metric," states the same acceptance rule:

> "This statistic indicates the number of categories into which the measurement process can be
> divided. This value should be greater than or equal to 5."

The `1.41 × PV / GRR` form is the manual's own: its glossary entry for *ndc* reads
*"Number of distinct categories. 1.41 PV/GRR"*. Verified directly against the primary manual on
2026-07-19 (SME: Sid).

**Correction (#223, audit A10-a):** previously cited "Section 3.3, Equation 3.3.2" with the
**fabricated** quotation *"ndc indicates how many distinct measurement categories can be reliably
distinguished across the observed part variation."* That sentence is a paraphrase of the real
definition above and appears nowhere in the manual.

**Note (correction, W08-2):** ndc is driven by **Part Variation (PV)**, not tolerance. It is
computed unconditionally, whether or not a tolerance is supplied — a study with no tolerance can
still report a real ndc and reach Accept/Marginal, not just Reject.

**Acceptance criterion — what AIAG actually says:**
- **ndc ≥ 5:** Adequate. This is AIAG's *only* published ndc criterion (Ch. II Sec. D; Ch. III
  Sec. B). It is a single pass/fail threshold, not a graded scale.

**Sub-bands below 5 — NOT in AIAG MSA; internal design choice (#223, audit A10-a):**
- **ndc 2–4:** Marginal (only 2–4 levels detectable).
- **ndc < 2:** Reject (cannot distinguish one part from another at all).

**Source:** Not in AIAG MSA; internal design choice built on AIAG's single `ndc ≥ 5` rule. The
manual gives no band between 5 and zero. These two sub-bands were previously printed under an
"**Acceptance Criterion (AIAG):**" heading, which attributed them to a standard that does not state
them. The verdict logic is **unchanged** — only the attribution is corrected.

**Rationale for the sub-bands:** AIAG's `≥ 5` alone maps every failing study to one outcome, which
would make the verdict blind to the difference between a system that resolves four categories and
one that resolves none. `ndc < 2` means the system cannot separate any two parts in the study, so it
is treated as a hard reject; `2–4` is reported as Marginal rather than Reject so a borderline system
is flagged for improvement instead of condemned. Both are this platform's choices and neither
loosens AIAG's rule: nothing below `ndc = 5` is ever reported as Accept.

**Rationale for AIAG's own threshold:**
- ndc ≥ 5 is a conservative heuristic meaning the measurement system can resolve at least 5
  meaningful steps within the **observed part variation** — ndc is PV-driven, not tolerance-driven
  (see the W08-2 correction note above; this sentence previously said "within the tolerance",
  contradicting it).
- This ensures that accept/reject decisions are not frequently reversed due to measurement noise.

**UI/export drift (#237):** `pages/gage_study.py` renders these sub-bands under an "AIAG Acceptance
Criteria" subheader and `exporter.py`'s `VERDICT_SENTENCES` repeats them. Those strings carry the
same misattribution and are **deliberately not changed here** (they would churn
`test_pages_gage_study.py` and `test_exporter.py`); they are tracked as **#237**.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_compute_ndc()` and used in `_compute_verdict()`

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 10 — Verdict (AIAG %GRR bands + platform ndc bands)

**Decision:** Assign a **verdict** (Accept / Marginal / Reject) from ndc and %GRR. The two columns
have **different provenance** and the matrix now says which is which:

| ndc | ndc source | %GRR | %GRR source | Verdict | Action |
|-----|------------|------|-------------|---------|--------|
| ≥ 5 | **AIAG** — Ch. II Sec. D | < 10% | **AIAG** — Table II-D 1 | **Accept** | Measurement system is adequate for the intended use. |
| 2–4 | *platform* (RULE 9) | 10–30% | **AIAG** — Table II-D 1 | **Marginal** | Acceptable for some uses; consider improvement plans. |
| < 2 | *platform* (RULE 9) | > 30% | **AIAG** — Table II-D 1 | **Reject** | Measurement system is inadequate and must be improved. |

**Source (%GRR bands):** AIAG MSA (4th Edition), Chapter II, Section D, **Table II-D 1 "GRR
Criteria"** — `"Under 10 percent"` / `"10 percent to 30 percent"` / `"Over 30 percent"`, quoted in
full under RULE 7 and RULE 8.

**Source (ndc ≥ 5):** AIAG MSA (4th Edition), Chapter II, Section D — *"This value should be greater
than or equal to 5."*

**Source (ndc 2–4 and ndc < 2):** **Not in AIAG MSA; internal design choice.** See RULE 9.

**Correction (#223, audit A10-a):** this rule previously cited "Section 3.3, 'Acceptability Criteria
& Guidelines'" — a locator scheme and a section title that do not exist in the 4th Edition — and its
matrix presented the whole ndc column as AIAG's. Only the `≥ 5` row is. **The verdict logic is
unchanged**; the matrix now attributes each column to its actual source.

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

Where this *does* deviate from AIAG is the choice of basis, not the bands: **Chapter I, Section B**
picks the basis by purpose —

> "For product control, variability of the measurement system must be small compared to the
> specification limits. Assess the measurement system to the feature tolerance."

> "For process control, the variability of the measurement system ought to demonstrate effective
> resolution and be small compared to manufacturing process variation. Assess the measurement system
> to the 6-sigma process variation and/or Total Variation from the MSA study."

The engine has no purpose input, so it takes the worse of the two — a deliberate conservative
deviation, documented in the SME note above.

**Locator correction (#223, audit A10-a):** the preceding paragraph previously attributed the
basis-by-purpose rule to **Ch. II §C**. Chapter II, Section C is "Preparation for a Measurement
System Study" and says nothing of the kind; the rule is in Chapter I, Section B, now quoted above.
The claim was true, the pointer was wrong.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` computes the effective
`verdict_pgrr` (the `max()` above) and passes it as the sole `pgrr` argument to
`_compute_verdict(ndc, pgrr)`, which applies only the ndc/threshold logic.

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 11 — Balanced Data Requirement (inference from AIAG's procedure; not an AIAG statement)

**Decision:** Require **balanced crossed data** for the Average-and-Range method:
- Every part measured by every appraiser the same number of times.
- If data is unbalanced, raise a clear error (W08-2) or log a warning and proceed with common subset (W09+ improvement).

**WITHDRAWN QUOTATION (#223, audit A10-a).** This rule previously read (shown as an exhibit, not a
citation — see the blockquote convention at the top of this file):

```
Source: AIAG MSA (4th Edition), Section 3.1, "Assumptions of the Average-and-Range Method."
"The method assumes a fully replicated crossed design: each part x each appraiser x each trial."
```

**All three parts of that citation are fabricated.** The 4th Edition has no `Section 3.x` numbering
scheme, no section titled "Assumptions of the Average-and-Range Method," and no such sentence — the
word "crossed" does not occur anywhere in the manual. The quotation is withdrawn in full and is
**not** replaced by another quotation, because no passage states this requirement.

**Status: procedure-derived inference — NOT an AIAG statement.** The requirement is kept, and the
reasoning below is this platform's, not AIAG's. AIAG never *asserts* that the Average-and-Range
method requires balance; it *prescribes a procedure that is balanced by construction* and gives no
procedure for anything else. The engine's requirement is inferred from that. A reader should treat
the following as the argument for a design decision, not as a rule quoted from a standard.

**Supporting passages (support for the inference, not statements of it):**

1. **Chapter III, Section A, "Example Test Procedures"** — the preconditions on the whole family of
   procedures. *"The procedures are appropriate to use when:"* … *"Only two factors or conditions of
   measurement (i.e., appraisers and parts) plus measurement system repeatability are being
   studied"*. A two-factor-plus-replication design with every cell filled is exactly a balanced
   crossed layout.
2. **Chapter III, Section B, "Conducting the Study,"** steps 1–7 — every step has each appraiser
   measure *the same* parts *the same* number of times: *"Let appraiser A measure n parts in a random
   order"*; *"Let appraisers B and C measure the same n parts without seeing each other's readings"*;
   *"If three trials are needed, repeat the cycle and enter data in rows 3, 8 and 13."* No step
   contemplates a cell with a different number of trials, and the data sheet has no place to record
   one.
3. **Footnote 44** — *"The total number of 'ranges' generated ought to be > 15 for a minimal level of
   confidence in the results."* The range count is `n_parts × n_appraisers` only when every cell is
   filled; on unbalanced data the manual's own confidence guidance stops being computable as stated.

**Rationale (internal, not AIAG):**
- The K constants are `1/d2*` values, and `d2*` is tabulated by subgroup size `m` and subgroup count
  `g` (Appendix C). Unequal cell sizes leave no single `m` to look up, so the K-table step of the
  method has no defined answer on unbalanced data. This is the load-bearing reason.
- Refusing is a deliberate choice over silently analysing a common subset: dropping measurements
  would change the study the user thinks they ran without telling them.
- The ANOVA method handles unbalanced data properly and is the correct upgrade path. **#195 landed
  ANOVA (`method="anova"`, RULE 17) but only for balanced studies** — the balance check runs ahead of
  the method dispatch and rejects unbalanced data for both methods. Extending ANOVA to unbalanced
  designs remains open work; nothing in this engine analyses an unbalanced study today.

*(The previous rationale also claimed "unbalanced data violates the normality assumptions." That
conflates balance with normality — they are independent — and was uncited. Removed.)*

**Current Implementation (W08-2):**
- Check if every (part, appraiser) pair has the same number of trials.
- If yes, proceed (set `is_balanced = True`).
- If no, raise `ValueError` with a clear message.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (balance check)

**Verified:** the three supporting passages above are checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid) and pinned in `CITATIONS.tsv`.
The *requirement itself* is this platform's inference from them and carries no AIAG quotation.

---

## RULE 12 — Minimum Study Size (deliberate relaxation of AIAG's recommendation)

**Decision:** Enforce **minimum study sizes** that are **looser than AIAG recommends**:
- At least **2 parts** (AIAG recommends `n ≥ 10`).
- At least **2 appraisers** (AIAG's procedure uses 3: appraisers A, B, C).
- At least **2 trials** (AIAG's procedure uses up to 3) per (part, appraiser) pair.

**WITHDRAWN QUOTATION (#223, audit A10-a).** This rule previously read (exhibit, not a citation):

```
Source: AIAG MSA (4th Edition), Section 3.1, "Recommended Study Design."
"A typical crossed study for Gage R&R is 10 parts x 3 appraisers x 3 trials = 270 measurements.
 Smaller studies are possible but less statistically robust."
```

**Fabricated, and self-evidently so:** the 4th Edition has no `Section 3.x` scheme and no
"Recommended Study Design" section, the sentence appears nowhere in the manual — and 10 × 3 × 3 = 90,
not 270. The arithmetic error is the tell: a number copied from a real source would have been right.

**What AIAG actually recommends** — Chapter III, Section B, "Conducting the Study":

> "Although the number of appraisers, trials and parts may be varied, the subsequent discussion
> represents the optimum conditions for conducting the study."

> "Obtain a sample of *n* ≥ 10 parts that represent the actual or expected range of process
> variation."

and footnote 44:

> "The total number of 'ranges' generated ought to be > 15 for a minimal level of confidence in the
> results. Although the form was designed with a maximum of 10 parts, this approach is not limited by
> that number. As with any statistical technique, the larger the sample size, the less sampling
> variation and less resultant risk will be present."

**Source of the 2/2/2 minimums:** **Not in AIAG MSA; internal design choice.** They are a deliberate
platform relaxation, not a standard. The engine's floor is the point below which the arithmetic has
no answer at all — not the point above which the answer is trustworthy.

**Why relax, stated plainly:** 2/2/2 is the *computability* floor, not a quality bar. A 2 × 2 × 2
study generates 4 ranges, well under footnote 44's `> 15`, so its EV/AV/GRR are statistically weak
even though they are arithmetically well-defined. The engine accepts such a study so a user can run
a trial or a teaching example without fabricating eight parts they do not have; it does **not** claim
such a study meets AIAG's recommendation. Note that AIAG's own text explicitly permits varying the
counts ("may be varied") while naming 10/3/3 as the *optimum* — so a smaller study is not
non-conforming, it is sub-optimal, and the user should read a small-study verdict accordingly.

**Current Implementation (W08-2):**
- Enforce minimums: 2 parts, 2 appraisers, 2 trials per pair. **Unchanged by #223** — this rule's
  correction is to its documentation, not its validation.
- The bundled template (`data/gage_rr_template.csv`) uses AIAG's recommended 10 × 3 × 3 design, so
  the documented happy path is the standard-conforming one.
- The K3 table is only tabulated to 10 parts, so studies above that raise `ValueError` (RULE 2) —
  an independent ceiling from this floor.

**Rationale for the floor itself:**
- Fewer than 2 parts or appraisers: no variation to measure.
- Fewer than 2 trials per cell: cannot compute a range within the cell, so EV is undefined.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (validation checks)

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## RULE 13 — Edge Case: All Measurements Identical (TV = 0)

**Decision:** If all part averages are identical (e.g., all measurements = 10.05):
- PV = 0, GRR = 0 (EV = AV = 0), so TV = sqrt(GRR² + PV²) = 0.
- %GRR_study = ∞ (GRR / 0).
- Verdict = "Reject" (measurement system cannot discriminate).

**Source:** **Not in AIAG MSA; internal design choice.** The manual has no passage on a
zero-total-variation study, so there is nothing to cite. The rationale below is this platform's.

**Attribution correction (#223, audit A10-a):** this line previously read *"AIAG MSA (4th Edition),
implicit."* — a non-citation dressed as one. "Implicit" names no chapter, no section and no text; it
borrows the standard's authority for a claim the standard does not make. The decision is unchanged.

**Rationale:**
- A measurement system that sees no variation cannot demonstrate that it is adequate.
- This case is rare in practice (all parts truly identical is uncommon) but can occur in test scenarios.
- The verdict "Reject" is conservative and appropriate: a system that cannot detect any part variation is unusable.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_compute_verdict()` (check `np.isfinite(pgrr)`)

---

## RULE 14 — Edge Case: Negative AV² (AIAG MSA, 4th Edition, Ch. III Sec. B)

**Decision:** If AV² becomes negative (due to high EV relative to appraiser variation):
- Clamp AV to 0.
- Log a warning (optional; low priority for W08-2).

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Analysis of Results — Numerical." The
manual states this clamp explicitly, immediately after giving the AV formula:

> "If a negative value is calculated under the square root sign, the appraiser variation (*AV*)
> defaults to zero."

**Attribution upgrade (#223, audit A10-a):** this entry previously read *"AIAG MSA (4th Edition),
implicit."* It is not implicit — it is stated outright, one line below the formula RULE 4 cites.
The clamp at `av = float(np.sqrt(max(av_squared, 0)))` is exactly what the manual prescribes, so
this rule is now a real citation rather than an appeal to the standard's authority.

**Rationale:**
- This occurs when EV is very large compared to appraiser differences.
- Mathematically, it indicates that appraiser variation is below the noise floor; setting AV=0 is conservative.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_average_and_range_method()` (line: `av = float(np.sqrt(max(av_squared, 0)))`)

**Verified:** quotation checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02 (SME: Sid), and pinned in `CITATIONS.tsv`.

---

## Deviation from AIAG MSA: ndc Upper Clamp at 100

**Decision:** Cap `ndc` at 100 for rendering and storage purposes (UI/JSON display).

**Source:** Not in AIAG MSA; internal design choice.

**Rationale:**
- In theory, ndc can be arbitrarily large (e.g., if GRR is very small and tolerance is large).
- For UI rendering and JSON APIs, a large ndc (e.g., 10,000) is not actionable; capping at 100 signals "more than adequate."
- ndc ≥ 5 is the AIAG acceptance criterion; anything above that is acceptable, so capping at 100 does not affect verdicts.

**Lower bound resolution — #224 (audit A10-b):** AIAG MSA 4th Edition (Chapter III, Section B, line 3427) specifies: *"For analysis, the ndc is the maximum of one or the calculated value truncated to the integer."* `_compute_ndc()` was updated in #224 to floor at `1` for valid positive inputs (`grr > 0` and `pv > 0`), while non-positive inputs (`grr <= 0` or `pv <= 0`) return `0`.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_compute_ndc()` (line: `return max(1, min(ndc_int, 100))`)

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

## RULE 16 — %EV / %AV / %PV on both bases (#225, audit A10-c: hypothesis refuted, scope gap closed)

**Decision:** Compute and report **all four** AIAG percentages on **both** bases — study variation
(`100 × component / TV`) and tolerance (`component × 6 / tolerance × 100`) — as the key family
`p{ev,av,grr,pv}_{study,tolerance}`. `%GRR` on both bases is unchanged and stays governed by
**RULE 7** (study) and **RULE 8** (tolerance); this rule covers the three components added for the
first time here: %EV, %AV, %PV.

**Source:** AIAG MSA (4th Edition), Chapter III, Section B, "Indices." The completed **Gage
Repeatability and Reproducibility Report** (Figure III-B 16) carries the four formulas verbatim:

> "*%EV*= 100 [*EV/TV*]"
> "*%AV*= 100 [*AV/TV*]"
> "*%GRR*= 100 [*GRR/TV*]"
> "*% PV*= 100 [*PV/TV*]"

The space in `% PV` on the fourth line is AIAG's own, reproduced verbatim.

RULE 7's SRC:3401 blockquote supplies the generalising sentence ("The percent that the other factors
consume of the total variation can be similarly calculated as follows:") and RULE 8's SRC:3419
blockquote supplies the tolerance-denominator swap. Neither is re-quoted here.

**Correction of a round-1 research claim:** these per-component formulas were previously believed to
be images, because SRC 3403-3407 are blank. That is true of *that* location only — the formulas
extract as **text** from the report form at SRC:3285-3311 (blank form: SRC:5911/5915/5920/5924).
Recorded so a future reader does not re-inherit the false constraint. What remains **unquotable** from
that form: anything spanning two of its table rows — the flattener interleaves the K-constant cells, so
a cross-row concatenation is not verbatim text and must never be presented as a quotation.

**Numeric oracle (plain prose, not a quotation):** for the canonical 10×3×3 study reproduced at
`apps/msa/data/aiag_reference_study.csv`, AIAG's own completed form (Figure III-B 16, SRC:3285-3311)
publishes %EV = 17.62%, %AV = 20.04%, %GRR = 26.68%, %PV = 96.38% and TV = 1.14610. The engine
reproduces all five within rel = 1e-3; the assertions live in
`apps/msa/tests/test_gage_rr_engine.py`.

**Hypothesis (#225, audit A10-c) — REFUTED, not merely unverified.** #225 suspected that %EV, %AV and
%PV shared the missing-×6 tolerance denominator that #190 fixed for %GRR. They could not: they were
never computed. Surfaces checked 2026-08-02 against the primary manual — `gage_rr_engine.py`'s return
dict and `_average_and_range_method()`, `exporter.py` (`_detail_rows`, `export_results_csv`,
`export_pdf`), `pages/gage_study.py`, `schema.py`, `quality_core`, root `app.py` and
`secom_app/msa.py`; a repo-wide grep for `%EV`/`%AV`/`%PV`/`pct_*` identifiers returned no code match,
only doc prose. **This PR closes the scope gap that made the question askable** — the ×6 guard is now
an implemented, test-enforced invariant rather than a note to a future reader. Do not reintroduce a
tolerance-basis percentage that bypasses it.

**The guard (now enforced):** every tolerance-basis figure routes through `_STUDY_VARIATION_SIGMA` on
its **own** line. A literal `6.0`, a literal `6`, or a factored-out scale variable in any of the four
is forbidden — it would reintroduce #190's 6× understatement, and in three more places than before.
`test_tolerance_basis_routes_through_study_variation_sigma` fails if the constant is bypassed.

**Degenerate case:** `TV == 0` → all four study-basis figures are `inf`, consistent with `pgrr_study`
and RULE 13; the verdict stays "Reject". The tolerance basis has no degenerate case (`tolerance` is
validated positive and finite on entry), so no guard is added for it. **%PV vs tolerance may exceed
100%** (149.95% for the reference study) and is deliberately **unclamped**: it is a ratio to a spec
width, not a share of a total.

**Verdict unchanged:** the six new figures are **reporting-only**. `_compute_verdict()` remains driven
by `ndc` and the worse of the two %GRR figures (RULE 10, SME resolution W08-2). No input produces a
different verdict than before this change.

**Not a deviation:** AIAG's *"Either or both approaches can be taken depending on the intended use of
the measurement system and the desires of the customer"* (SRC:3419, quoted under RULE 8) places
reporting both bases squarely within the standard.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `compute_gage_rr()` (the `tv > 0` block and the
`tolerance is not None` block); `apps/msa/msa_app/exporter.py` → `_detail_rows()`,
`export_results_csv()`; `apps/msa/msa_app/pages/gage_study.py` → the results metrics block. Amends
RULE 15's results-CSV payload list, which now carries all eight percentages (RULE 15's own text is
left unedited).

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-02, and pinned in `CITATIONS.tsv`.

---

## RULE 17 — ANOVA Method: interaction term, F-test and pooling (#195)

**Decision:** Implement AIAG's **ANOVA method** for crossed studies as an opt-in second technique,
`compute_gage_rr(..., method="anova")`. It estimates the part × appraiser interaction, tests it, and
either pools it into repeatability or carries it into `GRR = sqrt(EV² + AV² + INT²)`. RULE 1's
Average-and-Range stays the default; no existing call site changes behaviour.

**Source:** AIAG MSA (4th Edition), **Chapter III, Section B**, "Analysis of Variance (ANOVA) Method"
and **Appendix A**, "Analysis of Variance Concepts" (Tables A 1 – A 5). *(The #195 issue body cited
"§3"; the 4th Edition has no such locator — see the note on locators at the top of this file.)*

**Sums of squares.** The classical crossed two-factor decomposition with replication, for `n` parts,
`k` appraisers and `r` trials per cell — Table III-B 7 is computed "assuming a balanced two-factor
factorial design":

> "Table III-B 7 shows the ANOVA calculations for the example data from Figure III-B 15 assuming a
> balanced two-factor factorial design. Both factors are considered to be random."

```
SS_total = Σ(y − ȳ)²                  df = nkr − 1
SS_parts = kr·Σ(part̄ − ȳ)²            df = n − 1
SS_appr  = nr·Σ(appr̄ − ȳ)²            df = k − 1
SS_cells = r·Σ(cell̄ − ȳ)²             (cell = part × appraiser)
SS_AxP   = SS_cells − SS_parts − SS_appr    df = (n−1)(k−1)
SS_e     = SS_total − SS_cells              df = nk(r−1)
MS_x     = SS_x / df_x
```

**Only the interaction gets an F-ratio.** This is AIAG's own restriction, and it is why no
significance test is computed for the appraiser or parts rows:

> "The _F-ratio_ column is calculated only for the interaction in a MSA ANOVA; it is determined by the
> mean square of interaction divided by mean square error."

**Significance level: α = 0.05 — a convention, NOT an AIAG requirement.** The manual states no
numeric recommendation. It gives a *direction* only:

> "In order to decrease the risk of falsely concluding that there is no interaction effect, choose a
> high significance level."

and its own worked example (Table A 4) is footnoted:

> "* Significant at α = 0.05 level"

0.05 is therefore the only level evidenced in the primary source, and it is what this engine uses
(`_ANOVA_ALPHA`). **AIAG does not mandate a significance level**, and a looser level (0.20–0.25) is a
third-party convention this repo does not cite as AIAG's. SME decision, 2026-08-07: hardcode 0.05,
document it as the manual's worked-example convention, and expose **no** `alpha=` parameter — a
consumer who needs a different level reads `interaction_f` from the payload and decides for itself.
*The canonical study cannot validate this choice:* its interaction F is 0.4337 (p ≈ 0.98), which pools
at any conventional α. α only changes behaviour on other data.

**Auto-pooling when the interaction is not significant.** The interaction F statistic is compared to
`scipy.stats.f.ppf(1 − α, df_AxP, df_e)`. When it does not exceed that critical value, the manual's
additive model applies:

> "In the additive model, the interaction is not significant and the variance components for each
> source is determined as follow: First, the sum of square of gage error ( _SSe_ from Table A 3) is
> added to the sum of square of appraiser by part interaction ( _SSAP_ from Table A 3) and which is
> equal to the sum of squares pooled ( _SSpool_ ) with ( _nkr – n – k_ +1) degrees of freedom. Then
> the _SSpool_ will be divided by the ( _nkr – n – k_ +1) to calculate _MSpool_ ."

> "Since the calculated F value for the interaction (0.434) is less than the critical value of _F_ α
> **,** 18 **,** 60 , the interaction term is pooled with the equipment (error) term. That is,  the
> estimate of variance is based on the model without interaction."

with footnote 85: *"Where _n_ = number of parts, _k_ = number of appraisers and _r_ = number of
trials."* (`nkr − n − k + 1` is exactly `df_e + df_AxP`, which is how the code writes it.)

Pooling happens **automatically** (SME decision, 2026-08-07) because that is the manual's own
procedure and it is what reproduces the published numbers. It is not hidden: `interaction_f` and
`interaction_significant` are in the payload, so a consumer can always see whether pooling occurred.

**Variance components.** Table A 1 (non-additive, interaction significant) and the pooled additive
form:

| Component | Interaction significant (Table A 1) | Interaction pooled (additive) |
|---|---|---|
| EV² (equipment) | `MS_e` | `MS_pool` |
| INT² (interaction) | `(MS_AxP − MS_e) / r` | `0` |
| AV² (appraiser) | `(MS_A − MS_AxP) / (n·r)` | `(MS_A − MS_pool) / (n·r)` |
| PV² (part) | `(MS_P − MS_AxP) / (k·r)` | `(MS_P − MS_pool) / (k·r)` |

Table A 2 prints these as 6σ spreads (`EV = 6√MS_e`, etc.). This engine reports **1σ** components for
both methods and applies ×6 only on the tolerance basis, via the single `_STUDY_VARIATION_SIGMA`
constant (RULE 8 / #190) — the multiplier cancels out of `%GRR = GRR/TV` and `ndc = 1.41·PV/GRR`, and
ANOVA deliberately routes through the same one place rather than hardcoding a second `6`.
The interaction of part and appraiser is what makes the model non-additive:

> "If the interaction of part and appraiser is significant, then there exists a nonadditive model and
> therefore an estimate of its variance components is given."

**Negative variance components are clamped to zero** — AIAG's instruction, and the same treatment
RULE 14 already gives Average-and-Range's AV²:

> "For analysis purposes, the negative variance component is set to zero."

All four of EV², AV², PV², INT² are clamped: each is a difference (of mean squares, or of sums of
squares for equipment), so sampling variation — and, for `SS_e = SS_total − SS_cells`, floating-point
cancellation — can put any of them below zero.

**Degenerate case not covered by AIAG (internal decision):** if `MS_e = 0` (a perfectly repeatable
gage — every replicate in every cell identical) the F ratio `MS_AxP / MS_e` is undefined. This engine
then reports `interaction_f = inf` and treats the interaction as significant — any interaction is
infinitely large relative to zero error — and `interaction_f = 0.0`, not significant, when there is no
interaction. "No interaction" is judged against `_SS_CANCELLATION_FLOOR` (relative 1e-12), not against
literal zero: `SS_AxP = SS_cells − SS_parts − SS_appr` is a difference of large nearly-equal sums, so
an interaction-free study still leaves a residue of order `1e-16 × SS_total`, and treating that as an
interaction would flip the model to non-additive and put a noise-level term into GRR. AIAG says
nothing about either point; both are guards (against a `NaN` in the payload, and against
floating-point cancellation), not standard behaviour.

**Numeric oracle (plain prose, not a quotation).** For the canonical 10×3×3 study at
`apps/msa/data/aiag_reference_study.csv`, Table III-B 7 / Table A 4 publish SS = 3.1673 (appraiser),
88.3619 (parts), 0.3590 (interaction), 2.7589 (equipment), 94.6471 (total), with DF 2/9/18/60/89 and
interaction **F = 0.434**. Table III-B 8 / Table A 5 publish EV² = 0.039973 (σ = 0.199933),
AV² = 0.051455 (σ = 0.226838), INT = 0, GRR = 0.302373, PV² = 1.086447 (σ = 1.042327), TV = 1.085,
%EV 18.4, %AV 20.9, %GRR 27.9, %PV 96.0, and **ndc = 4**. The engine reproduces every one of these
(observed: F = 0.43372, EV = 0.1999332, AV = 0.2268375, INT = 0.0, GRR = 0.3023715, PV = 1.0423275,
TV = 1.0852996, %GRR 27.86, ndc 4, not significant → pooled). Note the manual's published values are
the **pooled** ones: the unpooled `MS_e = 0.045982` does not equal the published `EV² = 0.039973`,
while `MS_pool = 3.1179/78 = 0.039973` does — pooling is what makes the oracle reproducible.
Table III-B 9's own ANOVA-vs-Average-and-Range comparison (%GRR 27.9 vs 26.7 on this study) is the
manual's demonstration that the two methods agree to about a percentage point when the interaction is
not significant; they are not expected to agree exactly.

**Not implemented (deliberate scope, #195):** unbalanced designs (RULE 11 — the balance check runs
ahead of the method dispatch and applies to both methods); ANOVA output in the Excel/PDF/CSV exports
beyond the generic `method` / `method_note` rows they already carry; any UI selector. The
`interaction*` keys are payload-only.

**Applied In:** `apps/msa/msa_app/gage_rr_engine.py` → `_anova_method()`; the `method` dispatch and
`grr = sqrt(ev² + av² + interaction²)` in `compute_gage_rr()`; module constants `METHOD_ANOVA`,
`METHOD_NOTE_ANOVA`, `_ANOVA_ALPHA`; return keys `interaction` / `interaction_f` /
`interaction_significant`.

**Verified:** quotations checked verbatim against the primary manual
(`MSA_Reference_Manual_4th_Edition.md`) on 2026-08-07 and pinned in `CITATIONS.tsv`.

---

## Summary of Files & Code Pointers

| Assumption | Implemented In |
|-----------|---------------|
| Average-and-Range method (default) | `_average_and_range_method()` |
| ANOVA method / interaction F-test and pooling | `_anova_method()`; `METHOD_ANOVA` / `METHOD_NOTE_ANOVA` / `_ANOVA_ALPHA`; keys `interaction` / `interaction_f` / `interaction_significant` |
| Method declaration / un-estimated interaction | `compute_gage_rr()`, the `method` dispatch, keys `method` / `method_note`; `METHOD` / `METHOD_NOTE` |
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
| %EV / %AV / %PV vs study variation | `compute_gage_rr()`, keys `pev_study` / `pav_study` / `ppv_study` |
| %EV / %AV / %PV vs tolerance | `compute_gage_rr()`, keys `pev_tolerance` / `pav_tolerance` / `ppv_tolerance` (each `* _STUDY_VARIATION_SIGMA / tolerance`) |
