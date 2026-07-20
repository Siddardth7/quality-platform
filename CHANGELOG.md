# Changelog

All notable changes to the Quality Platform are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to adhere to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **MSA tests + CI coverage gate (W08-4, #57).** New engine reference test asserts
  `compute_gage_rr` against the AIAG MSA 4th-ed "study case 1" published
  EV/AV/%GRR/ndc/verdict, loaded from a new fixture
  `apps/msa/data/aiag_reference_study.csv` (raw 10x3x3 canonical study). New
  "MSA coverage gate" CI step enforces `--cov-fail-under=100` on
  `msa_app.gage_rr_engine` + `msa_app.schema` + `msa_app.exporter`, mirroring
  the SPC and Control Plan gates.
- **MSA app UI — study entry, results, verdict + export (W08-3, #56).** The Gage
  R&R page now shows a loop-link note (Control Plan → MSA → SPC) and a
  plain-English verdict interpretation sentence, and exports the study/results
  as CSV/Excel/PDF via `quality_core.io`. New `apps/msa/msa_app/exporter.py`
  (`GageStudyReport`, `export_csv`, `export_results_csv`, `export_excel`,
  `export_pdf`, `verdict_sentence`) mirrors the SPC/Control Plan exporter
  pattern; two CSV downloads are offered (the validated study frame, and a flat
  results table). New standalone `apps/msa/app.py`; the platform shell landing
  page (`shell/home.py`) now lists an MSA feature card.

## [0.7.0] - 2026-07-18

Week 07 — Close the loop. Completes the AIAG improvement loop end to end: a Control Plan
characteristic auto-configures the SPC view (spec/tolerance, sample size/frequency,
recommended chart type) with no manual re-entry (#88); an out-of-control SPC signal emits
candidate occurrence-rating / CAPA feedback back to the source FMEA cause — human-in-the-loop,
never auto-committed, anchored to the AIAG FMEA-4 / SAE J1739 occurrence table (#89); and a
dedicated cross-app integration test proves the full FMEA → Control Plan → SPC → FMEA walk on
real sample data, with the SPC coverage floor ratcheted to 100% line+branch (#90). Milestone
issues #88, #89, #90, #91 closed; all coverage bars green on `dev`.

### Added

- **SPC — Control Plan → Control Charts config (W07-1, #88).** The Control
  Charts page now reads a loaded Control Plan from session state and offers a
  "Characteristic (from Control Plan)" selector; picking one preselects the
  chart type from `recommended_chart` (falling back to the manual selectbox
  when it's `None`/invalid) and shows an info panel with LSL/USL/target,
  sample size, and frequency. New pure module
  `apps/spc/spc_app/control_plan_config.py` (`plan_characteristics`,
  `config_for`, `chart_type_index`) does the derivation — no new SPC math, no
  visualizer changes, no `controlplan_app` import from `spc_app` (the
  standalone SPC app still imports cleanly). Added to the SPC coverage gate in
  CI and `apps/spc/CLAUDE.md`.

- **SPC → FMEA candidate occurrence feedback + loop close (W07-2, #89).** An
  out-of-control signal on a Control Plan characteristic's chart now emits a
  **candidate** occurrence-rating / CAPA payload toward the source FMEA
  cause — never auto-committed. New pure module `apps/spc/spc_app/
  fmea_feedback.py` (`summarize_violations`, `build_occurrence_feedback`)
  maps the chart's OOC failing-rate onto the AIAG FMEA-4 (2008) / SAE J1739
  occurrence rate table (cited in-module; AIAG-VDA 2019 defines no numeric
  occurrence table, so the rate mapping is anchored to the legacy AIAG-4/J1739
  standard — see `docs/ASSUMPTIONS_LOG.md` Rule 10). `ControlPlanRow` gained a
  nullable `source_cause_id` join key (`controlplan_app/schema.py`),
  populated by a refactored `connector.build_control_plan` /
  new `connector.source_index`, so the SPC↔FMEA linkage survives Control
  Plan CSV export/reimport. A new per-characteristic demo SPC stream
  (`ply_misalignment`) binds a real, out-of-control monitored parameter to
  the composite-panel FMEA demo's highest-risk characteristic. The FMEA page
  renders a read-only candidate panel (no `spc_app` import). Closes the full
  FMEA → Control Plan → SPC → FMEA walk in the unified shell. Added
  `spc_app.fmea_feedback` to the SPC coverage gate (CI + `apps/spc/CLAUDE.md`).

### Tests

- **Dedicated Week-7 loop integration test (W07-4, #90).** New
  `apps/spc/tests/test_loop_integration.py` walks the composite-panel FMEA
  demo through the full Control Plan → SPC → FMEA chain on real sample data
  (no stubbed boundaries) and asserts the join-key round-trips end to end —
  the candidate feedback's `source_cause_id` matches the originating Control
  Plan row's and names the correct FMEA cause — and that the human-in-the-loop
  invariant holds (`current_occurrence` echoes unchanged, `suggested_occurrence`
  is a distinct candidate, nothing mutates the FMEA source mapping). Guarded
  with `pytest.importorskip` so it runs under the full root `uv run pytest`
  and skips cleanly under the isolated SPC gate. SPC coverage floor ratcheted
  95% → 100% (`.github/workflows/ci.yml`, `apps/spc/CLAUDE.md`) — all gated
  SPC modules already sit at 100% line+branch, so the ratchet is earned and
  safe.

## [0.6.0] - 2026-07-18

Week 06 — Control Plan. Closes the FMEA → Control Plan half of the AIAG loop: a
connector engine that turns relational FMEA failure modes into typed Control Plan
rows (with the AIAG SPC chart-selection rule table and AP/RPN prioritization), a
Streamlit authoring UI (ingest → review/edit → injection-safe CSV/Excel/PDF
export), and the enforcement to keep it honest — a 100% line+branch coverage gate
on the connector + schema, plus the Control Plan app added to the mypy gate.
Milestone issues #83, #84, #85, #86, #95 closed; all coverage bars green on `dev`.

### Added

- **CI — Control Plan coverage gate (W06-4, #86).** New `Control Plan coverage gate`
  step in `.github/workflows/ci.yml`, mirroring the SPC gate pattern, holds
  `controlplan_app.connector` + `controlplan_app.schema` (the FMEA→Control Plan
  engine and validated ingest schema) at 100% line+branch coverage. Scope excludes
  `controlplan_app.exporter` (W06-3), which is out of scope for #86. No test or
  source files changed — `test_connector.py` + `test_schema.py` already meet the
  floor.

- **`apps/controlplan` — Control Plan app UI (W06-3, #85).** The Control Plan page
  now runs the full FMEA → Control Plan flow: upload a flat FMEA CSV (or click
  "Load demo FMEA") through the shared `quality_core.io.load_table` boundary,
  adapt it with `flat_to_relational`, and derive a draft plan via
  `controlplan_app.connector.build_control_plan`. The generated rows are shown in
  an editable `st.data_editor` (add/delete rows, a `recommended_chart`
  selectbox); edits are re-validated through the existing
  `ControlPlanRow`/`ControlPlanDataset` models before export — the trust
  boundary is never skipped. New `controlplan_app/exporter.py` composes the
  shared `quality_core.io.export` primitives (mirrors `fmea_app/exporter.py`,
  minus matplotlib/chart pages — a Control Plan is a table) for CSV/Excel/PDF
  download buttons. The FMEA demo and input template CSVs are copied
  locally into `apps/controlplan/data/` (SME-resolved: self-contained app, no
  cross-app path coupling). Adds `openpyxl`/`fpdf2` to the app's dependencies.

- **`apps/controlplan` — FMEA → Control Plan connector engine (W06-2, #84).** New
  `controlplan_app.connector` maps a relational FMEA
  (`quality_core.schema.relational.RelationalFMEA`) into the #83 typed
  `ControlPlanDataset` output contract: `build_control_plan(fmea)` emits one row per
  `FailureMode` (worst-link S/O/D via `quality_core.scoring.rpn`/`action_priority`),
  sorted highest-risk first (AP then RPN, mirroring `fmea_app.ap_engine.rank_by_ap`);
  `characteristic` is derived from the owning `Function`'s component + the failure
  mode (collision-safe); `measurement_method` comes from the worst link's Current
  Process Control. Fields the relational FMEA has no source for
  (`sample_size`, `frequency`, `reaction_plan`, `recommended_chart`) are documented
  placeholder defaults (`# ponytail:`-marked) the W06-3 authoring UI will make
  editable. Also ships the standalone, fully-cited `recommend_chart(...)` AIAG
  SPC chart-selection rule table (variable: I-MR/Xbar-R/Xbar-S by subgroup size;
  attribute: p/c/u by defect-vs-defective and constant-vs-variable sample) as the
  standards core for later enrichment. New
  `apps/controlplan/docs/ASSUMPTIONS_LOG.md` records the citation and flags the
  Xbar-R↔Xbar-S subgroup-size boundary (n≥10→S) for primary-source confirmation.
  Engine + typed output only — no UI (W06-3, #85) and no CP→SPC→FMEA loop (Week 7).

- **`apps/msa` — Measurement System Analysis scaffold.** A new `msa_app` package mounts into the
  unified shell under an "MSA" nav group (Gage R&R page), following the SPC app pattern. It ships an
  app-local typed gage-study schema (`GageStudyRow` / `GageStudyDataset`) and validated CSV ingest via
  `quality_core.io.load_table`: rows carry `part, appraiser, trial, measurement`; ingest checks row
  types and `(part, appraiser, trial)` uniqueness. Study-level tolerance (USL/LSL) is captured as page
  inputs, not a CSV column. Includes a `gage_rr_template.csv` input template + download button. The
  Gage R&R computation (%GRR, ndc, AIAG verdict) lands in a later issue (#54).
- **`apps/controlplan`** — Control Plan app scaffold: shell-mounted (`app.py`,
  "Control Plan" nav group), version SSOT, and conftest, following the `apps/msa`
  pattern. Adds an app-local typed Control Plan row/dataset schema
  (`controlplan_app.schema`) on the shared `quality_core.io` validated-ingest
  boundary — characteristic, spec/tolerance (LSL/target/USL), measurement method,
  sample size/frequency, a nullable recommended SPC chart, and reaction plan, with
  a USL>LSL check, a target-within-`[lsl, usl]` check, and duplicate-characteristic
  dataset rejection. Scaffold + schema only — FMEA→Control Plan mapping (W06-2) and
  the authoring UI (W06-3) land later (#83).

### Changed

- **Ship-pipeline model routing** — split the four subagents by stage instead of all-Opus: the
  reasoning gates stay on Opus 4.8 (`research` = spec-in, `reviewer` = quality-out), while the
  spec-constrained middle stages move to Sonnet 5 (`coder`, `tester`). Keeps Opus judgment exactly
  where a mistake is expensive to unwind and cuts per-run model cost ~43% (coder+tester are ~54% of
  pipeline tokens, Sonnet ≈ 1/5 the per-token cost). Config-only change to `.claude/agents/*.md`.

### Fixed

- **mypy gate now covers `apps/controlplan` (W06-5, #95).** Added
  `apps/controlplan/controlplan_app,` to `mypy.ini`'s `files=` list, closing the gap
  where the app's typed library package was silently skipped by CI's bare
  `uv run mypy`. Adding the app surfaced a real (pre-existing) error at
  `control_plan.py:55` — a `**dict` unpack into `FMEARow` — fixed with the same
  `cast("dict[str, Any]", ...)` pattern already used in `fmea_app/rpn_engine.py`
  (type-only change, no runtime behavior difference). `uv run mypy` is green.

## [0.5.0] - 2026-07-10

Week 05: **relational domain model + cross-tool schema contracts.** The FMEA schema moves into the
shared core and gains an AIAG/VDA relational model (Function → Failure Mode → Effect/Cause/Control)
with loss-less flat adapters, action tracking + effectiveness, and end-to-end relational scoring/
exports. The engineering system was written down (Definition of Done, playbook, PR workflow) and
branch coverage turned on across every gate.

### Added

- **`quality_core.schema`** — the FMEA row/dataset contracts (`FMEARow`, `FMEADataset`), promoted out
  of the FMEA app so every tool shares one schema; re-exported from `fmea_app.schema` (zero-behaviour
  change), held at 100% by its own tests + a CI gate (W05-1, #34).
- **`quality_core.schema.relational`** — the AIAG/VDA relational model **Function → FailureMode →
  Effect / Cause / Control** (Severity on the Effect, Occurrence on the Cause, Detection on the
  Control), with loss-less `flat_to_relational` / `relational_to_flat` adapters. The model enforces
  the canonical invariants (unique IDs; no two entities share a `(description, rating)` pair; every
  entity referenced by ≥1 link) so the flat↔relational round-trip is loss-less both directions
  (W05-2, #35).
- **Shared schema base** — `quality_core.schema._base` (`StrictModel`, `find_duplicates`); the flat
  and relational models reuse one blank-rejection validator and one duplicate finder instead of
  hand-copying (#35).
- **Engineering system docs** — `docs/DEFINITION_OF_DONE.md`, `docs/ENGINEERING_SYSTEM_PLAYBOOK.md`,
  `docs/README.md`, `CONTRIBUTING.md`, and the project `ROADMAP.md`, codifying the issue → gates → PR
  → release loop (#41).
- **`quality_core.scoring`** — the shared scalar risk scorers `rpn(s,o,d)` and `action_priority(s,o,d)`
  (the AIAG-VDA 2019 Action Priority table), promoted out of the FMEA app so `quality_core` can score
  without importing an app; held at 100% by its own tests + a CI gate. `fmea_app.ap_engine` now
  re-exports the scalar API and keeps its pandas `calculate_ap` / `rank_by_ap` layers — zero-behaviour
  change (W05-3a, #44).
- **`quality_core.schema.action`** — FMEA action tracking + effectiveness (the AIAG "optimization"
  loop): `Action` (owner, `due` date, `ActionStatus` enum, optional re-rated `s_after`/`o_after`/
  `d_after`) and `Action.effectiveness(severity, occurrence, detection)` → an `Effectiveness` value
  reporting RPN and Action Priority **before → after**, the RPN delta, and whether AP dropped a band.
  Unset `*_after` fall back to the original; the original assessment is never mutated (W05-3, #36).
- **Relational FMEA engine entrypoint** — `fmea_app.rpn_engine.run_pipeline_relational(model)` (and
  `relational_to_dataframe`) run the W05-2 relational model through the exact same
  validate → score → rank pipeline as the flat path, so structured input scores and exports
  identically. Proven by content-level export equivalence (CSV bytes, Excel data-sheet grid, and
  PDF with timestamps stripped) against the flat-equivalent (W05-4, #37).
- **Action-tracking columns in FMEA exports** — a `FailureLink` can now carry an optional `Action`;
  when present, `relational_to_dataframe` appends action columns (owner, status, due, S/O/D after,
  revised RPN/AP, RPN delta via `Action.effectiveness`, blank for rows without an action). Excel and
  CSV render the extra columns; the PDF gains an **"Action Tracking"** page. All formula-injection-safe;
  action-free models export identically to the flat path (W05-4b, #47).
- **Relational + action-tracking UI (FMEA app)** — a **Relational** tab shows the
  Function → Failure Mode → Effect/Cause/Control hierarchy (auto-built from any upload via the W05-2
  adapter), and an **Actions** tab provides a per-failure action editor (owner, status, due, re-rated
  S'/O'/D') that reports before→after RPN/AP + the RPN delta and offers an action-aware Excel/PDF/CSV
  download. Flat CSV/Excel uploads are unchanged and auto-convert to the relational view (W05-5, #38).

### Changed

- **Branch coverage is on** — `branch = true` + `show_missing = true` in `pyproject.toml`; every
  per-surface gate (io/schema 100%, SPC ≥95%) now measures line **and** branch. Baseline recorded in
  `docs/COVERAGE_BASELINE_2026-07-09.md` (#41).
- **`quality_core.schema` locked at 100%** — the relational + action model is held at the 100%
  line+branch CI gate (established W05-1), with a consolidated guardrail-contract test asserting every
  malformed relational payload surfaces a clear, entity/row-addressed error (W05-6, #39).
- **Workflow** — adopt PR-per-issue + squash-merge with CI-green-required, going forward (#41).

### Fixed

- **`quality_core.io` `_format_row_error`** — removed a dead defensive branch (`"input" in first`;
  Pydantic's default `errors()` always carries `input`) and made the value echo crash-safe via
  `.get`; io is now 100% line + branch (#41).

## [0.4.0] - 2026-06-24

Week 04: Shared validation + export. The reuse story is now demonstrable — a single
`quality_core/io` library owns CSV/Excel/PDF export and validated CSV/Excel ingest, and **both**
FMEA and SPC consume it. SPC gained downloadable reports and validated uploads; FMEA was pointed
at the shared library with zero behaviour change (exports byte-identical).

🔗 Live: <https://quality-platform-nplyhc6rvsd3bfw6q9vvkd.streamlit.app/>

### Added

- **`quality_core/io` export primitives** — app-agnostic CSV/Excel (openpyxl)/PDF (fpdf2) building
  blocks: formula-injection escaping (`sanitize_for_export`, scalar `sanitize_cell`), styled table
  and key/value sheets, and PDF chrome (`render_table`, `add_image_page`, `pdf_title`,
  `pdf_subheader`, `pdf_summary_cells`).
- **`quality_core/io` validated-ingest boundary** (`validate.py`) — `read_table` (CSV/Excel read +
  size guard), pluggable `TableSchema` (per-tool Pydantic model), and `load_table`, all surfacing a
  user-safe `IngestError` (a `ValueError`) with row-addressed messages instead of stack traces.
- **SPC report export** — downloadable Excel + PDF for control-chart (per-point values, the UCL/LCL
  each point was tested against, rule violations) and capability (Cp/Cpk/Pp/Ppk, distribution,
  normality, stability) reports; injection-safe.
- **SPC validated uploads** — control-chart and capability uploads run through `load_table` with an
  SPC schema (`spc_app/schema.py`), so a malformed CSV gives a friendly error.

### Changed

- **FMEA points at the shared `quality_core/io`** — its hand-rolled PDF chrome and upload/CLI read
  now compose the core helpers. Verified content-identical (xlsx/pdf/csv); FMEA's domain-specific
  validation messages are intentionally preserved.
- **One shared IO implementation across both tools** — "write export and validation once, consume
  twice" is now real, replacing per-app copies.

### Tested

- **`quality_core.io` at 100% coverage** from its own tests (injection + validation paths), locked
  by a CI gate; the SPC testable surface (now including the report exporter and upload schema) stays
  gated at ≥95%.

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
