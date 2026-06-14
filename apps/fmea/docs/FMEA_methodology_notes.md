# FMEA Methodology Notes
**Project:** FMEA Risk Prioritization Tool  
**Author:** Siddardth | M.S. Aerospace Engineering, UIUC  
**Engineering Reference:** AIAG FMEA-4 (4th Edition) + AIAG/VDA FMEA Handbook (5th Edition, 2019)

---

## 1. What is FMEA?

Failure Mode and Effects Analysis (FMEA) is a structured, bottom-up risk assessment methodology used across aerospace, automotive, and medical device manufacturing. For each component or process step, engineers enumerate every way it can fail (*failure mode*), what happens downstream when it does (*effect*), why it fails (*cause*), and how well current controls detect or prevent the failure.

In process manufacturing — composites layup, autoclave cure, demold — a single undetected failure mode can propagate through the entire laminate stack, causing scrapped parts, rework costs, or structural non-conformance. FMEA forces this risk to be explicit and quantified before it reaches the customer.

---

## 2. RPN Formula

**RPN = Severity × Occurrence × Detection**

| Score | Severity (S) | Occurrence (O) | Detection (D) |
|---|---|---|---|
| 1 | No discernible effect | Failure is unlikely (< 1 in 1,500,000) | Controls will almost certainly detect |
| 5 | Moderate effect; causes customer dissatisfaction | Occasional failure (1 in 400) | Controls may detect |
| 9–10 | Safety/regulatory impact | High failure rate | Controls are unlikely to detect |

RPN ranges from 1 (minimum risk) to 1,000 (maximum risk).

**Limitation of RPN alone:** Two failure modes with identical RPNs can have radically different risk profiles. For example, S=10, O=1, D=1 (RPN=10) describes a rare but catastrophic event — which a pure RPN ranking would bury at the bottom of the list. This is why the AIAG 5th Edition introduced the Action Priority system (see Section 4) and why this tool adds explicit Severity >= 9 flagging.

---

## 3. Risk Tier Assignment

This tool assigns each failure mode to one of three risk tiers:

| Tier | Condition | Meaning |
|---|---|---|
| Red | RPN > 100 **or** Severity >= 9 | Immediate corrective action required |
| Yellow | RPN 50–100 **and** Severity < 9 | Corrective action recommended |
| Green | RPN < 50 **and** Severity < 9 | Monitor; action at engineer's discretion |

**Source:** AIAG FMEA-4, Section 3. The RPN > 100 threshold is the most widely cited cutoff across Tier-1 aerospace and automotive suppliers.

---

## 4. AIAG FMEA-4 Action Priority

Three flag columns are computed for every failure mode:

**`Flag_High_RPN`** — True if RPN > 100.  
Standard AIAG FMEA-4 corrective action trigger. Represents 10% of the maximum possible RPN (1,000).

**`Flag_High_Severity`** — True if Severity >= 9.  
AIAG FMEA-4 and FMEA 5th Ed. both state that Severity 9–10 failure modes require corrective action *regardless of Occurrence and Detection scores*. A failure that rarely happens but causes a safety incident when it does cannot be optimized away by good detection.

**`Flag_Action_Priority_H`** — True if RPN >= 200 OR Severity >= 9.  
A simplified implementation of the AIAG FMEA 5th Edition (2019) Action Priority "High" tier. The full 5th Ed. AP system uses a 3-dimensional S×O×D lookup table; this tool uses a conservative threshold-based approximation that is defensible for most PFMEA applications.

---

## 5. Pareto 80/20 Applied to Risk

A Pareto chart ranks failure modes from highest to lowest RPN and overlays a cumulative percentage line. The **80% line** identifies the small subset of failure modes that together account for 80% of total RPN exposure — these are the modes where corrective action investment has the highest return.

In composite manufacturing, this typically surfaces 4–6 modes (out of 30+) that dominate risk: autoclave cure deviations, ply misalignment, and bag integrity failures. Focusing corrective action on these modes before addressing the long tail is the correct engineering priority.

The 80/20 rule in FMEA is directional, not a hard threshold. The goal is to use it to *rank* corrective action investment, not to ignore everything below 80%.

---

## 6. References

1. **AIAG FMEA-4** (4th Edition, 2008). *Potential Failure Mode and Effects Analysis (FMEA) Reference Manual.* Automotive Industry Action Group.
2. **AIAG/VDA FMEA Handbook** (1st Edition, 2019). *Failure Mode and Effects Analysis — Design FMEA, Process FMEA, FMEA-MSR.* AIAG + VDA joint publication.
3. ASQ. *Failure Mode Effects Analysis (FMEA).* quality.asq.org
4. Quality-One International. *FMEA — Failure Mode and Effects Analysis.* quality-one.com
5. See `docs/ASSUMPTIONS_LOG.md` for every threshold decision with source citations.
