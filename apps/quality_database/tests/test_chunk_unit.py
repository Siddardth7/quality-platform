"""Unit tests for chunk.py (#284) — splitting boundaries and metadata carry-through."""

import pytest
from quality_database_app.chunk import (
    MAX_CHARS,
    OVERLAP_CHARS,
    chunk_corpus,
    chunk_record,
    split_text,
)
from quality_database_app.schema import SCHEMA_VERSION, Corpus, CorpusEnvelope, CorpusRecord

CARRIED = (
    "source_id",
    "region",
    "standard",
    "clause",
    "page",
    "confidence",
    "low_confidence",
    "extraction_quality",
    "serving_flag",
    "license_class",
)


def _record(text="short text", **overrides):
    fields = {
        "source_id": "fmea-vda-2019",
        "region": "DFMEA-severity-and-AP-prose",
        "standard": "AIAG & VDA FMEA Handbook",
        "clause": "Severity",
        "page": 41,
        "text": text,
        "confidence": "high",
        "low_confidence": False,
        "extraction_quality": "clean",
        "serving_flag": "paraphrase-and-point",
        "license_class": "licensed-commercial",
    }
    fields.update(overrides)
    return CorpusRecord(**fields)


def test_short_record_is_one_chunk():
    chunks = chunk_record(_record(), 7)
    assert len(chunks) == 1
    assert (chunks[0].chunk_id, chunks[0].chunk_index) == ("00007-00", 0)


@pytest.mark.parametrize("field", CARRIED)
def test_every_record_field_survives_onto_the_chunk(field):
    # Parametrized so a field added to CorpusRecord and forgotten in Chunk fails loud.
    record = _record()
    for chunk in chunk_record(record, 0):
        assert getattr(chunk, field) == getattr(record, field)


def test_absent_clause_and_page_are_carried_as_none():
    chunk = chunk_record(_record(clause=None, page=None), 0)[0]
    assert chunk.clause is None and chunk.page is None


def test_paragraph_split_keeps_clause_and_page_and_numbers_chunks():
    paragraph = "P" * (MAX_CHARS // 2)
    chunks = chunk_record(_record(text="\n\n".join([paragraph] * 4)), 3)
    assert len(chunks) > 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert [chunk.chunk_id for chunk in chunks][0] == "00003-00"
    assert all((chunk.clause, chunk.page) == ("Severity", 41) for chunk in chunks)
    assert all(len(chunk.text) <= MAX_CHARS for chunk in chunks)


def test_wall_of_text_falls_back_to_overlapping_windows():
    # No blank line anywhere: the paragraph split cannot help, the hard window must.
    pieces = split_text("W" * (MAX_CHARS + 1000))
    assert len(pieces) == 2
    assert pieces[0][-OVERLAP_CHARS:] == pieces[1][:OVERLAP_CHARS]


def test_trailing_window_inside_its_predecessor_is_dropped():
    # A tail shorter than the overlap adds no new text, so it is not emitted twice.
    pieces = split_text("W" * (MAX_CHARS + (MAX_CHARS - OVERLAP_CHARS)))
    assert len(pieces) == 2


def test_oversized_paragraph_after_a_buffered_one_flushes_the_buffer():
    small = "S" * (MAX_CHARS // 2)
    huge = "H" * (MAX_CHARS + 500)
    pieces = split_text(f"{small}\n\n{huge}")
    assert pieces[0] == small
    assert pieces[1].startswith("H")


def test_blank_paragraphs_are_skipped():
    paragraph = "P" * (MAX_CHARS - 10)
    pieces = split_text(f"{paragraph}\n\n   \n\n{paragraph}")
    assert pieces == [paragraph, paragraph]


def test_paragraphs_are_packed_up_to_the_limit():
    paragraph = "P" * (MAX_CHARS // 3)
    pieces = split_text("\n\n".join([paragraph] * 4))
    assert len(pieces) == 2
    assert all(len(piece) <= MAX_CHARS for piece in pieces)


def test_chunk_corpus_is_empty_for_an_empty_corpus_and_ordinal_keyed():
    envelope = CorpusEnvelope(schema_version=SCHEMA_VERSION, generated_by="test")
    assert chunk_corpus(Corpus(envelope=envelope, records=[])) == []
    # Same source_id under two regions: distinct ids, because the ordinal differs.
    corpus = Corpus(envelope=envelope, records=[_record(), _record(region="other")])
    assert [chunk.chunk_id for chunk in chunk_corpus(corpus)] == ["00000-00", "00001-00"]
