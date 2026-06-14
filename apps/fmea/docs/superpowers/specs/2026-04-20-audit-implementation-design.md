# FMEA Risk Analyzer — Audit Implementation Design

**Date:** 2026-04-20
**Status:** Approved
**Source:** Full Audit Report (`FMEA_Risk_Analyzer_Full_Audit_Report.md`)
**Approach:** Sequential Phases — each phase is independently deployable

---

## Goal

Transform the FMEA Risk Analyzer from a polished portfolio demo into a hardened product foundation. Fix all P0 correctness and trust issues first, then add reliability and UX improvements, then refactor the architecture for future product growth.

---

## Decisions

| Topic | Decision | Rationale |
|---|---|---|
| Schema layer | Pydantic v2 models | Future-proof for FastAPI, clean validation errors, JSON serialization built-in |
| CI setup | GitHub Actions + pre-commit hooks | Both: local fast feedback + public CI badge for portfolio |
| PDF export | Fix current matplotlib path | Remove misleading Plotly figure args, clean up API, no kaleido re-introduction |
| `app.py` split | Minimal 3-module split | `ui/filters.py`, `ui/charts.py`, `ui/exports.py` — thin orchestrator remains |
| `.xls` support | Remove | Untested, legacy format, erodes trust more than it adds value |

---

## Phase 1 — Correctness & Trust (P0)

**Goal:** Make the tool trustworthy. Fix every bug that can produce wrong engineering conclusions or break the user mid-workflow.

### 1.1 Schema Validation Hardening (`src/rpn_engine.py`)

- Enforce integer-only S/O/D: reject floats, booleans, and numeric strings
- Add null/type checks for all required non-score columns explicitly:
  - `ID` — must be non-null and integer-convertible; duplicate IDs rejected at this boundary
  - `Process_Step` — must be non-null string (drives UI filtering)
  - `Component`, `Function`, `Failure_Mode`, `Effect`, `Cause`, `Current_Control` — must be non-null strings (drive reporting)
- All rejections happen at the validation boundary — nothing malformed reaches UI, charts, or export
- Add regression tests: decimal inputs, null text fields, null ID, non-integer ID, duplicate IDs, boolean scores

### 1.2 Formula Injection Fix (`src/exporter.py`)

- Escape any cell value starting with `=`, `+`, `-`, or `@` in both Excel and CSV exports
- Add regression tests for each injection character
- Document the sanitization policy in code

### 1.3 Lazy Export Generation (`app.py`)

- Cache `export_excel()` and `export_pdf()` results in `st.session_state` keyed by **filtered DataFrame hash + filter state** (not source dataset hash alone — exports reflect the filtered view the user sees)
- Cache key: `hashlib.md5(df_filtered.to_json().encode()).hexdigest()` + `(rpn_min, sev9_only, tuple(sorted(process_steps)), export_type)`
- Generate bytes only once per unique filtered view, not on every Streamlit rerender
- Wrap both calls in `try/except` — export errors must not crash the dashboard render

### 1.4 PDF API Cleanup (`src/exporter.py`)

- Remove unused `pareto_fig` / `heatmap_fig` parameters from `export_pdf()`
- Update all call sites in `app.py`, tests, docs, and exporter docstrings/signatures (`fmea_analyzer.py` does not call `export_pdf()` today)
- Fix page break: repeat table headers on every new page
- Update all PDF-related documentation to reflect the clean matplotlib-only implementation

### 1.5 Documentation Rewrite

Files: `README.md`, `docs/FMEA_COMPLETE_GUIDE.md`, `docs/ASSUMPTIONS_LOG.md`

- Recompute all demo dataset statistics from actual CSV:
  - 11 process steps
  - Risk distribution: Red=19, Yellow=9, Green=2
  - High RPN=14, Action Priority H=8
  - Top 6 rows ≈ 29.15% of total RPN (not ~82%)
- Fix Pareto methodology narrative to match actual implementation (Risk_Tier coloring, not Pareto banding)
- Remove broken screenshot references (`README.md:251`)
- Add `LICENSE` file (MIT)
- Remove `.xls` from all supported format mentions
- Remove `kaleido` references from PDF documentation
- Fix AP-H framing: label it explicitly as a threshold simplification, not full AIAG/VDA AP compliance

---

## Phase 2 — Reliability & UX (P1)

**Goal:** Prove the product works end-to-end and remove friction points that undermine user confidence.

### 2.1 App-Level Integration Tests (`tests/test_app_integration.py`)

- Use Streamlit's `AppTest` harness
- Cover: demo dataset load, CSV upload, filter interactions, session state, export button triggers, malformed upload error handling
- Schema boundary tests: decimal S/O/D, null `Process_Step`, null `ID`, formula-prefixed strings (duplicate ID rejection is enforced in Phase 1 validation — these tests verify that behavior via the app layer)
- These replace the role the misleadingly-named `test_streamlit_edge_cases.py` was supposed to fill

### 2.2 Chart Cache Key Fix (`app.py`)

