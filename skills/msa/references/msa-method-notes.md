# MSA method notes (reference)

How the `msa` skill chooses a method, what a valid study needs before its numbers mean
anything, and which parts of the verdict are AIAG's and which are this platform's. Everything
below is sourced from `apps/msa/docs/ASSUMPTIONS_LOG.md`, which holds this repo's
primary-source citations; nothing is restated from the web, no quotation is re-derived from the
manual here, and no constant the log owns is copied into the skill body.

## Average-and-Range versus ANOVA

Average-and-Range is the engine's default (RULE 1). AIAG names three acceptable techniques and
states the trade-off between them directly:

> "Except for the Range method, the study data design is very similar for each of these methods.
> The ANOVA method is preferred because it measures the operator to part interaction gauge error,
> whereas the Range and the Average and Range methods does not include this variation." [sic —
> the manual's own grammar, quoted unaltered]

The two are equivalent under AIAG's own zero-interaction precondition:

> "The ANOVA approach can identify appraiser-part interaction but it can also evaluate other
> sources of variation which is the reason why it was included. Historically, the assumption is
> made that the interaction is zero, in which case the results of both approaches are equivalent."

So the practical rule: the Average-and-Range %GRR is **biased low** whenever the part × appraiser
interaction is non-zero — the case its own precondition excludes and the method cannot detect.
Re-running with `method="anova"` separates and F-tests that interaction (RULE 17). Whichever
technique ran is declared in the returned `method` / `method_note`; report it, so nobody mistakes
an Average-and-Range result for an ANOVA one.

## %GRR acceptance bands — study-variation basis

RULE 7, AIAG MSA 4th Ed., Ch. II Sec. D, **Table II-D 1 "GRR Criteria"**. Its lead-in reads
*"For measurement systems whose purpose is to analyze a process, a general guidelines [sic — the
manual's own grammar] for measurement system acceptability is as follows:"*, and the table gives:

| GRR | Decision |
|---|---|
| "Under 10 percent" | "Generally considered to be an acceptable measurement system." |
| "10 percent to 30 percent" | "May be acceptable for some applications" |
| "Over 30 percent" | "Considered to be unacceptable" |

Quote those rows; do not reframe them into a different threshold wording.

## %GRR on the tolerance basis

RULE 8. The tolerance basis is a denominator swap, stated outright by Ch. III Sec. B:

> "In that case, *%EV*, *%AV*, *%GRR* and *%PV* are calculated by substituting the value of
> tolerance *divided by six* in the denominator of the calculations in place of the total
> variation (*TV*). **Either or both approaches can be taken depending on the intended use of the
> measurement system and the desires of the customer.**"

Two consequences the log fixes explicitly:

- **One band set applies to BOTH bases** — the same 10 / 30 rows above. Ch. III Sec. B redirects
  to Table II-D 1 for the rule of thumb, and RULE 8 records a *refuted* proposal for a separate
  tolerance-only band set. Never introduce a second band set.
- The `6` is the 4th edition's convention; **5.15 is the superseded 3rd-edition figure** and is
  not used here.

When both bases are available, the engine drives its verdict from the **worse (higher)** of the
two %GRR values (RULE 10, SME resolution). That is the engine's behaviour — the skill reports it,
it does not perform the comparison.

## ndc — number of distinct categories

RULE 9. AIAG's single published acceptance criterion, Ch. II Sec. D:

> "This statistic indicates the number of categories into which the measurement process can be
> divided. This value should be greater than or equal to 5."

and Ch. III Sec. B, on reducing it to an integer:

> "For analysis, the *ndc* is the maximum of one or the calculated value truncated to the integer.
> This result should be greater than or equal to 5."

That is a single pass/fail threshold, not a graded scale. The engine's **2–4 = Marginal** and
**below 2 = Reject** sub-bands are **not in AIAG MSA** — they are this platform's own design
layered on AIAG's one threshold (RULE 9's "Sub-bands below 5 — NOT in AIAG MSA" heading).
State that distinction plainly rather than attributing the sub-bands to AIAG. Nothing below 5 is
ever reported as Accept, so the sub-bands do not loosen AIAG's rule. The upper clamp at 100 is
likewise this platform's, for display sanity, and does not affect a verdict.

## The verdict

RULE 10 crosses ndc with %GRR, and the matrix names each column's provenance:

| ndc | ndc source | %GRR | %GRR source | Verdict |
|---|---|---|---|---|
| ≥ 5 | **AIAG** — Ch. II Sec. D | under 10% | **AIAG** — Table II-D 1 | **Accept** |
| 2–4 | *platform* (RULE 9) | 10–30% | **AIAG** — Table II-D 1 | **Marginal** |
| < 2 | *platform* (RULE 9) | over 30% | **AIAG** — Table II-D 1 | **Reject** |

Report the verdict the engine returned and cite the matrix; do not re-derive it in prose.

**It is a flag, not a release decision.** AIAG says so itself (quoted in RULE 8, Ch. II §D):

> "The use of the GRR guidelines as threshold criteria alone is NOT an acceptable practice for
> determining the acceptability of a measurement system."

The same framing as the `fmea` skill's "a Risk Priority Number threshold is not a verdict".

## Study intake preconditions — the "why" behind the checklist

- **Balance (RULE 11).** AIAG never *asserts* that Average-and-Range requires a balanced crossed
  design; it *prescribes a procedure that is balanced by construction* — "Let appraiser A measure
  n parts in a random order", "Let appraisers B and C measure the same n parts without seeing each
  other's readings" — and gives no procedure for anything else. The requirement is this platform's
  inference from that, and the load-bearing reason is mechanical: the method's K constants are
  looked up by subgroup size and count, and unequal cell sizes leave no single size to look up. So
  the engine refuses rather than silently analysing a common subset, which would change the study
  the user thinks they ran. Present the requirement as the platform's inference, not as an AIAG
  statement.
- **Size (RULE 12).** The 2 / 2 / 2 floor is **not AIAG's** — it is a deliberate platform
  relaxation, the point below which the arithmetic has no answer at all, not the point above which
  the answer is trustworthy. AIAG's own text is:

  > "Although the number of appraisers, trials and parts may be varied, the subsequent discussion
  > represents the optimum conditions for conducting the study."

  > "Obtain a sample of *n* ≥ 10 parts that represent the actual or expected range of process
  > variation."

  with footnote 44 adding *"The total number of 'ranges' generated ought to be > 15 for a minimal
  level of confidence in the results."* A 2 × 2 × 2 study generates 4 ranges, well under that — so
  it is sub-optimal, not non-conforming, and a small-study result should be read accordingly.

## Edge cases

- **Every measurement identical (RULE 13).** Total variation is zero, so the study-basis %GRR is
  infinite and the verdict is `"Reject"`. **Not in AIAG MSA — an internal design choice**: a
  measurement system that sees no variation cannot demonstrate that it is adequate. Expected
  behaviour, not a bug.
- **Negative appraiser-variance term (RULE 14).** The manual prescribes the clamp explicitly,
  Ch. III Sec. B:

  > "If a negative value is calculated under the square root sign, the appraiser variation (*AV*)
  > defaults to zero."

  So a returned `av` of zero means computed-and-clamped, not "not computed" — which is what the
  null interaction fields mean instead.
