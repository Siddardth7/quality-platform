# Engineering Assumptions Log
**Project:** Quality Database — Corpus Ingestion + Cleaning (M4-2, #283) and Chunking +
Embedding + Vector Store (M4-3, #284), Citation Eval (M4-4, #285), Private Storage +
Access Boundary (M4-5, #286)
**Last Updated:** August 16, 2026

**No AIAG/ISO constant, threshold, or quotation is introduced by this app.** It moves
text; it does not compute or restate a standard. Provenance and licensing for every
source live in `docs/CORPUS_LEDGER.md` / `.tsv` (M4-1, #282), which this pipeline reads
and carries through verbatim. The decisions below are text-processing design
assumptions only.

---

## RULE 1 — Confidence comes entirely from the ledger's `extraction_quality` (SME-locked)

**Decision:** `clean` -> `confidence: "high"`; `mangled` / `not-extracted` / `n/a` ->
`confidence: "low"` and the record is emitted with `low_confidence: true`. A
low-confidence record is **flagged, never silently dropped**.

**Source:** SME decision, 2026-08-15 (#283). The ledger is the SME-reviewed source of
truth for extraction quality — `mangled` on `fmea-vda-2019` /
`PFMEA-O-D-tables-and-AP-band-labels` is the manual #256 finding.

**Rationale:** A second, code-derived confidence heuristic could disagree with the
human classification, and there would be no principled tie-breaker. Dropping a bad
region instead of flagging it would hide the gap from every downstream consumer.

**Applied In:** `quality_database_app/schema.py` -> `confidence_for()`,
`CorpusRecord.check_confidence_flag_agrees`

---

## RULE 2 — Page markers are per-source, and a marker is a page **footer** (heuristic)

**Decision:** `PAGE_MARKERS` is a table keyed by `source_id`:
`fmea-vda-2019` -> `^-\s(\d+)\s-\s*$`, `msa-4th` -> `^(\d+)\s*$`. A marker line closes
the page whose text precedes it, so lines up to and including the marker take its
number. A source with no entry in the table gets `page: None` on every record — never
a fabricated number.

**Source:** Read directly from the on-machine files (August 2026): the FMEA handbook
`.md` carries 165 `- N -` footer lines (first at line 39, after the AIAG copyright
notice on page 1); the MSA manual carries 223 bare-digit lines (`1` at line 233, `2` at
237, ...), each following that page's content. There is no published convention here —
this is an artefact of the two PDF-to-Markdown conversions, not a standard.

Known limitation: front matter numbered with roman numerals (MSA pages i–viii) carries no
matching marker, so those segments take the number of the first arabic footer that follows
them. The alternative — inferring a roman-numeral page sequence — is more machinery than
the front matter is worth, and would still be a guess.

**Rationale:** One universal page regex is wrong for both files: the MSA pattern would
match a `- N -` list item, and the FMEA pattern matches nothing in the MSA manual. A
config table keyed by `source_id` is the ceiling for #283 (2 sources), deliberately not
a plugin architecture.

**Applied In:** `quality_database_app/segment.py` -> `PAGE_MARKERS`, `_page_by_line()`

---

## RULE 3 — A marker is accepted only if it advances the page count (heuristic)

**Decision:** A line matching the source's marker pattern is treated as a page footer
only when its number is greater than the current page; otherwise it is left as ordinary
text.

**Source:** The FMEA marker sequence is increasing but not contiguous (1..7, then 14),
so "next page = current + 1" would reject real markers; the MSA bare-digit pattern is
loose enough that a numeric table cell or list numeral could otherwise reset the count.

**Rationale:** Monotonicity is the cheapest guard that keeps a stray numeric line from
fabricating a page number, which is the failure the spec names explicitly. Ceiling: a
source whose page numbering legitimately restarts (a per-part-numbered volume) would
lose the pages after the restart to the preceding number; no source in scope does this.

**Applied In:** `quality_database_app/segment.py` -> `_page_by_line()`

---

## RULE 4 — Cleaning is format-only, never content-repairing (definitional)

**Decision:** Normalization strips trailing whitespace, collapses runs of blank lines,
trims leading/trailing blanks, and removes page-marker lines. Nothing *inside* a line
is altered — no whitespace collapsing within a line, no `<br>` rewriting, no table
repair.

**Source:** #283 acceptance ("normalization must not paper over a mangled cell as
clean"); the #256 damage pattern (`Hih`/`g`, `Mdt`/`oerae`) sits inside table cells.

**Rationale:** The pipeline cannot verify what the correct text was, so any repair
would be a guess presented as an extraction. Damage must survive verbatim so the
`low_confidence` flag and the reviewer both stay honest.

**Applied In:** `quality_database_app/segment.py` -> `_normalize()`, `segment()`

---

## RULE 5 — Clause = the nearest preceding Markdown heading; the heading stays in the text

**Decision:** A segment runs from one `#`..`######` heading to the next; `clause` is
that heading's text verbatim (Markdown emphasis included, since stripping it would be a
content edit). The heading line is kept as the first line of the segment's `text`, so a
retrieved chunk carries its own title. Text before the first heading has
`clause: null`; a segment that normalizes to empty is dropped.

**Source:** Both in-scope sources are already Markdown-heading-structured; general
RAG-chunking practice is to split on heading boundaries and keep section metadata on
the chunk. Not a standards claim.

**Rationale:** Heading-boundary splitting needs no new dependency and no OCR. `null`
rather than `""` because `StrictModel` rejects blank strings — an absent clause must be
absent, not blank.

**Applied In:** `quality_database_app/segment.py` -> `HEADING`, `segment()`

---

## RULE 6 — A ledger region covers its whole file (known limitation)

**Decision:** The ledger does not line-delimit its regions, so every ingestible row is
segmented over the whole file it names. `fmea-vda-2019` therefore yields two record
sets over the same text — one `clean` / `paraphrase-and-point`, one `mangled` /
`never-ship`.

**Source:** `docs/CORPUS_LEDGER.tsv` — both `fmea-vda-2019` rows carry the same
`on_machine_path`, distinguished only by a prose `region` label.

**Rationale:** Inferring line ranges for a region would be exactly the unverifiable
guess RULE 4 forbids. The duplication errs toward over-flagging (extra `never-ship`
copies), not under-flagging. Ceiling: line-delimited regions are an M4-3+ ledger
change, not an inference this pipeline may make.

**Applied In:** `quality_database_app/pipeline.py` -> `run()`

---

## RULE 7 — No wall-clock timestamp in the output (definitional)

**Decision:** `CorpusEnvelope` carries `schema_version` and `generated_by` only. There
is no `generated_at`.

**Source:** #283 acceptance — "a re-run yields byte-identical output".

**Rationale:** An embedded timestamp would break byte-identity on every run, forcing
the determinism check to become a partial comparison and leaving real content drift
easier to miss. The filesystem mtime and git are the history, the same discipline as
`quality_core.project.io.write_artifact` ("a re-run overwrites its own file in place").
This is a deliberate narrowing of the spec's proposed envelope.

**Applied In:** `quality_database_app/schema.py` -> `CorpusEnvelope`

---

## RULE 8 — `md` only this issue; PDF rows are skipped and logged (SME-locked)

**Decision:** A row whose `format` is not `md` — and a row that is `not-held` or whose
`on_machine_path` is a sentinel (`not-located`, `in-repo`) — is skipped, with the
reason logged at INFO. A source file that cannot be read is skipped with a WARNING,
not an error, because the corpus is private and absent on CI.

**Source:** SME decision, 2026-08-15 (#283): md-only, zero new dependencies; the ~18
PDF rows and the extraction-dependency decision are deferred to **#329**.

**Rationale:** A `not-extracted` row has no text to segment; running against it would
emit an empty or garbage record. Skipping loudly keeps the gap visible.

**Superseded in part by RULE 13 (#329):** this rule stands as the record of #283's
decision, but `pdf` is no longer a skipped format — only formats with no reader at all
are. The `not-held` / sentinel-path / unreadable-source skips are unchanged.

**Applied In:** `quality_database_app/ledger.py` -> `skip_reason()`,
`quality_database_app/pipeline.py` -> `run()`

---

## RULE 9 — Chunk = one record; `MAX_CHARS` / `OVERLAP_CHARS` are tunable defaults (#284)

**Decision:** The default retrieval chunk is **one M4-2 `CorpusRecord`, unchanged**. A
record is split only when its text exceeds `MAX_CHARS = 3000`: paragraphs (blank-line
delimited) are packed greedily up to that limit first, and only a single paragraph that
is itself over the limit falls back to a hard character window with
`OVERLAP_CHARS = 200` shared between adjacent windows. A trailing window that would sit
entirely inside its predecessor is dropped rather than emitted as a duplicate.

**Source:** Engineering assumption, not a standard. `3000` characters is ~750 tokens at
the ~4-characters-per-token rule of thumb — comfortably inside any current embedding
model's context while keeping a chunk small enough to cite. `200` is enough shared text
that a citation cut mid-thought has a neighbouring chunk that disambiguates it. Neither
number is measured against this corpus yet.

**Rationale:** `segment.py` (RULE 5) already split on Markdown heading boundaries, so a
record is already clause-scoped and carries its page — re-splitting it by a blind fixed
size would throw that structure away for no gain. Ceiling: both constants are named at
their definition site as tunable and are to be re-tuned against M4-4's (#285) eval set;
the fallback window is explicitly the last resort, not the default strategy.

**Applied In:** `quality_database_app/chunk.py` -> `MAX_CHARS`, `OVERLAP_CHARS`,
`split_text()`, `_windows()`

---

## RULE 10 — The embedder is abstracted; CI never runs a real model (SME-locked, #284)

**Decision:** `chunk.py` / `index.py` / `store.py` depend only on the `Embedder`
protocol. `FakeEmbedder` — a deterministic sha256-derived unit vector, 32 dimensions,
offline — is the **only** embedder the CI path exercises. A real local model
(`fastembed`, ONNX) lives in `embed_fastembed.py` behind the optional `embed`
dependency group and is excluded from the coverage gate.

**Source:** SME decision, 2026-08-15 (#284). CI has no network and no model cache, the
same constraint that keeps the licensed corpus itself off CI (RULE 8).

**Rationale:** Hash vectors carry no semantic similarity, so these tests assert the
plumbing — metadata survives, filters apply, results are ordered and deterministic —
never retrieval quality, which is M4-4's eval harness. Real embedding is a hand-run.
Ceiling: swapping the real backend must never touch `chunk.py`/`index.py`/`store.py`;
if it does, the seam has been broken.

**Applied In:** `quality_database_app/embed.py` -> `Embedder`, `FakeEmbedder`;
`quality_database_app/embed_fastembed.py`; `.github/workflows/ci.yml` -> Quality
Database coverage gate

---

## RULE 11 — `never-ship` chunks are indexed and filtered at query time (SME-locked, #284)

**Decision:** Every chunk is embedded and persisted, including
`serving_flag: never-ship`. `VectorStore.search()` takes `exclude_never_ship: bool = True`
and drops them from results by default; `exclude_never_ship=False` returns them.

**Source:** SME decision, 2026-08-15 (#284), extending RULE 1's "flag, never silently
drop" to the index.

**Rationale:** Excluding at build time would erase the flag from the artefact, so the
licensing gap would stop being auditable and the index would silently disagree with the
corpus about what exists. Filtering at query time keeps the data honest and the query
layer (M5) safe by default. Ceiling: a serving decision beyond "never-ship" — e.g.
`paraphrase-and-point` enforcement in the answer layer — is M5's, not this store's.

**Applied In:** `quality_database_app/store.py` -> `_matches()`, `VectorStore.search()`

---

## RULE 12 — Metadata filters cover `standard` / `source_id` / `region` only (#284)

**Decision:** `VectorStore.search()` filters on the fields the ledger actually carries.
There is no `tool` filter.

**Source:** `docs/CORPUS_LEDGER.tsv` has no `tool` column, and `CorpusRecord` has no
such field.

**Rationale:** A `standard -> tool` (FMEA app / SPC app / MSA app) mapping is not
derivable from the corpus today; inventing one here would be an unverifiable guess of
exactly the kind RULE 4 forbids. Ceiling: if M5's query layer needs tool scoping, it
adds an explicit, reviewed mapping table — this store does not infer one.

**Applied In:** `quality_database_app/store.py` -> `_matches()`

---

## RULE 13 — PDF is text-layer only: `pypdf`, one segment per page, no OCR (SME-locked, #329)

**Decision:** `pdf` joins `md` in `INGESTIBLE_FORMATS`. Extraction uses **`pypdf` and
nothing else**: one `CorpusRecord` per page that has extractable text, `page` = pypdf's
own 1-indexed page number, `clause` = **always `None`**. A held PDF whose every page
extracts to nothing — an image-only scan — is skipped with a WARNING naming the OCR
follow-up, not emitted as zero records. `extraction_quality` is **never** written or
derived by this pipeline, so all 15 newly extracted rows stay `not-extracted` and every
record they produce is `low_confidence: true` until the SME edits the ledger by hand.

**Source:** SME decisions, 2026-08-16 (#329), on evidence gathered per-row against the
on-machine corpus: of the 20 `format=pdf` / `not-extracted` ledger rows, **15 have a
real text layer** and **5 are image-only scans with zero extractable characters**
(`aiag-apqp-2nd`, `iatf-16949-2016`, `iso-9001-2015`, `western-electric-1956`,
`montgomery-isqc-8`). OCR for those 5 is issue **#335**.

**Rationale:** `pypdf` is pure Python with zero transitive dependencies (BSD); OCR would
need `pytesseract` plus the system `tesseract` binary — not `pip`-installable, not
covered by `uv sync`, a separate SME-level decision. `pdfplumber`'s extra layout fidelity
buys nothing here because raw PDF text has no heading structure to segment on anyway.
Hence `clause=None`: inventing "the first line of a page is a heading" would be exactly
the unverifiable repair RULE 4 forbids. Page numbers, conversely, are *more* trustworthy
than the `md` path's footer-marker heuristic (RULE 2/3) — they come from the document's
own page tree, not from the text. Auto-flipping `extraction_quality` to `clean` would be
the second, code-derived confidence signal RULE 1 exists to prevent. `never-ship` PDF
rows are extracted and flagged like every other never-ship source (RULE 11): flag, never
silently drop. Ceiling: the 5 image-only rows stay invisible to retrieval until #335.

**Applied In:** `quality_database_app/extract_pdf.py` -> `extract()`,
`quality_database_app/ledger.py` -> `INGESTIBLE_FORMATS`,
`quality_database_app/pipeline.py` -> `read_segments()`, `run()`

---

## RULE 14 — Storage stays local and gitignored; auth is deferred to M5-2 (SME-locked, #286)

**Decision:** Two parts.

(a) **Storage (OQ1).** The private corpus store is what M4-2/M4-3 already write —
`apps/quality_database/.corpus_out/` (`corpus.json` + `index/`), derived from the
on-machine `$CORPUS_ROOT` tree. M4-5 creates no new location, adds no dependency, and
stands up no remote/cloud store. It adds the machine check
(`tests/test_no_corpus_content.py`: nothing under `.corpus_out/` is tracked, and no
tracked file carries verbatim non-`serve` corpus text) and one sanctioned reader
(`quality_database_app/storage.py`) that **fails closed** — a missing index raises
`IngestionError`, never an empty store.

(b) **Auth (OQ2).** #286 introduces **no** new secret or auth mechanism. It is a local
filesystem read with no caller identity to authenticate, so auth code here would be dead
code. When M5-2 exposes this reader over the network it must **reuse** M1-8's
shared-secret bearer posture rather than invent a second scheme: a single
`MCP_AUTH_TOKEN`-style env secret, fail-closed when unset (a `RuntimeError` at provider
build time, not an open endpoint), and constant-time comparison via
`hmac.compare_digest`.

**Source:** SME decision, 2026-08-16 (#286). The auth pattern is
`apps/mcp/mcp_app/transport.py` (`TOKEN_ENV`, `build_auth_provider()`,
`hmac.compare_digest`), shipped by M1-8 / issue #267. Storage policy: `docs/CORPUS_LEDGER.md`
("the corpus is private; only our derivations are public"). No AIAG/ISO claim is made by
this rule — it is an internal architecture decision, cited to repo files.

**Rationale:** A remote store and a second auth scheme would both be infrastructure bought
for zero live callers (M5-2 does not exist yet), and two auth schemes in one repo is the
configuration that eventually leaves one of them fail-open. Ceiling: `storage.py` cannot
*enforce* "only the endpoint may read the corpus" — there is no caller to gate today; that
enforcement is explicitly M5-2's job. What #286 asserts is narrower and true: the location
is private and guarded, there is exactly one intended reader, and it fails closed.

**Applied In:** `quality_database_app/storage.py`, `tests/test_no_corpus_content.py`,
`.gitignore`, `.github/workflows/ci.yml` -> Quality Database coverage gate
