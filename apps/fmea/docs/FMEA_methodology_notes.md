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

## 4. Action Priority — RPN-era flags and the AIAG-VDA AP engine

The tool offers **two prioritization bases**, switchable in the app (and carried
into exports): the classic **RPN** score and the AIAG/VDA 2019 **Action Priority
(AP)**. Both are always computed; the toggle selects which one ranks and tiers
the view.

### 4.1 RPN-era criticality flags

Three boolean flags accompany the RPN score, grounded in AIAG FMEA-4:

**`Flag_High_RPN`** — True if RPN > 100.
Standard AIAG FMEA-4 corrective action trigger. Represents 10% of the maximum possible RPN (1,000).

**`Flag_High_Severity`** — True if Severity >= 9.
AIAG FMEA-4 and the AIAG/VDA Handbook both state that Severity 9–10 failure modes require corrective action *regardless of Occurrence and Detection scores*. A failure that rarely happens but causes a safety incident when it does cannot be optimized away by good detection.

**`Flag_Action_Priority_H`** — True if RPN >= 200 OR Severity >= 9.
A **threshold heuristic on the RPN side** that approximates the AP "High" tier. It is intentionally kept as a quick flag alongside RPN; it is *not* the AP engine. For the standard's actual High/Medium/Low determination, use the AP engine below (§4.2).

### 4.2 AIAG-VDA 2019 Action Priority (AP) engine

The AIAG/VDA FMEA Handbook (2019) replaced RPN-based prioritization with **Action
Priority**: a published lookup table that maps each S×O×D combination directly to
**High / Medium / Low**. AP fixes RPN's core flaw (§2) by making **Severity the
dominant factor — emphasis order S → O → D** — rather than treating the three
terms as interchangeable multiplicands.

`fmea_app/ap_engine.py` implements the full published table (no approximation):

- `action_priority(s, o, d)` → `"High" | "Medium" | "Low"` (pure scalar lookup).
- `calculate_ap(df)` adds the `AP` column; `rank_by_ap(df)` orders High → Medium
  → Low with RPN/Severity/ID as stable tiebreaks.

The table is grouped into bands — **S {9-10, 7-8, 4-6, 2-3, 1}**,
**O {8-10, 6-7, 4-5, 2-3, 1}**, **D {7-10, 5-6, 2-4, 1}** — and reads as
"Severity dominates": S 9-10 is almost entirely High, S 1 is Low everywhere. Each
severity block below is an Occurrence × Detection grid (Detection columns ordered
worst → best: D 7-10, 5-6, 2-4, 1):

**Severity 9-10**

| O \ D | 7-10 | 5-6 | 2-4 | 1 |
|---|:---:|:---:|:---:|:---:|
| 8-10 | H | H | H | H |
| 6-7  | H | H | H | H |
| 4-5  | H | H | H | H |
| 2-3  | H | H | H | M |
| 1    | H | M | L | L |

**Severity 7-8**

| O \ D | 7-10 | 5-6 | 2-4 | 1 |
|---|:---:|:---:|:---:|:---:|
| 8-10 | H | H | H | H |
| 6-7  | H | H | H | M |
| 4-5  | H | M | M | M |
| 2-3  | M | M | L | L |
| 1    | L | L | L | L |

**Severity 4-6**

| O \ D | 7-10 | 5-6 | 2-4 | 1 |
|---|:---:|:---:|:---:|:---:|
| 8-10 | H | H | M | M |
| 6-7  | M | M | M | L |
| 4-5  | M | L | L | L |
| 2-3  | L | L | L | L |
| 1    | L | L | L | L |

**Severity 2-3**

| O \ D | 7-10 | 5-6 | 2-4 | 1 |
|---|:---:|:---:|:---:|:---:|
| 8-10 | M | M | L | L |
| 6-7  | L | L | L | L |
| 4-5  | L | L | L | L |
| 2-3  | L | L | L | L |
| 1    | L | L | L | L |

**Severity 1** — Low for every Occurrence and Detection combination.

**Worked example:** `S=10, O=2, D=2` → RPN = 40 (which a pure RPN ranking would
bury), but AP = **High** because a safety-severity failure is High regardless of
how rare or detectable it is — the handbook's own RPN-vs-AP illustration.

The transcription is guarded by tests against an independent copy of the published
table (all 1000 S/O/D combinations) plus a monotonicity invariant: AP never
decreases when any one of S, O, or D increases. See `tests/test_ap_engine.py` and
`docs/ASSUMPTIONS_LOG.md` Rule 7.

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
