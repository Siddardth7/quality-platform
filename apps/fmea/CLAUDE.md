# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the
FMEA app inside the Quality Platform monorepo.

## Project orientation

The FMEA app is one of five apps in the `quality-platform` uv workspace, all sharing
`packages/quality-core`. It runs standalone (`apps/fmea/app.py`), has a CLI entry
(`fmea_analyzer.py`), and is mounted into the unified shell (`app.py` at repo root).

Read the **root `CLAUDE.md`** first — workspace layout, the full CI gate, the branch
ladder, and the hard-won rules live there. Then, for this app:
- **`FMEA-Memory.md`** — durable project memory (architecture, current version, recent fixes-not-to-regress, known unknowns).
- **`CLAUDE_CODE_PLAYBOOK.md`** — operating protocol (Opus plans / Sonnet executes, session flow, gates).
- **`AUDIT_AND_ROADMAP_PROMPT.md`** — the 10-phase audit→fix→build→release program. Open at the start of each phase.
- **`FUTURE_SCOPE_AND_MARKET_RESEARCH.md`** — only at Phase 9 (BUILD).

## Commands

All commands run from the **workspace root** via `uv` (not from `apps/fmea`). The
`requirements.txt` / `requirements-dev.txt` in this directory are legacy leftovers from
before the uv workspace — they are not the install path.

### Install
```bash
uv sync --frozen
```

### Run
```bash
uv run streamlit run apps/fmea/app.py                    # standalone FMEA app
uv run streamlit run app.py                              # unified shell, from repo root
uv run python apps/fmea/fmea_analyzer.py \
  --input apps/fmea/data/composite_panel_fmea_demo.csv --charts    # CLI
```

### Gate (must be green before merging)
```bash
uv run ruff check .
uv run mypy
uv run pytest --cov
```

There is no FMEA-specific coverage gate in CI; FMEA is covered by the repo-wide
`uv run pytest --cov`. See the root `CLAUDE.md` for the eight per-surface gates that do run.

### Single test
```bash
uv run pytest apps/fmea/tests/test_rpn_engine.py -q                 # one module
uv run pytest apps/fmea -k "injection" -q                           # by keyword
```

CI (`.github/workflows/ci.yml`, job id `gate`) runs on Python 3.11. There is no
pre-commit hook configuration in this repo — `ruff` and `mypy` are enforced by CI only.

## Architecture (big picture)

Layered Streamlit app with a clean orchestrator → engine → adapter split. Two entry points, one engine.

```
app.py            Streamlit entry, thin orchestrator
fmea_analyzer.py  CLI entry  (may be partially redundant with fmea_app/ — verify before deleting)
        │
        ▼
fmea_app/rpn_engine.py     Pure-pandas pipeline: validate_input → calculate_rpn → flag_critical → rank_by_rpn → run_pipeline
fmea_app/schema.py         Pydantic v2 FMEARow / FMEADataset — validate_input delegates here
        │
        ├──► fmea_app/plotly_charts.py    interactive charts for Streamlit
        ├──► fmea_app/visualizer.py       static matplotlib charts for CLI + PDF embedding
        └──► fmea_app/exporter.py         openpyxl (Excel, color-coded) + fpdf2 (3-page A4 PDF)
                                     holds _TOOL_VERSION (currently hardcoded "1.0.0")

ui/filters.py | ui/charts.py | ui/exports.py    Streamlit-only helpers, consumed by app.py
```

**Data flow:** CSV/Excel upload → `validate_input` (11 required columns; S/O/D strict ints 1–10) → `calculate_rpn` (vectorized `S*O*D`) → `flag_critical` (three boolean flags) → `rank_by_rpn` (sort desc + Red/Yellow/Green tier) → `ui/filters.py` applies sidebar masks → `ui/charts.py` renders Plotly → `ui/exports.py` calls `fmea_app/exporter.py` for bytes.

**Domain constants live in `fmea_app/rpn_engine.py`:** `RPN_HIGH_THRESHOLD=100`, `SEVERITY_HIGH_THRESHOLD=9`, `RPN_ACTION_PRIORITY_H_THRESHOLD=200`, `RPN_RED_THRESHOLD=100`, `RPN_YELLOW_MIN=50`. Every threshold has a citation in `docs/ASSUMPTIONS_LOG.md` — do not change a threshold without updating that doc.

## Conventions that matter here

- **Conventional commits** in active use: `feat:`, `fix:`, `refactor:`, `docs:`, `ci:`, `style:`, `test:`. One logical change per commit.
- **Strict-int validation for S/O/D** — floats and bools are rejected at the ingest boundary (`_is_strict_int` helper). Tests enforce this; don't loosen.
- **CSV/formula-injection mitigation in exporters** — `=`, `+`, `-`, `@` prefixes are escaped on all string columns before Excel/CSV write. There is a regression test; don't regress.
- **Export cache key** is a hash of the *filtered* DataFrame with index reset. Don't change the hashing without updating tests for index-sensitivity.
- **Version SSOT** is `fmea_app/__init__.py::__version__` (currently `0.7.0`, matching the
  workspace). `fmea_app/exporter.py` reads it as `_TOOL_VERSION = __version__` — do not
  reintroduce a hardcoded literal. `tests/test_version.py` pins it.
- **`ruff.toml`:** target `py311`, line length 100, selects `E F W I`, ignores `E501` globally (formatter handles). `F401` is enforced globally (#203) with a per-file ignore on `fmea_app/exporter.py`, the one module that re-exports without `__all__`. Per-file: `F811` allowed in `tests/`.

## Engineering references

`docs/FMEA_COMPLETE_GUIDE.md` (start here for domain context), `docs/FMEA_methodology_notes.md` (RPN derivation + AP logic), `docs/ASSUMPTIONS_LOG.md` (every threshold with AIAG citation), `docs/FMEA_input_schema.md` (column spec).
