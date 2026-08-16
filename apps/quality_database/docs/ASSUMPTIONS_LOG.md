# Engineering Assumptions Log
**Project:** Quality Database — Corpus Ingestion + Cleaning Pipeline (M4-2, #283)
**Last Updated:** August 15, 2026

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

**Applied In:** `quality_database_app/ledger.py` -> `skip_reason()`,
`quality_database_app/pipeline.py` -> `run()`
