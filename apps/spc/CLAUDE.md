# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the
SPC app inside the Quality Platform monorepo.

## Project orientation

The SPC app is one of two apps in the `quality-platform` uv workspace (the other is
`apps/fmea`), both sharing `packages/quality-core`. It runs standalone (`apps/spc/app.py`)
and is also mounted into the unified platform shell (`shell/`) via `importlib`.

Before changing domain logic, read:
- **`docs/ASSUMPTIONS_LOG.md`** — every AIAG SPC constant and threshold with its citation.
  Do not change a constant or threshold without updating that log.

## Commands

All commands run from the **workspace root** via `uv` (not from `apps/spc`).

### Install
```bash
uv sync --frozen
```

### Run
```bash
uv run streamlit run apps/spc/app.py        # standalone SPC app
uv run streamlit run app.py                 # unified platform shell (FMEA + SPC), from repo root
```

### Gate (must be green before merging)
```bash
uv run ruff check .
uv run mypy
uv run pytest --cov
# SPC coverage gate (CI enforces this on the testable SPC surface):
uv run pytest apps/spc \
  --cov=spc_app.spc_engine --cov=spc_app.simulation --cov=spc_app.visualizer \
  --cov-fail-under=95
```

CI (`.github/workflows/ci.yml`, job id `gate`) runs exactly these on Python 3.11.

### Single test
```bash
uv run pytest apps/spc/tests/test_control_charts.py -q          # one module
uv run pytest apps/spc -k "capability" -q                       # by keyword
```

## Architecture (big picture)

Thin Streamlit entry scripts → render functions → a pure computation engine. Charts and
capability never touch Streamlit; they return values and Plotly figures.

```
app.py                          standalone Streamlit entry; home page + version caption
pages/{1_Control_Charts,        thin wrappers: page config + theme, then delegate to
       2_Process_Capability,    spc_app.pages render functions (so the shell can mount
       3_Live_Simulation}.py    the same bodies without the standalone chrome)
        │
        ▼
spc_app/pages/control_charts.py      render_control_charts — dispatch over chart type
spc_app/pages/process_capability.py  render_capability — Cp/Cpk + stability gate
spc_app/pages/live_simulation.py     render_simulation — live subgroup stream
        │
        ▼
spc_app/spc_engine/             pure SPC computation (fully unit-tested):
    control_charts.py             compute_xbar_r/_s, compute_imr, compute_p/c/u
                                  (each returns a precise TypedDict result)
    capability.py                 compute_capability (Cp/Cpk/Pp/Ppk), normality_test
    rule_detection.py             detect_we_violations, detect_nelson_violations
    constants.py                  AIAG SPC chart constants (see ASSUMPTIONS_LOG.md)
    data_generator.py             deterministic 6-stream demo dataset
    utils.py                      subgroup_rows
spc_app/simulation/engine.py    SimulationEngine — mean shift / spike / drift injection
spc_app/visualizer.py           Plotly builders: control chart, capability histogram, Cpk gauge
```

**Data flow (Control Charts):** demo CSV / upload → filter by `stream` → `subgroup_rows`
→ `compute_*` (engine) → `detect_we/nelson_violations` → `build_control_chart` with rule
overlays → `summarize_metrics` for the metric tiles.

**Capability stability gate:** the Capability page runs `assess_control_chart` first —
Western Electric rule detection on the stream's control chart — and shows a prominent
warning when the process is out of statistical control, because Cp/Cpk are only
meaningful on a stable process.

## Conventions that matter here

- **Version SSOT** is `spc_app/__init__.py::__version__`, read by `app.py`. Bump it (and
  `apps/spc/pyproject.toml`) together at release.
- **AIAG constants** live in `spc_app/spc_engine/constants.py`; every value is cited in
  `docs/ASSUMPTIONS_LOG.md`. Don't change one without updating the other.
- **Engine returns TypedDicts** (`XbarRResult`, … `UResult` in `control_charts.py`). Page
  dispatch variables that span chart types are typed `Mapping[str, Any]` (honest read-only
  union surface); engine functions keep their exact types.
- **Coverage bar:** the testable SPC surface (`spc_engine` + `simulation` + `visualizer`)
  is gated at ≥95% in CI. Streamlit `pages/` are excluded — they need a runtime — matching
  how the FMEA bar covers `fmea_app/` but not its entry scripts.
- **Conventional commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `ci:`.
- **Shared tooling** (`ruff.toml`, `mypy.ini`) lives at the workspace root; the SPC app is
  linted and type-checked against the same bar as quality-core and FMEA.

## Engineering references

- AIAG SPC Reference Manual, 4th Ed. (2005) — control chart constants & capability indices
- Western Electric Statistical Quality Control Handbook (1956) — WE rules
- L. S. Nelson, *Journal of Quality Technology* (1984) — Nelson rules 1–8
- `docs/ASSUMPTIONS_LOG.md` — every constant/threshold used here, with citations
