# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the
SECOM app inside the Quality Platform monorepo.

## Project orientation

SECOM is the **semiconductor case study**: it applies the platform's existing SPC, capability,
and MSA machinery to a real, messy public dataset (UCI ML Repository, dataset 179 — ~590
sensor columns with heavy, honest missingness).

**SECOM is engine-only (#206).** There is no `app.py` and no `pages/` — the W09-5 Streamlit
view was deleted. Every module is computational and every one of them is coverage-gated.

Read the **root `CLAUDE.md`** first — workspace layout, CI gate, branch ladder, and the
hard-won rules live there. Then, before changing domain logic:

- **`docs/ASSUMPTIONS_LOG.md`** — every filter threshold and analysis choice with its source
  (or an explicit statement that no standard exists).
- **`docs/MSA_APPLICABILITY.md`** — why Gage R&R cannot be run on this dataset.
- **`docs/CASE_STUDY.md`** — the narrative write-up.

## Commands

All commands run from the **workspace root** via `uv`. There is nothing to `streamlit run`.

```bash
uv sync --frozen
```

### Gate (must be green before merging)

```bash
uv run ruff check .
uv run mypy
uv run pytest --cov

# SECOM coverage gate (CI enforces 100% line+branch on ALL engine modules):
uv run pytest apps/secom \
  --cov=secom_app.ingest --cov=secom_app.selection --cov=secom_app.charts \
  --cov=secom_app.capability --cov=secom_app.msa --cov=secom_app.yield_dppm \
  --cov=secom_app.doe_screening \
  --cov-report=term-missing --cov-fail-under=100
```

Unlike the SPC and MSA gates, there is **no `pages/` exclusion** — SECOM has no UI.

### Single test

```bash
uv run pytest apps/secom/tests/test_import_boundary.py -q   # the architectural tripwire
uv run pytest apps/secom/tests/test_doe_screening.py -q     # screening math
uv run pytest apps/secom -k "missingness" -q                # by keyword
```

## Architecture (big picture)

A pipeline of screens and adapters over the shared engines. SECOM **reuses** math; it does
not reimplement it.

```
secom_app/ingest.py        load_secom -> SecomDataset; secom_missingness.
                           NaN-PRESERVING on purpose (see below).
        │
        ▼
secom_app/selection.py     select_signals(SelectionCriteria) — three filters in order,
                           first failing rule wins the reported `reason`. A data-screening
                           step, NOT a published standard.
        │
        ├──► charts.py       control_chart_for_signal / control_charts_for_selection
        │                    -> SignalControlChart. I-MR math + WE/Nelson detection all
        │                    from quality_core.spc (W09-2, #66).
        │
        ├──► capability.py   capability_for_signal -> SignalCapability. Adapts the chart
        │                    result into quality_core.spc.capability.compute_capability,
        │                    coupled to the W09-2 stability gate (W09-3, #67).
        │
        ├──► msa.py          gage_rr_applicability / assert_gage_rr_applicable
        │                    -> MsaApplicability. Refuses; computes nothing (W09-4, #68).
        │
        ├──► yield_dppm.py   yield_summary -> YieldSummary; failing_signal_pareto.
        │                    Reuses W09-2 violation detection (W09-5, #69).
        │
        └──► doe_screening.py  screen_signals -> ScreeningResult. Welch's t / Cohen's d /
                               BH-FDR via scipy.stats (W11-1, #72).
```

## Conventions that matter here

- **Missingness is preserved, deliberately.** The shared validated-ingest boundary
  (`quality_core.io.load_table`) is the **wrong tool** for SECOM: it validates one Pydantic
  row model per row and normalises `NaN -> None`, which would destroy the dataset's defining
  trait. `ingest.py` bypasses it on purpose. Do not "fix" SECOM to use the shared loader.
- **Imports go downward only, and a test enforces it.**
  `tests/test_import_boundary.py` runs a **clean non-pytest interpreter** to prove both
  `secom_app` and `msa_app` resolve through the installed workspace packages — not through
  a `sys.path` hack. This app has **no `conftest.py` at all** since #231, which made
  `msa-app` installable and let the last shim go. No `spc_app` import survives anywhere in
  this app (#204, retargeted by #205 PR 3). If you find yourself importing another app, stop.
- **Reuse, never reimplement.** `charts.py` and `capability.py` are adapters over
  `quality_core.spc`; `msa.py` computes no math at all. Re-deriving I-MR limits or Cp/Cpk
  here is always wrong — the AIAG I-MR formula is written exactly once, in
  `quality_core.spc.control_charts.imr_limits()`.
- **The MSA guard refuses on structural grounds, and that is the feature.** SECOM is
  observational: one reading per wafer per sensor, with no part/appraiser/trial axis and
  none that can be legitimately constructed. Do not add a synthetic axis to make Gage R&R
  "work" — see `docs/MSA_APPLICABILITY.md`.
- **DOE screening is association, not a designed experiment.** Sensor levels are passively
  recorded, never set or randomized, so this is a screening ANALYSIS — a real fractional
  factorial / Plackett-Burman *design* requires manipulated factors SECOM cannot provide.
  Keep that disclaimer in any prose you write; do not call it "DOE" unqualified.
- **Where no standard exists, say so.** `selection.py` and `doe_screening.py` state in their
  docstrings that there is no AIAG/quality-standard table for what they do. Preserve those
  statements — implying a standard that does not exist is the same failure mode as
  fabricating a quotation.
- **SME resolutions are labelled and locked** (e.g. OQ1a in `yield_dppm.py`: the Pareto ranks
  by *violation events* on failed wafers, so one signal firing 3 rules on one wafer counts 3).
  Do not re-decide a labelled resolution without the SME.
- **Version SSOT** is `secom_app/__init__.py::__version__` (`0.7.0`), pinned by
  `tests/test_version.py`.

## Engineering references

- UCI ML Repository, dataset 179 (SECOM) — source data
- AIAG SPC Reference Manual, 4th Ed. — the I-MR and capability math (via `quality_core.spc`)
- AIAG MSA Reference Manual, 4th Ed. — the crossed-study structure SECOM cannot satisfy
- `docs/ASSUMPTIONS_LOG.md`, `docs/MSA_APPLICABILITY.md`, `docs/CASE_STUDY.md`
