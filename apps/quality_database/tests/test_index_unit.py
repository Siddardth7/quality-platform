"""Unit tests for index.py (#284) — the corpus-file -> saved-index job."""

import pytest
from quality_database_app.chunk import chunk_corpus
from quality_database_app.embed import FakeEmbedder
from quality_database_app.index import build_index, run
from quality_database_app.pipeline import write_records
from quality_database_app.schema import (
    SCHEMA_VERSION,
    Corpus,
    CorpusEnvelope,
    CorpusRecord,
    IngestionError,
)
from quality_database_app.store import METADATA_FILE, VECTORS_FILE, VectorStore


def _corpus(records=1):
    return Corpus(
        envelope=CorpusEnvelope(schema_version=SCHEMA_VERSION, generated_by="test"),
        records=[
            CorpusRecord(
                source_id="fmea-vda-2019",
                region="DFMEA-severity-and-AP-prose",
                standard="AIAG & VDA FMEA Handbook",
                clause=f"Clause {index}",
                page=index + 1,
                text=f"Body text number {index}.",
                confidence="high",
                low_confidence=False,
                extraction_quality="clean",
                serving_flag="paraphrase-and-point",
                license_class="licensed-commercial",
            )
            for index in range(records)
        ],
    )


def test_build_index_preserves_chunk_order_and_width():
    chunks = chunk_corpus(_corpus(3))
    store = build_index(chunks, FakeEmbedder())
    assert store.chunks == chunks
    assert store.vectors.shape == (3, FakeEmbedder().dimension)


def test_build_index_of_nothing_is_an_empty_store():
    assert build_index([], FakeEmbedder()).chunks == []


def test_run_writes_a_loadable_index(tmp_path, caplog):
    corpus_path = tmp_path / "corpus.json"
    write_records(corpus_path, _corpus(2))
    out_dir = tmp_path / "index"

    with caplog.at_level("INFO"):
        store = run(FakeEmbedder(), corpus_path=corpus_path, out_dir=out_dir)

    assert (out_dir / VECTORS_FILE).exists() and (out_dir / METADATA_FILE).exists()
    assert [chunk.chunk_id for chunk in VectorStore.load(out_dir).chunks] == [
        chunk.chunk_id for chunk in store.chunks
    ]
    assert "indexed 2 chunks from 2 records" in caplog.text


def test_run_propagates_corpus_file_errors(tmp_path):
    # load_records() owns corpus-file error handling; index.py does not re-implement it.
    with pytest.raises(IngestionError):
        run(FakeEmbedder(), corpus_path=tmp_path / "missing.json", out_dir=tmp_path / "index")
