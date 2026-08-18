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
`western-electric-1956`, `montgomery-isqc-8` — yield nothing usable from their text layer
and are **skipped with a WARNING** unless an OCR backend is supplied (#335, below). They
are not silently dropped.

Extraction does **not** re-grade a source: those 15 rows keep `extraction_quality:
not-extracted` in the ledger, so every record they produce is `low_confidence: true`
until the SME reviews the text and edits the ledger by hand (RULE 1, RULE 13). A
`never-ship` PDF row is extracted and flagged like any other, never skipped (RULE 11).

## OCR fallback (#335)

Two changes (RULE 15). First, a page now needs **30 words** to become a record, not just
one non-blank character: `western-electric-1956` and `montgomery-isqc-8` carry a thin junk
text layer (an SPC-software advert, a browser-extension prompt) that used to ingest as
three low-confidence records, while the handbook's real 1956 foreword page — ~120 words —
still passes. It is a heuristic with a stated ceiling, not content-aware junk detection.

Second, `extract()` and `pipeline.run()` take an `ocr` argument. The default is `NullOcr`
(recognizes nothing, so CI behaviour is unchanged and needs no system binary), and OCR is
consulted **only** for a page below the word threshold — a readable page is never
re-recognized. `TesseractOcr` (PyMuPDF rasterization + local `tesseract`) is the real
backend, behind the optional `ocr` extra and out of the coverage gate, exactly like
`FastEmbedEmbedder`. Everything runs locally; no page image leaves the machine.

```bash
brew install tesseract          # or: apt-get install tesseract-ocr — never on CI
uv sync --extra ocr
uv run python -c "
from quality_database_app.ocr_tesseract import TesseractOcr
from quality_database_app.pipeline import run
print(len(run(ocr=TesseractOcr()).records))
"
```

OCR text does **not** change a row's grading: `extraction_quality` stays `not-extracted`
(so records stay `low_confidence: true`) until the SME reads the output and edits the
ledger by hand (RULE 1).

## Output is never committed

`run()` writes to `apps/quality_database/.corpus_out/corpus.json`, which is
`.gitignore`d. The corpus is private; only our derivations are public
(`docs/CORPUS_LEDGER.md`). M4-5 (#286) settled storage there: the private store is this
gitignored `.corpus_out/` plus the on-machine `$CORPUS_ROOT` sources — nothing moved and
nothing is committed. `tests/test_no_corpus_content.py` enforces both halves (no tracked
artefact, no verbatim licensed text in any tracked file), and
`quality_database_app.storage.load_index()` is the one sanctioned read path into the
index — it fails closed if no index has been built. Do not commit anything under
`.corpus_out/`.

```bash
uv run python -c "from quality_database_app.pipeline import run; print(len(run().records))"
uv run pytest apps/quality_database -q
```
