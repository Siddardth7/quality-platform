# Engineering Assumptions Log
**Project:** SPC Manufacturing Quality Dashboard
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** August 6, 2026

This document records every non-obvious engineering decision — and every published
constant or threshold — used in the SPC app. Each entry explains what was chosen, why,
and where it is applied. It is the defense against any methodology question and the
reason a constant should never be edited in isolation.

> **Where the code lives (audit A12, #205).** `constants.py`, `rule_detection.py` and
> `utils.py` were promoted out of `spc_app/spc_engine/` into **`quality_core/spc/`** so
> SECOM, the Control Plan app and the future API share one copy instead of importing
> sideways into this app. The `spc_app.spc_engine.*` modules of those three names are now
> **re-export shims** — edit the constant in `quality_core/spc/`, never in the shim. The
> "Applied In" lines below name the real home; `packages/quality-core/tests/
> test_spc_constants.py` pins the AIAG tables whole and
> `apps/spc/tests/test_spc_engine_shims.py` asserts the shims are the same objects, so a
> shadow copy fails rather than silently drifting. PR 2 of #205 promoted
> `control_charts.py`, `phase.py` and `stability.py`, and PR 3 promoted
> `capability.py`, all the same way (their `spc_app/spc_engine/` modules are shims
> too). `data_generator.py` is the one engine module that stays app-resident — it
> is the app's demo dataset, not shared standards math.

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

**Applied In:** `quality_core/spc/constants.py::XBAR_R_CONSTANTS` →
`quality_core/spc/control_charts.py::compute_xbar_r`.

---

## RULE 2 — X-bar / S Chart Constants (A3, B3, B4, c4)

**Decision:** Use the AIAG X-bar/S constants keyed by subgroup size `n` (2–12): `A3` for
the X-bar limits, `B4`/`B3` for the S-chart limits, and `c4` to estimate sigma
(`sigma_hat = Sbar / c4`). X-bar/S is preferred over X-bar/R for larger subgroups (n >= 10)
because the sample standard deviation uses all observations, not just the range. That
boundary is stated once, in `apps/controlplan/docs/ASSUMPTIONS_LOG.md` RULE 1 (which
`controlplan_app/connector.py::recommend_chart` implements as `2 <= n <= 9 -> Xbar-R`,
`n >= 10 -> Xbar-S`); this line is reworded from "n > ~10" to match it (OQ-1, #196). The
exact cell is still flagged there for primary-source (AIAG SPC 4th Ed.) confirmation.

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005), X-bar/S constants table. `c4` is the
unbiasing constant for the sample standard deviation of a normal sample.

**Formulas applied:** `UCL/LCL_x = Xbarbar ± A3·Sbar`; `UCL_s = B4·Sbar`,
`LCL_s = max(0, B3·Sbar)`; `sigma_hat = Sbar / c4`.

**Applied In:** `quality_core/spc/constants.py::XBAR_S_CONSTANTS` →
`quality_core/spc/control_charts.py::compute_xbar_s`.

---

## RULE 3 — Individuals / Moving-Range Constants (E2, D4, d2)

**Decision:** For individuals data use a moving range of size 2 with `E2 = 2.660`,
`D4 = 3.267`, `d2 = 1.128`. Sigma is estimated from the average moving range
(`sigma_hat = MRbar / d2`).

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005), I-MR constants for moving-range
length 2. `E2 = 3 / d2(2)` gives 3-sigma individuals limits from the average moving range.

**Formulas applied:** `UCL/LCL_x = Xbar ± E2·MRbar`; `UCL_mr = D4·MRbar`, `LCL_mr = 0`;
`sigma_hat = MRbar / 1.128`.

