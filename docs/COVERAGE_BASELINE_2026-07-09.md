# Coverage baseline — branch coverage flip (2026-07-09)

**Why this exists.** The playbook rule is *baseline-first*: measure line **and branch** coverage
before turning the branch gate on, so the gate never lands red. This records the state at the moment
`branch = true` was enabled (issue #41), and the one gap that was closed to keep every gate green.

## Method

```bash
uv run pytest packages/quality-core --cov=quality_core.io --cov-branch --cov-report=term-missing
uv run pytest packages/quality-core --cov=quality_core.schema --cov-branch --cov-report=term-missing
uv run pytest apps/spc --cov=spc_app.spc_engine --cov=spc_app.simulation \
  --cov=spc_app.visualizer --cov=spc_app.exporter --cov=spc_app.schema --cov-branch --cov-report=term-missing
```

## Gated surfaces — before vs after enabling branch coverage

| Surface | Gate | Line (before) | Branch (before) | After fix |
|---------|------|:---:|:---:|:---:|
| `quality_core.io` | 100% | 100% | **99%** — 1 partial (`validate.py 226->231`) | **100% / 100%** ✅ |
| `quality_core.schema` | 100% | 100% | 100% (44 branches) | 100% / 100% ✅ |
| SPC testable surface | ≥95% | 100% | 100% (124 branches) | 100% / 100% ✅ |

## The one gap and its fix

`quality_core/io/validate.py`, `_format_row_error`, branch `226->231`: the `else` of
`if "input" in first:`. Empirically, `pydantic.ValidationError.errors()` (default
`include_input=True`) **always** carries `input` — only `errors(include_input=False)`, which this
module never calls, omits it. So the guard's false path was **dead defensive code** (flagged by the
over-engineering pass). Fix: drop the guard and read `first.get("input")` unconditionally —
crash-safe, behaviour identical for every real error, and the dead branch is gone. io is now 100%
line + branch.

## Outcome

`branch = true` + `show_missing = true` are on in `pyproject.toml`. All three per-surface gates pass
on **line and branch**; no floor was lowered. SPC sits at 100% branch against a 95% floor — headroom
to ratchet SPC to 96–98 in a future version close once it's durably there.

> Point-in-time doc. Do not edit after the flip; write a new dated baseline before the next gate
> change (e.g. an SPC floor ratchet).
