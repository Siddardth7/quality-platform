---
name: example-skill
description: Template skill — copy this folder to start a new quality-platform skill. Demonstrates scoring one FMEA Severity/Occurrence/Detection triple by calling the fmea_score MCP tool; do not install directly.
---

# Example skill — score one FMEA triple

This is the copy-from template for quality-platform skills. It shows the whole pattern in the
smallest possible case: the skill orchestrates, the engine decides. Read
`skills/CONVENTIONS.md` before you edit a copy of this folder.

## When to use

The user supplies one Severity / Occurrence / Detection triple and wants its Risk Priority
Number and AIAG-VDA Action Priority. For a whole FMEA table, use the `fmea_run` tool instead.

## Steps

1. Connect to the quality-platform MCP server over stdio. The host normally has it configured
   already; if not, it launches as `python -m mcp_app.server` from the workspace root.
2. Collect the three ratings from the user. Each is an integer on the AIAG 1-10 scale. Do not
   invent a rating the user did not give, and do not translate ratings between scales — the
   rating text lives in the FMEA app's own rating-scale tools (`fmea_list_scales`,
   `fmea_get_scale`), not in this skill.
3. Call the `fmea_score` tool with `severity`, `occurrence` and `detection`.
4. Report the returned `rpn` and `action_priority` **verbatim**. Never recompute, round,
   re-derive or "sanity check" either value — the engine owns that arithmetic, and a second
   opinion computed here is a defect, not a safeguard.
5. If the tool returns an error (any rating outside 1-10), surface the error message to the
   user and ask for a corrected rating. Do not retry with a clamped value.

`scripts/call_fmea_score.py` is the same flow as a runnable script, for when a shell call is
cheaper than a tool call.

## Reference

- [`references/mcp-tool-contract.md`](references/mcp-tool-contract.md) — the tool namespace
  convention, the `fmea_score` request/response shape, and the error contract.