**Applied In:** `quality_core/spc/constants.py` (`IMR_E2`, `IMR_D4`, `IMR_D2`) →
`quality_core/spc/control_charts.py::imr_limits` → `quality_core/spc/
control_charts.py::compute_imr` and `secom_app/charts.py::control_chart_for_signal`.
`imr_limits` is the single place this formula is written (#205 PR 2).

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

**Applied In:** `quality_core/spc/control_charts.py::compute_p / compute_c / compute_u`.

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

**Applied In:** `quality_core/spc/capability.py::compute_capability`.

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
avoid over-flagging benign trend/alternating patterns. Same precondition, independently
verifiable: NIST/SEMATECH e-Handbook §6.1.6 — *"Process capability compares the output of an
in-control process to the specification limits"*
(https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm).

**Applied In:** `quality_core/spc/stability.py::assess_stability` (control-chart assembly +
WE detection) and `quality_core/spc/capability.py::compute_capability_study`
(`stable` / `stability_note` on `CapabilityStudy`). The Streamlit page
(`spc_app/pages/process_capability.py`) is now only a consumer — it holds the stream →
chart-type map and renders the warning.

**Note (2026-07-30, #191):** `stable` is tri-state `bool | None` — `None` means stability was
**not assessed** because no control-chart context was supplied, and is never defaulted to
`True` (that would fabricate a conformance claim). The engine does **not** derive the control
chart from the data: I-MR on a flattened subgrouped stream understates sigma and flips
verdicts, so the caller supplies the violation list. Indices are always returned (annotate,
do not block).

**Note (2026-07-30, #192):** the WE detector's 2σ/1σ same-side reading was corrected (RULE 8)
— WE 2/3 are now more sensitive (an opposite-side point no longer suppresses a genuine
same-side hit). Verified no stability-gate verdict changes on the demo dataset.

---

## RULE 8 — Western Electric and Nelson Run Rules (Two Separate Sets)

**Decision:** `rule_set` is a mutually exclusive selector (never both at once); each set is
detected and labelled as its **own**, complete, self-consistent numbering — the Nelson set
does **not** borrow Western Electric's labels or run length. Sigma zones are measured from the
centerline; both sets share the same zone/limit math (`_zone_violations`), differing only in
labels and the same-side run length:

**Western Electric (WE), 4 tests, run length 8:**
- **WE 1:** 1 point beyond ±3 sigma
- **WE 2:** 2 of 3 consecutive beyond ±2 sigma on the same side
- **WE 3:** 4 of 5 consecutive beyond ±1 sigma on the same side
- **WE 4:** 8 consecutive points on the same side of the centerline

**Nelson, 8 tests, run length 9 (its own numbering, per Nelson 1984):**
- **Nelson 1:** 1 point beyond ±3 sigma
- **Nelson 2:** 9 consecutive points on the same side of the centerline
- **Nelson 3:** 6 consecutive points steadily increasing or decreasing
- **Nelson 4:** 14 consecutive points alternating up and down
- **Nelson 5:** 2 of 3 consecutive beyond ±2 sigma on the same side
- **Nelson 6:** 4 of 5 consecutive beyond ±1 sigma on the same side
- **Nelson 7:** 15 consecutive points within ±1 sigma of the centerline
- **Nelson 8:** 8 consecutive points outside ±1 sigma on both sides

**Source:** ⚠️ **UNVERIFIED — third-party reproduction only for both sets.**
Western Electric *Statistical Quality Control Handbook* (1956), Part B — not in repo;
corroborated via NIST/SEMATECH e-Handbook §6.3.2
(`https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm`), which reproduces the WECO
rules as used here (beyond ±3σ; 2-of-3 beyond ±2σ; 4-of-5 beyond ±1σ; 8-in-a-row same side).
L. S. Nelson, "The Shewhart Control Chart — Tests for Special Causes," *Journal of Quality
Technology* 16(4), 1984, pp. 237-239 (DOI 10.1080/00224065.1984.11978921) — paywalled, not in
repo; the Test 1–8 numbering above was taken from a third-party reproduction citing pp. 238-239.

**Defect caught (2026-07-30, #192):** two bugs, both traced to the code contradicting this
log's own prior wording. (1) The same-side reading ("2 of 3 … **on the same side**") had been
implemented with an extra, unspecified condition requiring the *opposite* side to have zero
hits — `_count_same_side` returned `(positive >= n and negative == 0) or (negative >= n and
positive == 0)` instead of just `positive >= n or negative >= n`, so a single opposite-side
point silently suppressed a genuine same-side signal on WE 2/3 and (before this fix) on the
Nelson equivalents. (2) `detect_nelson_violations` started from `detect_we_violations`'s output
verbatim, so it emitted `"Western Electric Rule 1-4"` labels (including WE 4's **8**-in-a-row)
under the Nelson rule set, and never emitted Nelson's own Test 2 (**9**-in-a-row) at all —
structurally incoherent with a set that is supposed to be its own eight tests.

**Correctness guard:** `apps/spc/tests/test_rule_detection.py` — the F-03/F-04 regression block
(same-side fires with an opposite-side point present for WE 2/3; negative case for one-hit-per-
side; Nelson 8-in-a-row does not fire; Nelson 9-in-a-row fires as `"Nelson Rule 2"`; WE 4 still
fires at 8-in-a-row) plus the renumbered Nelson 3/4/5/6 tests and the DECISION-2 guard that no
`detect_nelson_violations` output starts with `"Western Electric"`. `apps/secom/tests/
test_charts.py` pins the SECOM default-ruleset (`"nelson"`) label change.

**Applied In:** `quality_core/spc/rule_detection.py`.

---

## RULE 9 — Normality Check (Shapiro-Wilk, p > 0.05)

**Decision:** Flag the capability distribution as "approximately normal" when the
Shapiro-Wilk test p-value exceeds 0.05; otherwise warn that capability results may need
non-normal review.

**Source:** Shapiro & Wilk (1965), "An analysis of variance test for normality." The 0.05
significance level is the conventional default. Capability indices assume an approximately
normal distribution, so the check is advisory context for the Cpk numbers.

**Applied In:** `quality_core/spc/capability.py::normality_test`.

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

**Applied In:** `quality_core/spc/phase.py` (`freeze_xbar_r`, `freeze_xbar_s`, `freeze_imr`,
`FrozenLimits`, `ExcludedPoint`) → `quality_core/spc/control_charts.py::compute_xbar_r/_s/_imr`
(`frozen=` parameter) → `quality_core/spc/constants.py` (`MIN_BASELINE_SUBGROUPS`,
`MIN_BASELINE_INDIVIDUALS`).

---

## RULE 12 — EWMA Chart (λ, L, time-varying limits)

**Decision:** `compute_ewma(values, mu0, sigma, lam, L)` implements the exponentially weighted
moving average chart on individuals, with `mu0`/`sigma` supplied as plain floats (an independent
Phase I estimate — never derived from the z-series itself):

- **Recursion:** `z_0 = λ·x_1 + (1−λ)·μ0`, `z_i = λ·x_i + (1−λ)·z_{i−1}`, with `z_0 = μ0` (the
  Phase I target), not `x_1`. `λ` defaults to `EWMA_DEFAULT_LAMBDA = 0.20` (range 0.05–0.40 in the
  tabulated pairings; usual practitioner range 0.2–0.3).
- **Exact time-varying variance**, not the asymptotic approximation: `Var(z_i) =
  σ²·(λ/(2−λ))·[1−(1−λ)^(2i)]`, so `UCL_i = μ0 + L·σ·sqrt(Var(z_i)/σ²)` and `LCL_i` symmetric —
  limits are deliberately tighter near point 1 and widen toward the asymptote `σ²·λ/(2−λ)`.
- **`EWMA_DEFAULT_L = 2.860`** is the L paired with λ=0.20 for ARL0 ≈ 370–500. `EWMA_L_BY_LAMBDA`
  documents five Lucas & Saccucci (1990) λ/L pairings for the same ARL0 target.
- **λ/L pairing is a soft-warn field, not a hard gate.** `EWMAResult` carries `pairing_adequate`
  and `pairing_note`: if the caller's `lam` matches a tabulated key (`abs(lam-key) <= 1e-9`) and the
  supplied `L` differs from the paired value by more than 0.01, `pairing_adequate=False` with an
  explanatory note (mirrors Rule 11's `baseline_adequate`/`baseline_note` pattern — never raises).
  An untabulated `lam` cannot be judged, so it defaults to `pairing_adequate=True`,
  `pairing_note=""` rather than a false warning. A practitioner may legitimately tune λ/L outside
  the table; this only flags the common L=3-with-small-λ mistake the issue called out.
- **Run-rules do not apply to EWMA** — the z-series is autocorrelated by construction (each point
  depends on all prior points), so only limit crossings signal here. Western Electric / Nelson rule
  gating on EWMA is out of scope (tracked separately as W10-5).

**Source:**
- **Recursion + λ default** — **NIST/SEMATECH e-Handbook §6.3.2.4** (primary, quoted verbatim:
  `EWMA_t = λY_t + (1−λ)EWMA_{t−1}`, `EWMA_0` = the Phase I target mean, "λ is usually set between
  0.2 and 0.3"). <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm>
- **Asymptotic variance** `σ²·λ/(2−λ)` — NIST §6.3.2.4 (primary).
- **Exact time-varying variance** `[1−(1−λ)^(2i)]` term — **Montgomery, *Introduction to
  Statistical Quality Control*, §9.2, eq. 9.25** (secondary; NIST states only the asymptotic form).
  Standard, universally reproduced.
- **λ/L pairings (`EWMA_L_BY_LAMBDA`, ARL0 ≈ 370–500)** — **Lucas & Saccucci (1990), *Technometrics*
  32(1), Table 3**, as reproduced in **Montgomery Table 9.11**. ⚠️ Primary source is paywalled —
  these five numeric pairings are checked against the Montgomery reproduction and the issue body,
  not the original Technometrics table cell-by-cell (same "secondary, not primary-quotable" flag
  Rule 11 used for the Montgomery individuals-baseline floor).

**Applied In:** `quality_core/spc/control_charts.py::compute_ewma` (`EWMAResult`),
`quality_core/spc/constants.py` (`EWMA_DEFAULT_LAMBDA`, `EWMA_DEFAULT_L`, `EWMA_L_BY_LAMBDA`),
`spc_app/visualizer.py::build_ewma_chart`.

---

## RULE 13 — CUSUM Chart (k, h, FIR head-start)

**Decision:** Tabular two-sided CUSUM on standardized individuals; `k=0.5` (=δ/2, 1σ target
shift), `h=5` decision interval in σ units, `C+`/`C−` positive-accumulator convention, optional
FIR seed `h/2` on both arms, run-length counters estimate shift onset. **No WE/Nelson run-rule
gating on CUSUM points** — the accumulators are autocorrelated by construction, so only `h`
crossings signal; run-rule gating for CUSUM is deferred to W10-5.

- **Recursion (standardized first):** `z_i = (x_i − μ0)/σ`; `C+_i = max(0, z_i − k + C+_{i-1})`,
  `C−_i = max(0, −z_i − k + C−_{i-1})`, seeded at `C+_0 = max(0, z_0 − k + seed)`,
  `C−_0 = max(0, −z_0 − k + seed)` where `seed = h/2` if FIR is enabled, else `0`. The `max(0, …)`
  reset barrier is mandatory on both arms every step.
- **`C−` is a positive accumulator**, not a running negative sum — `max(0, −z − k + …)`. A sign
  flip here would silently disable the lower-arm test. The visualizer negates `C−` for display
  only (Montgomery Fig. 9.2 two-sided style, C+ up / −C− down, decision lines at both `+h` and
  `−h`); the stored series in `CUSUMResult` always stays the positive accumulator.
- **FIR (fast initial response):** an optional 50% head-start (`h/2`) applied to both arms at
  `i=0`, decaying back toward 0 on on-target data within a few points — it shortens detection of a
  shift present at start-up without permanently inflating the accumulator when the process is
  on-target.
- **Run-length counters** (`n_plus`/`n_minus`) count consecutive periods since the corresponding
  arm last rose above 0, resetting to 0 whenever the arm resets — used to estimate shift onset.

**Source (with the primary-vs-secondary flags from the research section):**
- **`k=δσ/2`, the recursions, and `h≈4 or 5`** — **NIST/SEMATECH e-Handbook §6.3.2.3, primary,
  quotable.** <https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm> Verified verbatim
  2026-07-25.
- **`ARL0≈465 / ARL1(1σ)≈10.4` at `h=5`, `ARL0≈168` at `h=4`** — **Montgomery, *Introduction to
  SQC*, §9.1 (Table 9.10) / Lucas (1976), secondary — explicitly NOT in NIST §6.3.2.3.** NIST
  states only that CUSUM outperforms Shewhart for shifts ≤2σ; it publishes no numeric ARL table
  for these `(k, h)` pairs. Do not present these ARL figures as NIST values (same flag class as
  Rule 11's individuals-baseline figure and Rule 12's λ/L pairings).
- **FIR = `h/2` (50% head-start)** — **Lucas, J. M. & Crosier, R. B. (1982), *Technometrics*
  24(3)**, "Fast Initial Response for CUSUM Quality Control Schemes." Primary source is
  paywalled — checked against the reproduction in Montgomery §9.1.4, not cell-verified against
  the 1982 original (same treatment as Rule 12's Lucas & Saccucci citation).

**Applied In:** `quality_core/spc/constants.py` (`CUSUM_DEFAULT_K`, `CUSUM_DEFAULT_H`,
`CUSUM_FIR_FRACTION`); `quality_core/spc/control_charts.py::compute_cusum` (`CUSUMResult`);
`spc_app/visualizer.py::build_cusum_chart`.

---

## RULE 14 — Non-normal capability (Box-Cox / Yeo-Johnson) + Pp/Ppk confidence intervals

**Decision:** `compute_capability_study(data, lsl, usl, *, alpha=CAPABILITY_ALPHA,
allow_yeojohnson=True)` extends the existing normal-path `compute_capability` (unchanged
signature/keys, plus new CI fields) with a full non-normal capability study:

- **Gate:** Shapiro-Wilk (`normality_test`) on the pooled sample. Normal → normal-theory
  Cp/Cpk/Pp/Ppk (parametric CIs on Pp/Ppk only), no transform.
- **Transform (non-normal, Decision 2):** positive data → Box-Cox MLE-λ (`scipy.stats.boxcox`,
  `alpha=` for the likelihood CI); non-positive data → Yeo-Johnson by default
  (`allow_yeojohnson=True`), or an opt-in documented shift `c = 1 − min(x)` then Box-Cox on
  `x+c` when `allow_yeojohnson=False`. Box-Cox is never called on ≤0 data.
- **Rounded-λ snap:** the nearest of `BOXCOX_LAMBDA_CANDIDATES` is substituted for the MLE λ
  only if it falls inside the likelihood CI (`scipy.special.boxcox` re-transform); otherwise the
  MLE λ is kept. Yeo-Johnson never snaps (no tabulated conventional λ set for it here).
- **Spec limits transform identically** to the data (same λ, same shift). For λ<0 the
  transform is not monotone in the naive-swap sense some references describe; the correct,
  general-purpose guard is `lsl_t, usl_t = sorted((t(lsl), t(usl)))` — an ordering-preservation
  guard, not a literal "if λ<0, swap" branch, and it is correct for any λ sign.
- **Re-test after transform:** if still non-normal, fall back to a **fitted-distribution
  percentile method** (ISO 22514-2) on the *original* (untransformed) data rather than
  reporting a Box-Cox capability index on data that failed its own normality check.
  Candidate families `{lognorm, weibull_min, gamma, johnsonsu}` are fit by MLE
  (`scipy.stats.<dist>.fit`), each candidate wrapped in try/except (a failed fit is skipped);
  the finite-AIC minimum (`AIC = 2k − 2·loglik`) is selected. If every candidate fails, an
  empirical `np.quantile` last resort is used and `fitted_dist=None`. Percentiles come from the
  selected distribution's `ppf(0.00135)`/`ppf(0.99865)` (mimicking ±3σ coverage per NIST
  §6.1.6); `Cpk` mirrors the two-sided-vs-one-sided `None` handling of `_centered_capability`
  but uses the fitted median and the two percentiles as its two one-sided denominators. Pp/Ppk
  are `None` for this method (no separate within/overall percentile split exists).
- **Within-σ (Decision 1):** estimated in the SAME space as the capability computation (raw for
  the normal path, transformed for Box-Cox/Yeo-Johnson) by **reusing** the existing
  `compute_imr`/`compute_xbar_r` estimators — individuals → moving-range `MR̄/IMR_D2`;
  2D subgroups → `R̄/d₂(n)` (`compute_xbar_r`'s own 2≤n≤10 guard is reused, not reimplemented).
  Overall σ is always the transformed-or-raw sample SD (`ddof=1`). This preserves the
  Cp/Cpk-within vs Pp/Ppk-overall split after a transform.
- **Confidence intervals:** `compute_capability` returns `alpha`, `n`, `ci_estimator`, `ci_df`,
  `pp_ci`, `ppk_ci`, `ppk_lower`. The exact χ² interval
  (`pp·sqrt(chi2.ppf(α/2, n−1)/(n−1))` to `pp·sqrt(chi2.ppf(1−α/2, n−1)/(n−1))`) and the
  Bissell (1990) large-sample normal approximation (`se = sqrt(1/(9n) + Ppk²/(2(n−1)))`,
  two-sided `Ppk ± z_{1−α/2}·se`, one-sided lower bound `Ppk − z_{1−α}·se`) are **derived for σ
  estimated by the sample standard deviation `s` with ν = n−1**. They are therefore attached to
  **Pp/Ppk**, which use `np.std(x, ddof=1)` — the estimator the derivation assumes
  (`ci_estimator="sample_sd_ddof1"`, `ci_df=n−1`). This applies to the normal and
  Box-Cox/Yeo-Johnson-normal paths.
- **No CI is reported for Cp/Cpk.** Those use the within-subgroup estimator (R̄/d₂ or MR̄/d₂,
  "Within-σ" bullet above), whose effective degrees of freedom are fewer than n−1; applying the
  n−1 forms to them produces intervals that are too narrow. An effective-df correction for R̄/d₂
  was considered and **not** adopted: no primary source is available on-machine, and this log
  does not carry uncited constants (#193, audit F-05). `cp_ci`/`cpk_ci`/`cpk_lower` are `None`
  on these paths.
- **Percentile path (unchanged):** the fitted-percentile path instead gets a **deterministic
  bootstrap** CI on the percentile indices themselves, reported in `cp_ci`/`cpk_ci`/`cpk_lower`
  with `ci_estimator="bootstrap_percentile"`, `ci_df=None` (no df assumption): fixed
  `BOOTSTRAP_SEED = 12345`, fixed `BOOTSTRAP_RESAMPLES = 2000`,
  `scipy.stats.bootstrap(method="percentile")` — the statistic refits the candidate families
  per resample; a resample where every fit fails uses the empirical fallback statistic. A CI
  whose point estimate is `None` (one-sided spec) is skipped (`*_ci = None` on that side).
  Fixing the seed and resample count is mandatory for bit-reproducible, auditable CIs — this is
  an engineering choice, not a statistical one.
- **Small-n caveat:** the Bissell/χ²/bootstrap CIs assume a large sample (n≈30–50). `n<30` never
  raises; the study's `note` field carries a caveat instead (soft-warn, mirrors Rule 11/12's
  `*_adequate`/`*_note` pattern).
- **Degenerate input:** constant data (zero variance) raises `ValueError` — no capability
  index, transform, or normality test is meaningful on a single-valued sample.

**Source:**
- **Box-Cox formula `x(λ)=(x^λ−1)/λ, λ≠0; ln x, λ=0`, MLE-λ ("λ that maximizes the
  log-likelihood")** — **NIST/SEMATECH e-Handbook §6.5.2 "What to do when data are
  non-normal"** — PRIMARY, quotable. Verified 2026-07-25.
  <https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc52.htm>
- **Percentile index `Ĉ_Np = (USL−LSL)/(p_0.99865 − p_0.00135)`, "mimics ±3σ coverage"** —
  **NIST/SEMATECH e-Handbook §6.1.6 "What is Process Capability?"** — PRIMARY, quotable.
  Verified 2026-07-25. <https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm>
- **χ² Cp/Pp interval; Bissell (1990) large-sample Cpk/Ppk variance `1/(9n) + Ĉ²/(2(n−1))`** —
  D. C. Montgomery, *Introduction to Statistical Quality Control*, Ch. 8; A. F. Bissell, "How
  Reliable Is Your Capability Index?", *Applied Statistics* 39(3):331–340 (1990). Both are
  derived for σ estimated by the sample standard deviation, ν = n−1. **Not verified
  on-machine** — neither text is in the local reference set; the estimator/df pairing recorded
  above is verified from the implementation, not from the primary text.
- **Box & Cox (1964), "An Analysis of Transformations," *Journal of the Royal Statistical
  Society, Series B* 26(2) — PAYWALLED primary.** NIST §6.5.2 is the quotable stand-in used
  above; the original transformation paper was not directly consulted.
- **Fitted-distribution percentile capability method** — **ISO 22514-2 — PAYWALLED, cited, not
  quoted.** The min-AIC family-selection rule over `{lognorm, weibull_min, gamma, johnsonsu}` is
  our own operationalization of "fit the best distribution" (AIC per **Akaike, H. (1974)**), an
  engineering choice, not a verbatim ISO procedure — flagged as such.
- **Bootstrap percentile-method CI** — **Efron, B. & Tibshirani, R. J. (1993), *An Introduction
  to the Bootstrap* — secondary/paywalled book**, the percentile-method mechanism reproduced by
  `scipy.stats.bootstrap(method="percentile")`. The fixed seed/resample count is an engineering
  reproducibility choice, not part of the cited method itself.

**Applied In:** `quality_core/spc/capability.py` (`compute_capability` CI fields,
`CapabilityStudy`, `compute_capability_study`, `_within_sigma`, `_fit_percentile_capability`,
`_percentile_cpk`, `_bootstrap_percentile_ci`, `_cp_chi2_ci`, `_cpk_bissell_ci`);
`quality_core/spc/constants.py` (`CAPABILITY_ALPHA`, `BOXCOX_LAMBDA_CANDIDATES`,
`NONNORMAL_LOWER_PCTL`, `NONNORMAL_UPPER_PCTL`, `PERCENTILE_FIT_CANDIDATES`, `BOOTSTRAP_SEED`,
`BOOTSTRAP_RESAMPLES`).

**Assumption note — `force_method` user override (W10-5, #145):** `compute_capability_study`
accepts `force_method="normal"` to skip the Shapiro-Wilk gate and compute normal-theory
Cp/Cpk (parametric CIs on Pp/Ppk) on raw data regardless of the actual normality result. This is a deliberate
user override, not an engine claim that the data is normal — the returned `note` always
records "user-forced," and the responsibility for that assumption's validity is the
analyst's, mirroring how Rule 7's stability gate still renders (marked indicative) rather
than blocking. `force_method="boxcox"`/`"percentile"` are the same override pattern for
the other two paths (no normality assumption at stake for those — they force a specific
already-validated methodology rather than skip a check).

---

## RULE 15 — Run-Rule Gating (WE/Nelson Restricted to Shewhart Charts)

**Decision:** Western Electric (Rules 1–4) and Nelson (Tests 1–8) run-rules are valid only
on Shewhart charts — X̄-R, X̄-S, I-MR, p, c, u — where successive plotted points are
independent. They are **statistically invalid on EWMA and CUSUM**, whose plotted
statistics (the EWMA z-series; the CUSUM C+/C− accumulators) are autocorrelated by
construction: each point is a function of all prior points, so run-length-based patterns
(a trend, an alternation, a run on one side) are expected to occur far more often than the
independent-point run-rule tables assume, causing systematic false alarms if WE/Nelson were
applied to them. EWMA/CUSUM charts signal exclusively on their own limit / decision-interval
crossings (`EWMAResult.signals`, `CUSUMResult.signals`), which is the correct and complete
detection mechanism for those charts.

This is enforced at a single chokepoint rather than per-caller: `rule_detection.
detect_violations(chart_type, points, cl, sigma, rule_set)` returns `[]` immediately for any
`chart_type` outside `SHEWHART_CHART_TYPES = {"Xbar-R","Xbar-S","I-MR","p","c","u"}` (and for
`sigma<=0`), otherwise dispatches to the existing `detect_we_violations`/
`detect_nelson_violations` unchanged. Both page-level callers — the Control Charts page's
per-branch rule overlay and the capability stability gate (`quality_core/spc/stability.py::
assess_stability`) — now route through this one function, so no caller can (accidentally or otherwise) run
WE/Nelson on an EWMA/CUSUM chart.

**Source:** Western Electric *Statistical Quality Control Handbook* (1956) and L. S. Nelson,
*Journal of Quality Technology* 16(4) (1984) — same citations as RULE 8, which define the
rules being restricted here. The autocorrelation rationale is Montgomery, *Introduction to
Statistical Quality Control*, §9 (EWMA §9.2 / CUSUM §9.1) — both z-series and C+/C−
accumulators are explicitly serially correlated by their recursive definitions, already
noted (without the gating enforcement) in RULE 12/13. No new external citation is
introduced by this rule.

**Applied In:** `quality_core/spc/rule_detection.py` (`SHEWHART_CHART_TYPES`,
`detect_violations`) → `spc_app/pages/control_charts.py::detect_rule_violations` →
`quality_core/spc/stability.py::assess_stability`.

---

*Sources referenced in this log:*
- *AIAG SPC Reference Manual, 4th Edition (2005) — control-chart constants, attribute charts, capability indices*
- *Western Electric — Statistical Quality Control Handbook (1956)*
- *L. S. Nelson — Journal of Quality Technology 16(4), 1984 — tests for special causes*
- *Shapiro, S. S. & Wilk, M. B. (1965) — An analysis of variance test for normality*
- *AIAG FMEA-4, 4th Ed. (2008) / SAE J1739 — Occurrence ranking table (rate bands, see Rule 10)*
- *NIST/SEMATECH e-Handbook of Statistical Methods, §6.3.2.1, §6.3.2.4 & §6.5.4.3 — Phase I baseline
  size, EWMA recursion/variance, Phase I/II terminology*
- *Montgomery, D. C. — Introduction to Statistical Quality Control, Ch. 5–6, §9.2 — I-MR baseline
  size (secondary), Phase I/II framework, EWMA exact variance*
- *Lucas, J. M. & Saccucci, M. S. (1990) — Technometrics 32(1) — EWMA λ/L design, as reproduced in
  Montgomery Table 9.11 (secondary, paywalled primary)*
- *NIST/SEMATECH e-Handbook of Statistical Methods, §6.3.2.3 — CUSUM recursion, k, h rule-of-thumb*
- *Montgomery, D. C. — Introduction to Statistical Quality Control, §9.1 (Table 9.10), §9.1.4 —
  CUSUM ARL figures (secondary) and FIR reproduction*
- *Lucas, J. M. & Crosier, R. B. (1982) — Technometrics 24(3) — Fast Initial Response for CUSUM
  Quality Control Schemes (secondary, paywalled primary)*
- *NIST/SEMATECH e-Handbook of Statistical Methods, §6.5.2 & §6.1.6 — Box-Cox transformation /
  MLE-λ, percentile-based process capability index (primary, quotable)*
- *Montgomery, D. C. — Introduction to Statistical Quality Control, Ch. 8 — Cp χ² CI, Cpk
  large-sample CI (secondary)*
- *Bissell, A. F. (1990) — Applied Statistics 39(3):331–340 — Cpk confidence interval variance (secondary,
  paywalled primary)*
- *Box, G. E. P. & Cox, D. R. (1964) — Journal of the Royal Statistical Society, Series B 26(2) —
  the Box-Cox transformation (secondary, paywalled primary; NIST §6.5.2 the quotable stand-in)*
- *ISO 22514-2 — Statistical methods in process management: Capability and performance — Part 2 —
  fitted-distribution percentile capability (paywalled, cited not quoted)*
- *Akaike, H. (1974) — IEEE Transactions on Automatic Control 19(6) — Akaike Information
  Criterion, used here for min-AIC candidate-family selection (engineering choice)*
- *Efron, B. & Tibshirani, R. J. (1993) — An Introduction to the Bootstrap — bootstrap
  percentile-method confidence intervals (secondary, paywalled book)*
