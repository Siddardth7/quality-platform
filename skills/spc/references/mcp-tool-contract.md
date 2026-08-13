# MCP tool contract (reference)

Level-3 detail for the `spc` skill, kept out of `SKILL.md` per progressive disclosure: a
host loads this only when it needs the wire-level contract. Every shape below is the one
registered in `apps/mcp/mcp_app/server.py`.

## Namespace convention

The quality-platform MCP server names its tools by one fixed rule:

| Kind | Prefix | Examples |
|---|---|---|
| Meta — describes the server process itself | none | `health`, `version` |
| Domain — wraps one engine function | `<domain>_` | `fmea_score`, `spc_capability`, `msa_gage_rr`, `controlplan_build` |

Reference tools by these exact names. The full catalog lives in `apps/mcp/README.md`; a
skill never invents a tool name or a second naming scheme. In particular there is **no**
np-chart tool, no single "rule detection" tool (there are two, one per rule set), and no
freeze/apply pair for the attribute or EWMA/CUSUM charts.

## Chart tools

Each takes the engine's native input shape — wide subgroups for the X-bar charts, a flat
series for I-MR/EWMA/CUSUM, parallel count/size lists for the attribute charts — and returns
the engine's result mapping verbatim.

### `spc_xbar_r`

`spc_xbar_r(subgroups: list[list[float]]) -> dict`

Request:

```json
{"subgroups": [[10.2, 10.4, 10.1, 10.3], [10.5, 10.3, 10.6, 10.4]]}
```

One inner list per subgroup, all the same length, subgroup size 2-10 (the tabulated
A2/D3/D4 range). Returns the subgroup means and ranges, both centre lines, both charts'
limits, and `sigma_hat` estimated as Rbar/d2:

```json
{"xbarbar": 10.355, "rbar": 0.25, "ucl_x": 10.53725, "lcl_x": 10.17275,
 "sigma_hat": 0.12141816415735784}
```

Ragged or empty input and an untabulated subgroup size are structured tool errors.

### `spc_xbar_s`

`spc_xbar_s(subgroups: list[list[float]]) -> dict`

Same wide-subgroup input and response shape as `spc_xbar_r`, but the tabulated A3/B3/B4
range is 2-12 and `sigma_hat` is Sbar/c4.

### `spc_imr`

`spc_imr(values: list[float]) -> dict`

A flat series of individual measurements (n=1). Needs at least two values; returns the
individuals and moving-range series with both charts' limits and `sigma_hat` from MRbar/d2.

### `spc_p`

`spc_p(defective_counts: list[float], sample_sizes: list[float]) -> dict`

```json
{"defective_counts": [3, 5, 2], "sample_sizes": [100, 120, 90]}
```

