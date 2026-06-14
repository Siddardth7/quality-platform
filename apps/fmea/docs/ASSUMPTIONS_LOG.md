# Engineering Assumptions Log
**Project:** FMEA Risk Prioritization Tool
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC
**Last Updated:** March 26, 2026

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
- No fixed threshold (use only Action Priority): Valid per AIAG 5th Ed., but RPN threshold retained here for backwards compatibility with FMEA-4-based workflows still common in industry

**Applied In:** `src/rpn_engine.py` → `flag_critical()` → column `Flag_High_RPN`

---

## RULE 2 — Severity ≥ 9 Mandatory Flag (Safety Rule)

**Decision:** Any failure mode with **Severity score = 9 or 10 must be flagged for corrective action regardless of RPN** (`Flag_High_Severity = True`).

**Source:** AIAG FMEA-4 and AIAG FMEA 5th Edition (2019), Section 4.4 — "Severity Ranking." Both editions state explicitly that Severity 9–10 failure modes require action independent of Occurrence and Detection scores.

**Severity Scale Reference (AIAG FMEA-4):**
- Severity 10: Failure affects safe vehicle operation without warning (safety/regulatory)
- Severity 9: Failure affects safe vehicle operation with warning (safety/regulatory)
- Severity 8 and below: Non-safety impact; RPN-based prioritization applies

**Rationale:** A failure mode with S=9, O=1, D=1 yields RPN=9 — which would never be flagged by a pure RPN threshold. However, if that failure mode occurs even once, it could cause a safety incident. The Severity ≥ 9 rule exists precisely to catch these low-frequency, high-consequence events that RPN-only systems miss.

**Real-World Anchor (Composites Context):** Autoclave overpressure events (S=10) and bag burst during cure (S=9) are examples where corrective action is mandatory regardless of how rarely they occur or how easy they are to detect after the fact.

**Applied In:** `src/rpn_engine.py` → `flag_critical()` → column `Flag_High_Severity`

---

## RULE 3 — Action Priority (AP) Classification

**Decision:** Implement a **simplified Action Priority system** with three levels (H/M/L) based on AIAG FMEA 5th Edition (2019), applied as follows:

| Action Priority | Condition | Meaning |
|----------------|-----------|---------|
| **H (High)** | RPN ≥ 200 OR Severity ≥ 9 | Immediate corrective action required |
| **M (Medium)** | RPN 100–199 (and S < 9) | Corrective action strongly recommended |
| **L (Low)** | RPN < 100 (and S < 9) | Monitor; action at engineer's discretion |

**Source:** AIAG FMEA 5th Edition (2019) introduced the AP system to replace sole reliance on RPN ranking, acknowledging that RPN has mathematical limitations (e.g., different S/O/D combinations can produce identical RPNs with very different risk profiles). Free summary available at: quality-one.com/fmea/ and asq.org/quality-resources/fmea.

**Rationale for Simplified Implementation:** The full AIAG 5th Ed. AP lookup table uses a 3D matrix (S × O × D) with ~1000 cells. For this tool, a simplified threshold-based approximation is used because: (1) it is defensible and conservative, (2) exact AP table values vary by company-specific customization, and (3) the simplified version captures the intent — severe or high-RPN items get H, moderate get M, low get L.

**Deviation from Standard:** The official AIAG 5th Ed. AP table assigns H based on specific S/O combinations regardless of D. This tool uses RPN ≥ 200 as a proxy for the H-tier, which is conservative (may flag some items as H that the full table would classify M). This is an acceptable engineering tradeoff for a portfolio tool.

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

*Sources referenced in this log:*
- *AIAG FMEA-4 (4th Edition) — Potential Failure Mode and Effects Analysis*
- *AIAG/VDA FMEA Handbook (5th Edition, 2019)*
- *ASQ FMEA Resource Guide: asq.org/quality-resources/fmea*
- *Quality-One FMEA Reference: quality-one.com/fmea*
- *Juran's Quality Handbook, 7th Ed. — Pareto Analysis*
