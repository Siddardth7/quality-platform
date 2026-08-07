# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the
MSA app inside the Quality Platform monorepo.

## Project orientation

The MSA app implements **crossed Gage R&R** by the AIAG Average-and-Range method. It is one
of five apps in the `quality-platform` uv workspace, all sharing `packages/quality-core`.
It has no standalone `pages/` entry scripts of its own beyond `app.py`; the shell mounts
`render_gage_study` as the "Gage R&R" page.

Read the **root `CLAUDE.md`** first — workspace layout, CI gate, branch ladder, and the
hard-won rules live there. Then, before changing domain logic:

- **`docs/ASSUMPTIONS_LOG.md`** — 15 numbered RULES, each an AIAG formula, constant,
  threshold, or a declared deviation, with its citation. Do not change a value without
  updating its rule.
- **`docs/CITATIONS.tsv`** — the machine-checkable quotation manifest (see below).

## Commands

All commands run from the **workspace root** via `uv`.

```bash
uv sync --frozen
uv run streamlit run apps/msa/app.py     # standalone
uv run streamlit run app.py              # unified shell -> "Gage R&R"
```

### Gate (must be green before merging)

```bash
uv run ruff check .
uv run mypy
uv run pytest --cov

# MSA coverage gate (CI enforces 100% line+branch on the testable surface):
uv run pytest apps/msa \
  --cov=msa_app.gage_rr_engine --cov=msa_app.schema --cov=msa_app.exporter \
  --cov-report=term-missing --cov-fail-under=100
```

`pages/` and `app.py` are excluded — they need a Streamlit runtime, mirroring the SPC gate.

### Single test

```bash
uv run pytest apps/msa/tests/test_gage_rr_engine.py -q   # AIAG math
uv run pytest apps/msa/tests/test_citations.py -q        # quotation manifest
uv run pytest apps/msa -k "ndc" -q                       # by keyword
```

## Architecture (big picture)

Thin Streamlit page → validated ingest → pure engine → export layer. The engine never
touches Streamlit.

```
app.py                        standalone Streamlit entry
        │
        ▼
msa_app/pages/gage_study.py   render_gage_study — upload, tolerance entry, results
                              Tolerance dataclass; load_uploaded_study; TEMPLATE_PATH
        │
        ▼
msa_app/schema.py             GageStudyRow / GageStudyDataset (Pydantic v2),
                              GAGE_STUDY_SCHEMA (TableSchema), load_gage_study_csv.
                              Long/tidy form: one row per measurement —
                              part x appraiser x trial. Routes through the shared
                              quality_core.io validated-ingest boundary.
        │
        ▼
msa_app/gage_rr_engine.py     compute_gage_rr — the whole AIAG computation:
                              EV (repeatability), AV (reproducibility), GRR, PV, TV,
                              %EV/%AV/%GRR/%PV each vs study variation and vs
                              tolerance (#225), ndc, verdict. Average-and-Range by
                              default; method="anova" adds the part x appraiser
                              interaction (#195).
        │
        ▼
msa_app/exporter.py           GageStudyReport + export_csv / export_results_csv /
                              export_excel / export_pdf — one study rendered four ways,
                              composed over quality_core.io.export primitives.
                              verdict_sentence renders the verdict prose.
```

## Conventions that matter here

- **Two methods, Average-and-Range by default.** `compute_gage_rr(..., method=...)` selects
  between `METHOD = "average_and_range"` (the default — do **not** flip it; SME decision) and
  `METHOD_ANOVA = "anova"` (#195, `_anova_method`, RULE 17). Whichever ran is declared in the
  payload as `method` / `method_note` (`METHOD_NOTE` / `METHOD_NOTE_ANOVA`), not hidden —
  Average-and-Range's note states that it does **not** estimate the part x appraiser
  interaction. ANOVA adds `interaction` / `interaction_f` / `interaction_significant`, which
  are `None` under Average-and-Range; its `grr` is `sqrt(EV² + AV² + INT²)`, not `sqrt(EV² +
  AV²)`. The interaction F-test uses α = 0.05 (`_ANOVA_ALPHA`) — the level in AIAG's own
  worked example, **not** an AIAG requirement; a non-significant interaction is pooled into
  repeatability per the manual's procedure. Do not add an `alpha=` parameter (SME decision).
- **Study variation is 6σ** (`_STUDY_VARIATION_SIGMA = 6.0`), per RULE 7. The AIAG 4th Ed.
  form uses 6 sigma; earlier editions used 5.15. Do not "fix" this to 5.15.
- **The verdict mixes AIAG and platform logic, and says so.** The %GRR bands (<10% accept,
  10–30% marginal, >30% reject) are AIAG's; the **ndc sub-bands are not** — `ndc >= 5` is
  AIAG's threshold, but combining it with the %GRR bands into a single Accept/Marginal/
  Reject call is this platform's composition (RULE 10). Keep that distinction in any text
  you write.
- **Declared deviations are deliberate.** ndc is clamped to `[0, 100]`; the minimum study
  size is a deliberate relaxation of AIAG's recommendation (RULE 12); balanced data is an
  inference from AIAG's procedure, **not** an AIAG statement (RULE 11). Each is documented
  as a deviation — do not present any of them as an AIAG requirement.
- **Edge cases are specified, not accidental:** all-identical measurements (TV = 0, RULE 13)
  and negative AV² (RULE 14) have defined behaviour with tests. Don't "simplify" them away.
- **Citation integrity is CI-enforced.** `docs/CITATIONS.tsv` is the manifest of verbatim
  AIAG quotations; `tests/test_citations.py` validates manifest shape and that every live
  blockquote in the docs is manifest-backed (audit A10-a, #223). Six fabricated quotations
  were withdrawn under that issue and are retained in fenced blocks explicitly labelled as
  fabricated — **do not "restore" them**.
- **The on-machine manual is the only valid source** for AIAG claims:
  `/Users/sid/Documents/Upskill/SixSigma/MSA_Reference_Manual_4th_Edition.md`. Never verify
  a quotation via web search. Match formatting-tolerantly — markdown emphasis and inline
  `<sup>` markup produce false "fabricated" verdicts.
- **Version SSOT** is `msa_app/__init__.py::__version__` (`0.7.0`), pinned by
  `tests/test_version.py` and consumed by the exporter as `_TOOL_VERSION`.

## Engineering references

- AIAG MSA Reference Manual, 4th Ed. — Ch. II Sec. D, Ch. III Sec. B, Appendix C
- `docs/ASSUMPTIONS_LOG.md` — 15 rules, every formula/constant/threshold with citation
- `docs/CITATIONS.tsv` — verbatim quotation manifest (CI-checked)
