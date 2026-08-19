---
name: spc
description: Build or analyze control charts and process capability studies by calling the quality-platform SPC MCP tools — X-bar/R, X-bar/S, I-MR, p/c/u attribute charts, EWMA and CUSUM, Western Electric/Nelson rule detection, Phase I/II baseline freezing, and Cp/Cpk/Pp/Ppk capability with its stability and normality gates. Use for control-chart, process-stability and process-capability requests, not FMEA risk scoring or Gage R&R measurement-system analysis.
---

# spc — chart a process and study its capability

Run an SPC workflow by calling the quality-platform MCP tools. The engine owns every
number; this skill decides which tool to call, in what order, and how to present what comes
back. See `skills/CONVENTIONS.md` for the rules this skill is written to.

## When to use

The user is looking at process measurements over time — a control chart, a run-rule question,
a Phase I baseline, or a capability study against spec limits. Pick the tool family by the
shape of the data:

| What the user has | Tool family |
|---|---|
| Variables data in subgroups, or one measurement per point | `spc_xbar_r` / `spc_xbar_s` / `spc_imr` |
| Attribute data — defectives or defect counts | `spc_p` / `spc_c` / `spc_u` |
| A hunt for a small sustained shift | `spc_ewma` / `spc_cusum` |
| An accepted baseline to monitor new data against | `spc_freeze_*`, then `spc_apply_*` |
| A question about out-of-control signals | `spc_detect_we_violations` or `spc_detect_nelson_violations` |
| Spec limits and a "is this process capable?" question | `spc_assess_stability`, then `spc_capability` |

Which chart for which subgroup size, when EWMA or CUSUM is the right answer instead of a
Shewhart chart, and every precondition a capability study carries live in
[`references/spc-method-notes.md`](references/spc-method-notes.md) — read it before routing,
rather than guessing from the table above.

Two routing rules that are not judgement calls:

- **Western Electric and Nelson are mutually exclusive.** Pick one rule set for a chart; never
  report both (`apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 8).
- **Never run either detector on an EWMA or CUSUM chart.** Those two statistics are
  autocorrelated by construction, so run rules produce systematic false alarms; they signal
  only on their own limit or decision-interval crossings (RULE 15). Refuse and explain rather
  than calling the tool — the MCP layer does not gate this for you.

This is not the skill for FMEA risk scoring (Risk Priority Number, Action Priority) or for
Gage R&R measurement systems analysis — those have their own tools on the same server.

## Steps

1. Connect to the quality-platform MCP server over stdio. The host normally has it
   configured already; if not, it launches as `python -m mcp_app.server` from the workspace
   root.
2. Establish the data shape before choosing anything: variables or attribute, the subgroup
   size, and whether this is a first retrospective look (Phase I) or monitoring against an
   already-accepted baseline (Phase II). Route per
   [`references/spc-method-notes.md`](references/spc-method-notes.md); ask the user rather
   than inferring a subgroup size or a chart type from the numbers.
3. For run-rule detection, take `cl` and `sigma` from the chart tool's own result. On an X-bar
   chart `sigma` is the sigma of the *plotted points* — the chart's `sigma_hat` divided by the
   square root of the subgroup size — not `sigma_hat` itself. It comes from the engine's
   result, never from a fresh pass over the raw data.
4. For a capability study, collect LSL and/or USL from the user (at least one is needed for an
   index) and establish stability first: call `spc_assess_stability`, or a chart tool followed
   by `spc_detect_we_violations`, and pass the resulting signal list as `spc_capability`'s
   `violations`. Omitting it leaves `stable` null, which means **not assessed** — report it
   that way and never read it as in control. Let `force_method="auto"` choose the distribution
   path, or call `spc_normality_test` if the user asks the normality question directly; do not
   pre-judge normality yourself.
5. Call the chosen tool(s) and report what came back **verbatim** — the limits, the signal
   list, the indices, the confidence intervals and every null among them. Never round,
   re-derive an index from another one, or run a "sanity check" calculation; a second opinion
   computed here is a defect, not a safeguard.
6. On a tool error — ragged or empty subgroups, an untabulated subgroup size, a non-finite or
   non-positive sample size, a sigma at or below zero, constant data, fewer than three
   observations, or a frozen baseline that does not match the new data's chart type — surface
   the message to the user and ask for corrected input. Never clamp a limit, drop a point, or
   substitute a default for a value the user did not give.

## Worked example

User: *"Here are ten subgroups of four parts each. Spec is 9.8 to 10.8 — is the process
capable?"*

Three calls, in order:

1. `spc_xbar_r` with the ten subgroups. The engine returns `xbarbar=10.355`,
   `rbar=0.24999999999999983`, `ucl_x=10.53725`, `lcl_x=10.17275` and
   `sigma_hat=0.12141816415735784`.
2. `spc_detect_we_violations` with the subgroup means as `points`, `cl=10.355`, and `sigma`
   set to the chart's plotted-point sigma (`sigma_hat` over the square root of 4,
   `0.06070908207867892`). It returns `[]` — no Western Electric signal on this baseline.
3. `spc_capability` with the same ten subgroups as `data`, `lsl=9.8`, `usl=10.8`, and
   `violations=[]` — the empty list from step 2, which is what states "assessed, in control".
   Abridged to the fields this example turns on; the engine also returns the
   method-selection fields (`normal_before`, `lambda_used`, `fitted_dist`, `note` and the
   rest), and a real report passes on every field it sent:

```json
{
  "method": "normal",
  "cp": 1.3726666666666678,
  "cpk": 1.2216733333333352,
  "pp": 1.1947035802691601,
  "ppk": 1.063286186439553,
  "pp_ci": [0.9304287839813086, 1.4584477931703752],
  "ppk_ci": [0.8056991824051143, 1.3208731904739919],
  "ppk_lower": 0.8471123581530918,
  "ci_estimator": "sample_sd_ddof1",
  "ci_df": 39,
  "mean": 10.355,
  "sigma_hat": 0.12141816415735784,
  "sigma_overall": 0.13950461806527573,
  "alpha": 0.05,
  "n": 40,
  "stable": true,
  "stability_note": null
}
```

Report those fields as engine output. The `cpk` value of 1.2216733333333352 falls in the
"Marginal — reduce variation before release-critical use" tier for 1.00-1.32 in
`apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 6; `stable` is `true` because the caller supplied an
empty violation list, which the engine takes as chart context rather than deriving one
(RULE 7). The absence of confidence intervals on `cp`/`cpk` is expected on this path, not a
gap — only Pp and Ppk carry intervals here, tagged by `ci_estimator` and `ci_df` (RULE 14).
Nothing above is re-derived in this skill.

`scripts/call_spc_capability.py` is the capability call as a runnable script, for when a shell
call is cheaper than a tool call.

## Reference

- [`references/mcp-tool-contract.md`](references/mcp-tool-contract.md) — the tool namespace
  convention, the request/response shape of every SPC tool (charts, freeze/apply, rule
  detection, capability, normality, stability), and the error contract.
- [`references/spc-method-notes.md`](references/spc-method-notes.md) — the full chart-selection
  matrix, Phase I versus Phase II, the EWMA/CUSUM parameter notes, and the capability
  preconditions, each cited to a rule in `apps/spc/docs/ASSUMPTIONS_LOG.md`.
