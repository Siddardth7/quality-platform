# Changelog

All notable changes to the Quality Platform are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to adhere to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-06-16

Week 03: AP-native FMEA. FMEA moves from RPN-only to the AIAG/VDA 2019 Action Priority standard —
the full published S×O×D → High/Medium/Low table, a user-selectable prioritization basis, and
data-driven rating scales — with the AP table verified cell-by-cell against the AIAG & VDA FMEA
Handbook (2019) primary source.

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **AIAG-VDA Action Priority (AP) engine** (`fmea_app/ap_engine.py`) — the complete published
  S×O×D → High/Medium/Low table (no approximation), with `action_priority()`, `calculate_ap()`,
  and `rank_by_ap()`. Severity-weighted (S → O → D), but high severity does not auto-escalate.
- **RPN ↔ AP toggle** in the FMEA app — both columns shown side by side; the selected basis drives
  ranking, tiering, the critical-items view, and the Excel / PDF / CSV exports.
- **Data-driven S/O/D rating scales** — AIAG default in `data/rating_scales.json` plus a validated
  custom-scale upload, with an in-app Rating Scale reference (`fmea_app/rating_scales.py`).
- **Primary-source verification of the AP table** — the engine matches the AIAG & VDA FMEA Handbook
  (2019) table for all 1000 S/O/D combinations, cross-checked against an external peer-reviewed
  case study (MDPI, Pop et al. 2026), guarded by an independent test oracle.

### Changed

- **FMEA version single-source-of-truth** — `fmea_app.__version__`, read by the exporter and the
  app sidebar, with a drift-guard test; the hardcoded `"1.0.0"` is removed.
- **FMEA docs** — methodology §4.2, `ASSUMPTIONS_LOG.md` Rule 7, and the README now document the AP
  engine and cite the verified handbook primary source.

### Fixed

- **Corrected the AP table's Severity 9-10 block** — a transcription from a third-party reproduction
  had shifted the occurrence rows (e.g. `S9-10/O1` was `H,M,L,L`; the handbook is all `Low`). Caught
  in code review, resolved against the primary source. Monotonicity alone did not catch it (the
  shifted block stayed monotonic), so the test oracle is now transcribed from the handbook.
- **Critical-items panel** cites the correct standard under the AP basis; **rating-scale upload**
  rejects custom keys that collide on integer coercion (`"1"` vs `"1.0"`).

### Notes

- FMEA: 266 tests; platform: 390 tests, ruff + mypy clean.

## [0.2.0] - 2026-06-15

Week 02: SPC parity. The SPC app is brought to the same engineering bar as FMEA — type-safe,
lint-clean, coverage-gated, with two capability/charting gaps closed and full planning docs.

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **c-chart** surfaced in the Control Charts UI (`compute_c` was implemented but unwired): new
  constant-area `panel_defects` demo stream, render branch with WE/Nelson rule overlays, and
  metric tiles.
- **Capability stability gate** — the Process Capability page now runs Western Electric rule
  detection first and warns prominently that Cp/Cpk are not valid on an out-of-control process.
- **SPC coverage gate** in CI — the testable SPC surface (engine + simulation + visualizer) is
  enforced at ≥95% (`--cov-fail-under`); brought to 100% (incl. the previously-untested
  `simulation/engine.py`).
- **SPC planning docs** — `apps/spc/CLAUDE.md`, `apps/spc/docs/ASSUMPTIONS_LOG.md` (every AIAG
  constant + threshold cited), and a version single-source-of-truth (`spc_app.__version__`) with
  a drift-guard test.

### Changed

- **SPC is now mypy-clean and in the type gate** — replaced lossy `dict[str, float | list[float]]`
  engine returns with precise TypedDicts; `spc_app` added to `mypy.ini`.
- **SPC is now ruff-clean** under the unified root config (import-ordering enforced).
- **Dependency pins reconciled** to one coherent set — every dependency declared `>=<locked
  version>`, identical across `quality-core` and both apps; dev-tool floors aligned to locked.

### Removed

- Stray `apps/spc/docs/superpowers/` plan/spec artifacts from the standalone era.

### Notes

- FMEA: 105 tests. SPC: now 124 tests (engine/simulation/visualizer at 100%). Workspace: 229 tests,
  ruff + mypy clean, CI gate + SPC coverage gate green.

## [0.1.0] - 2026-06-15

First public release — Week 01: monorepo + shared core. The platform now publicly exists.

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **Monorepo** housing the FMEA Risk Analyzer (`apps/fmea`) and Manufacturing SPC Dashboard
  (`apps/spc`), each migrated with full original commit history preserved.
- **`quality_core`** shared package — schema, IO, and a unified theme (amber/violet palette +
  RPN risk-tier tokens) consumed by both apps.
- **Unified shell** (`app.py`) — a single `st.navigation` surface mounting a landing page, FMEA,
  and the three SPC workflows (Control Charts, Process Capability, Live Simulation). One
  `set_page_config` + theme, mounted render callables.
- **Unified tooling** — one `ruff.toml`, one `mypy.ini`, and a workspace pytest config covering
  `quality-core` + both apps with combined coverage.
- **CI** (`.github/workflows/ci.yml`) — `uv sync → ruff → mypy → pytest` on every push and PR to
  `main`, Python 3.11 via `astral-sh/setup-uv`.
- **`requirements.txt`** exported from `uv.lock` (third-party, pinned) as the Streamlit Cloud
  deploy fallback; the shell resolves all first-party code from the repo via `sys.path`.

### Notes

- FMEA: 105 tests, ruff + mypy clean. SPC: 83 tests (ruff/mypy lint cleanup scheduled for W02).
- uv is the toolchain; the workspace runs on Python 3.11.

[0.3.0]: https://github.com/Siddardth7/quality-platform/releases/tag/v0.3.0
[0.2.0]: https://github.com/Siddardth7/quality-platform/releases/tag/v0.2.0
[0.1.0]: https://github.com/Siddardth7/quality-platform/releases/tag/v0.1.0
