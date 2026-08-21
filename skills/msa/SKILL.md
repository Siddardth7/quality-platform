---
name: msa
description: Validate a measurement system by calling the quality-platform MSA MCP tool — crossed Gage R&R via Average-and-Range or ANOVA, returning %GRR (study-variation and tolerance bases), ndc, EV/AV/PV components and an AIAG-cited Accept/Marginal/Reject verdict. Use for gauge study, repeatability & reproducibility, %GRR/ndc and measurement-system-capability requests, not control charts/process capability or FMEA risk scoring.
---

# msa — run a Gage R&R study

Validate a measurement system by calling the quality-platform MSA MCP tool. The engine owns
every number; this skill decides what study to ask for, which method, and how to present what
comes back. See `skills/CONVENTIONS.md` for the rules this skill is written to.

## When to use

The user is asking whether they can trust their gauge — a Gage R&R study, repeatability and
reproducibility, %GRR, ndc, or the equipment- and appraiser-variation components of a
measurement system.

**There is one MSA analysis tool, `msa_gage_rr`.** The design problem here is study intake, not tool
choice: unlike the SPC and FMEA skills there is no routing table, because there is nothing to
route to. What decides whether the answer means anything is whether the study handed to the
tool is a valid crossed design — so run the intake checklist below before calling anything.

