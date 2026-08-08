# Engineering Assumptions Log
**Project:** FMEA Risk Prioritization Tool
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** August 7, 2026

This document records every non-obvious engineering decision made in this project.
Each entry explains what was chosen, why, and what alternatives were considered.
This log is the defense against any interview question about methodology choices.

---

## RULE 1 — RPN Threshold for Corrective Action Required

**Decision:** Flag any failure mode with **RPN > 100** as requiring corrective action (`Flag_High_RPN = True`).

**Source:** AIAG FMEA-4 (4th Edition), the industry standard for Process FMEA in automotive and aerospace supply chains. The 100-point threshold is the most widely cited cutoff across Tier-1 suppliers (Boeing, GE, Honeywell supplier quality requirements).

**Rationale:** On a 10×10×10 scale (max RPN = 1000), RPN = 100 represents exactly 10% of maximum possible risk. Empirically, automotive and aerospace quality teams treat this as the minimum threshold at which structured corrective action planning is required rather than optional monitoring.

**Alternatives Considered:**
- RPN > 80: Too aggressive — would flag low-consequence failure modes and overwhelm the action list
- RPN > 125: More conservative; used by some companies but less common in literature
- No fixed threshold (use only Action Priority): this is what the AIAG & VDA FMEA Handbook (1st Ed., 2019) §3.5.9 actually recommends —

  > The use of a Risk Priority Number (RPN) threshold is not a recommended practice for determining the need for actions.

  The RPN threshold is retained here anyway for backwards compatibility with FMEA-4-based workflows still common in industry, and the handbook's own AP table ships alongside it as RULE 7.

**Applied In:** `src/rpn_engine.py` → `flag_critical()` → column `Flag_High_RPN`

---

## RULE 2 — Severity ≥ 9 Flag (repo-chosen safety heuristic)

**Decision:** Any failure mode with **Severity score = 9 or 10 is flagged regardless of RPN** (`Flag_High_Severity = True`).

