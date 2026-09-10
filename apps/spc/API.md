# `quality-spc` — stable API

The SPC app's published surface is its **validated ingest contract**, `spc_app.schema`.
The control-chart, capability, rule-detection and phase math a consumer would want lives in
`quality_core.spc`, not here — see `packages/quality-core/API.md`. `spc_app` is the
Streamlit dashboard composed over that core; only the ingest schema is a stable, reusable
surface.

`spc_app` itself exports only `__version__` — import from the submodule
(`from spc_app.schema import load_spc_csv`).

The stable surface is the module's `__all__`. The fenced manifest below is the
machine-checkable copy; `tests/test_api_surface.py` asserts set equality both ways.

---

## 1. Stable symbols

### `spc_app.schema`

```
<!-- STABLE SYMBOLS: spc_app.schema -->
SPCChartKey
SPCRow
SPC_SCHEMA
load_spc_csv
IngestError
<!-- END STABLE SYMBOLS -->
```

| Symbol | Kind | Purpose | Source |
|---|---|---|---|
| `SPCChartKey` | constant (Literal alias) | The app's internal chart keys (`"xbar_r"`, `"xbar_s"`, `"imr"`, `"p"`, `"u"`, `"c"`). | `apps/spc/spc_app/schema.py:41` |
| `SPCRow` | class | One row of an SPC dataset (Pydantic v2). | `apps/spc/spc_app/schema.py:44` |
| `SPC_SCHEMA` | constant | The `TableSchema` ingest contract for an SPC upload. | `apps/spc/spc_app/schema.py:86` |
| `load_spc_csv` | function | Read + validate an uploaded SPC `.csv` against `SPC_SCHEMA`. | `apps/spc/spc_app/schema.py:95` |
| `IngestError` | class | Re-exported from `quality_core.io` so a caller catches one exception type. | `packages/quality-core/src/quality_core/io/validate.py:87` |

### Deliberately **not** part of the stable surface

Two dataclasses are reachable via `dir()` but are UI-report internals, excluded on purpose
(SME decision, #261):

- **`spc_app.exporter.ControlChartReport`** — the export/PDF report payload. It exists to
  carry a rendered report between the page and the exporter, not to be produced or consumed
  by an engine caller.
- **`spc_app.control_plan_config.SPCViewConfig`** — Streamlit page configuration. Not an
  engine input or output.

Neither is returned by, or accepted by, any symbol listed above; neither module declares an
`__all__`, and neither appears in any manifest block. Treat both as internal: they may
change or disappear without a version bump.

Likewise `spc_app.spc_engine`, `spc_app.simulation`, `spc_app.visualizer`,
`spc_app.fmea_feedback` and `spc_app.pages` are app composition over `quality_core.spc` —
a reusable consumer should call `quality_core.spc` directly.

---

## 2. Signatures

```python
load_spc_csv(source: str | BinaryIO) -> pd.DataFrame
```

`SPCRow` is a Pydantic model; construct it as `SPCRow(**row)`. `SPC_SCHEMA` is a
`TableSchema` value, not a callable.

---

## 3. I/O types

**Owned by this package:**

| Type | Kind | Source | Used by |
|---|---|---|---|
| `SPCRow` | Pydantic v2 model — `stream`, `subgroup`, `value` (plus the optional columns declared in `SPC_SCHEMA`) | `apps/spc/spc_app/schema.py:44` | the row model inside `SPC_SCHEMA` |
| `SPCChartKey` | `Literal["xbar_r", "xbar_s", "imr", "p", "u", "c"]` | `apps/spc/spc_app/schema.py:41` | the app's chart-key vocabulary |

`SPCChartKey` is the app's snake_case key set and is **distinct** from the platform
vocabulary `SPCChart` (`"Xbar-R"`, `"Xbar-S"`, `"I-MR"`, `"p"`, `"c"`, `"u"`) owned by
`quality_core.spc.constants`.

**Owned elsewhere — see that package's `API.md`, not restated here:**

| Type | Owner | Reference |
|---|---|---|
| `TableSchema` (the type of `SPC_SCHEMA`) | `quality_core.io` | `packages/quality-core/API.md` |
| `IngestError` (re-exported above) | `quality_core.io` | `packages/quality-core/API.md` |
| `SPCChart`, and every chart/capability result type | `quality_core.spc` | `packages/quality-core/API.md` |

`load_spc_csv` returns a plain validated `pd.DataFrame`.

---

## 4. Stability

Zero behaviour change since v0.13.0; this file documents the existing contract, it does not
introduce one.

Going forward: removing a listed symbol, changing a listed signature, or changing the shape
of a listed type is a **breaking** change. Adding a new symbol (to `__all__` and to the
manifest block above) is **non-breaking**.
