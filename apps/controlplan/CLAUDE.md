# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the
Control Plan app inside the Quality Platform monorepo.

## Project orientation

The Control Plan app holds the validated Control Plan ingest schema and the
**FMEA → Control Plan connector** (W06-2, #84). It is one of five apps in the
`quality-platform` uv workspace, all sharing `packages/quality-core`. It has no standalone
`app.py`; the unified shell (`app.py` at repo root) mounts `render_control_plan` as the
"Control Plan" page.

Read the **root `CLAUDE.md`** first — workspace layout, CI gate, branch ladder, and the
hard-won rules live there. Then, before changing domain logic:

- **`docs/ASSUMPTIONS_LOG.md`** — RULE 1 (the SPC chart-selection rule table) and RULE 2
  (field defaults when there is no FMEA source), with citations. Do not change a mapping
  or a default without updating the rule.

## Commands

All commands run from the **workspace root** via `uv`.

```bash
uv sync --frozen
uv run streamlit run app.py    # unified shell -> "Control Plan" (no standalone entry)
```

### Gate (must be green before merging)

```bash
uv run ruff check .
uv run mypy
uv run pytest --cov

# Control Plan coverage gate (CI enforces 100% line+branch):
uv run pytest apps/controlplan \
  --cov=controlplan_app.connector --cov=controlplan_app.schema \
  --cov-report=term-missing --cov-fail-under=100
```

`pages/` **and the exporter** are excluded from this gate — mirroring how the SPC bar
covers the engine surface but not its entry scripts.

### Single test

```bash
uv run pytest apps/controlplan/tests/test_connector.py -q             # connector engine
uv run pytest apps/controlplan/tests/test_spc_chart_vocabulary.py -q  # chart vocabulary
uv run pytest apps/controlplan -k "duplicate" -q                      # by keyword
```

## Architecture (big picture)

Thin Streamlit page → validated ingest → pure connector engine → export layer. The
connector is engine + typed output only; it holds no UI.

```
(no standalone app.py — mounted by the repo-root shell)
        │
        ▼
controlplan_app/pages/control_plan.py   render_control_plan — upload an FMEA, generate a
                                        plan, edit it, export. load_uploaded_fmea,
                                        validate_edited_plan; TEMPLATE_PATH / DEMO_PATH;
                                        plan + source index held in st.session_state
        │
        ▼
controlplan_app/connector.py            build_control_plan — maps a relational FMEA
                                        (quality_core.schema.relational.RelationalFMEA)
                                        into ControlPlanDataset.
                                        recommend_chart — the SPC chart-selection rule
                                        table (RULE 1).
                                        source_index — traceability back to the FMEA.
        │
        ▼
controlplan_app/schema.py               ControlPlanRow / ControlPlanDataset (Pydantic v2),
                                        CONTROL_PLAN_SCHEMA (TableSchema),
                                        load_control_plan_csv. Fields: characteristic,
                                        spec/tolerance (LSL/target/USL), measurement
                                        method, sample size/frequency, control method
                                        (recommended SPC chart), reaction plan.
        │
        ▼
controlplan_app/exporter.py             export_csv / export_excel / export_pdf — bytes for
                                        st.download_button, composed over
                                        quality_core.io.export. No charts: a Control Plan
                                        is a table.
```

## Conventions that matter here

- **The connector does not redefine the output schema.** `build_control_plan` maps *into*
  the existing `ControlPlanDataset` contract (#83). Adding a field means changing
  `schema.py`, not shadowing it in the connector.
- **SME-locked mapping decisions** (recorded in the connector docstring and
  `docs/ASSUMPTIONS_LOG.md`): one `ControlPlanRow` per `FailureMode` (granularity), and
  the characteristic is `f"{function.component} — {failure_mode.description}"`. These were
  confirmed by the SME — do not re-decide them silently.
- **`recommend_chart` is a rule table, not a heuristic.** It is RULE 1 in the assumptions
  log and is pinned by `tests/test_spc_chart_vocabulary.py` against the shared SPC chart
  vocabulary in `quality_core.spc`. If the vocabulary changes, that test is the tripwire —
  fix the table, don't loosen the test.
- **Defaults are declared, not invented.** `_DEFAULT_SAMPLE_SIZE` and `_DEFAULT_FREQUENCY`
  apply only where the FMEA supplies no source (RULE 2). They are placeholders a quality
  engineer is expected to override, not recommendations — and every row
  `build_control_plan` emits says so, via `sample_plan_is_placeholder=True` (F-10, #196).
- **Export escapes formula injection.** `export_csv`/`export_excel` route through
  `quality_core.io.export`, which escapes `=`, `+`, `-`, `@` prefixes on string columns.
  There are regression tests; don't bypass the shared primitives.
- **Version SSOT** is `controlplan_app/__init__.py::__version__` (`0.7.0`), pinned by
  `tests/test_version.py` and consumed by the exporter as `_TOOL_VERSION`.

## Engineering references

- AIAG APQP / Control Plan methodology — plan field set and reaction-plan intent
- `docs/ASSUMPTIONS_LOG.md` — the chart-selection rule table and field defaults, cited
- `quality_core.spc` — the shared chart vocabulary `recommend_chart` must agree with
