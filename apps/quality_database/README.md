# Quality Database — corpus ingestion + cleaning (M4-2, #283)

**Engine-only (like `apps/secom`, #206).** A tested library with no `app.py`, no
`st.navigation` entry, and no Streamlit dependency at all — this app is pure text
processing. It is a full workspace member sharing `quality_core` (only
`quality_core.schema.StrictModel`); it imports no other app.

It turns M4-1's corpus ledger into the clean intermediate corpus M4-3 embeds:

- **`quality_database_app/ledger.py`** — reads `docs/CORPUS_LEDGER.tsv` (#282), the
  input contract. `skip_reason()` names why a row is out of scope; `ingestible_rows()`
  keeps the rest. `$CORPUS_ROOT` (default `/Users/sid/Documents/Upskill/SixSigma`)
  re-roots the ledger's absolute paths, exactly as `tests/test_corpus_ledger.py` does.
- **`quality_database_app/segment.py`** — Markdown heading-boundary segmentation with
  per-`source_id` page-marker patterns (the FMEA handbook's `- N -` footer, the MSA
  manual's bare-digit line). Cleaning is format-only and never content-repairing, so
  OCR damage survives verbatim instead of being silently "fixed".
- **`quality_database_app/schema.py`** — `CorpusRecord` (standard / clause / page +
  confidence, with the ledger's `serving_flag`, `license_class` and
  `extraction_quality` carried through) inside an envelope, on `StrictModel`.
- **`quality_database_app/pipeline.py`** — `run()` ties it together and writes the
  corpus. A re-run over unchanged inputs is byte-identical.

## Scope of #283

`md` sources only — the two licensed `.md` conversions the ledger names, plus this
project's own `.md` derivations. Every `pdf` row is **skipped and logged**; PDF text
extraction (and the dependency decision it implies) is follow-up issue **#329**. This
app adds **zero new dependencies**.

## Output is never committed

`run()` writes to `apps/quality_database/.corpus_out/corpus.json`, which is
`.gitignore`d. The corpus is private; only our derivations are public
(`docs/CORPUS_LEDGER.md`), and committed storage for the ingested corpus is M4-5
(#286). Do not commit anything under `.corpus_out/`.

```bash
uv run python -c "from quality_database_app.pipeline import run; print(len(run().records))"
uv run pytest apps/quality_database -q
```
