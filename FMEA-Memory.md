# FMEA Risk Analyzer — Project Memory

> Durable, session-portable context. Load this first in any new Claude Code session before touching code or running the program. Pair with `CLAUDE_CODE_PLAYBOOK.md` (how to operate) and `AUDIT_AND_ROADMAP_PROMPT.md` (the steps). Open `FUTURE_SCOPE_AND_MARKET_RESEARCH.md` only at Session D / Phase 9.

---

## 1. What this project is

A Streamlit web app that automates **Process FMEA risk analysis**: user uploads CSV/Excel of failure modes → tool validates schema, computes RPN (Severity × Occurrence × Detection), applies AIAG FMEA-4 criticality flags, ranks into Red/Yellow/Green tiers, renders interactive Pareto + heatmap, exports color-coded Excel and a 3-page A4 PDF. Also has a CLI entry point.

- **Live demo:** `fmea-risk-analyzer-mhwzcki9sdzfz5d8rbzsdn.streamlit.app`
- **Repo:** `git@github.com:Siddardth7/fmea-risk-analyzer.git` (branch: `main`)
- **Author/owner:** Siddardth Pathipaka — M.S. Aerospace, UIUC
- **License:** MIT
- **Audience this is being built for:** engineering hiring managers + small engineering teams stuck on Excel.

---

## 2. Current version & baseline status

- **Version:** `1.0.0` — hardcoded as `_TOOL_VERSION` in `src/exporter.py`. **No single source of truth yet** — this is a known finding to fix in Phase 10.2.
- **Tests:** README badge claims 98 passing across 5 test modules. **Verify in Phase 1.3 before trusting.**
- **CI:** `.github/workflows/ci.yml` runs ruff, mypy (`src/`, `ui/` only, with `--ignore-missing-imports`), and pytest with coverage. Pre-commit: ruff + ruff-format + mypy.
- **No `CLAUDE.md` yet** — generate via `/init` in Session A / Phase 1.2.

---

## 3. Repo map (entry points → modules)

```
app.py                  Streamlit entry, thin orchestrator (~739 LOC per audit prompt; verify)
fmea_analyzer.py        CLI entry (~258 LOC). SUSPECT: may duplicate src/rpn_engine.py — check in Phase 1.4
requirements.txt        Pinned runtime deps
requirements-dev.txt    Pinned dev deps (pytest, ruff, mypy, pytest-cov)

src/
  __init__.py
  rpn_engine.py         Core: validate_input → calculate_rpn → flag_critical → rank_by_rpn → run_pipeline
  schema.py             Pydantic v2 FMEARow / FMEADataset models (validate_input delegates here)
  exporter.py           Excel (openpyxl, color fills) + PDF (fpdf2 + matplotlib PNG embed). Holds _TOOL_VERSION.
  plotly_charts.py      Interactive Pareto + heatmap for Streamlit
  visualizer.py         Static matplotlib charts for CLI and PDF embedding

ui/
  __init__.py
  filters.py            Sidebar RPN slider + Severity≥9 toggle
  charts.py             Chart-rendering helpers consumed by app.py
  exports.py            Export-button helpers consumed by app.py

tests/
  test_rpn_engine.py            RPN math, flagging, ranking, validation
  test_exporter.py              Excel + PDF output bytes
  test_visualizer.py            matplotlib chart functions
  test_streamlit_edge_cases.py  empty / malformed / all-green
  test_app_integration.py       upload → validate → export boundary
  test_ui_modules.py            ui/ helpers

data/
  composite_panel_fmea_demo.csv   30-row CFRP aerospace PFMEA demo
  fmea_input_template.csv         Blank user template

docs/
  FMEA_COMPLETE_GUIDE.md          Knowledge + teaching guide (start here for domain)
  FMEA_methodology_notes.md       RPN derivation, AP logic, Pareto application
  ASSUMPTIONS_LOG.md              Every threshold with AIAG citation
  FMEA_input_schema.md            Column spec + validation rules
  EXECUTION_ROADMAP.md            Original 4-week build plan
  LAUNCH_POST.md                  LinkedIn launch copy
  superpowers/                    (unknown — inspect if relevant)

.github/workflows/ci.yml
.streamlit/config.toml            Cloud theme config
.pre-commit-config.yaml           ruff + ruff-format + mypy
ruff.toml
.devcontainer/                    Dev container setup
```

