# SPC method notes (reference)

How the `spc` skill chooses a chart, what Phase I and Phase II mean here, and what a
capability study requires before its numbers mean anything. Everything below is sourced from
`apps/spc/docs/ASSUMPTIONS_LOG.md`, which holds this repo's primary-source citations; nothing
is restated from the web, and no constant the log owns is copied here.

## Choosing a chart

Start with the kind of data, then the subgroup size.

| Data | Situation | Tool | Rule |
|---|---|---|---|
| Variables | one measurement per point (n=1) | `spc_imr` | RULE 3 |
| Variables | subgroup size 2-9 | `spc_xbar_r` | RULE 1 |
| Variables | subgroup size 10 and above (tabulated to 12) | `spc_xbar_s` | RULE 2 |
| Attribute | proportion defective, variable sample size | `spc_p` | RULE 4 |
| Attribute | defect count per constant-size inspection unit | `spc_c` | RULE 4 |
| Attribute | defects per unit, variable sample size | `spc_u` | RULE 4 |
| Variables | hunting a small sustained shift | `spc_ewma` or `spc_cusum` | RULES 12-13 |

The 2-9 versus 10-and-above boundary is the tabulated-constants line: X-bar/R carries A2/D3/D4
for subgroup sizes 2-10 (RULE 1) and X-bar/S carries A3/B3/B4 for 2-12 (RULE 2). X-bar/S is
preferred once the subgroup gets large because S uses every observation in the subgroup rather
than only its two extremes. The same boundary is cited cross-app in
`apps/controlplan/docs/ASSUMPTIONS_LOG.md` RULE 1, so do not re-draw it here.

A subgroup size outside a chart's tabulated range is a structured tool error, not a licence to
substitute a nearby constant. Ask the user to re-subgroup.

## Phase I versus Phase II

A first, retrospective look at a set of data is **Phase I**: call the plain chart tool and the
limits are computed from that data itself. Once a baseline has been reviewed and accepted, it
is frozen (`spc_freeze_xbar_r`, `spc_freeze_xbar_s`, `spc_freeze_imr`) and new data is charted
against those fixed limits (`spc_apply_xbar_r`, `spc_apply_xbar_s`, `spc_apply_imr`) — that is
**Phase II**, and the fact that nothing is recomputed from the new data is what makes a Phase
II signal meaningful (RULE 11).

Three things RULE 11 fixes and the skill must not soften:

- **Freeze/apply exists only for the three Shewhart variables charts.** There is no freeze or
  apply tool for p, c, u, EWMA or CUSUM. Do not imply otherwise.
- **Excluding a baseline point requires a documented cause.** The Phase I loop is signal, then
  assignable cause, then removal, then recompute. An exclusion without a cause string is a
  tool error, and rightly so.
- **`baseline_adequate` / `baseline_note` are a soft gate.** A baseline below the minimum
  subgroup or individuals count sets the flag and the note; it never raises. Report the note —
  a thin baseline is weak evidence, not invalid evidence.

## Run-rule sets

Western Electric (4 rules, same-side run length 8) and Nelson (8 tests, its own numbering,
same-side run length 9) are two complete, self-consistent sets, and `rule_set` is mutually
exclusive: pick one per chart and never mix labels across them (RULE 8). Both are exposed as
their own tool, `spc_detect_we_violations` and `spc_detect_nelson_violations`.

The stability gate uses Western Electric by default rather than the fuller Nelson set, to avoid
over-flagging benign trend and alternating patterns (RULE 7).

**Citation status, stated rather than papered over:** RULE 8 marks both sets'
primary text as **unverified — third-party reproduction only**. The Western Electric
*Statistical Quality Control Handbook* (1956) and Nelson's 1984 *Journal of Quality Technology*
paper are neither of them in this repo; the corroborating source the log actually quotes is the
NIST/SEMATECH e-Handbook §6.3.2, which reproduces the WECO rules as implemented. Do not present
the rule text to a user as verified against a primary standard.

### The EWMA/CUSUM prohibition

