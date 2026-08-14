# MCP tool contract (reference)

Level-3 detail for the `control-plan` skill, kept out of `SKILL.md` per progressive disclosure:
a host loads this only when it needs the wire-level contract. Every shape below is the one
registered in `apps/mcp/mcp_app/server.py`.

## Namespace convention

The quality-platform MCP server names its tools by one fixed rule:

| Kind | Prefix | Examples |
|---|---|---|
| Meta — describes the server process itself | none | `health`, `version` |
| Domain — wraps one engine function | `<domain>_` | `fmea_score`, `spc_capability`, `msa_gage_rr`, `controlplan_build` |

Reference tools by these exact names. The full catalog lives in `apps/mcp/README.md`; a skill
never invents a tool name or a second naming scheme. There are **exactly four Control Plan
tools** on this server — `controlplan_build`, `controlplan_recommend_chart`,
`controlplan_source_index`, and `controlplan_build_from_project`. All four are thin
passthroughs over `controlplan_app` (the first three over `connector`, the fourth over
`project_arrow`, which is itself glue over the same connector); no Control Plan logic is
reimplemented at the tool boundary.

`controlplan_build_from_project(project_root: str) -> dict[str, Any]` is `controlplan_build`
against a project directory (#276/#277): it reads `<project_root>/fmea/fmea.json`, derives the
same rows, writes them to `<project_root>/control-plan/plan.json` — overwriting in place on a
re-run, no merge and no history array — and returns the written artifact
(`schema_version`/`generated_at`/`generated_by` plus `rows`). A missing or malformed
`fmea/fmea.json` is a structured tool error.

## `controlplan_build`

```python
def controlplan_build(fmea_model: dict[str, Any]) -> list[dict[str, Any]]
```

### Request

`fmea_model` is the same `RelationalFMEA` JSON object `fmea_run_relational` accepts — the
connector consumes it directly, with no separate Control Plan input schema. The field set is
documented once, in the `fmea` skill:
[`skills/fmea/references/mcp-tool-contract.md`](../../fmea/references/mcp-tool-contract.md).
It is deliberately not restated here; two copies of one contract is how they fork.

### Response

One row per `FailureMode`, ordered highest-risk first (Action Priority, then Risk Priority
Number, computed inside the engine for ordering only). Eleven keys on every row:

| Key | What it is |
|---|---|
| `characteristic` | `component — failure-mode description`, with a deterministic suffix if two modes collide |
| `lsl` / `usl` / `target` | always null from this tool — the FMEA carries no tolerances |
| `measurement_method` | the worst-risk link's control description, FMEA-derived |
| `sample_size` | connector default, **no FMEA source** |
| `frequency` | connector default, **no FMEA source** |
| `recommended_chart` | always null here — call `controlplan_recommend_chart` once a characteristic is classified |
| `reaction_plan` | templated from the worst-risk effect, **no FMEA source** |
| `source_cause_id` | provenance — the dataset-unique id of the worst-risk cause behind the row |
| `sample_plan_is_placeholder` | provenance — true whenever `sample_size`/`frequency`/`reaction_plan` are the defaults above |

The last two are the **provenance fields**. `source_cause_id` says where the row came from;
`sample_plan_is_placeholder` says which of its fields did *not* come from anywhere (F-10, #196
— `apps/controlplan/docs/ASSUMPTIONS_LOG.md` RULE 2). Every row this tool emits carries
`sample_plan_is_placeholder = true`; the field defaults to `false` so a hand-edited or uploaded
row can assert its own values.

An empty `functions` list returns `[]`. That is a valid result, not an error.

## `controlplan_recommend_chart`

```python
def controlplan_recommend_chart(
    data_type: Literal["variable", "attribute"],
    subgroup_size: int,
    defect_based: bool = False,
    constant_sample: bool = True,
) -> dict[str, str]
```

Returns `{"recommended_chart": <chart name>}` — a rule-table lookup, standalone: it carries no
reaction plan, no sample plan and no placeholder flag, and it takes no tolerance. The rule
table (`apps/controlplan/docs/ASSUMPTIONS_LOG.md` RULE 1, sourced to the AIAG SPC Reference
Manual, 4th Ed. (2005)):

| `data_type` | Condition | `recommended_chart` |
|---|---|---|
| `variable` | `subgroup_size == 1` | `I-MR` |
| `variable` | `2 <= subgroup_size <= 9` | `Xbar-R` |
| `variable` | `10 <= subgroup_size <= 12` | `Xbar-S` |
| `variable` | `subgroup_size > 12` | structured tool error — see below |
| `attribute` | `defect_based=false` | `p` (`np` folds into `p`; there is no `np` key) |
| `attribute` | `defect_based=true`, `constant_sample=true` | `c` |
| `attribute` | `defect_based=true`, `constant_sample=false` | `u` |

There is no upper bound on attribute sample size.

**The Xbar-R / Xbar-S boundary carries an open flag.** RULE 1 records that this one cell comes
from a third-party reproduction cross-check rather than the primary manual, and states:

> **This one number should be confirmed against the primary AIAG SPC Reference Manual, 4th
> Ed. (2005) decision tree before being treated as final** — it is the one cell in the rule
> table sourced from a third-party reproduction rather than the primary manual directly

Repeat that caveat when the boundary is load-bearing to an answer (a subgroup size of 9 or 10).
Do not present the boundary as primary-source-confirmed, and do not resolve it here: it is an
app-level assumptions-log flag, not something a skill closes.

## `controlplan_source_index`

```python
def controlplan_source_index(fmea_model: dict[str, Any]) -> dict[str, dict[str, Any]]
```

Same `fmea_model` contract as `controlplan_build`. Keys are **exactly** the `characteristic`
strings `controlplan_build` produces for the same model — both tools share one traversal in
`controlplan_app.connector`, so the two key sets cannot diverge. Join by exact string match;
there is no separate ID for the row.

Each value:

| Key | What it is |
|---|---|
| `failure_mode_id` | the source `FailureMode.id` |
| `cause_id` | equals that row's `source_cause_id`, exactly — the round-trip property |
| `cause_description` | the worst-risk cause's live description |
| `occurrence` | that cause's occurrence rating |
| `component` | the source function's component |

The `cause_id` ↔ `source_cause_id` equality is the traceability guarantee: it is what proves a
control-plan row and an FMEA cause are the same finding. It holds only for the *same*
`fmea_model` passed to both tools.

## Error contract

The server converts engine input errors into a structured MCP `ToolError` — a client never sees
a Python traceback.

| Condition | Message shape |
|---|---|
| A relational model with a repeated ID | duplicate-ID validation error |
| A link pointing at an ID that does not exist | unknown-link-reference validation error |
| `subgroup_size < 1` | `subgroup_size must be >= 1, got ...` |
| `subgroup_size > 12` with `data_type="variable"` | exceeds-largest-supported-X-bar/S-subgroup-size error |
| A `data_type` other than `variable`/`attribute` | unknown-data-type / argument validation error |
| An argument the tool does not take | `Unexpected keyword argument` |
| A tool name that does not exist | `Unknown tool` |

Surface the message to the user and ask for corrected input. Do not clamp a subgroup size to
12, fall back to `I-MR`, drop a failure mode, or retry with a value the user did not give. An
empty `functions` list is not in this table — it returns `[]`.

## Transport

stdio is the default and is unauthenticated — that is what Claude Desktop, Cursor and Claude
Code launch, and it is what `scripts/call_controlplan_build.py` uses. HTTP mode
(`MCP_TRANSPORT=http`) requires an `MCP_AUTH_TOKEN` bearer secret and is out of scope for
skills; see `apps/mcp/README.md`.
