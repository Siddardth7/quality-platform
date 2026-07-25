# Engineering Assumptions Log
**Project:** SPC Manufacturing Quality Dashboard
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** June 15, 2026

This document records every non-obvious engineering decision — and every published
constant or threshold — used in the SPC app. Each entry explains what was chosen, why,
and where it is applied. It is the defense against any methodology question and the
reason a constant should never be edited in isolation.

---

## RULE 1 — X-bar / R Chart Constants (A2, D3, D4, d2)

**Decision:** Use the AIAG control-chart constants keyed by subgroup size `n` (2–10):
`A2` for the X-bar limits, `D4`/`D3` for the R-chart limits, and `d2` to estimate the
within-subgroup process sigma (`sigma_hat = Rbar / d2`).

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005), control-chart constants table.
These are the standard Shewhart constants derived from the distribution of the relative
range of normal samples.

**Formulas applied:** `UCL/LCL_x = Xbarbar ± A2·Rbar`; `UCL_r = D4·Rbar`,
`LCL_r = max(0, D3·Rbar)`; `sigma_hat = Rbar / d2`.

**Applied In:** `spc_app/spc_engine/constants.py::XBAR_R_CONSTANTS` →
`control_charts.py::compute_xbar_r`.

---

## RULE 2 — X-bar / S Chart Constants (A3, B3, B4, c4)

**Decision:** Use the AIAG X-bar/S constants keyed by subgroup size `n` (2–12): `A3` for
the X-bar limits, `B4`/`B3` for the S-chart limits, and `c4` to estimate sigma
(`sigma_hat = Sbar / c4`). X-bar/S is preferred over X-bar/R for larger subgroups (n > ~10)
because the sample standard deviation uses all observations, not just the range.

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005), X-bar/S constants table. `c4` is the
unbiasing constant for the sample standard deviation of a normal sample.

**Formulas applied:** `UCL/LCL_x = Xbarbar ± A3·Sbar`; `UCL_s = B4·Sbar`,
`LCL_s = max(0, B3·Sbar)`; `sigma_hat = Sbar / c4`.

**Applied In:** `spc_app/spc_engine/constants.py::XBAR_S_CONSTANTS` →
`control_charts.py::compute_xbar_s`.

---

## RULE 3 — Individuals / Moving-Range Constants (E2, D4, d2)

**Decision:** For individuals data use a moving range of size 2 with `E2 = 2.660`,
`D4 = 3.267`, `d2 = 1.128`. Sigma is estimated from the average moving range
(`sigma_hat = MRbar / d2`).

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005), I-MR constants for moving-range
length 2. `E2 = 3 / d2(2)` gives 3-sigma individuals limits from the average moving range.

**Formulas applied:** `UCL/LCL_x = Xbar ± E2·MRbar`; `UCL_mr = D4·MRbar`, `LCL_mr = 0`;
`sigma_hat = MRbar / 1.128`.

**Applied In:** `spc_app/spc_engine/constants.py` (`IMR_E2`, `IMR_D4`, `IMR_D2`) →
`control_charts.py::compute_imr`.

---

## RULE 4 — Attribute Chart Limits (p, c, u)

**Decision:** Attribute charts use 3-sigma limits from their respective discrete
distributions, with the lower limit clamped at 0 (and the p-chart upper limit clamped at 1):

| Chart | Statistic | Sigma | Limits |
|-------|-----------|-------|--------|
| **p** | proportion defective | `sqrt(pbar·(1−pbar)/nᵢ)` (per-point, variable n) | `pbar ± 3·sigma`, clamped to [0, 1] |
| **c** | count per constant unit | `sqrt(cbar)` (constant) | `cbar ± 3·sqrt(cbar)`, LCL ≥ 0 |
| **u** | defects per unit | `sqrt(ubar/nᵢ)` (per-point) | `ubar ± 3·sigma`, LCL ≥ 0 |

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005). p/np from the binomial; c/u from the
Poisson. The c-chart requires a **constant area of opportunity** — hence the demo
`panel_defects` stream fixes the sample size at 1 inspected panel.

**Applied In:** `control_charts.py::compute_p / compute_c / compute_u`.

---

## RULE 5 — Capability Indices (Cp, Cpk, Pp, Ppk)

**Decision:** Report four capability indices using the standard definitions:

- `Cp  = (USL − LSL) / (6·sigma_hat)` — potential capability (within-subgroup spread)
- `Cpk = min((USL − mean)/(3·sigma_hat), (mean − LSL)/(3·sigma_hat))` — centered capability
- `Pp`, `Ppk` — same formulas using the **overall** sigma (sample standard deviation,
  `ddof=1`) instead of the within-subgroup `sigma_hat`.

`sigma_hat` (within) comes from the appropriate control chart (Rule 1–3); `sigma_overall`
is the ordinary sample standard deviation. Cp/Pp are reported only when **both** spec
limits are present; one-sided specs report only the relevant Cpk/Ppk side.

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005), process capability and performance
indices. The within-vs-overall distinction (Cp/Cpk vs Pp/Ppk) is the standard short-term
vs long-term capability split.