**Source — corrected 2026-08-07 (#197).** This flag is a **repo-chosen safety heuristic, not a standards requirement.** This entry previously claimed that AIAG FMEA-4 and a "Section 4.4" of a fifth edition of the AIAG FMEA manual both "state explicitly that Severity 9–10 failure modes require action independent of Occurrence and Detection scores." That claim is false on two counts: **AIAG never published a fifth edition of the FMEA manual** — the 2019 document is the **AIAG & VDA FMEA Handbook, 1st Edition** — and that handbook says no such thing. Its Table AP — transcribed and cell-verified in RULE 7 — assigns **Low** to S 9–10 with Occurrence 1 for every Detection value, and Low to S 9–10 / O 2–3 once Detection is 2–4 or better. What the handbook does say, §3.5.9, verbatim:

> It is recommended that potential Severity 9-10 failure effects with Action Priority High and Medium, at a minimum, be reviewed by management including any recommended actions that were taken.

That is a **management-review recommendation gated on AP being High or Medium**, not an unconditional "S 9–10 always requires action" rule.

**Why the flag is kept anyway:** `Flag_High_Severity` fires on **every** S ≥ 9 row irrespective of O and D, which is **strictly more conservative** than the handbook's own Table AP. It is a belt-and-suspenders flag layered on top of the AP engine (RULE 7), chosen by this repo for a safety-critical composites context — see the rationale and anchor below. It is deliberately *not* attributed to AIAG or VDA. The handbook's AP determination remains available and unmodified via RULE 7.

**Severity Scale Reference (AIAG FMEA-4):**
- Severity 10: Failure affects safe vehicle operation without warning (safety/regulatory)
- Severity 9: Failure affects safe vehicle operation with warning (safety/regulatory)
- Severity 8 and below: Non-safety impact; RPN-based prioritization applies

**Rationale:** A failure mode with S=9, O=1, D=1 yields RPN=9 — which would never be flagged by a pure RPN threshold, and which the handbook's Table AP rates Low. However, if that failure mode occurs even once, it could cause a safety incident. This repo's Severity ≥ 9 flag exists precisely to surface these low-frequency, high-consequence events that RPN-only ranking buries — an accepted over-flagging cost, taken knowingly.

**Real-World Anchor (Composites Context):** Autoclave overpressure events (S=10) and bag burst during cure (S=9) are examples where corrective action is mandatory regardless of how rarely they occur or how easy they are to detect after the fact.

**Applied In:** `src/rpn_engine.py` → `flag_critical()` → column `Flag_High_Severity`

---

## RULE 3 — `Flag_Action_Priority_H` RPN-side heuristic (superseded as "the AP system" — see RULE 7)

**⚠ Superseded.** This rule once described `Flag_Action_Priority_H` as this tool's Action Priority implementation. It is not, and the fifth edition of the AIAG FMEA manual it cited does not exist. The real Action Priority determination is the published AIAG & VDA (1st Ed., 2019) table lookup in **RULE 7** (`fmea_app/ap_engine.py`). What follows documents the RPN-side proxy flag that is retained alongside it, and why its thresholds are what they are.

**Decision:** Compute a three-level (H/M/L) **RPN-side proxy** for prioritization urgency, applied as follows:

| Action Priority | Condition | Meaning |
|----------------|-----------|---------|
| **H (High)** | RPN ≥ 200 OR Severity ≥ 9 | Immediate corrective action required |
| **M (Medium)** | RPN 100–199 (and S < 9) | Corrective action strongly recommended |
| **L (Low)** | RPN < 100 (and S < 9) | Monitor; action at engineer's discretion |

**Source of the *idea*:** the AIAG & VDA FMEA Handbook (1st Edition, 2019) §3.5.9 introduced the Action Priority method to replace sole reliance on RPN ranking, acknowledging that RPN has mathematical limitations (different S/O/D combinations can produce identical RPNs with very different risk profiles). The handbook's own method is implemented in RULE 7. **The thresholds in the table above are this repo's, not AIAG's or VDA's** — no published standard defines an "RPN ≥ 200" tier.

**Why the proxy exists at all:** it predates the AP engine (RULE 7) and is kept for continuity with RPN-mode ranking and with exports generated before the AP engine shipped. It is a coarse RPN-side signal, not a standards determination — a reader wanting the handbook's answer must use the AP toggle, which routes to `action_priority()`.

**Rationale for the 200 cutoff (a repo decision):** on a 1–1000 RPN range, 200 is 20% of maximum risk and roughly twice RULE 1's corrective-action threshold. It is deliberately conservative in the over-flagging direction — it can raise H on items the handbook's Table AP rates Medium, never the reverse. Because RPN weights S, O, and D equally and the handbook's AP method does not, the two will disagree by construction; where they disagree, RULE 7 is the standards-correct answer.

**Applied In:** `src/rpn_engine.py` → `flag_critical()` → column `Flag_Action_Priority_H`

---

## RULE 4 — Risk Tier Color Coding (Red / Yellow / Green)

**Decision:** Assign a visual Risk Tier to each failure mode based on RPN and flag status:

| Risk Tier | Condition | Color |
|-----------|-----------|-------|
| **Red** | RPN > 100 OR Severity ≥ 9 | `#d32f2f` |
| **Yellow** | RPN 50–100 AND Severity < 9 | `#f57c00` |
| **Green** | RPN < 50 AND Severity < 9 | `#388e3c` |

**Source:** Color convention adapted from AIAG FMEA risk matrix color standards and common automotive quality dashboard practice (red/amber/green = RAG status, widely used in AS9100 and IATF 16949 quality systems).

**Applied In:** `src/rpn_engine.py` → `rank_by_rpn()` → column `Risk_Tier`

---

## RULE 5 — Pareto Chart Bar Coloring

**Decision:** Pareto chart bars are **colored by Risk_Tier** (Red/Yellow/Green) assigned in Rule 4, not by Pareto 80/20 cumulative banding. A dashed 80% reference line is overlaid on the cumulative % line to help users identify the "vital few" failure modes visually.

**Source:** Pareto Principle (Vilfredo Pareto, 1896) — applied to quality engineering by Joseph Juran as the 80/20 rule. In FMEA context: the cumulative RPN line shows where risk is concentrated, enabling corrective action prioritization.

**Note on demo dataset:** The composite panel demo dataset does not exhibit a classic 80/20 distribution. The top 6 of 30 failure modes account for approximately 29% of total RPN. The Pareto chart remains useful for identifying the highest-RPN failure modes regardless of the exact cumulative percentage.

**Applied In:** `src/plotly_charts.py` → `pareto_chart_plotly()` → bar color mapped to `Risk_Tier`

---

## RULE 6 — Data-Driven S/O/D Rating Scales (W03-4)

**Decision:** The 1–10 anchor descriptions for Severity, Occurrence, and Detection are **data, not constants**. The default scale is the **AIAG & VDA 2019 PFMEA** scale, shipped as `data/rating_scales_2019_pfmea.json` (`AIAG & VDA 2019 PFMEA (default)`). **AIAG FMEA-4** is retained as a selectable legacy option in `data/rating_scales.json` (`AIAG FMEA-4 (legacy)`). Both are loaded/validated by `fmea_app/rating_scales.py`, and a user may still supply a custom 1–10 scale (a company-specific PFMEA rubric) that passes through the same validation (every factor must define ratings 1–10 exactly, with non-empty descriptions).

**Which columns the 2019 anchors come from.** The handbook publishes several columns per factor; one per factor is quoted here, chosen because it is per-rating (not merged across rating pairs) and clean in the primary-source conversion. Severity is Table P1's *Impact to End User (when known)* column — the end-user consequence, which is what a PFMEA severity score is scored against. Occurrence is Table C2.3.1's *Incidents per 1000 items/vehicles* column (the Alternate PFMEA Occurrence table), the handbook's own quantitative rate anchors; the main-body Table P2 is qualitative ("Extremely high" / "Very high") and merges cells across rating pairs, so it is not per-rating quotable. Detection is Table P3's *Opportunity for Detection* column, which describes the detection method; the *Ability to Detect* column likewise merges across rating pairs. The columns not shipped (Severity *Effect*, Occurrence *Prediction of Failure Cause Occurring* / *Type of Control*, Detection *Ability to Detect*) are excluded for that reason, not because they were overlooked. All 30 shipped anchors are line-pinned to the handbook in `CITATIONS.tsv` and re-verified against the primary source by `tests/test_citations.py`.

**Scope — the *math* is scale-independent; the *result's standards fidelity* is not.** The rating scales describe what each score *means* to the analyst. Changing them does **not** change RPN (`S × O × D`) or the Action Priority lookup: the engines consume the integer scores 1–10 either way, and no threshold in Rules 1–5 or cell in the AP table moves. That much is true of the code path.

It is **not** true of the answer an analyst gets. The AP table's band boundaries are calibrated to the S/O/D tables published in the same handbook, and the anchors are what determine which integer an analyst assigns in the first place. The handbook says so directly (§3.5.9):

> Since the AP Table was designed to work with the Severity, Occurrence, and Detection tables provided in this handbook, if the organization chooses to modify the S, O, D, tables for specific products, processes, or projects, the AP table should also be carefully reviewed.

**That mismatch is now resolved.** The default scale and the AP table (RULE 7) are both transcribed from the AIAG & VDA FMEA Handbook (1st Ed., 2019) — the same handbook, calibrated together — so an analyst using the default gets an internally consistent pairing, which the earlier FMEA-4-default arrangement did not provide.

**The residual caveat now belongs to the legacy option.** Scoring against the **AIAG FMEA-4 (legacy)** scale and then reading an Action Priority is still the modify-the-S/O/D-tables case the passage above warns about: the AP table was calibrated to the 2019 tables, not to FMEA-4's. The legacy scale is kept because organisations still running FMEA-4 rubrics need their historical scores to mean what they meant; it is not the recommended pairing for a new AP-based analysis. The same caveat applies, unchanged, to any custom uploaded scale.

**Source of the default text:** AIAG & VDA FMEA Handbook, 1st Ed. (2019) — Severity from Table P1, Occurrence from Table C2.3.1, Detection from Table P3 (see the column note above); documented in `docs/FMEA_input_schema.md` § "Scoring Scales — AIAG & VDA 2019 PFMEA (default)" so the documented scale and the in-app scale stay in sync. The legacy text is AIAG FMEA-4 (4th Ed.), documented in that file's "Legacy: AIAG FMEA-4" subsection.

**Applied In:** `fmea_app/rating_scales.py` → `load_default_scales()` / `load_legacy_fmea4_scales()` (loaders + validation) · `data/rating_scales_2019_pfmea.json` (default) · `data/rating_scales.json` (legacy) · `ui/filters.py` → `render_rating_scale_selector()` · `ui/components.py` → `render_rating_scales()`

---

## RULE 7 — AIAG-VDA Action Priority (AP) Engine (W03-1 / W03-3)

**Decision:** Implement the **full published AIAG/VDA 2019 Action Priority table** as a first-class prioritization basis alongside RPN. `action_priority(S, O, D)` returns **High / Medium / Low** by lookup — not a threshold approximation. Emphasis order is **Severity → Occurrence → Detection** (Severity weighted most), but high severity does **not** auto-escalate: a Severity 9–10 failure that is rare (O 1) is Low for every Detection, and S 9–10 / O 2–3 is Low once detection is adequate (D 2–4 or better). Severity 1 is Low everywhere. The user toggles RPN ↔ AP in the app; the choice drives ranking, tiering, and exports.

**Relationship to Rule 2 / the RPN flags:** This supersedes the old characterization of `Flag_Action_Priority_H` as "the AP system." That flag (RPN ≥ 200 OR Severity ≥ 9) is retained as a **simplified RPN-side heuristic** and is explicitly *not* the AP determination. The real H/M/L comes from the AP table in this rule.

**Source (primary, verified):** AIAG & VDA FMEA Handbook (1st Edition, 2019), "Action Priority (AP) for DFMEA and PFMEA" table (identical for DFMEA and PFMEA per the handbook's own note; the FMEA-MSR AP table is *different* and not used here). The grid was transcribed and machine-diffed cell-by-cell against the handbook (both the DFMEA and PFMEA copies, which are identical). The band layout (S {9-10, 7-8, 4-6, 2-3, 1}; O {8-10, 6-7, 4-5, 2-3, 1}; D {7-10, 5-6, 2-4, 1}) and full H/M/L grid are reproduced in `docs/FMEA_methodology_notes.md` §4.2.

**Transcription error caught (2026-06-16):** an initial transcription of the S 9-10 block (sourced from a third-party reproduction) was shifted by one occurrence band — `O4-5/D1`, the whole `O2-3` row, and the whole `O1` row were wrong (e.g. `S9-10/O1` was `H,M,L,L` instead of the correct all-`Low`). It was *not* caught by monotonicity (the shifted block stayed monotonic) and slipped through the original same-source test oracle. It was corrected only after verifying against the handbook primary source.

**Correctness guard:** `tests/test_ap_engine.py` now pins cell values three ways: (1) AP-09 — an independent hand-transcription of the handbook table (with its own band classifier) checked against the engine for all 1000 S/O/D combinations; (2) AP-12 — eight worked PFMEA rows from the external MDPI case study (Pop et al. 2026, Tables 2–3); and (3) AP-05 monotonicity, kept only as a *necessary* structural check (not sufficient to pin values, as the shift above proved).

**Applied In:** `fmea_app/ap_engine.py` → `action_priority()`, `calculate_ap()`, `rank_by_ap()` · surfaced via the RPN↔AP toggle in `app.py` and carried into `fmea_app/exporter.py`.

---

*Sources referenced in this log:*
- *AIAG FMEA-4 (4th Edition) — Potential Failure Mode and Effects Analysis*
- *AIAG & VDA FMEA Handbook, 1st Edition (2019) — the joint AIAG/VDA successor to FMEA-4. AIAG never published a fifth edition of the FMEA manual; every reference to one in this log was a misattribution, corrected in #197. Verbatim quotations from it are indexed in `CITATIONS.tsv` and re-checked against the primary source by `tests/test_citations.py`.*
- *ASQ FMEA Resource Guide: asq.org/quality-resources/fmea*
- *Quality-One FMEA Reference: quality-one.com/fmea*
- *Juran's Quality Handbook, 7th Ed. — Pareto Analysis*
