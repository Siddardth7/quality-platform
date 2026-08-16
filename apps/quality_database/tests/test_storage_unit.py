"""Unit tests for storage.py (#286) — path resolution and the fail-closed read path.

Offline and tmp-path only: the real ``.corpus_out/`` is private and is absent on CI, so
every test here builds its own store, exactly like ``test_store_unit.py``.
"""

import numpy as np
import pytest
from quality_database_app import storage
from quality_database_app.chunk import Chunk
from quality_database_app.index import DEFAULT_INDEX_DIR
from quality_database_app.schema import IngestionError
from quality_database_app.store import METADATA_FILE, VectorStore


def _store():
    chunk = Chunk(
        chunk_id="00000-00",
        chunk_index=0,
        source_id="fmea-vda-2019",
        region="DFMEA-severity-and-AP-prose",
        standard="AIAG & VDA FMEA Handbook",
        clause="Severity",
        page=41,
        text="text 0",
        confidence="high",
        low_confidence=False,
        extraction_quality="clean",
        serving_flag="paraphrase-and-point",
        license_class="licensed-commercial",
    )
    return VectorStore.build([chunk], [[1.0, 0.0]])


def test_resolve_index_dir_defaults_to_the_gitignored_corpus_out(monkeypatch):
    """No override -> the M4-3 location, unchanged. #286 moved nothing (OQ1)."""
    monkeypatch.delenv(storage.CORPUS_OUT_DIR_ENV, raising=False)
    assert storage.resolve_index_dir() == DEFAULT_INDEX_DIR


def test_resolve_index_dir_honours_the_override(monkeypatch, tmp_path):
    """The override names the store directory; ``index/`` is appended by this module."""
    monkeypatch.setenv(storage.CORPUS_OUT_DIR_ENV, str(tmp_path))
    assert storage.resolve_index_dir() == tmp_path / "index"


def test_resolve_index_dir_treats_an_empty_override_as_unset(monkeypatch):
    """An exported-but-empty env var must not resolve to ``/index``."""
    monkeypatch.setenv(storage.CORPUS_OUT_DIR_ENV, "")
    assert storage.resolve_index_dir() == DEFAULT_INDEX_DIR


def test_load_index_reads_the_store_at_the_resolved_location(monkeypatch, tmp_path):
    _store().save(tmp_path / "index")
    monkeypatch.setenv(storage.CORPUS_OUT_DIR_ENV, str(tmp_path))

    loaded = storage.load_index()

    assert [chunk.chunk_id for chunk in loaded.chunks] == ["00000-00"]
    assert np.array_equal(loaded.vectors, np.array([[1.0, 0.0]]))


def test_load_index_fails_closed_when_no_index_has_been_built(monkeypatch, tmp_path):
    """A missing index is an error, never a silently empty store (OQ3)."""
    monkeypatch.setenv(storage.CORPUS_OUT_DIR_ENV, str(tmp_path))
    with pytest.raises(IngestionError, match="no index has been built yet"):
        storage.load_index()


def test_load_index_propagates_a_corrupt_store_unchanged(monkeypatch, tmp_path):
    """``VectorStore.load``'s own IngestionError is not swallowed or reworded."""
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    (index_dir / METADATA_FILE).write_text("{not json", encoding="utf-8")
    monkeypatch.setenv(storage.CORPUS_OUT_DIR_ENV, str(tmp_path))

    with pytest.raises(IngestionError, match="not valid JSON"):
        storage.load_index()
