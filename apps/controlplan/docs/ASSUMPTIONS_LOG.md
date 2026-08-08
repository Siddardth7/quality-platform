# Engineering Assumptions Log

**Project:** Control Plan app
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** August 6, 2026

This document records every non-obvious engineering decision — and every published
constant or threshold — used in the Control Plan app. Each entry explains what was
chosen, why, and where it is applied. Mirrors the discipline of
`apps/spc/docs/ASSUMPTIONS_LOG.md` and the AP-table verification precedent in
`tests/test_scoring.py`.

---

## RULE 1 — SPC Chart-Selection Rule Table (`recommend_chart`)

**Decision:** Select a control chart from data type + subgroup size (+ attribute
counting mode), per the AIAG chart-selection decision tree:

- Variable data: `n == 1` → `I-MR`; `2 <= n <= 9` → `Xbar-R`; `n >= 10` (up to 12) →
  `Xbar-S`; `n > 12` → `ValueError` (see the upper-bound entry below).
- Attribute data: classifying units good/bad → `p` (`np` folds into `p`; the
  `SPCChart` schema Literal has no `np` key); counting defects per unit, constant
  sample → `c`; counting defects per unit, variable sample → `u`.

**Source:** AIAG SPC Reference Manual, 4th Ed. (2005), control-chart selection logic
— the same primary source already cited by `apps/spc/docs/ASSUMPTIONS_LOG.md` (Rules
1–4) and by `quality_core.scoring` for the AP table.

**Flag — the Xbar-R ↔ Xbar-S boundary (n = 9 vs 10):** third-party references
disagree by one (SPC for Excel and the Six Sigma Study Guide say "n ≥ 9 → S";
Montgomery, *Introduction to Statistical Quality Control*, says "n > 10 → S"). This
connector hard-codes `n >= 10 -> Xbar-S` (n ≤ 9 stays Xbar-R) as the default. **This
one number should be confirmed against the primary AIAG SPC Reference Manual, 4th
Ed. (2005) decision tree before being treated as final** — it is the one cell in the
rule table sourced from a third-party reproduction rather than the primary manual
directly, the way `tests/test_scoring.py` independently re-verifies the AP grid
against the AIAG/VDA standard.

**Upper bound — `n > 12` raises (F-07, #196):** `Xbar-S` is only computable for
subgroup sizes the AIAG X-bar/S constants table covers
(`quality_core.spc.constants.XBAR_S_CONSTANTS`, keys 2–12; `compute_xbar_s` raises
"X-bar S chart requires subgroup size between 2 and 12." above it). `recommend_chart`
therefore raises `ValueError` for variable data with `n > 12` rather than naming a
chart the engine cannot compute. The ceiling is read from the constants table
(`max(XBAR_S_CONSTANTS)`), not hard-coded. Extending the table above n=12 would
require A3/B3/B4/c4 values that are not in any on-machine primary source, so it is
deliberately not done. The bound applies to variable data only — attribute charts
(`p`/`c`/`u`) take a sample size with no constants table, and large n is normal there.

**Boundary wording reconciled (OQ-1, #196):** `apps/spc/docs/ASSUMPTIONS_LOG.md`
RULE 2 previously read "n > ~10"; it now states `n >= 10`, matching this rule and the
connector. No code or math changed — the third-party-sourced flag above still stands.

**Applied In:** `controlplan_app/connector.py::recommend_chart`.

---

## RULE 2 — FMEA → Control Plan Field Defaults (No FMEA Source)

**Decision:** `build_control_plan` (W06-2, #84) derives `characteristic` and
`measurement_method` from the relational FMEA, but `sample_size`, `frequency`, and
`reaction_plan` have no FMEA-model equivalent (severity/occurrence/detection carry
no sample plan or containment text). Defaulted to `sample_size=1`,
`frequency="per shift"`, and a templated `reaction_plan` built from the
failure mode's worst effect. `recommended_chart` is always emitted `None` — the
relational FMEA carries no data-type/subgroup-size input, so the engine does not
guess one; `recommend_chart()` (Rule 1) exists for a later enrichment step to call.

**Source:** Not a published standard — an explicit placeholder decision (SME-
confirmed, `.pipeline/spec.md` "SME RESOLUTIONS" §4), the same way the AP thresholds
in `apps/fmea/docs/ASSUMPTIONS_LOG.md` are recorded even though they are project
conventions rather than universal constants.

**Provenance flag (F-10, #196):** because these three fields have no FMEA source,
every row `build_control_plan` emits now carries `sample_plan_is_placeholder=True`
(`controlplan_app/schema.py::ControlPlanRow`), so a downstream consumer cannot
mistake a defaulted sample plan for an FMEA-derived one. The field defaults to
`False` — an uploaded or hand-edited row asserts its own values — and is an optional
ingest column, so an upload predating it still validates.

**Applied In:** `controlplan_app/connector.py::build_control_plan` (`# ponytail:`
marked module constants); the W06-3 authoring UI (#85) will make these user-editable
per row.

---

*Sources referenced in this log:*
- *AIAG SPC Reference Manual, 4th Edition (2005) — control-chart selection*
- *Montgomery, D. C. — Introduction to Statistical Quality Control (for the
  third-party Xbar-R/Xbar-S boundary cross-check, Rule 1)*