**Applied In:** `spc_app/spc_engine/capability.py::compute_capability`.

---

## RULE 6 — Capability Target (Cpk ≥ 1.33) and Interpretation Tiers

**Decision:** Use Cpk ≥ 1.33 as the "capable" target, with three interpretation tiers:

| Cpk | Interpretation |
|-----|----------------|
| `< 1.00` | Not capable |
| `1.00 – 1.32` | Marginal — reduce variation before release-critical use |
| `≥ 1.33` | Capable — common minimum target for stable manufacturing |

**Source:** Cpk ≥ 1.33 (= 4-sigma, ~63 ppm) is the widely adopted minimum capability target
across automotive and aerospace supplier quality systems (AIAG SPC; AS9100/IATF 16949
practice). 1.00 corresponds to the spec exactly spanning ±3 sigma.

**Applied In:** standards display in `apps/spc/app.py`; interpretation table in
`spc_app/pages/process_capability.py::CAPABILITY_REFERENCE`.

---

## RULE 7 — Capability Validity Requires a Stable Process (Stability Gate)

**Decision:** Before reporting Cp/Cpk/Pp/Ppk, run **Western Electric** rule detection on the
stream's control chart. If any out-of-control signal is present, show a prominent warning
that the indices are not valid until the process is stabilized (the numbers still render,
marked indicative only).

**Source:** AIAG SPC Reference Manual, 4th Ed. — capability indices assume the process is in
statistical control; computing them on an unstable process is misleading. WE rules are used
(rather than the fuller Nelson set) as the classic Shewhart out-of-control criterion, to
avoid over-flagging benign trend/alternating patterns.

**Applied In:** `spc_app/pages/process_capability.py::assess_control_chart`.

---

## RULE 8 — Western Electric and Nelson Run Rules

**Decision:** Detect special-cause patterns using the Western Electric rules (1–4) and the
Nelson rules (5–8), with sigma zones measured from the centerline:

- **WE 1:** 1 point beyond ±3 sigma
- **WE 2:** 2 of 3 consecutive beyond ±2 sigma on the same side
- **WE 3:** 4 of 5 consecutive beyond ±1 sigma on the same side
- **WE 4:** 8 consecutive points on the same side of the centerline
- **Nelson 5:** 6 consecutive points steadily increasing or decreasing
- **Nelson 6:** 14 consecutive points alternating up and down
- **Nelson 7:** 15 consecutive points within ±1 sigma of the centerline
- **Nelson 8:** 8 consecutive points outside ±1 sigma on both sides

**Source:** Western Electric *Statistical Quality Control Handbook* (1956) for rules 1–4;
L. S. Nelson, "The Shewhart Control Chart — Tests for Special Causes," *Journal of Quality
Technology* 16(4), 1984, for rules 5–8.

**Applied In:** `spc_app/spc_engine/rule_detection.py`.

---

## RULE 9 — Normality Check (Shapiro-Wilk, p > 0.05)

**Decision:** Flag the capability distribution as "approximately normal" when the
Shapiro-Wilk test p-value exceeds 0.05; otherwise warn that capability results may need
non-normal review.

**Source:** Shapiro & Wilk (1965), "An analysis of variance test for normality." The 0.05
significance level is the conventional default. Capability indices assume an approximately
normal distribution, so the check is advisory context for the Cpk numbers.

**Applied In:** `spc_app/spc_engine/capability.py::normality_test`.

---

## RULE 10 — Occurrence Ranking Table (SPC → FMEA candidate feedback) — AIAG-4 / SAE J1739, SME-confirmed

**Decision:** When an out-of-control signal fires on a Control Plan characteristic's
chart, map the observed OOC failing-rate (`violating_points / total_points`) onto a
10-band occurrence-ranking table to produce a **candidate** `suggested_occurrence`
(never auto-applied — human-in-the-loop). The ten rate bands encoded:

| Rank | Incident rate (upper bound) | Rank | Incident rate (upper bound) |
|------|------------------------------|------|------------------------------|
| 1 | ≤ 1 in 1,500,000 | 6 | 1 in 80 |
| 2 | 1 in 150,000 | 7 | 1 in 20 |
| 3 | 1 in 15,000 | 8 | 1 in 8 |
| 4 | 1 in 2,000 | 9 | 1 in 3 |
| 5 | 1 in 400 | 10 | ≥ 1 in 2 |

**Source:** **AIAG FMEA-4 (4th Ed., 2008) / SAE J1739 — Occurrence ranking table**, where
occurrence is keyed to the predicted rate of incidents per items/opportunities for a
cause. The ten values above are exactly that published table.

**Standard-edition note (SME-confirmed):** the harmonised AIAG-VDA FMEA Handbook (1st Ed.,
2019) does **not** define a numeric incident-rate occurrence table — its Occurrence rating
is qualitative, keyed to prevention-control effectiveness (verified July 2026 against
secondary summaries of the 2019 handbook; the 2019 O-table has no rate anchors). A rate→rank
mapping can therefore only be anchored to the legacy AIAG-4 / J1739 rate table, which is what
this rule cites and uses. `suggested_occurrence` is a **candidate** under that standard
(never auto-applied); a shop running pure AIAG-VDA 2019 Occurrence criteria treats it as
supporting SPC evidence for the analyst's control-based rating.

