# MCP tool contract (reference)

Level-3 detail for the `fmea` skill, kept out of `SKILL.md` per progressive disclosure: a
host loads this only when it needs the wire-level contract. Every shape below is the one
registered in `apps/mcp/mcp_app/server.py`.

## Namespace convention

The quality-platform MCP server names its tools by one fixed rule:

| Kind | Prefix | Examples |
|---|---|---|
| Meta — describes the server process itself | none | `health`, `version` |
| Domain — wraps one engine function | `<domain>_` | `fmea_score`, `spc_capability`, `msa_gage_rr`, `controlplan_build` |

Reference tools by these exact names. The full catalog lives in `apps/mcp/README.md`; a
skill never invents a tool name or a second naming scheme.

## `fmea_score`

`fmea_score(severity: int, occurrence: int, detection: int) -> {"rpn": int, "action_priority": str}`

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

## `fmea_run`

`fmea_run(rows: list[dict]) -> list[dict]`

Each row dict carries the 11 required FMEA columns: `ID`, `Process_Step`, `Component`,
`Function`, `Failure_Mode`, `Effect`, `Severity`, `Cause`, `Occurrence`, `Current_Control`,
`Detection`. The tool runs the full pipeline (validate, score, flag, rank) and returns the
rows ranked by Risk Priority Number descending, each carrying:

| Field | Meaning |
|---|---|
| `RPN` | Risk Priority Number for the row |
| `AP` | AIAG-VDA Action Priority — `High` / `Medium` / `Low` |
| `Flag_High_RPN` | repo-retained FMEA-4-compatibility flag (see `fmea-method-notes.md`) |
| `Flag_High_Severity` | repo-chosen safety heuristic, fires on every Severity 9-10 row |
| `Flag_Action_Priority_H` | the RPN-side proxy flag, *not* the Action Priority determination |
| `Risk_Tier` | the row's tier under the active ranking basis |

## `fmea_run_relational`

`fmea_run_relational(model: dict) -> list[dict]`

`model` is a `RelationalFMEA` JSON object — functions linked to failure modes, and those to
effects, causes and controls by ID. It is flattened losslessly and then run through the same
validate/score/flag/rank pipeline as `fmea_run`, so the output shape matches, plus the
action-tracking columns when any link carries an action.

## `fmea_list_scales`

`fmea_list_scales() -> list[dict]`

Returns the built-in rating-scale menu:

```json
[{"id": "2019", "name": "..."}, {"id": "fmea4", "name": "..."}]
```

The names come from the bundled scale files themselves, so the menu cannot drift from what
`fmea_get_scale` actually returns.

## `fmea_get_scale`

`fmea_get_scale(scale_id: str = "2019", custom_json: str | None = None) -> dict`

Returns one scale's full severity/occurrence/detection rating text. `scale_id` is one of:

| `scale_id` | Scale |
|---|---|
| `"2019"` (default) | AIAG & VDA 2019 PFMEA |
| `"fmea4"` | AIAG FMEA-4 legacy |
| `"custom"` | requires `custom_json`: raw JSON text with `severity`/`occurrence`/`detection` keys, each mapping ratings 1-10 to a description |

**Scale selection is presentation-only.** It documents what a score *means*; it never
re-scores anything and never changes the numbers `fmea_score`, `fmea_run` or
`fmea_run_relational` return (`apps/fmea/docs/ASSUMPTIONS_LOG.md` RULE 6).

## Error contract

The server converts engine input errors into a structured MCP `ToolError` — a client never
sees a Python traceback. Typical messages:

| Condition | Message shape |
|---|---|
| A rating outside 1-10 | `Severity score 11 is out of range` |
| An argument the tool does not take | `Unexpected keyword argument` |
| A tool name that does not exist | `Unknown tool` |
| A relational model with a repeated ID | duplicate-ID validation error |
| A link pointing at an ID that does not exist | unknown-link-reference validation error |
| An unknown `scale_id`, or `scale_id="custom"` with no `custom_json` | `Unknown scale_id ...` / `scale_id='custom' requires custom_json.` |

Surface the message to the user and ask for corrected input. Do not clamp, default, drop a
row, or retry with a value the user did not give.

## Transport

stdio is the default and is unauthenticated — that is what Claude Desktop, Cursor and Claude
Code launch, and it is what `scripts/call_fmea_score.py` uses. HTTP mode
(`MCP_TRANSPORT=http`) requires an `MCP_AUTH_TOKEN` bearer secret and is out of scope for
skills; see `apps/mcp/README.md`.
