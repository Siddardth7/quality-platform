# FMEA method notes (reference)

Why the `fmea` skill reports two numbers and leads with one of them. Everything here is
sourced from `apps/fmea/docs/ASSUMPTIONS_LOG.md`, which holds this repo's primary-source
citations; nothing is restated from the web, and no constant is copied here that the log
owns.

## Risk Priority Number — the FMEA-4 legacy metric

The Risk Priority Number is the product of Severity, Occurrence and Detection, ranging 1 to
1000. The engine computes it; the skill never does.

This repo flags rows above 100 (`Flag_High_RPN`). That threshold is **retained for
compatibility with FMEA-4-based workflows, not a standards requirement.** ASSUMPTIONS_LOG
RULE 1 records the handbook's own position, AIAG & VDA FMEA Handbook (1st Ed., 2019) §3.5.9,
verbatim:

> The use of a Risk Priority Number (RPN) threshold is not a recommended practice for
> determining the need for actions.

So a high number is a signal to report, not a verdict to announce.

## Action Priority — the 2019 AIAG-VDA method

Action Priority is a **lookup**, not a threshold approximation: the engine reads the
published AIAG & VDA "Action Priority (AP) for DFMEA and PFMEA" table and returns High,
Medium or Low. Emphasis order is Severity, then Occurrence, then Detection
(ASSUMPTIONS_LOG RULE 7).

High Severity does **not** auto-escalate. The handbook's own worked case — Severity 10,
Occurrence 2, Detection 2 — comes back `Low`, because a safety-critical failure that is rare
and well detected is not where action is most needed
(`quality_core/scoring.py` `action_priority` docstring). A host that expects "S=10 means
High" should recognise this as correct behaviour, not a bug — and should not re-derive it.

The table in this engine is transcribed and cell-verified against the handbook primary
source. RULE 7 documents a transcription error that was caught this way: an early draft of
the Severity 9-10 block, taken from a third-party reproduction, was shifted by one Occurrence
band and survived a monotonicity check — evidence that the shipped table is verified, not
assumed.

**FMEA-MSR is a different table.** The monitoring-and-system-response AP table is not the one
this engine implements (RULE 7). If a user is specifically doing an MSR FMEA, say so rather
than reporting an AP value as if it applied.

## Which one to report

Both come back from every scoring call. Present both, let Action Priority carry the
prioritization weight per the handbook's own recommendation, and never manufacture a
pass/fail verdict from the Risk Priority Number alone.

## Rating scale choice is orthogonal

Selecting the 2019 default, the FMEA-4 legacy scale, or a custom scale changes only what each
1-10 integer *means* to the analyst assigning it. It never changes the Risk Priority Number
or the Action Priority the engine returns (ASSUMPTIONS_LOG RULE 6). Scale text also carries a
standards caveat the log states in full: the AP table was calibrated to the 2019 S/O/D
tables, so pairing Action Priority with the FMEA-4 legacy scale or a custom rubric is the
modify-the-tables case the handbook warns about. Point a user at RULE 6 rather than
summarising the caveat away.