- Replace weak cache key `(rpn_min, sev9_only, steps, len(df), dark)` with one that includes a stable content hash
- Implementation: `hashlib.md5(df.to_json().encode()).hexdigest()` included in the key
- Prevents stale charts after dataset changes with identical filter selections

### 2.3 Dynamic RPN Filter (`app.py`)

- Replace hardcoded `max=300` with `max=int(df["RPN"].max())`, floored at 10, capped at 1000
- Slider now reflects actual dataset range

### 2.4 Validation Summary Panel (`app.py`)

- Show a compact "Dataset Health" panel after successful upload, before main dashboard renders
- Display: row count, column coverage, any near-boundary score warnings, long text field warnings
- Makes validation boundary visible and builds user confidence

### 2.5 Dev Dependencies (`requirements-dev.txt`)

- Separate runtime deps (`requirements.txt`) from dev/test deps (`requirements-dev.txt`)
- Dev deps: `pytest`, `pytest-cov`, `ruff`, `mypy`
- Update README test instructions accordingly

---

## Phase 3 — Product Foundation (P2)

**Goal:** Refactor the architecture so the codebase can grow into a real product without accumulating more structural debt.

### 3.1 Pydantic Schema Layer (`src/schema.py`)

- Introduce `FMEARow` Pydantic model mirroring the exact existing column contract:
  - `ID: int` — non-null, positive integer
  - `Process_Step`, `Component`, `Function`, `Failure_Mode`, `Effect`, `Cause`, `Current_Control`: `str` — non-null
  - `Severity`, `Occurrence`, `Detection`: `int` with `ge=1, le=10` constraints
  - Computed `RPN` property (`Severity * Occurrence * Detection`)
- Introduce `FMEADataset` model:
  - Wraps `list[FMEARow]`
  - Dataset-level validator: reject duplicate `ID` values
- `rpn_engine.py` validation rewrites to use these models as the single source of truth
- DataFrame-level checks become model-level checks; DataFrames remain for computation only
- Sets foundation for future FastAPI API contract

### 3.2 `app.py` Minimal Split

New structure:
```
ui/
  __init__.py
  filters.py      # Sidebar filter logic, process step multiselect, RPN slider
  charts.py       # Chart rendering, cache key logic, dark mode handling
  exports.py      # Export button generation, lazy caching, error isolation
app.py            # Thin orchestrator (~150 lines): imports and composes ui modules
```

- No behavior changes — purely structural
- Each module has one clear responsibility and can be understood independently

### 3.3 CI Pipeline

**`.github/workflows/ci.yml`:**
- Trigger: every push and pull request
- Jobs: `pytest` (with coverage), `ruff` (lint), `mypy` (type check)
- Add CI status badge to README

**`.pre-commit-config.yaml`:**
- Hooks: `ruff --fix`, `mypy`
- Runs locally before every commit for fast feedback

### 3.4 PDF Layout Improvements (`src/exporter.py`)

- Repeated table headers on every page break
- Width-aware text wrapping for long cell values
- Tests on larger datasets (100, 500 rows)

### 3.5 Dead Dependency Cleanup (`requirements.txt`)

- Remove `kaleido`
- Add `pydantic>=2.0` as runtime dependency
- Audit all remaining pins for accuracy and necessity

---

## Architecture After Phase 3

```
fmea-risk-analyzer/
├── app.py                    # Thin orchestrator
├── fmea_analyzer.py          # CLI wrapper
├── src/
│   ├── schema.py             # NEW: Pydantic FMEARow + FMEADataset models
│   ├── rpn_engine.py         # Uses schema models for validation
│   ├── plotly_charts.py      # Interactive Streamlit charts
│   ├── visualizer.py         # Static matplotlib charts (CLI + PDF)
│   └── exporter.py           # Hardened Excel + PDF export
├── ui/                       # NEW: extracted from app.py
│   ├── filters.py
│   ├── charts.py
│   └── exports.py
├── tests/
│   ├── test_rpn_engine.py
│   ├── test_visualizer.py
│   ├── test_exporter.py
│   ├── test_streamlit_edge_cases.py
│   └── test_app_integration.py   # NEW
├── .github/workflows/ci.yml      # NEW
├── .pre-commit-config.yaml        # NEW
├── requirements.txt
└── requirements-dev.txt           # NEW
```

---

## What Is Not In Scope

These items are explicitly deferred to avoid scope creep:

- Full AIAG/VDA Action Priority lookup table (P3)
- Project persistence / database (P3)
- Authentication / multi-user (P3)
- DFMEA support (P3)
- FastAPI backend extraction (P3)
- Plotly-based PDF rendering (reconsidered only when backend service exists)

---

## Success Criteria

| Phase | Done When |
|---|---|
| Phase 1 | All 61 existing tests pass + new boundary tests pass; no float scores accepted; no formula injection in exports; PDF API has no unused args; README stats match actual CSV |
| Phase 2 | `AppTest`-based integration tests pass for upload, filter, and export flows; RPN slider max is data-driven; validation panel renders on upload |
| Phase 3 | Pydantic models are the validation source of truth; `app.py` is ≤150 lines; CI runs green on push; `kaleido` removed from deps |
