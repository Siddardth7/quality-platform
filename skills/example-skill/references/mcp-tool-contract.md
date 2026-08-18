# MCP tool contract (reference)

Level-3 detail for `example-skill`, kept out of `SKILL.md` per progressive disclosure: a host
loads this only when it needs the wire-level contract.

## Namespace convention

The quality-platform MCP server (`apps/mcp/mcp_app/server.py`) names its tools by one fixed
rule:

| Kind | Prefix | Examples |
|---|---|---|
| Meta — describes the server process itself | none | `health`, `version` |
| Domain — wraps one engine function | `<domain>_` | `fmea_score`, `spc_capability`, `msa_gage_rr`, `controlplan_build` |

Reference tools by these exact names. The full catalog lives in `apps/mcp/README.md`; a skill
never invents a tool name or a second naming scheme.

## `fmea_score`

Request:

```json
{"severity": 9, "occurrence": 8, "detection": 5}
```

All three arguments are required integers on the AIAG 1-10 scale. The generated input schema
sets `additionalProperties: false`, so a misspelled argument fails before the tool body runs.

Response:

```json
{"rpn": 360, "action_priority": "High"}
```

Both values are engine output. Present them as-is.

## Error contract

The server converts engine input errors into a structured MCP `ToolError` — a client never
sees a Python traceback. Typical messages:

| Condition | Message shape |
|---|---|
| A rating outside 1-10 | `Severity score 11 is out of range` |
| An argument the tool does not take | `Unexpected keyword argument` |
| A tool name that does not exist | `Unknown tool` |

Surface the message to the user and ask for corrected input. Do not clamp, default, or retry
with a value the user did not give.

## Transport

stdio is the default and is unauthenticated — that is what Claude Desktop, Cursor and Claude
Code launch, and it is what `scripts/call_fmea_score.py` uses. HTTP mode
(`MCP_TRANSPORT=http`) requires an `MCP_AUTH_TOKEN` bearer secret and is out of scope for
skills; see `apps/mcp/README.md`.
