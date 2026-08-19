"""On-disk contract for the ingested corpus (M4-2, #283).

Mirrors the shape of ``quality_core.project.schema`` — an envelope header plus a list
of rows, built on the shared :class:`quality_core.schema.StrictModel` — without
importing the M3 project-file models, which describe a different domain (a per-project
artifact graph, not a document corpus).

Confidence is derived **entirely** from the ledger's ``extraction_quality`` column
(SME-locked, #283): ``clean`` is trusted, everything else is flagged. There is
deliberately no second, code-derived confidence heuristic that could disagree with the
SME-reviewed ledger.
"""

from __future__ import annotations

from typing import Literal

import pydantic
from quality_core.schema._base import StrictModel

SCHEMA_VERSION = 1

Confidence = Literal["high", "low"]

#: The only ``extraction_quality`` value whose text is trusted verbatim. Every other
#: value (``mangled`` / ``not-extracted`` / ``n/a``) yields a flagged record — flagged,
#: never silently dropped, so a downstream consumer can see the gap exists.
TRUSTED_EXTRACTION_QUALITY = "clean"


class IngestionError(ValueError):
    """A ledger or corpus file could not be read, parsed, or validated."""


def confidence_for(extraction_quality: str) -> Confidence:
    """Map a ledger ``extraction_quality`` value onto a record confidence."""
    return "high" if extraction_quality == TRUSTED_EXTRACTION_QUALITY else "low"


class CorpusEnvelope(StrictModel):
    """The header the corpus file carries.

    No wall-clock timestamp: a re-run over unchanged inputs must produce a
    byte-identical file (#283 acceptance), and an embedded ``generated_at`` would
    break that on every run. The filesystem mtime and git are the history —
    the same discipline as ``quality_core.project.io.write_artifact``
    ("a re-run overwrites its own file in place").
    """

    schema_version: int
    generated_by: str


class CorpusRecord(StrictModel):
    """One segment of one ledger row's source document.

    ``serving_flag`` / ``license_class`` / ``extraction_quality`` are carried through
    from the ledger verbatim so the licensing and provenance context travels with the
    text: M4-3 reads them, it does not re-derive them.
    """

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

    @pydantic.model_validator(mode="after")
    def check_confidence_flag_agrees(self) -> "CorpusRecord":
        if self.low_confidence != (self.confidence == "low"):
            raise ValueError(
                f"low_confidence={self.low_confidence} contradicts confidence={self.confidence!r}"
            )
        return self


class Corpus(StrictModel):
    """The whole ingested corpus: one file for every ledger row in scope.

    One file rather than one-per-``source_id`` because a source_id can appear on the
    ledger more than once (``fmea-vda-2019`` carries two regions), so the file name
    would have to encode ``(source_id, region)`` to stay unique — needless layout for
    the handful of rows in scope.
    """

    envelope: CorpusEnvelope
    records: list[CorpusRecord]
