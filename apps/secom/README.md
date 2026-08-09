# SECOM — Semiconductor Manufacturing Dataset

**SECOM is engine-only (#206).** It is a tested analysis *library* over the SECOM
dataset — consumed by its own suite and, from P3 onward, by the platform API — and
is deliberately **not** mounted in the unified Streamlit shell: there is no `app.py`
here and no `st.navigation` entry, unlike FMEA, SPC, Control Plan, and MSA. It is a
full workspace member (`pyproject.toml`) sharing `quality_core`. All SPC chart and
capability math comes from `quality_core.spc` (#205) — this app imports no other app.

SECOM (UCI ML Repository, dataset 179) is real semiconductor fab process data:
1567 production runs x 590 sensor readings, with a pass/fail label and a
timestamp per run. Unlike the platform's other CSV uploads, SECOM's defining
trait is heavy, honest missingness across its sensor columns — so it is not
routed through `quality_core.io.load_table`'s per-row Pydantic validation
(which rejects a row with a missing required float). Instead:

- **`secom_app/ingest.py`** — `load_secom()` reads the two vendored raw files
  (`data/secom.data`, `data/secom_labels.data`) into an aligned, NaN-preserving
  `SecomDataset`. It validates *structure* (matching row counts, in-domain
  labels), never cell presence, and raises `quality_core.io.IngestError` (a
  user-safe `ValueError`) on a structural problem. `secom_missingness()`
  reports per-signal present/missing counts.
- **`secom_app/selection.py`** — `select_signals()` screens the 590 sensor
  columns for SPC/capability suitability: drops signals with too few present
  values (`MIN_NON_MISSING = 100`, AIAG SPC capability sample-size guidance),
  drops zero-variance columns (Cp/Cpk is undefined at sigma=0), and drops
  near-zero-variance columns (`caret::nearZeroVar` defaults — a third-party
  heuristic, not a quality standard). Returns a full audit table so every
  inclusion/exclusion is explainable.

**Out of scope for this issue:** no UI page, no spec limits (USL/LSL), no
Cp/Cpk computation. SECOM ships no tolerances; W09-1 selects *candidate*
signals only. See `docs/ASSUMPTIONS_LOG.md` for the full rationale and
standard-vs-heuristic labelling of every screening rule.

- **`secom_app/charts.py`** (W09-2, #66) — `control_chart_for_signal()` /
  `control_charts_for_selection()` run every `select_signals()`-kept signal
  through the shared SPC I-MR engine (`quality_core.spc.control_charts`, reused
  read-only). The AIAG limit formula is not reimplemented here: SECOM feeds its
  own gap-aware pooled `mrbar` into `imr_limits()`, the single place that formula
  is written (#205 PR 2). Handles SECOM's
  honest missingness by splitting each signal into gap-free runs before any
  moving-range math (a moving range never spans a missing cell), and attaches
  a per-signal lag-1 autocorrelation diagnostic flag (never a filter/gate).
  Still no spec limits / no Cp/Cpk — see `docs/ASSUMPTIONS_LOG.md`.

- **`secom_app/capability.py`** (W09-3, #67) — Cp/Cpk/Pp/Ppk against
  caller-supplied limits, stability-gated: `capability_for_signal()` reuses
  `quality_core.spc.capability`'s `compute_capability` (never re-derives Cp/Cpk math) fed
  the W09-2 control chart's present values and within-process σ̂; still
  computes indices on an unstable process but flags `stable=False` with a
  `stability_warning` rather than fabricating a limit or hard-suppressing.

- **`secom_app/msa.py`** (W09-4, #68) — SECOM has no `part`/`appraiser`/
  `trial` structure and none can be legitimately constructed, so this module
  refuses rather than fabricates: `gage_rr_applicability()` /
  `assert_gage_rr_applicable()` return/raise a standards-anchored verdict
  pointing at `docs/MSA_APPLICABILITY.md`. No Gage R&R math is added; a real
  study runs through the existing `apps/msa` app (`compute_gage_rr`).

- **`secom_app/yield_dppm.py`** (W09-5, #69) — `yield_summary()` computes
  wafer-level yield and DPPM (defective **units** per million — explicitly
  not DPMO, which SECOM's single pass/fail-per-wafer label cannot support).
  `failing_signal_pareto()` reuses the *existing* W09-2 SPC violation
  detection (`control_charts_for_selection`, no anomaly rule re-derived) to
  rank kept signals by how many special-cause violation events land on
  failed wafers — an association/screening Pareto, not a root-cause claim.
  Engine-only: the thin Streamlit view that shipped with W09-5 was deleted by
  #206 (see the engine-only note at the top).

- **`secom_app/doe_screening.py`** (W11-1, #72) — `screen_signals()` runs an
  observational univariate effect screen (Welch's t + Cohen's d, BH-FDR
  significance, all reused via `scipy.stats` — no hand-rolled statistics) of
  pass/fail on `select_signals()`-kept signals; explicitly labelled a
  screening ANALYSIS of association, not a designed experiment (SECOM's
  factor levels are never set or randomized). Engine-only, no page.

**Data provenance:** the two raw UCI files are vendored unchanged under
`data/`; see `data/LICENSE_SECOM.txt` for citation and license (CC BY 4.0).

**Case study:** see `docs/CASE_STUDY.md` for a short, honest write-up of what
the series above shows and its limitations.