**Data flow (must match reality — verify in Phase 1):** upload → `validate_input` → `calculate_rpn` (vectorized `S*O*D`) → `flag_critical` (three boolean flags) → `rank_by_rpn` (sort desc + assign Red/Yellow/Green) → filter via `ui/filters.py` → render via `ui/charts.py` (Plotly) → export via `ui/exports.py` → bytes from `src/exporter.py`.

---

## 4. Stack (pinned)

Python 3.10+ (CI may pin 3.11). Pinned runtime:
- `streamlit==1.56.0`, `pandas==3.0.2`, `plotly==6.6.0`, `numpy==2.4.4`
- `fpdf2==2.8.7`, `openpyxl==3.1.5`, `matplotlib==3.10.8`, `pydantic>=2.0`

Dev: `pytest>=8.0`, `pytest-cov>=5.0`, `ruff>=0.4`, `mypy>=1.10`.

> **pandas 3.0.2 and numpy 2.4.4 are aggressive pins** — flag for Phase 3.3 web-CVE check; some advisories may apply.

---

## 5. The engineering essentials (don't get this wrong)

- **RPN = Severity × Occurrence × Detection.** Each on integer 1–10. Range 1–1000.
- **Flag rules (AIAG FMEA-4 + tool conventions):**
  - `Flag_High_RPN` = RPN > 100
  - `Flag_High_Severity` = Severity ≥ 9 (mandatory action regardless of O/D)
  - `Flag_Action_Priority_H` = (RPN ≥ 200) OR (Severity ≥ 9) — *simplified* approximation of AIAG-VDA AP "High" tier
- **Risk tiers:** Red = RPN>100 OR Sev≥9; Yellow = 50≤RPN≤100 AND Sev<9; Green = RPN<50 AND Sev<9.
- **Input schema is exactly 11 columns** — see `docs/FMEA_input_schema.md`. S/O/D must be **strict ints** (floats and bools rejected — recent fixes hardened this; see commits `063d707`, `dd2a2f8`, `2bb996a`).
- **CSV/formula injection** is mitigated in exporters (commits `d5cf351`, `513fda2`) — `=`, `+`, `-`, `@` prefixes escaped. Don't regress this.
- **Export cache** keys on a filtered-DataFrame hash with index reset (commits `2e007a8`, `eb1ddde`). Don't regress.

---

## 6. The methodology gap (drives the roadmap)

The 2019 AIAG-VDA harmonized handbook **replaced RPN with Action Priority (AP)** — a severity-first lookup table returning High/Medium/Low. This tool currently does RPN with a simplified AP-H flag, not the full AP matrix.

**→ The full AP engine is Tier-1 feature #1 and the highest-leverage thing to build in Phase 9.** Keep RPN alongside for legacy/teaching. Details: `FUTURE_SCOPE_AND_MARKET_RESEARCH.md` §4 Tier 1.

---

## 7. Operating protocol

From `CLAUDE_CODE_PLAYBOOK.md`:

- **Opus plans, Sonnet executes.** Switch with `/model`. Opus reads docs, designs, decides, reviews; Sonnet implements one bounded unit per pass against a written plan. **Every plan must be written down** (entry in AUDIT_REPORT.md, ROADMAP.md, or an explicit checklist) — handoff cannot live only in Opus's head.
- **Stages are sequential, gates are hard:** AUDIT (Phases 1–7, read-only) → FIX (Phase 8) → BUILD (Phase 9) → RELEASE (Phase 10). No feature work until the green gate after fixes.
- **Three user checkpoints:** end of Phase 1 (baseline), end of Phase 7 (audit report), before Phase 10 (release).
- **One logical change per commit.** Conventional commits already in use: `feat:`, `fix:`, `refactor:`, `docs:`, `ci:`, `style:`, `test:`.
- **Ask before destructive/irreversible actions:** deleting modules (e.g., `fmea_analyzer.py`), force push, tagging, publishing.

---

## 8. Useful commands

```bash
# Baseline / gate
pip install -r requirements.txt -r requirements-dev.txt --break-system-packages
python -m pytest tests/ -v --cov=src --cov-report=term-missing
ruff check .
mypy src/ ui/ --ignore-missing-imports

# Run app / CLI
streamlit run app.py
python fmea_analyzer.py --input data/composite_panel_fmea_demo.csv --charts

# Audit scanners (install once)
pip install pip-audit bandit vulture radon deptry --break-system-packages
pip-audit -r requirements.txt
bandit -r src/ ui/ app.py fmea_analyzer.py
vulture . --min-confidence 70
radon cc -s -a src/ ui/ app.py
radon mi src/
deptry .
pip list --outdated
```

