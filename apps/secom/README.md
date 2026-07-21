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

**Data provenance:** the two raw UCI files are vendored unchanged under
`data/`; see `data/LICENSE_SECOM.txt` for citation and license (CC BY 4.0).
