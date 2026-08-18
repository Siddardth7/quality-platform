"""Read ``docs/CORPUS_LEDGER.tsv`` — the M4-1 (#282) manifest that is this pipeline's input.

The ledger, not this module, decides what may be ingested and how its text may be
served. Everything here is reading and filtering; no row is reclassified.

The ``CORPUS_ROOT`` env var and its default match ``tests/test_corpus_ledger.py`` exactly,
so a machine with the private corpus mounted elsewhere exercises both, and CI — which
holds no licensed manual — behaves the same way for both.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from quality_core.schema._base import StrictModel

from quality_database_app.schema import IngestionError

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parents[3] / "docs" / "CORPUS_LEDGER.tsv"

CORPUS_ROOT_ENV_VAR = "CORPUS_ROOT"
DEFAULT_CORPUS_ROOT = Path("/Users/sid/Documents/Upskill/SixSigma")

#: ``not-located`` = cited by an app log but no copy held; ``in-repo`` = this project's
#: own committed prose. Neither names a file under the corpus root.
PATH_SENTINELS = frozenset({"not-located", "in-repo"})

#: The formats the pipeline can read: ``md`` (#283) and ``pdf`` (#329, via ``pypdf``).
#: A ``pdf`` row with no text layer passes this filter and is skipped later, by
#: :func:`~quality_database_app.pipeline.run`, once extraction has proved it empty.
INGESTIBLE_FORMATS = frozenset({"md", "pdf"})

COLUMNS = (
    "source_id",
    "title",
    "edition",
    "on_machine_path",
    "format",
    "region",
    "status",
    "extraction_quality",
    "license_class",
    "serving_flag",
    "rationale",
    "cited_by",
)


class LedgerRow(StrictModel):
    """One ``(source_id, region)`` row of the ledger, field-for-field with its header."""

    source_id: str
    title: str
    edition: str
    on_machine_path: str
    format: str
    region: str
    status: str
    extraction_quality: str
    license_class: str
    serving_flag: str
    rationale: str
    cited_by: str

    @property
    def key(self) -> str:
        return f"{self.source_id}/{self.region}"


def corpus_root() -> Path:
    """The root of the private corpus tree, overridable with ``$CORPUS_ROOT``."""
    return Path(os.environ.get(CORPUS_ROOT_ENV_VAR, DEFAULT_CORPUS_ROOT))


def load_ledger(path: Path = DEFAULT_LEDGER_PATH) -> list[LedgerRow]:
    """Read and validate the ledger TSV.

    Raises
    ------
    IngestionError
        If the file is missing, has no header, has a header other than :data:`COLUMNS`,
        or holds a row that fails validation (e.g. a blank cell).
    """
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames is None or tuple(reader.fieldnames) != COLUMNS:
                raise IngestionError(
                    f"'{path}' header is {reader.fieldnames}, expected {list(COLUMNS)}."
                )
            raw_rows = list(reader)
    except OSError as exc:
        raise IngestionError(f"'{path}' could not be read: {exc}.") from exc

    rows = []
    for raw in raw_rows:
        try:
            rows.append(LedgerRow.model_validate(raw))
        except Exception as exc:
            raise IngestionError(f"'{path}' has an invalid row {raw}: {exc}.") from exc
    return rows


def skip_reason(row: LedgerRow) -> str | None:
    """Why this row cannot be ingested, or ``None`` if it can be.

    Returning the reason (rather than a bare bool) is what makes a skip *observable*:
    the pipeline logs it, so a row silently dropping out of the corpus is visible.
    """
    if row.format not in INGESTIBLE_FORMATS:
        return (
            f"format={row.format!r} is not one of "
            f"{sorted(INGESTIBLE_FORMATS)} — no reader for it"
        )
    if row.status == "not-held":
        return "status='not-held' — no copy to read"
    if row.on_machine_path in PATH_SENTINELS:
        return f"on_machine_path={row.on_machine_path!r} names no file under the corpus root"
    return None


def ingestible_rows(rows: list[LedgerRow]) -> list[LedgerRow]:
    """The rows the pipeline ingests, in ledger order (see :func:`skip_reason` for the rest)."""
    return [row for row in rows if skip_reason(row) is None]


def resolve_path(on_machine_path: str, root: Path) -> Path:
    """Re-root a ledger path under ``root`` when it points at the default corpus root.

    The ledger records absolute paths (SME-reviewable as written); re-rooting is what
    makes ``$CORPUS_ROOT`` mean something on a machine that keeps the corpus elsewhere.
    """
    path = Path(on_machine_path)
    if root != DEFAULT_CORPUS_ROOT and path.is_relative_to(DEFAULT_CORPUS_ROOT):
        return root / path.relative_to(DEFAULT_CORPUS_ROOT)
    return path
