"""File-backed vector store: ``vectors.npy`` + ``metadata.json`` (M4-3, #284).

No server and no new dependency (SME-locked, #284). The corpus is ~941 records, so a
brute-force cosine scan over a few thousand vectors is sub-millisecond — an ANN index
or a Postgres/pgvector service would be machinery bought for a problem that does not
exist yet.

# ponytail: brute-force scan, O(n) per query. Upgrade path: swap the body of
# `search()` for an ANN index (or a served store) if the corpus outgrows a linear
# scan. `VectorStore` is the seam — nothing outside this module sees the vectors.

Persistence is deterministic in the same sense as
``quality_database_app.pipeline.write_records``: pretty JSON, no wall-clock content, so
re-indexing unchanged inputs rewrites byte-identical files.

Never-ship chunks are **stored** and excluded at query time (``exclude_never_ship``
defaults to ``True``), never dropped at build time — the flag stays in the data so the
licensing gap remains auditable, while the query layer is safe by default.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pydantic

from quality_database_app.chunk import Chunk
from quality_database_app.schema import SCHEMA_VERSION, IngestionError

VECTORS_FILE = "vectors.npy"
METADATA_FILE = "metadata.json"

NEVER_SHIP = "never-ship"


@dataclass(frozen=True)
class SearchResult:
    """One hit: the chunk itself plus its cosine score.

    # ponytail: the chunk is carried whole rather than re-flattened onto this class —
    # `result.chunk.page` / `.clause` / `.standard` are the citation fields, and a
    # field-by-field copy would be a second place to forget one.
    """

    chunk: Chunk
    score: float


def _matches(
    chunk: Chunk,
    standard: str | None,
    source_id: str | None,
    region: str | None,
    exclude_never_ship: bool,
) -> bool:
    """Metadata filter over the fields the ledger actually has.

    There is no ``tool`` field anywhere in the ledger or the corpus schema; a
    ``standard -> tool`` mapping is an M5 decision, not something to invent here.
    """
    if exclude_never_ship and chunk.serving_flag == NEVER_SHIP:
        return False
    if standard is not None and chunk.standard != standard:
        return False
    if source_id is not None and chunk.source_id != source_id:
        return False
    return not (region is not None and chunk.region != region)


class VectorStore:
    """Chunks plus their vectors, searchable by cosine similarity."""

    def __init__(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        self.chunks = chunks
        self.vectors = vectors

    @classmethod
    def build(cls, chunks: list[Chunk], vectors: list[list[float]]) -> "VectorStore":
        """Build a store from chunks and their vectors; empty input is a valid store."""
        if len(chunks) != len(vectors):
            raise ValueError(f"{len(chunks)} chunks but {len(vectors)} vectors.")
        if not chunks:
            return cls([], np.zeros((0, 0), dtype=np.float64))
        return cls(chunks, np.array(vectors, dtype=np.float64))

    def save(self, out_dir: Path) -> None:
        """Write ``vectors.npy`` + ``metadata.json`` into ``out_dir``, overwriting."""
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / VECTORS_FILE).open("wb") as handle:
            np.save(handle, self.vectors)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "chunks": [chunk.model_dump(mode="json") for chunk in self.chunks],
        }
        (out_dir / METADATA_FILE).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, out_dir: Path) -> "VectorStore":
        """Load a store written by :meth:`save`, validating the metadata contract."""
        metadata_path = out_dir / METADATA_FILE
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise IngestionError(f"'{metadata_path}' could not be read: {exc}.") from exc
        except ValueError as exc:
            raise IngestionError(f"'{metadata_path}' is not valid JSON: {exc}.") from exc
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise IngestionError(
                f"'{metadata_path}' has schema_version {payload.get('schema_version')}, "
                f"expected {SCHEMA_VERSION}."
            )
        try:
            chunks = [Chunk.model_validate(row) for row in payload["chunks"]]
        except (KeyError, TypeError, pydantic.ValidationError) as exc:
            raise IngestionError(f"'{metadata_path}' is not a valid chunk index: {exc}.") from exc
        vectors = np.load(out_dir / VECTORS_FILE)
        if vectors.shape[0] != len(chunks):
            raise IngestionError(
                f"'{out_dir}' holds {vectors.shape[0]} vectors for {len(chunks)} chunks."
            )
        return cls(chunks, vectors)

    def search(
        self,
        query_vector: list[float],
        k: int = 5,
        standard: str | None = None,
        source_id: str | None = None,
        region: str | None = None,
        exclude_never_ship: bool = True,
    ) -> list[SearchResult]:
        """The ``k`` best-matching chunks passing every filter, best first.

        Returns fewer than ``k`` results (including none) when the filters leave fewer
        in scope — an empty result is a legitimate answer, not an error. A query vector
        of the wrong width fails loud rather than being coerced.
        """
        if not self.chunks:
            return []
        if len(query_vector) != self.vectors.shape[1]:
            raise ValueError(
                f"query vector has {len(query_vector)} dimensions, "
                f"store holds {self.vectors.shape[1]}."
            )

        query = np.asarray(query_vector, dtype=np.float64)
        norms = np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query)
        # A zero-norm vector has no direction; score it 0 rather than dividing by zero.
        scores = np.where(norms == 0, 0.0, self.vectors @ query / np.where(norms == 0, 1.0, norms))

        results: list[SearchResult] = []
        # Stable sort: equal scores keep chunk order, so results are deterministic.
        for position in np.argsort(-scores, kind="stable"):
            if len(results) == k:
                break
            chunk = self.chunks[int(position)]
            if _matches(chunk, standard, source_id, region, exclude_never_ship):
                results.append(SearchResult(chunk=chunk, score=float(scores[position])))
        return results
