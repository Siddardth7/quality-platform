# Quality Database — corpus ingestion + retrieval (M4-2 #283, M4-3 #284)

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

## Retrieval (M4-3, #284)

The corpus is then chunked, embedded and indexed for retrieval:

- **`quality_database_app/chunk.py`** — `chunk_corpus()`. The default chunk is **one
  record as-is** (`segment.py` already split on headings); a record longer than
  `MAX_CHARS` splits on paragraph boundaries first, and only a single over-long
  paragraph falls back to a hard window with `OVERLAP_CHARS`. Both constants are tunable
  (ASSUMPTIONS_LOG RULE 9). Every chunk carries its record's `standard` / `clause` /
  `page` / `serving_flag` / `license_class` verbatim, so a hit is always citable.
- **`quality_database_app/embed.py`** — the `Embedder` protocol and `FakeEmbedder`, a
  deterministic offline embedder (sha256-derived unit vectors). **This is the only
  embedder CI runs**: hash vectors carry no semantic similarity, so the tests assert the
  plumbing, not retrieval quality (that is M4-4's eval harness).
- **`quality_database_app/store.py`** — `VectorStore`: `vectors.npy` + `metadata.json`,
  brute-force cosine scan, no server and no new dependency. `search()` filters on
  `standard` / `source_id` / `region` and **excludes `never-ship` chunks by default**
  (`exclude_never_ship=False` to include them) — the flag stays in the data, the query
  layer is safe by default.
- **`quality_database_app/index.py`** — `run(embedder)`: corpus file -> chunks ->
  vectors -> a saved index under `.corpus_out/index/`. There is deliberately no default
  embedder; the caller passes one.

### Real embedding is a hand-run

`fastembed` is an **optional** dependency (`[project.optional-dependencies] embed`),
never installed on CI, and `embed_fastembed.py` is excluded from the coverage gate — it
needs that extra and downloads a model on first use. A real end-to-end index:

```bash
uv sync --extra embed
uv run python -c "
from quality_database_app.embed_fastembed import FastEmbedEmbedder
from quality_database_app.index import run
print(len(run(FastEmbedEmbedder()).chunks))
"
```

The output lands in `apps/quality_database/.corpus_out/index/`, gitignored with the rest
of `.corpus_out/`.

## Scope of #283

`md` sources only — the two licensed `.md` conversions the ledger names, plus this
project's own `.md` derivations. Every `pdf` row was **skipped and logged** (lifted by
#329, below). #283 added **zero new dependencies**; #284 adds only `numpy`, already a
direct dependency of `quality-core`.

## PDF extraction (#329)

`pdf` rows are now ingested too, via **`pypdf`** — this app's first genuinely new runtime
dependency (pure Python, no transitive requirements, BSD). Extraction is **text-layer
only**: one record per page that has text, with pypdf's real 1-indexed page number and
`clause=None` (raw PDF text carries no heading structure to segment on).

Of the ledger's 20 `format=pdf` rows, **15 have a text layer and are extracted**. The
five image-only scans — `aiag-apqp-2nd`, `iatf-16949-2016`, `iso-9001-2015`,
`western-electric-1956`, `montgomery-isqc-8` — extract to nothing and are **skipped with
a WARNING** naming issue **#335**, where OCR (which needs the system `tesseract` binary,
not a `pip` install) is being decided. They are not silently dropped.

Extraction does **not** re-grade a source: those 15 rows keep `extraction_quality:
not-extracted` in the ledger, so every record they produce is `low_confidence: true`
until the SME reviews the text and edits the ledger by hand (RULE 1, RULE 13). A
`never-ship` PDF row is extracted and flagged like any other, never skipped (RULE 11).

## Output is never committed

`run()` writes to `apps/quality_database/.corpus_out/corpus.json`, which is
`.gitignore`d. The corpus is private; only our derivations are public
(`docs/CORPUS_LEDGER.md`), and committed storage for the ingested corpus is M4-5
(#286). Do not commit anything under `.corpus_out/`.

```bash
uv run python -c "from quality_database_app.pipeline import run; print(len(run().records))"
uv run pytest apps/quality_database -q
```
