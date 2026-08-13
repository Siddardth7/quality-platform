# Control Plan method notes (reference)

Where the `control-plan` skill's numbers and defaults come from, and — as often matters more
here — where they demonstrably do *not* come from. Everything below is sourced from
`apps/controlplan/docs/ASSUMPTIONS_LOG.md` and `apps/controlplan/CLAUDE.md`, which hold this
repo's citations for the Control Plan surface; nothing is restated from the web and no constant
the log owns is copied into the skill body.

## Chart-selection table provenance

RULE 1. The rule table behind `controlplan_recommend_chart` is cited to the **AIAG SPC
Reference Manual, 4th Ed. (2005)** control-chart selection logic — the same primary source
already cited by `apps/spc/docs/ASSUMPTIONS_LOG.md` and by `quality_core.scoring` for the
Action Priority table:

- Variable data: `n == 1` → `I-MR`; `2 <= n <= 9` → `Xbar-R`; `n >= 10` (up to 12) → `Xbar-S`;
  `n > 12` → error (see the upper bound below).
- Attribute data: classifying units good/bad → `p` (`np` folds into `p`; the `SPCChart` schema
  Literal has no `np` key); counting defects per unit with a constant sample → `c`; with a
  variable sample → `u`.

**One cell of that table is flagged open.** RULE 1's "Flag" paragraph, verbatim:

> **Flag — the Xbar-R ↔ Xbar-S boundary (n = 9 vs 10):** third-party references disagree by
> one (SPC for Excel and the Six Sigma Study Guide say "n ≥ 9 → S"; Montgomery, *Introduction
> to Statistical Quality Control*, says "n > 10 → S"). This connector hard-codes
> `n >= 10 -> Xbar-S` (n ≤ 9 stays Xbar-R) as the default. **This one number should be
> confirmed against the primary AIAG SPC Reference Manual, 4th Ed. (2005) decision tree before
> being treated as final** — it is the one cell in the rule table sourced from a third-party
> reproduction rather than the primary manual directly, the way `tests/test_scoring.py`
> independently re-verifies the AP grid against the AIAG/VDA standard.

Do not soften or drop that caveat when a subgroup size of 9 or 10 decides the answer. It is an
engine-level flag on an app's assumptions log; a skill reports it, it does not resolve it.

## Placeholder fields — sample size, frequency, reaction plan (#196 F-10)

RULE 2. `build_control_plan` derives `characteristic` and `measurement_method` from the
relational FMEA, but `sample_size`, `frequency` and `reaction_plan` have **no FMEA-model
equivalent** — severity, occurrence and detection carry no sample plan and no containment text.
They are defaulted, and the log is explicit about what that default is worth:

> **Source:** Not a published standard — an explicit placeholder decision (SME-confirmed,
> `.pipeline/spec.md` "SME RESOLUTIONS" §4), the same way the AP thresholds in
> `apps/fmea/docs/ASSUMPTIONS_LOG.md` are recorded even though they are project conventions
> rather than universal constants.

There is no AIAG reaction-plan or sample-plan table behind these three fields. Do not cite one,
and do not invent one to fill the gap.

`sample_plan_is_placeholder` is the provenance flag that makes this visible on the wire (F-10,
#196). Its exact semantics:

- It defaults to `false` — an uploaded or hand-edited row asserts its own values.
- Only `controlplan_build` output sets it `true`, and it sets it on **every** row it emits.
- It is an optional ingest column, so an upload predating the field still validates.

So `true` means "these three fields are defaults, not engineering". Say that to the user rather
than presenting the row as complete.

## Why `n > 12` raises rather than answering (#196 F-07)

RULE 1, "Upper bound", verbatim:

> `Xbar-S` is only computable for subgroup sizes the AIAG X-bar/S constants table covers
> (`quality_core.spc.constants.XBAR_S_CONSTANTS`, keys 2–12; `compute_xbar_s` raises "X-bar S
> chart requires subgroup size between 2 and 12." above it). `recommend_chart` therefore raises
> `ValueError` for variable data with `n > 12` rather than naming a chart the engine cannot
> compute. The ceiling is read from the constants table (`max(XBAR_S_CONSTANTS)`), not
> hard-coded. Extending the table above n=12 would require A3/B3/B4/c4 values that are not in
> any on-machine primary source, so it is deliberately not done. The bound applies to variable
> data only — attribute charts (`p`/`c`/`u`) take a sample size with no constants table, and
> large n is normal there.

The error is the correct answer, not a failure to answer. Surface it verbatim; never clamp the
subgroup size to 12, and never fall back to `I-MR`.

## Mapping decisions that are SME-locked

Two decisions are recorded as SME-confirmed in the connector docstring and
`apps/controlplan/CLAUDE.md` ("Conventions that matter here"):

- **Granularity (Q1)** — one `ControlPlanRow` per `FailureMode`. Not per link, not per cause,
  not per effect.
- **Characteristic naming (Q2)** — `f"{component} — {failure_mode.description}"`, with the
  failure-mode id and then an incrementing counter appended on collision, so distinct rows
  never share a name. This is a naming convention, not an FMEA field.

Neither is the skill's or the user's to re-decide. The collision-suffix algorithm itself is
implementation detail owned by `apps/controlplan/controlplan_app/connector.py` — point there if
someone wants the detail, rather than restating it and letting the two drift.
