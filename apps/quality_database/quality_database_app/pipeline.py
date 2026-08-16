"""Ledger -> segments -> corpus file (M4-2, #283).

The whole pipeline: read ``docs/CORPUS_LEDGER.tsv``, skip (and log) every row #283
cannot ingest, read each remaining Markdown source, segment it, and emit one
:class:`~quality_database_app.schema.CorpusRecord` per segment with the ledger's
confidence, serving flag and licence class carried through.

Re-running over unchanged inputs produces a byte-identical output file — the write
discipline of ``quality_core.project.io.write_artifact``: pretty JSON, parent dir
created, overwrite in place, no wall-clock content.

The output is corpus-derived text, so it is **gitignored, never committed**, per the
M4-1 policy ("the corpus is private; only our derivations are public"); committed
storage is M4-5's (#286) decision.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pydantic

from quality_database_app import __version__
from quality_database_app.ledger import (
    DEFAULT_LEDGER_PATH,
    LedgerRow,
    corpus_root,
    ingestible_rows,
    load_ledger,
    resolve_path,
    skip_reason,
)
from quality_database_app.schema import (
    SCHEMA_VERSION,
    Corpus,
    CorpusEnvelope,
    CorpusRecord,
    IngestionError,
    confidence_for,
)
from quality_database_app.segment import page_marker_for, segment

logger = logging.getLogger(__name__)

DEFAULT_OUT_PATH = Path(__file__).resolve().parents[1] / ".corpus_out" / "corpus.json"


def build_records(row: LedgerRow, text: str) -> list[CorpusRecord]:
    """Segment one source's text into records carrying that ledger row's classification."""
    confidence = confidence_for(row.extraction_quality)
    return [
        CorpusRecord(
            source_id=row.source_id,
            region=row.region,
            standard=row.title,
            clause=piece.clause,
            page=piece.page,
            text=piece.text,
            confidence=confidence,
            low_confidence=confidence == "low",
            extraction_quality=row.extraction_quality,
            serving_flag=row.serving_flag,
            license_class=row.license_class,
        )
        for piece in segment(text, page_marker_for(row.source_id))
    ]


def run(
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    root: Path | None = None,
    out_path: Path = DEFAULT_OUT_PATH,
) -> Corpus:
    """Ingest every ingestible ledger row and write the corpus to ``out_path``."""
    root = corpus_root() if root is None else root
    rows = load_ledger(ledger_path)

    for row in rows:
        reason = skip_reason(row)
        if reason is not None:
            logger.info("skipping %s: %s", row.key, reason)

    records: list[CorpusRecord] = []
    for row in ingestible_rows(rows):
        path = resolve_path(row.on_machine_path, root)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            # The corpus is private and is not on CI; a missing source is a skip with a
            # log line, not a failure — the ledger already asserts the path elsewhere.
            logger.warning("skipping %s: %s could not be read: %s", row.key, path, exc)
            continue
        records.extend(build_records(row, text))

    corpus = Corpus(
        envelope=CorpusEnvelope(
            schema_version=SCHEMA_VERSION, generated_by=f"quality_database_app=={__version__}"
        ),
        records=records,
    )
    write_records(out_path, corpus)
    return corpus


def write_records(path: Path, corpus: Corpus) -> None:
    """Write the corpus as pretty JSON, creating parent directories, overwriting in place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(corpus.model_dump(mode="json"), indent=2, ensure_ascii=False)
    path.write_text(payload + "\n", encoding="utf-8")


def load_records(path: Path) -> Corpus:
    """Load and validate a corpus file written by :func:`write_records`."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise IngestionError(f"'{path}' could not be read: {exc}.") from exc
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise IngestionError(f"'{path}' is not valid JSON: {exc}.") from exc
    try:
        corpus = Corpus.model_validate(payload)
    except pydantic.ValidationError as exc:
        raise IngestionError(f"'{path}' is not a valid Corpus: {exc}.") from exc
    if corpus.envelope.schema_version != SCHEMA_VERSION:
        raise IngestionError(
            f"'{path}' has schema_version {corpus.envelope.schema_version}, "
            f"expected {SCHEMA_VERSION}."
        )
    return corpus
