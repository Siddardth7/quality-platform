---
name: fmea
description: Score or rank Failure Mode and Effects Analysis (FMEA) rows by calling the quality-platform FMEA MCP tools — Risk Priority Number (RPN) and AIAG-VDA Action Priority (AP) for one Severity/Occurrence/Detection triple, a full DFMEA/PFMEA table, or a relational failure-mode model. Use for failure mode, root cause and risk-prioritization requests, not statistical process control or Gage R&R.
---

# fmea — score and rank failure modes

Run an FMEA workflow by calling the quality-platform MCP tools. The engine owns every
number; this skill decides which tool to call, in what order, and how to present what comes
back. See `skills/CONVENTIONS.md` for the rules this skill is written to.

## When to use

The user is working on failure modes and their risk — a DFMEA or PFMEA table, a single
rating triple, or a linked failure-mode model. Pick the tool by the shape of what they gave
you:

| What the user has | Tool |
|---|---|
| One Severity / Occurrence / Detection triple | `fmea_score` |
| A flat table of FMEA rows (11 columns) | `fmea_run` |
| A relational model — functions linked to failure modes, effects, causes, controls | `fmea_run_relational` |
| A question about what a rating *means* | `fmea_list_scales`, then `fmea_get_scale` |

Every scoring call returns two numbers: the Risk Priority Number and the AIAG-VDA Action
Priority. Present both. Action Priority is the standards-correct prioritization; the Risk
Priority Number is reported alongside it but is not itself a pass/fail test — the AIAG & VDA
FMEA Handbook (1st Ed., 2019) §3.5.9 says so directly, quoted in
`apps/fmea/docs/ASSUMPTIONS_LOG.md` RULE 1:

> The use of a Risk Priority Number (RPN) threshold is not a recommended practice for
> determining the need for actions.

So do not invent a threshold verdict from the Risk Priority Number alone. Report what the
engine returned and let Action Priority carry the prioritization weight.

This is not the skill for statistical process control (control charts, capability) or for
measurement systems analysis (Gage R&R) — those have their own tools on the same server. Nor
is it the skill for a question about what a standard itself says or why a threshold exists
("does AIAG publish an RPN action threshold?") — that is `quality-research`.

## Steps

1. Connect to the quality-platform MCP server over stdio. The host normally has it
   configured already; if not, it launches as `python -m mcp_app.server` from the workspace
   root.
2. Decide the shape of the request — one triple, a flat table, or a relational model — and
   route to `fmea_score`, `fmea_run` or `fmea_run_relational` accordingly.
3. For a flat table, collect all 11 required columns from the user: `ID`, `Process_Step`,
   `Component`, `Function`, `Failure_Mode`, `Effect`, `Severity`, `Cause`, `Occurrence`,
   `Current_Control`, `Detection`. Do not invent a value for a missing column — ask for it.
4. If the user asks what a rating *means* (not what number to assign), call
   `fmea_list_scales` and then `fmea_get_scale`. The default is `scale_id="2019"` (AIAG & VDA
   2019 PFMEA); use `scale_id="fmea4"` only if the user asks for the legacy scale, or
   `scale_id="custom"` with their own scale JSON. Say plainly that choosing a scale changes
   only what each 1-10 integer means to the analyst — it never changes the numbers
   `fmea_score`/`fmea_run`/`fmea_run_relational` return (`ASSUMPTIONS_LOG.md` RULE 6).
5. Call the chosen tool and report what it returned **verbatim**: `rpn` and
   `action_priority` for a single triple; for the table tools, the ranked rows with their
   `RPN`, `AP`, `Risk_Tier` and the three criticality flags. Never recompute, round,
   re-derive or "sanity check" a value — a second opinion computed here is a defect, not a
   safeguard.
6. On a tool error (a rating outside 1-10, a missing column, a duplicate ID or an unknown
   link reference in a relational model), surface the message to the user and ask for
   corrected input. Never clamp a rating or silently drop a row.

## Worked example

User: *"Score this failure mode: Severity 9, Occurrence 8, Detection 5. What's the RPN and
Action Priority?"*

Call `fmea_score` with `severity=9`, `occurrence=8`, `detection=5`. The engine returns:

```json
{"rpn": 360, "action_priority": "High"}
```

Report those two values as engine output. The Action Priority comes from the published AIAG
& VDA 2019 Action Priority table lookup (`ASSUMPTIONS_LOG.md` RULE 7); the Risk Priority
Number is the engine's own product of the three ratings (RULE 1). Neither is re-derived
here.

`scripts/call_fmea_score.py` is the same call as a runnable script, for when a shell call is
cheaper than a tool call.

## Reference

- [`references/mcp-tool-contract.md`](references/mcp-tool-contract.md) — the tool namespace
  convention, the request/response shape of all five FMEA tools, and the error contract.
- [`references/fmea-method-notes.md`](references/fmea-method-notes.md) — Action Priority
  (2019 AIAG-VDA) versus the FMEA-4 Risk Priority Number, and which one to lead with.