Parallel lists of equal length. Every sample size must be finite and positive — a NaN size
once produced NaN limits with no error at all (#200), which is why this is now a structured
tool error rather than a silently propagated null. Limits vary per point.

### `spc_c`

`spc_c(defect_counts: list[float]) -> dict`

One count per inspection unit at constant sample size; limits are constant, with the lower
limit clamped at zero. Empty input is a structured tool error.

### `spc_u`

`spc_u(defect_counts: list[float], sample_sizes: list[float]) -> dict`

Same parallel-list contract and sample-size validation as `spc_p`; use it rather than the
c-chart whenever the inspected area of opportunity is not constant.

### `spc_ewma`

`spc_ewma(values: list[float], mu0: float, sigma: float, lam: float = 0.20, L: float = 2.860) -> dict`

`mu0` and `sigma` are independent Phase I estimates and are **never** derived from the series
being charted (`apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 12). The `lam`/`L` defaults are the
cited pairing carried in the engine's constants; a mismatched pair is still computed but
returns `pairing_adequate=False` with a `pairing_note` naming the recommended L — surface that
note, the tool deliberately does not swallow it. Returns the z-series and time-varying limits.
Empty values, a sigma at or below zero, a `lam` outside (0,1] or an `L` at or below zero are
structured tool errors.

### `spc_cusum`

`spc_cusum(values: list[float], mu0: float, sigma: float, k: float = 0.5, h: float = 5, fir: bool = False) -> dict`

`mu0`/`sigma` are Phase I estimates as for `spc_ewma`. `k` is the reference value and `h` the
decision interval in sigma units, both defaulting to the cited engine constants; `fir=True`
applies the head start to both arms (RULE 13). Returns the two accumulator series and the
run-length counters. Empty values or a non-positive `sigma`/`k`/`h` are structured tool errors.

## Phase I freeze / Phase II apply

Two families rather than a flag on the chart tools. A freeze result is a plain dict that goes
straight back in as the `frozen` argument — that round trip is the whole point of the pair.
**These exist only for the three Shewhart variables charts**; there is no freeze or apply tool
for p, c, u, EWMA or CUSUM.

### `spc_freeze_xbar_r` / `spc_freeze_xbar_s`

`spc_freeze_xbar_r(baseline: list[list[float]], excluded: list[dict] | None = None, phase_i_range: tuple[str, str] | None = None) -> dict`

`excluded` drops baseline subgroups with an assignable cause, as
`{"index": int, "cause": str}` objects. The cause is mandatory — an out-of-range, duplicated
or uncaused index is a structured tool error, because dropping a point without a documented
reason is not a defensible baseline. `phase_i_range` is an optional (start, end) label pair
recorded on the result. The result carries the limits, `sigma_hat` and its method, the
exclusions, and `baseline_adequate` / `baseline_note` flagging a baseline below the minimum
subgroup count (RULE 11) — a soft warning, never a raise. `spc_freeze_xbar_s` has an identical
contract with the 2-12 subgroup-size range.

### `spc_freeze_imr`

`spc_freeze_imr(baseline: list[float], excluded: list[dict] | None = None, phase_i_range: tuple[str, str] | None = None) -> dict`

Same `excluded`/`phase_i_range` contract, except an excluded index drops one individual value
rather than a whole subgroup, and the adequacy floor is a minimum number of individuals.

### `spc_apply_xbar_r` / `spc_apply_xbar_s` / `spc_apply_imr`

`spc_apply_xbar_r(subgroups: list[list[float]], frozen: dict) -> dict`
`spc_apply_xbar_s(subgroups: list[list[float]], frozen: dict) -> dict`
`spc_apply_imr(values: list[float], frozen: dict) -> dict`

`frozen` is the matching freeze result passed straight back in. The plotted statistics come
from the new data, but the limits are taken from `frozen` verbatim and nothing is recomputed —
which is what makes a Phase II signal meaningful. A frozen baseline for a different chart type
or a different subgroup size than the new data is a structured tool error.

## Rule detection

Two tools, one per rule set. They are **mutually exclusive** — pick one for a chart, never
report both (RULE 8).

### `spc_detect_we_violations`

`spc_detect_we_violations(points: list[float], cl: float, sigma: float) -> list[dict]`

```json
{"points": [10.25, 10.45, 10.25], "cl": 10.355, "sigma": 0.06070908207867892}
```

`cl` and `sigma` come from a chart tool's result. **For X-bar charts `sigma` is the sigma of
the plotted points** — the chart's `sigma_hat` divided by the square root of the subgroup size
— not `sigma_hat` itself. Take it from the engine's result; do not make a fresh pass over the
raw data to get it. Returns one object per signal, empty when in control:

```json
[{"index": 12, "rule": "Western Electric Rule 1"}]
```

A sigma at or below zero is a structured tool error.

### `spc_detect_nelson_violations`

`spc_detect_nelson_violations(points: list[float], cl: float, sigma: float) -> list[dict]`

Same `points`/`cl`/`sigma` contract and the same `{"index", "rule"}` output, over the Nelson
set — the zone tests plus the trend, alternation, stratification and mixture tests, labelled
with Nelson's own numbering.

**Never call either detector on an EWMA or CUSUM chart's points** (RULE 15): those statistics
are autocorrelated by construction and run-rule patterns fire far more often than the
independent-point tables assume. The MCP layer does not gate this — the skill is the
enforcement point. Attribute charts (p, c, u) *are* Shewhart charts and run rules are valid on
them; do not conflate "attribute chart" with "autocorrelated chart".

## Capability and normality

### `spc_capability`

`spc_capability(data: list[float] | list[list[float]], lsl: float | None, usl: float | None, alpha: float = 0.05, allow_yeojohnson: bool = True, force_method: str = "auto", violations: list[dict] | None = None) -> dict`

`data` is flat individuals or wide subgroups (subgroups give a within-subgroup sigma). At
least one of `lsl`/`usl` is needed for an index; with **neither**, the indices come back null
and nothing raises — report the nulls, that is not an error. `force_method` is `"auto"`,
`"normal"`, `"boxcox"` or `"percentile"` and overrides the default Shapiro-Wilk-driven path
selection (`allow_yeojohnson=False` forces a shifted Box-Cox for non-positive data instead).

Two result subtleties, both deliberate:

- **Confidence intervals attach only to the estimator they were derived for.** On the normal
  path `cp_ci`/`cpk_ci` are always null while `pp_ci`/`ppk_ci`/`ppk_lower` carry intervals; on
  the percentile path Pp/Ppk and their intervals are null while `cp_ci`/`cpk_ci` carry
  bootstrap intervals. Every field comes back verbatim, nulls included: "no interval for this
  estimator" and "interval not computed" are different facts, and `ci_estimator`/`ci_df` are
  what tell them apart (RULE 14).
- **`violations` drives a tri-state stability gate.** It is the caller's own signal list from
  `spc_detect_we_violations`, `spc_detect_nelson_violations`, or the `signals` of
  `spc_assess_stability`. Omit it and `stable` is null — "not assessed", never a fabricated
  in-control claim. Pass `[]` to state the chart was assessed and is in control. No stability
  check runs inside this tool (RULE 7).

Alpha outside (0,1), data that is neither 1-D nor 2-D, fewer than three observations, or
constant data are structured tool errors.

### `spc_normality_test`

`spc_normality_test(data: list[float]) -> dict`

```json
{"W": 0.972, "p_value": 0.41, "is_normal": true}
```

Shapiro-Wilk. `is_normal` is the p > 0.05 gate that `spc_capability`'s `"auto"` selection uses
(RULE 9). Needs at least three values.

## Stability

### `spc_assess_stability`

`spc_assess_stability(values: list[float], subgroups: list[str | int], chart_type: str = "I-MR", rule_set: str = "Western Electric") -> dict`

**Long format, unlike the chart tools:** `values` and `subgroups` are parallel lists with one
row per measurement, which is what preserves measurement order within a subgroup on the I-MR
path. Do not pass wide subgroups here.

```json
{"values": [10.2, 10.4, 10.1, 10.3], "subgroups": [1, 1, 2, 2], "chart_type": "Xbar-R"}
```

`chart_type` is `"I-MR"`, `"Xbar-R"` or `"Xbar-S"` and is caller-supplied on purpose —
inferring it from the data understates sigma and flips verdicts (#191). `rule_set` is
`"Western Electric"` (default) or `"Nelson"`. Returns `sigma_hat` and a `signals` list; an
empty list means in control. Feed `signals` straight into `spc_capability`'s `violations`.
Ragged subgroups or a subgroup size outside the chart's tabulated range are structured tool
errors.

## Report export

`spc_export_control_chart_excel`, `spc_export_control_chart_pdf`,
`spc_export_capability_excel` and `spc_export_capability_pdf` are also available and follow the
same call pattern as the chart and capability tools, returning a rendered report artifact
rather than a result mapping. They are outside this skill's core workflow — see
`apps/mcp/README.md` for their parameters.

## Error contract

The server converts engine input errors into a structured MCP `ToolError` — a client never
sees a Python traceback. Typical messages:

| Condition | Message shape |
|---|---|
| Ragged or empty subgroups | subgroup-shape validation error |
| A subgroup size outside the chart's tabulated range | untabulated subgroup size |
| A non-finite or non-positive sample size on `spc_p`/`spc_u` | sample-size validation error |
| A sigma at or below zero on a detector or on EWMA/CUSUM | `sigma must be positive` |
| Fewer than three observations, or constant data, on `spc_capability` | insufficient/degenerate data error |
| An excluded baseline point with no cause, or a duplicate index | exclusion validation error |
| A `frozen` baseline whose chart type or subgroup size does not match the new data | frozen-baseline mismatch error |
| An argument the tool does not take | `Unexpected keyword argument` |
| A tool name that does not exist | `Unknown tool` |

Surface the message to the user and ask for corrected input. Do not clamp a limit, default a
sample size, drop a point, or retry with a value the user did not give.

## Transport

stdio is the default and is unauthenticated — that is what Claude Desktop, Cursor and Claude
Code launch, and it is what `scripts/call_spc_capability.py` uses. HTTP mode
(`MCP_TRANSPORT=http`) requires an `MCP_AUTH_TOKEN` bearer secret and is out of scope for
skills; see `apps/mcp/README.md`.