**Never call `spc_detect_we_violations` or `spc_detect_nelson_violations` on an EWMA or CUSUM
chart's points.** This is a hard rule, not a caveat (RULE 15). Both statistics are
autocorrelated by construction — each plotted point is a function of all prior points — so
run-length patterns occur far more often than the independent-point run-rule tables assume, and
applying the rules produces systematic false alarms. EWMA and CUSUM signal exclusively on their
own limit and decision-interval crossings, which is the complete detection mechanism for those
charts.

Run rules *are* valid on p, c and u charts: the Shewhart family in RULE 15 is X-bar/R, X-bar/S,
I-MR, p, c and u. "Attribute chart" is not the same category as "autocorrelated chart".

The engine enforces this at its own chokepoint for its own callers, but the MCP tools expose
the two detectors directly — so on this path the skill is the enforcement point. Refuse and
explain rather than making the call.

## EWMA and CUSUM parameters

Both charts detect a small sustained shift faster than a Shewhart chart, and both need `mu0`
and `sigma` supplied as **independent Phase I estimates — never derived from the series being
charted** (RULES 12-13). If the user has no prior baseline, chart the baseline first and get
the estimates from that, or say the shift test cannot be run yet.

- **EWMA** (`spc_ewma`): `lam` is the smoothing weight and `L` the limit multiplier. The
  defaults are a cited pairing chosen for a target average run length, and the tabulated
  pairings live in the engine's constants — do not invent a pairing. A mismatched `lam`/`L`
  is still computed, but comes back with `pairing_adequate=False` and a `pairing_note` naming
  the recommended `L`; surface that note (RULE 12). EWMA limits are deliberately time-varying:
  tighter at the start of the series, widening toward an asymptote.
- **CUSUM** (`spc_cusum`): `k` is the reference value and `h` the decision interval in sigma
  units, both defaulting to the cited engine values; `fir=True` applies an optional head start
  to both arms, which shortens detection of a shift already present at startup (RULE 13). Both
  accumulator series are stored as positive accumulators — a negated lower arm is a display
  convention, not the data.

## Capability preconditions

`spc_capability` will return something for almost any input. Whether it *means* anything
depends on three gates, all of which the caller is responsible for.

1. **Spec limits.** At least one of LSL/USL is needed for an index. With neither, the indices
   come back null and nothing raises — report the nulls as nulls (RULE 5).
2. **Stability.** Capability indices assume the process is in statistical control; computing
   them on an unstable process is misleading (RULE 7). Establish it by calling
   `spc_assess_stability`, or a chart tool followed by `spc_detect_we_violations`, and pass the
   signal list in as `violations`. The resulting `stable` field is **tri-state**: `true`
   (assessed, in control), `false` (assessed, signals present — the indices still render, and
   render as indicative only, with a `stability_note`), or `null`, which means *not assessed*
   and is never to be read or reported as in control. The engine deliberately does not derive
   the chart itself: an I-MR chart on a flattened subgrouped stream understates sigma and flips
   verdicts (#191).
3. **Normality and method selection.** `force_method="auto"` runs Shapiro-Wilk (the p > 0.05
   gate, RULE 9) and picks a path: normal theory, a Box-Cox or Yeo-Johnson transform, or, if
   the data is still non-normal after transforming, an ISO 22514-2 fitted-percentile method on
   the original untransformed data (RULE 14). Let the tool choose. Name the path it reports via
   `method`; do not restate the transform math and do not pre-judge normality by eye.

Two things fall out of the method choice and routinely look like bugs when they are not.
Confidence intervals attach only to the estimator they were derived for — Pp and Ppk on the
normal path, Cp and Cpk on the percentile path, with the other pair null and `ci_estimator` /
`ci_df` identifying which is which (RULE 14). And the within-subgroup sigma behind Cp/Cpk is a
different estimate from the overall sigma behind Pp/Ppk, so the two pairs are expected to
differ; that spread is a signal about between-subgroup variation, not an inconsistency to
reconcile (RULE 5).

### Interpreting Cpk

RULE 6 sets the tiers this repo reports against:

| Cpk | Interpretation |
|---|---|
| below 1.00 | Not capable |
| 1.00 - 1.32 | Marginal — reduce variation before release-critical use |
| 1.33 and above | Capable — common minimum target for stable manufacturing |

Quote the tier, cite RULE 6, and leave the boundary alone. The engine returns the index; this
skill only says which band the log puts it in.
