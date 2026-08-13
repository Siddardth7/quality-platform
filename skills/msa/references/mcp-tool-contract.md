# MCP tool contract (reference)

Level-3 detail for the `msa` skill, kept out of `SKILL.md` per progressive disclosure: a host
loads this only when it needs the wire-level contract. Every shape below is the one registered
in `apps/mcp/mcp_app/server.py`.

## Namespace convention

The quality-platform MCP server names its tools by one fixed rule:

| Kind | Prefix | Examples |
|---|---|---|
| Meta — describes the server process itself | none | `health`, `version` |
| Domain — wraps one engine function | `<domain>_` | `fmea_score`, `spc_capability`, `msa_gage_rr`, `controlplan_build` |

Reference tools by these exact names. The full catalog lives in `apps/mcp/README.md`; a skill
never invents a tool name or a second naming scheme. In particular there is **exactly one MSA
analysis tool on this server** — no `msa_list_methods`, no separate scale or constants lookup the
way FMEA has `fmea_list_scales`. Do not invent one. (The server also registers MSA *export*
tools — `msa_export_excel`, `msa_export_pdf`, `msa_export_study_csv`, `msa_export_results_csv` —
which are out of scope for this skill.)

## `msa_gage_rr`

```python
def msa_gage_rr(
    study: list[dict[str, Any]],
    method: Literal["average_and_range", "anova"] = "average_and_range",
    tolerance: float | None = None,
) -> dict[str, Any]
```

A verbatim passthrough over the shipped `msa_app` Gage R&R engine: no reshaping at the tool
boundary, no defaults invented there, nulls preserved.

### `study` — long/tidy form

One object per individual measurement, four keys each:

```json
{"study": [
  {"part": 1, "appraiser": "A", "trial": 1, "measurement": 10.00},
  {"part": 1, "appraiser": "A", "trial": 2, "measurement": 10.01},
  {"part": 1, "appraiser": "B", "trial": 1, "measurement": 10.01},
  {"part": 1, "appraiser": "B", "trial": 2, "measurement": 10.02}
]}
```

`part` and `appraiser` are any hashable label, `trial` an integer, `measurement` a finite
number. This is **not** the wide-subgroup shape the SPC chart tools take.

Preconditions, both checked before either method runs:

- **Crossed and balanced** — every part measured by every appraiser, the same trial count in
  every (part, appraiser) cell (`apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 11).
- **At least 2 parts, 2 appraisers and 2 trials per cell** (RULE 12).

### `method`

`"average_and_range"` (default) or `"anova"`. ANOVA additionally estimates and tests the
part × appraiser interaction; `interaction`, `interaction_f` and `interaction_significant` are
null under `"average_and_range"`, which cannot estimate it. Any other value is a tool error.

### `tolerance`

USL − LSL, optional. Omitted: only the study-variation basis is populated and the four
tolerance-basis keys are null. Supplied: both AIAG bases are populated.

### Return keys

Every key comes back on every call; nulls are meaningful and are passed on as-is.

| Key | What it is |
|---|---|
| `ev` | repeatability, the equipment-variation component |
| `av` | reproducibility, the appraiser-variation component |
| `grr` | the combined gage repeatability and reproducibility component |
| `pev_study` / `pav_study` / `pgrr_study` / `ppv_study` | the four components as a percent of study variation |
| `pev_tolerance` / `pav_tolerance` / `pgrr_tolerance` / `ppv_tolerance` | the same four on the tolerance basis; null when no `tolerance` was sent |
| `ndc` | number of distinct categories (integer; clamped to the 1–100 range this platform documents) |
| `verdict` | `"Accept"`, `"Marginal"` or `"Reject"` |
| `tv` | total variation |
| `pv` | part variation |
| `mean` | overall mean of all measurements |
| `n_parts` / `n_appraisers` / `n_trials` | the study's dimensions as the engine read them |
| `is_balanced` | whether every (part, appraiser) cell carried `n_trials` measurements |
| `method` | the AIAG technique that actually ran |
| `method_note` | what that technique can and cannot see — surface it, it is not boilerplate |
| `interaction` | the part × appraiser interaction in the same units as the components; null under Average-and-Range |
| `interaction_f` | the interaction F statistic; null under Average-and-Range |
| `interaction_significant` | whether that statistic exceeded its critical value; null under Average-and-Range |

`ppv_tolerance` may exceed 100% and is deliberately unclamped. Report it as returned.

## Error contract

The server converts engine input errors into a structured MCP `ToolError` — a client never
sees a Python traceback.

| Condition | Message shape |
|---|---|
| Empty `study` | empty-study validation error |
| Fewer than 2 parts or 2 appraisers | minimum-study-size error |
| Fewer than 2 trials in a (part, appraiser) cell | minimum-trials error |
| Unbalanced design | unbalanced-study error |
| A non-numeric, NaN or infinite `measurement` | measurement validation error |
| A non-positive or non-finite `tolerance` | tolerance validation error |
| A `method` other than the two registered values | unknown-method error |
| An argument the tool does not take | `Unexpected keyword argument` |
| A tool name that does not exist | `Unknown tool` |

Surface the message to the user and ask for corrected input. Do not drop a row, invent a
balancing measurement, default a tolerance, or retry with a value the user did not give.

## Transport

stdio is the default and is unauthenticated — that is what Claude Desktop, Cursor and Claude
Code launch, and it is what `scripts/call_msa_gage_rr.py` uses. HTTP mode
(`MCP_TRANSPORT=http`) requires an `MCP_AUTH_TOKEN` bearer secret and is out of scope for
skills; see `apps/mcp/README.md`.