---

## 9. Known unknowns / things to verify in Phase 1

1. Is `fmea_analyzer.py` (root, ~258 LOC) still wired in, or dead code duplicating `src/rpn_engine.py`?
2. Does the test suite actually pass at 98 (README badge claim) on current `main`?
3. What is the real coverage % on `src/` and `ui/`?
4. Does `mypy --strict` reveal a meaningful gap vs CI's `--ignore-missing-imports` mode?
5. Are pandas 3.0.2 / numpy 2.4.4 / streamlit 1.56 actually mutually resolvable on a fresh install?
6. What is `docs/superpowers/`?

---

## 10. The three-document system (re-orient if lost)

| File | Purpose | When to read |
|---|---|---|
| `CLAUDE_CODE_PLAYBOOK.md` | HOW to operate (models, sessions, skills) | Every new session, first |
| `AUDIT_AND_ROADMAP_PROMPT.md` | THE STEPS (Phases 1–10) | Before each phase |
| `FUTURE_SCOPE_AND_MARKET_RESEARCH.md` | WHAT to build + WHY (Tier 1/2/3) | Session D / Phase 9 only |
| `FMEA-Memory.md` *(this file)* | Durable project memory | Every new session, alongside playbook |

Artifacts to be produced by the program (not yet present):
- `CLAUDE.md` (Phase 1.2)
- `AUDIT_REPORT.md` (Phase 7)
- `ROADMAP.md` (Phase 9.5)
- `CHANGELOG.md` (Phase 10.3)

---

---

## 11. Phase 1 baseline (recorded 2026-06-05)

Environment: macOS, `/opt/homebrew/bin/python3.11` (3.11.15). Deps installed from `requirements.txt` + `requirements-dev.txt`.

**Gate results:**
- **pytest: 97 passed, 1 FAILED.** Failure: `tests/test_app_integration.py::test_demo_renders_without_exception`. Root cause: `app.py:173` uses `pd.io.formats.style.Styler` as a return-type annotation; on **pandas 3.0.2** this attribute path no longer resolves at module load → `AttributeError: module 'pandas.io.formats' has no attribute 'style'`. **The Streamlit app does not currently load.** README badge claim of "98 passing" is stale relative to the pandas pin.
- **Coverage: 88% on `src/`.** Per-module: `rpn_engine` 100%, `visualizer` 100%, `exporter` 97%, `schema` 97%, **`plotly_charts` 18% (major gap, lines 42–51, 84–195, 221–329)**.
- **ruff: clean.**
- **mypy (`--ignore-missing-imports`): 3 errors, all in `src/visualizer.py`** — line 215 (`imshow extent` list-vs-tuple), line 233 (`set_xticklabels` with `range[int]`), line 234 (`set_yticklabels` with `range[int]`).

**Repo map confirmed:**
- `app.py` = 739 LOC ✓; `fmea_analyzer.py` = 258 LOC.
- `fmea_analyzer.py` is **not a duplicate** of `src/` — it imports `run_pipeline` from `src.rpn_engine` and chart fns from `src.visualizer`. It's a thin CLI wrapper. Keep, don't delete blindly.
- Internal import graph: `app.py` → `src.rpn_engine`; `ui/charts.py` → `src.plotly_charts`; `ui/exports.py` → `src.exporter`; `src.exporter` lazy-imports matplotlib charts from `src.visualizer` for PDF embedding; `src.rpn_engine` → `src.schema`.
- Vulture (confidence ≥70): only 2 hits — `source_active` unused at `app.py:271`, and `cls` at `src/schema.py:34` (false positive, standard pydantic validator).

**Top candidates already surfaced for the Phase 7 fix queue:**
1. **CRITICAL** — `app.py:173` Styler annotation breaks on pandas 3.0.2 (app won't load). Fix: string-forward annotation `"pd.io.formats.style.Styler"` or explicit `import pandas.io.formats.style`.
2. **MEDIUM** — `src/visualizer.py` mypy errors (3) — tuple-cast `extent`, stringify `range` for tick labels.
3. **MEDIUM** — `src/plotly_charts.py` coverage gap (18%) — almost all chart rendering untested.
4. **LOW** — `app.py:271` unused `source_active`.
5. **DOC** — README claims "98 passing"; actual on current pins is 97 passing + 1 failing. Refresh once #1 is fixed.

---

*Last updated: 2026-06-05 — Phase 1 baseline recorded; awaiting user gate to proceed to Phase 2.*
