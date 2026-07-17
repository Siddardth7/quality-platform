# Engineering Assumptions Log

**Project:** Control Plan app
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** July 17, 2026

This document records every non-obvious engineering decision — and every published
constant or threshold — used in the Control Plan app. Each entry explains what was
chosen, why, and where it is applied. Mirrors the discipline of
`apps/spc/docs/ASSUMPTIONS_LOG.md` and the AP-table verification precedent in
`tests/test_scoring.py`.

---

## RULE 1 — SPC Chart-Selection Rule Table (`recommend_chart`)

**Decision:** Select a control chart from data type + subgroup size (+ attribute
counting mode), per the AIAG chart-selection decision tree:

- Variable data: `n == 1` → `I-MR`; `2 <= n <= 9` → `Xbar-R`; `n >= 10` → `Xbar-S`.
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

**Applied In:** `controlplan_app/connector.py::build_control_plan` (`# ponytail:`
marked module constants); the W06-3 authoring UI (#85) will make these user-editable
per row.

---

*Sources referenced in this log:*
- *AIAG SPC Reference Manual, 4th Edition (2005) — control-chart selection*
- *Montgomery, D. C. — Introduction to Statistical Quality Control (for the
  third-party Xbar-R/Xbar-S boundary cross-check, Rule 1)*