**Applied In:** `spc_app/fmea_feedback.py::_OCCURRENCE_BANDS`, `_rate_to_occurrence`.

---

## RULE 11 — Phase I/II Control-Limit Freezing (baseline minimums + frozen limits)

**Decision:** Split control charting into a Phase I (retrospective baseline) and Phase II
(fixed, "frozen" limits applied to future data) workflow:

- **Phase I baseline minimums (soft guardrail):** `MIN_BASELINE_SUBGROUPS = 25` for X-bar/R
  and X-bar/S; `MIN_BASELINE_INDIVIDUALS = 100` for I-MR. Falling below the floor sets
  `baseline_adequate = False` and a non-empty `baseline_note` in the returned `FrozenLimits`
  struct — it never raises. A thin baseline is weak evidence, not an invalid one, mirroring
  the Capability stability gate (Rule 7: warn, still render).
- **Exclusion requires a documented cause.** Removing an assignable-cause point from the
  baseline (`ExcludedPoint`) requires a non-empty `cause` string, and indices must be unique
  and in range; limits are then recomputed on the retained points — the Phase I
  signal -> documented cause -> remove -> recompute loop.
- **σ is still within-subgroup dispersion**, never pooled/global SD: `sigma_hat` in the
  frozen struct is Rbar/d2, Sbar/c4, or MRbar/d2, exactly as computed by the existing
  `compute_xbar_r/_s/_imr` (Rules 1–3) on the retained baseline — freezing reuses those
  functions rather than reimplementing limit math.
- **Phase II applies frozen limits, doesn't recompute them.** `compute_xbar_r/_s/_imr` accept
  an optional `frozen: FrozenLimits` argument; when supplied, the plotted statistics
  (subgroup means, ranges/std devs/moving ranges) still come from the new data, but the
  center line, dispersion center, sigma, and control limits come from the frozen struct.
  Limits must not float with new data. A guard rejects a frozen struct whose `chart_type` or
  subgroup size `n` doesn't match the new data.
- **`FrozenLimits` is the persistence contract.** It is an all-primitives `TypedDict`
  (JSON-serializable via `json.dumps`) — that serializability is the audit/persistence
  contract for this feature. No disk/DB storage layer exists or is added.
- **Dates are ISO-8601 strings**, not `date` objects, so the struct stays JSON-clean.
  `frozen_at` auto-fills `datetime.now(UTC).isoformat()` when the caller omits it, since the
  engine has no authority over the Phase I calendar dates supplied by the caller.

**Source:**
- `MIN_BASELINE_SUBGROUPS = 25` — **NIST/SEMATECH e-Handbook §6.3.2.1**
  (`itl.nist.gov/div898/handbook/pmc/section3/pmc321.htm`): Shewhart's guidance is "a sequence
  of not less than twenty-five samples of size four that are in control." Primary source,
  quotable.
- `MIN_BASELINE_INDIVIDUALS = 100` — **Montgomery, *Introduction to Statistical Quality
  Control*, Ch. 6** (secondary / common-practice figure). No primary NIST quote for "~100
  individuals" was found this session — flagged as Montgomery-sourced, not NIST-quotable.
- Phase I (retrospective/iterative) vs Phase II (fixed limits) — Montgomery Ch. 5–6; the
  Phase I/Phase II terminology also appears explicitly in NIST §6.5.4.3 (multivariate); NIST's
  univariate sections call Phase I "retrospective."

**Applied In:** `spc_app/spc_engine/phase.py` (`freeze_xbar_r`, `freeze_xbar_s`, `freeze_imr`,
`FrozenLimits`, `ExcludedPoint`) → `spc_app/spc_engine/control_charts.py::compute_xbar_r/_s/_imr`
(`frozen=` parameter) → `spc_app/spc_engine/constants.py` (`MIN_BASELINE_SUBGROUPS`,
`MIN_BASELINE_INDIVIDUALS`).

---

*Sources referenced in this log:*
- *AIAG SPC Reference Manual, 4th Edition (2005) — control-chart constants, attribute charts, capability indices*
- *Western Electric — Statistical Quality Control Handbook (1956)*
- *L. S. Nelson — Journal of Quality Technology 16(4), 1984 — tests for special causes*
- *Shapiro, S. S. & Wilk, M. B. (1965) — An analysis of variance test for normality*
- *AIAG FMEA-4, 4th Ed. (2008) / SAE J1739 — Occurrence ranking table (rate bands, see Rule 10)*
- *NIST/SEMATECH e-Handbook of Statistical Methods, §6.3.2.1 & §6.5.4.3 — Phase I baseline size, Phase I/II terminology*
- *Montgomery, D. C. — Introduction to Statistical Quality Control, Ch. 5–6 — I-MR baseline size (secondary), Phase I/II framework*