This is not the skill for control charts or process capability (SPC) or for failure-mode risk
scoring (FMEA) — those have their own tools on the same server. Nor is it the skill for a
question about what a standard itself says or why a threshold exists ("why is the ndc
threshold 5?") — that is `quality-research`.

## Intake checklist

Walk this with the user first. If an item is missing, ask for it; do not fill it in yourself.

- **Design — crossed and balanced.** Every part is measured by every appraiser, with the same
  number of trials in every (part, appraiser) cell. An unbalanced study is a structured tool
  error raised before either method runs — never drop rows or invent a measurement to balance
  it (`apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 11; the balance requirement is this platform's
  inference from AIAG's procedure, not an AIAG statement, so do not present it as one).
- **Size.** The platform floor is 2 parts, 2 appraisers and 2 trials per cell — a computability
  floor, not a quality bar (RULE 12). AIAG's own optimum is 10 parts × 3 appraisers × 3 trials.
  A study at the floor is arithmetically valid and statistically weak; say so to the user
  rather than letting a 2×2×2 study read as equivalent to a 10×3×3 one.
- **Data shape — long/tidy, one row per measurement.** Keys `part`, `appraiser`, `trial`,
  `measurement`:

  ```json
  {"part": 1, "appraiser": "A", "trial": 1, "measurement": 10.00}
  ```

  This is **not** the wide-subgroup shape the SPC chart tools take; do not conflate the two. If
  the user's data is wide (say one column per trial), reshape it to long form before calling —
  that is a data-shape transform, not a computation, and no AIAG number is derived by doing it.
- **Tolerance — optional.** Ask for it (USL − LSL) only if the user cares about the
  tolerance-basis percentages, or says "spec", "USL", "LSL" or "tolerance". Without one the
  study-variation basis is still complete: the four tolerance-basis keys come back `null`,
  which means "not requested", not "failed". Never invent a tolerance.
- **Method.** Default to Average-and-Range. Raise ANOVA only if the user cares about the
  part × appraiser interaction, or wants to re-run because the Average-and-Range result looks
  suspicious ([`references/msa-method-notes.md`](references/msa-method-notes.md), RULES 1 and 17).
- **Degenerate study.** If every measurement is identical the total variation is zero, the
  tool still returns a result, the study-basis %GRR comes back as infinity or a very large
  number, and the verdict is `"Reject"` (RULE 13 — a platform design choice, not AIAG). Tell
  the user that is expected behaviour and ask them to check the data if it was unintended;
  never substitute a value to avoid it.

## Steps

1. Connect to the quality-platform MCP server over stdio. The host normally has it configured
   already; if not, it launches as `python -m mcp_app.server` from the workspace root.
2. Run the intake checklist above with the user. Do not call the tool on an incomplete or
   unbalanced study description — ask for what is missing.
3. Decide `method`. `"average_and_range"` is the default; `"anova"` additionally estimates and
   tests the part × appraiser interaction. Average-and-Range cannot see that interaction, and
   its %GRR is biased low when the interaction is non-zero — the tradeoff and its citations are
   in [`references/msa-method-notes.md`](references/msa-method-notes.md) (RULES 1, 17).
4. Ask for `tolerance` only per the checklist. Omitting it still produces a complete
   study-variation-basis result.
5. Call `msa_gage_rr` with `study` (long/tidy), `method` and `tolerance`.
6. Report the returned dict **verbatim**: the EV, AV, GRR, PV and TV components, all four
   study-basis percentages and — when a tolerance was given — all four tolerance-basis ones,
   `ndc`, `verdict`, `method`/`method_note`, and the interaction triple. Never recompute,
   round, or "sanity check" a value; a second opinion computed here is a defect, not a
   safeguard.
7. On a tool error — empty study, fewer than 2 parts or appraisers, fewer than 2 trials in a
   cell, an unbalanced design, a non-numeric/NaN/infinite measurement, a non-positive
   tolerance, or an unknown method — surface the message verbatim and ask for corrected input.

## Worked example

User: *"Three parts, two operators, two repeats each, spec width 2.0 — is my gauge good
enough?"*

That is a balanced 3 × 2 × 2 crossed study, above the 2/2/2 floor. In long/tidy form:

```python
study = [
  {"part": 1, "appraiser": "A", "trial": 1, "measurement": 10.00},
  {"part": 1, "appraiser": "A", "trial": 2, "measurement": 10.01},
  {"part": 1, "appraiser": "B", "trial": 1, "measurement": 10.01},
  {"part": 1, "appraiser": "B", "trial": 2, "measurement": 10.02},
  {"part": 2, "appraiser": "A", "trial": 1, "measurement": 10.50},
  {"part": 2, "appraiser": "A", "trial": 2, "measurement": 10.51},
  {"part": 2, "appraiser": "B", "trial": 1, "measurement": 10.49},
  {"part": 2, "appraiser": "B", "trial": 2, "measurement": 10.52},
  {"part": 3, "appraiser": "A", "trial": 1, "measurement": 11.00},
  {"part": 3, "appraiser": "A", "trial": 2, "measurement": 11.02},
  {"part": 3, "appraiser": "B", "trial": 1, "measurement": 11.01},
  {"part": 3, "appraiser": "B", "trial": 2, "measurement": 11.00},
]
```

One call: `msa_gage_rr` with that `study`, `method="average_and_range"` and `tolerance=2.0`.
The engine returns:

```json
{
  "ev": 0.013292999999999717,
  "av": 0.0,
  "grr": 0.013292999999999717,
  "pev_study": 2.5467393315688454,
  "pav_study": 0.0,
  "pgrr_study": 2.5467393315688454,
  "ppv_study": 99.96756533384735,
  "pev_tolerance": 3.987899999999915,
  "pav_tolerance": 0.0,
  "pgrr_tolerance": 3.987899999999915,
  "ppv_tolerance": 156.5376750000001,
  "ndc": 55,
  "verdict": "Accept",
  "tv": 0.5219615464850479,
  "pv": 0.5217922500000003,
  "mean": 10.5075,
  "n_parts": 3,
  "n_appraisers": 2,
  "n_trials": 2,
  "is_balanced": true,
  "method": "average_and_range",
  "method_note": "Average-and-Range method: the part x appraiser interaction is NOT estimated. AIAG MSA 4th Ed., Ch. III Sec. B: the Average and Range method \"does not include\" the operator-to-part interaction, which is therefore absorbed into the reported components; %GRR is biased low when that interaction is non-zero. ANOVA (which separates it) is available via method=\"anova\".",
  "interaction": null,
  "interaction_f": null,
  "interaction_significant": null
}
```

Report those fields as engine output. The verdict prose the skill may add on top of them is
only the band lookup: `pgrr_study` of 2.55% and `pgrr_tolerance` of 3.99% both fall in
Table II-D 1's *"Under 10 percent"* → *"Generally considered to be an acceptable measurement
system."* row (`apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 7), and the returned `ndc` of 55 is far
above AIAG's *"This value should be greater than or equal to 5."* (RULE 9). Those two
conditions together are what the engine's `"Accept"` verdict encodes (RULE 10) — the skill
names the band, it does not re-derive the number.

Two fields that routinely read as bugs and are not:

- `"av": 0.0` is computed and clamped, not skipped — the appraiser-difference term came out
  negative under the square root and defaults to zero, which the manual prescribes (RULE 14).
- `"interaction": null` genuinely means "not applicable under this method": Average-and-Range
  cannot estimate the part × appraiser interaction (RULE 1). Branch on null, not on zero.

And the verdict is a guideline flag, not a release decision — AIAG says so itself, quoted in
[`references/msa-method-notes.md`](references/msa-method-notes.md).

`scripts/call_msa_gage_rr.py` is the same call as a runnable script, for when a shell call is
cheaper than a tool call.

## Reference

- [`references/mcp-tool-contract.md`](references/mcp-tool-contract.md) — the tool namespace
  convention, the request/response shape of `msa_gage_rr`, the error contract and transport.
- [`references/msa-method-notes.md`](references/msa-method-notes.md) — Average-and-Range versus
  ANOVA, the AIAG %GRR bands on both bases, the ndc threshold and which parts of the verdict
  are AIAG's and which are this platform's, each cited to `apps/msa/docs/ASSUMPTIONS_LOG.md`.
