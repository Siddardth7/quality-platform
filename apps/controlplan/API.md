# `controlplan-app` — stable API

The FMEA → Control Plan connector engine. One published module,
`controlplan_app.connector`: it maps a relational FMEA into the Control Plan output
contract, holds the AIAG SPC chart-selection rule table, and exposes the traceability index
back to the FMEA. Engine + typed output only — no UI.

`controlplan_app` itself exports only `__version__` — import from the submodule
(`from controlplan_app.connector import build_control_plan`). `controlplan_app.schema` is
the output contract it maps *into* (see I/O types); `exporter` and `pages/` are application
surface.

The stable surface is the module's `__all__`. The fenced manifest below is the
machine-checkable copy; `tests/test_api_surface.py` asserts set equality both ways.

---

## 1. Stable symbols

### `controlplan_app.connector`

```
<!-- STABLE SYMBOLS: controlplan_app.connector -->
build_control_plan
recommend_chart
source_index
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `build_control_plan` | function | One `ControlPlanRow` per `FailureMode` (Q1), sorted highest-risk first. | `apps/controlplan/controlplan_app/connector.py:199` |
| `recommend_chart` | function | The AIAG SPC chart-selection rule table → an `SPCChart` key (RULE 1). | `apps/controlplan/controlplan_app/connector.py:87` |
| `source_index` | function | Characteristic → its source-cause identity, for SPC-side enrichment (#89 OQ1). | `apps/controlplan/controlplan_app/connector.py:255` |

The module's helpers (`_reaction_plan`, `_worst_link`, `_iter_named_modes`,
`_source_cause_id`) and its placeholder defaults (`_DEFAULT_SAMPLE_SIZE`,
`_DEFAULT_FREQUENCY`, `_MAX_XBAR_S_N`) are internal. `DataType` is the argument alias for
`recommend_chart` (`Literal["variable", "attribute"]`) — pass the string literal; it is not
a published name.

---

## 2. Signatures

```python
build_control_plan(fmea: RelationalFMEA) -> ControlPlanDataset
recommend_chart(data_type: DataType, subgroup_size: int, *, defect_based: bool = False, constant_sample: bool = True) -> SPCChart
source_index(fmea: RelationalFMEA) -> dict[str, dict[str, object]]
```

`DataType` is `Literal["variable", "attribute"]` (`connector.py`). `recommend_chart` raises
`ValueError` for a subgroup size above the largest n in `XBAR_S_CONSTANTS` (n = 12; F-07,
#196).

---

## 3. I/O types

**Owned by this package:**

| Type | Kind | Source | Used by |
|---|---|---|---|
| `ControlPlanDataset` | Pydantic v2 model wrapping `ControlPlanRow`s; enforces unique characteristics | `apps/controlplan/controlplan_app/schema.py` | return of `build_control_plan` |
| `ControlPlanRow` | Pydantic v2 row model — characteristic, LSL/target/USL, measurement method, sample size/frequency, control method, reaction plan, `sample_plan_is_placeholder`, `source_cause_id` | `apps/controlplan/controlplan_app/schema.py` | rows of `ControlPlanDataset` |

`build_control_plan` is defined against the existing #83 `ControlPlanDataset` contract and
does not redefine it — adding a field means changing `schema.py`.

**Owned elsewhere — see that package's `API.md`, not restated here:**

| Type | Owner | Reference |
|---|---|---|
| `SPCChart` (`Literal["Xbar-R", "Xbar-S", "I-MR", "p", "c", "u"]`) | `quality_core.spc.constants` — origin. `controlplan_app.schema` re-exports it for convenience; the vocabulary is the core's. | `packages/quality-core/API.md` |
| `RelationalFMEA`, `FailureMode`, `Function`, `Cause`, `Effect`, `Control`, `FailureLink` | `quality_core.schema` | `packages/quality-core/API.md` |

`source_index` returns a plain `dict[str, dict[str, object]]` keyed by characteristic — no
dedicated type.

---

## 4. Stability

Zero behaviour change since v0.13.0; this file documents the existing contract, it does not
introduce one.

Going forward: removing a listed symbol, changing a listed signature, or changing the shape
of a listed type is a **breaking** change. Adding a new symbol (to `__all__` and to the
manifest block above) is **non-breaking**.
