# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project orientation

Before starting work, also read:
- **`FMEA-Memory.md`** — durable project memory (architecture, current version, recent fixes-not-to-regress, known unknowns).
- **`CLAUDE_CODE_PLAYBOOK.md`** — operating protocol (Opus plans / Sonnet executes, session flow, gates).
- **`AUDIT_AND_ROADMAP_PROMPT.md`** — the 10-phase audit→fix→build→release program. Open at the start of each phase.
- **`FUTURE_SCOPE_AND_MARKET_RESEARCH.md`** — only at Phase 9 (BUILD).

## Commands

### Install
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Run
```bash
streamlit run app.py                                                # web app
python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv --charts   # CLI
```

### Gate (must be green before merging)
```bash
python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing
ruff check src/ tests/ app.py fmea_analyzer.py ui/
mypy src/ ui/ --ignore-missing-imports
```

### Single test
```bash
pytest tests/test_rpn_engine.py::test_calculate_rpn_basic -v        # one test
pytest tests/test_rpn_engine.py -v                                  # one module
pytest -k "injection" -v                                            # by keyword
```

CI (`.github/workflows/ci.yml`) runs on Python 3.11 and executes exactly the three gate commands above. Pre-commit hooks: `ruff --fix`, `ruff-format`, `mypy --ignore-missing-imports`.

## Architecture (big picture)

Layered Streamlit app with a clean orchestrator → engine → adapter split. Two entry points, one engine.

```
app.py            Streamlit entry, thin orchestrator
fmea_analyzer.py  CLI entry  (may be partially redundant with src/ — verify before deleting)
        │
        ▼
src/rpn_engine.py     Pure-pandas pipeline: validate_input → calculate_rpn → flag_critical → rank_by_rpn → run_pipeline
src/schema.py         Pydantic v2 FMEARow / FMEADataset — validate_input delegates here
        │
        ├──► src/plotly_charts.py    interactive charts for Streamlit
        ├──► src/visualizer.py       static matplotlib charts for CLI + PDF embedding
        └──► src/exporter.py         openpyxl (Excel, color-coded) + fpdf2 (3-page A4 PDF)
                                     holds _TOOL_VERSION (currently hardcoded "1.0.0")

ui/filters.py | ui/charts.py | ui/exports.py    Streamlit-only helpers, consumed by app.py
```

**Data flow:** CSV/Excel upload → `validate_input` (11 required columns; S/O/D strict ints 1–10) → `calculate_rpn` (vectorized `S*O*D`) → `flag_critical` (three boolean flags) → `rank_by_rpn` (sort desc + Red/Yellow/Green tier) → `ui/filters.py` applies sidebar masks → `ui/charts.py` renders Plotly → `ui/exports.py` calls `src/exporter.py` for bytes.

**Domain constants live in `src/rpn_engine.py`:** `RPN_HIGH_THRESHOLD=100`, `SEVERITY_HIGH_THRESHOLD=9`, `RPN_ACTION_PRIORITY_H_THRESHOLD=200`, `RPN_RED_THRESHOLD=100`, `RPN_YELLOW_MIN=50`. Every threshold has a citation in `docs/ASSUMPTIONS_LOG.md` — do not change a threshold without updating that doc.

## Conventions that matter here

- **Conventional commits** in active use: `feat:`, `fix:`, `refactor:`, `docs:`, `ci:`, `style:`, `test:`. One logical change per commit.
- **Strict-int validation for S/O/D** — floats and bools are rejected at the ingest boundary (`_is_strict_int` helper). Tests enforce this; don't loosen.
- **CSV/formula-injection mitigation in exporters** — `=`, `+`, `-`, `@` prefixes are escaped on all string columns before Excel/CSV write. There is a regression test; don't regress.
- **Export cache key** is a hash of the *filtered* DataFrame with index reset. Don't change the hashing without updating tests for index-sensitivity.
- **Version is currently hardcoded** as `_TOOL_VERSION` in `src/exporter.py`. There is no single source of truth yet — Phase 10.2 will introduce one.
- **`ruff.toml`:** target `py311`, line length 100, selects `E F W I`, ignores `E501` (formatter handles) and `F401` (re-exports). Per-file: `F811` allowed in `tests/`.

## Engineering references

`docs/FMEA_COMPLETE_GUIDE.md` (start here for domain context), `docs/FMEA_methodology_notes.md` (RPN derivation + AP logic), `docs/ASSUMPTIONS_LOG.md` (every threshold with AIAG citation), `docs/FMEA_input_schema.md` (column spec).
