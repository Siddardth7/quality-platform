"""Corpus records -> retrievable chunks (M4-3, #284).

The default chunk is **one M4-2 record, as-is**. ``segment.py`` already split the
source on Markdown heading boundaries, so a record is already clause-scoped and
already carries its page — re-splitting it by a blind fixed size would throw that
structure away. Splitting happens only when a single record's text is longer than
:data:`MAX_CHARS`, and even then paragraph boundaries are tried before any hard cut.

Every chunk carries its originating record's metadata verbatim — ``standard``,
``clause``, ``page``, ``confidence``, ``serving_flag``, ``license_class``. Nothing is
re-derived and nothing is dropped, including ``serving_flag == "never-ship"``: the
index keeps the flag and :meth:`~quality_database_app.store.VectorStore.search`
filters on it, so the gap stays auditable (the M4-1/M4-2 "flag, never silently drop"
discipline).
"""

from __future__ import annotations

from quality_core.schema._base import StrictModel

from quality_database_app.schema import Confidence, Corpus, CorpusRecord

#: Longest text kept in a single chunk. **Tunable** — a working default (~750 tokens
#: at ~4 chars/token), not a standards constant. Re-tune against M4-4's eval set.
MAX_CHARS = 3000

#: Characters shared between adjacent windows on the hard-fallback split path only.
#: **Tunable**, same caveat: enough shared context that a citation cut mid-thought has
#: a neighbour to disambiguate it. See ASSUMPTIONS_LOG RULE 9.
OVERLAP_CHARS = 200

PARAGRAPH_BREAK = "\n\n"


class Chunk(StrictModel):
    """One retrievable unit: a record's text (or a slice of it) plus its provenance.

    Mirrors :class:`~quality_database_app.schema.CorpusRecord` field-for-field, plus
    the two identity fields retrieval needs. Kept as a ``StrictModel`` rather than a
    plain dataclass because the index's ``metadata.json`` is an on-disk contract and
    gets validated on load, exactly like the corpus file itself.
    """

    chunk_id: str
    chunk_index: int
    source_id: str
    region: str
    standard: str
    clause: str | None = None
    page: int | None = None
    text: str
    confidence: Confidence
    low_confidence: bool
    extraction_quality: str
    serving_flag: str
    license_class: str


def _windows(text: str) -> list[str]:
    """Hard character windows with :data:`OVERLAP_CHARS` shared between neighbours.

    Last resort only: reached when a single paragraph has no internal blank line to
    split on. A trailing window that would sit entirely inside its predecessor is
    dropped rather than emitted as a duplicate chunk.
    """
    step = MAX_CHARS - OVERLAP_CHARS
    return [
        text[start : start + MAX_CHARS]
        for start in range(0, len(text), step)
        if start == 0 or len(text) - start > OVERLAP_CHARS
    ]


def split_text(text: str) -> list[str]:
    """Split ``text`` into pieces of at most :data:`MAX_CHARS`, boundary-aware.

    Short text is returned untouched (the common case). Otherwise paragraphs are
    packed greedily up to the limit; only a paragraph that is itself over the limit
    falls through to :func:`_windows`.
    """
    if len(text) <= MAX_CHARS:
        return [text]

    pieces: list[str] = []
    buffer = ""
    for paragraph in text.split(PARAGRAPH_BREAK):
        if not paragraph.strip():
            continue
        if len(paragraph) > MAX_CHARS:
            if buffer:
                pieces.append(buffer)
                buffer = ""
            pieces.extend(_windows(paragraph))
            continue
        if not buffer:
            buffer = paragraph
        elif len(buffer) + len(PARAGRAPH_BREAK) + len(paragraph) <= MAX_CHARS:
            buffer = buffer + PARAGRAPH_BREAK + paragraph
        else:
            pieces.append(buffer)
            buffer = paragraph
    if buffer:
        pieces.append(buffer)
    return pieces


def chunk_record(record: CorpusRecord, record_ordinal: int) -> list[Chunk]:
    """Chunk one record, stamping every piece with the record's metadata."""
    return [
        Chunk(
            chunk_id=f"{record_ordinal:05d}-{index:02d}",
            chunk_index=index,
            source_id=record.source_id,
            region=record.region,
            standard=record.standard,
            clause=record.clause,
            page=record.page,
            text=text,
            confidence=record.confidence,
            low_confidence=record.low_confidence,
            extraction_quality=record.extraction_quality,
            serving_flag=record.serving_flag,
            license_class=record.license_class,
        )
        for index, text in enumerate(split_text(record.text))
    ]


def chunk_corpus(corpus: Corpus) -> list[Chunk]:
    """Chunk every record in ``corpus``, in record order.

    Deterministic: the same corpus yields the same ``chunk_id`` list in the same order
    on every run. ``chunk_id`` is keyed on the record's ordinal, so the same
    ``source_id`` under two regions (``fmea-vda-2019``) cannot collide.
    """
    chunks: list[Chunk] = []
    for ordinal, record in enumerate(corpus.records):
        chunks.extend(chunk_record(record, ordinal))
    return chunks
