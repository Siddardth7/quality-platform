"""The indexing job: corpus file -> chunks -> vectors -> a saved store (M4-3, #284).

``run()`` embeds the **whole** corpus. It takes its embedder as an argument and
imports no real backend — CI passes :class:`~quality_database_app.embed.FakeEmbedder`,
and the real end-to-end run is a local hand-run (see the app README), exactly like
M4-2's corpus read: the licensed corpus is never on CI.

There is deliberately no default embedder. A default would let a real indexing run
silently produce a hash-vector index that retrieves nothing useful, and that failure
would be invisible until M4-4's eval.
"""

from __future__ import annotations

import logging
from pathlib import Path

from quality_database_app.chunk import Chunk, chunk_corpus
from quality_database_app.embed import Embedder
from quality_database_app.pipeline import DEFAULT_OUT_PATH, load_records
from quality_database_app.store import VectorStore

logger = logging.getLogger(__name__)

DEFAULT_INDEX_DIR = Path(__file__).resolve().parents[1] / ".corpus_out" / "index"


def build_index(chunks: list[Chunk], embedder: Embedder) -> VectorStore:
    """Embed ``chunks`` and build the store, preserving chunk order."""
    return VectorStore.build(chunks, embedder.embed([chunk.text for chunk in chunks]))


def run(
    embedder: Embedder,
    corpus_path: Path = DEFAULT_OUT_PATH,
    out_dir: Path = DEFAULT_INDEX_DIR,
) -> VectorStore:
    """Read the corpus file, chunk it, embed it, and save the index to ``out_dir``.

    Corpus-file errors are :class:`~quality_database_app.schema.IngestionError` from
    ``load_records()`` unchanged — this job does not re-implement that handling.
    """
    corpus = load_records(corpus_path)
    chunks = chunk_corpus(corpus)
    store = build_index(chunks, embedder)
    store.save(out_dir)
    logger.info(
        "indexed %d chunks from %d records into %s", len(chunks), len(corpus.records), out_dir
    )
    return store
