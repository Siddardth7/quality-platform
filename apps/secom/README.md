# SECOM — Semiconductor Manufacturing Dataset

Scaffold for the SECOM app. It mounts into the unified Quality Platform shell
alongside FMEA, SPC, MSA, and Control Plan, sharing `quality_core`.

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
  through the *existing* SPC I-MR engine (`apps/spc/spc_app/spc_engine/`,
  reused read-only, no reimplemented control-limit math). Handles SECOM's
  honest missingness by splitting each signal into gap-free runs before any
  moving-range math (a moving range never spans a missing cell), and attaches
  a per-signal lag-1 autocorrelation diagnostic flag (never a filter/gate).
  Still no spec limits / no Cp/Cpk — see `docs/ASSUMPTIONS_LOG.md`.

- **`secom_app/capability.py`** (W09-3, #67) — Cp/Cpk/Pp/Ppk against
  caller-supplied limits, stability-gated: `capability_for_signal()` reuses
  the existing SPC `compute_capability` (never re-derives Cp/Cpk math) fed
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
  `secom_app/pages/yield_dppm.py` (`render_yield_dppm()`) is a thin,
  non-gated Streamlit view of this engine's output, mirroring
  `msa_app/pages/gage_study.py`.

**Data provenance:** the two raw UCI files are vendored unchanged under
`data/`; see `data/LICENSE_SECOM.txt` for citation and license (CC BY 4.0).

**Case study:** see `docs/CASE_STUDY.md` for a short, honest write-up of what
the series above shows and its limitations.
