"""The committed citation eval set: schema, loader, and the serving policy it enforces
(M4-4, #285).

A **gold item** is a question plus the *locator* its answer must cite —
``source_id`` / ``region`` / ``standard`` and, where it could be derived, ``clause``
and ``page``. It is deliberately not "a question plus the right answer text": for the
licensed sources this platform actually cites, the right answer text is exactly what a
generated answer may not reproduce.

**Two tiers** (SME-locked, 2026-08-15, #285 — ASSUMPTIONS_LOG RULE 13):

- ``page-pinned`` — MSA and FMEA items, derived by ``build_gold_set.py`` from that
  app's ``docs/CITATIONS.tsv`` against the on-machine manual. Verified down to
  ``page`` (and ``chunk_id`` where the corpus index resolved one).
- ``coarse`` — SPC / Control Plan / SECOM items, hand-authored against the
  ``docs/CORPUS_LEDGER.tsv`` rows those apps' ``ASSUMPTIONS_LOG.md`` already cites.
  Those sources have no ``CITATIONS.tsv`` manifest and are not extracted, so there is
  no page to pin honestly; they are verified at ``(source_id, region)`` granularity.

The tier is recorded on the item rather than inferred from the domain, so a report can
segment by it and nobody reads a coarse item as page-verified.

**The serving policy is enforced here, not left to the scorer** (SME-locked, #285 Q4):
``expected_excerpt`` may only be set for a ``quote``/``serve`` tier source, and only
within ``docs/CORPUS_LEDGER.md``'s cap (<=50 words, <=2 sentences). A
``paraphrase-and-point`` item therefore *cannot* carry verbatim text at all — the
scorer has nothing to reward reproduction against, by construction.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Literal

import pydantic
from quality_core.schema._base import StrictModel, find_duplicates

from quality_database_app.chunk import Chunk
from quality_database_app.schema import IngestionError

GOLD_SET_SCHEMA_VERSION = 1

DEFAULT_GOLD_SET_PATH = Path(__file__).resolve().parents[1] / "docs" / "eval" / "gold_set.json"

Tier = Literal["page-pinned", "coarse"]

#: Serving flags whose text may appear verbatim in a generated answer at all.
#: ``docs/CORPUS_LEDGER.md`` "Serving flags": ``serve`` is unrestricted, ``quote`` is
#: capped, ``paraphrase-and-point`` bars "any verbatim excerpt, however short", and
#: ``never-ship`` bars citing the source at all.
QUOTABLE_FLAGS = frozenset({"quote", "serve"})

#: ``docs/CORPUS_LEDGER.md`` "The quote cap" — this project's own serving policy
#: (SME-ratified 2026-08-15), not an AIAG/ISO constant.
MAX_QUOTE_WORDS = 50
MAX_QUOTE_SENTENCES = 2

_SENTENCE_END = re.compile(r"[.!?]+(?:\s|$)")
_HTML_TAG = re.compile(r"<[^>]+>")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def normalise(text: str) -> str:
    """Reduce text to lowercase alphanumeric words separated by single spaces.

    A deliberate port of ``apps/msa/tests/test_citations.py::_normalise`` — the
    workspace's import rule is downward only (``apps`` never import each other, and
    nothing imports another app's *test* module), so the function cannot be shared by
    import. Its behaviour, and its reason for existing, must not drift: a naive
    substring match against Markdown reports a *genuine* quotation as fabricated, and a
    false fabrication verdict is as serious as a real fabrication (CLAUDE.md,
    "Standards fidelity").

    NFKC folds compatibility forms; soft hyphens and zero-width spaces are dropped;
    HTML tags (``<br>``, ``<sup>``) become whitespace; every remaining non-alphanumeric
    character collapses to a single space. Lossy by design: it cannot tell ``>= 5``
    from ``5``, so a matched excerpt must carry enough *words* to be distinctive.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("­", "").replace("​", "")
    text = _HTML_TAG.sub(" ", text)
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def within_quote_cap(text: str) -> bool:
    """Whether ``text`` fits ``docs/CORPUS_LEDGER.md``'s <=50 words / <=2 sentences cap."""
    words = len(text.split())
    sentences = len([piece for piece in _SENTENCE_END.split(text) if piece.strip()])
    return words <= MAX_QUOTE_WORDS and sentences <= MAX_QUOTE_SENTENCES


class GoldItem(StrictModel):
    """One eval question and the locator a correct answer must cite."""

    item_id: str
    domain: Literal["msa", "fmea", "spc", "controlplan", "secom"]
    tier: Tier
    question: str
    source_id: str
    region: str
    standard: str
    clause: str | None = None
    page: int | None = None
    #: ``None`` where no index-derived match exists — coarse items and any page-pinned
    #: row whose quote spans a chunk boundary. Relevance then degrades to
    #: ``(source_id, region)``; see :func:`is_relevant`.
    expected_chunk_id: str | None = None
    #: Copied verbatim from the ledger row, never re-derived.
    serving_flag: str
    expected_excerpt: str | None = None
    #: ``False`` = the correct behaviour is a refusal (a ``never-ship`` source).
    answerable: bool
    derived_from: str

    @pydantic.model_validator(mode="after")
    def check_serving_policy(self) -> "GoldItem":
        """No verbatim text may be stored for a source that may not be reproduced."""
        if self.expected_excerpt is None:
            return self
        if self.serving_flag not in QUOTABLE_FLAGS:
            raise ValueError(
                f"{self.item_id}: expected_excerpt is set for serving_flag "
                f"{self.serving_flag!r}, which bars verbatim reproduction "
                f"(docs/CORPUS_LEDGER.md 'Serving flags')."
            )
        if not within_quote_cap(self.expected_excerpt):
            raise ValueError(
                f"{self.item_id}: expected_excerpt exceeds the quote cap "
                f"({MAX_QUOTE_WORDS} words / {MAX_QUOTE_SENTENCES} sentences)."
            )
        return self

    @pydantic.model_validator(mode="after")
    def check_tier_evidence(self) -> "GoldItem":
        """A ``page-pinned`` item must actually carry the page it claims to pin."""
        if self.tier == "page-pinned" and self.page is None:
            raise ValueError(f"{self.item_id}: tier 'page-pinned' but page is null.")
        return self

    @pydantic.model_validator(mode="after")
    def check_never_ship_is_unanswerable(self) -> "GoldItem":
        """A ``never-ship`` source may not be cited at all, so it cannot be answerable."""
        if self.serving_flag == "never-ship" and self.answerable:
            raise ValueError(
                f"{self.item_id}: serving_flag 'never-ship' but answerable=True — a "
                f"never-ship source may not be cited or paraphrased in any user-facing "
                f"output, so refusal is the only correct behaviour."
            )
        return self


class GoldSet(StrictModel):
    """The whole committed eval set."""

    schema_version: int
    items: list[GoldItem]

    @pydantic.model_validator(mode="after")
    def check_populated_and_unique(self) -> "GoldSet":
        """An empty or duplicated set would make every downstream score vacuous.

        Same posture as ``test_citations.py``'s
        ``test_manifest_is_populated_and_has_no_duplicate_rows``: an empty manifest is
        a FINDING, not a pass.
        """
        if not self.items:
            raise ValueError("gold set is empty — every eval score would be vacuous.")
        duplicates = find_duplicates(item.item_id for item in self.items)
        if duplicates:
            raise ValueError(f"duplicate item_id(s) in the gold set: {sorted(duplicates)}")
        return self


def is_relevant(item: GoldItem, chunk: Chunk) -> bool:
    """Whether ``chunk`` is the ground truth for ``item``.

    The single relevance comparison for the whole eval — the two tiers differ only
    here, so no metric function carries a tier branch. A page-pinned item that resolved
    a ``chunk_id`` is matched exactly; everything else falls back to the
    ``(source_id, region)`` granularity its ground truth actually supports.
    """
    if item.expected_chunk_id is not None:
        return chunk.chunk_id == item.expected_chunk_id
    return chunk.source_id == item.source_id and chunk.region == item.region


def load_gold_set(path: Path = DEFAULT_GOLD_SET_PATH) -> GoldSet:
    """Read and validate the committed gold set."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise IngestionError(f"'{path}' could not be read: {exc}.") from exc
    except ValueError as exc:
        raise IngestionError(f"'{path}' is not valid JSON: {exc}.") from exc
    try:
        gold_set = GoldSet.model_validate(payload)
    except pydantic.ValidationError as exc:
        raise IngestionError(f"'{path}' is not a valid gold set: {exc}.") from exc
    if gold_set.schema_version != GOLD_SET_SCHEMA_VERSION:
        raise IngestionError(
            f"'{path}' has schema_version {gold_set.schema_version}, "
            f"expected {GOLD_SET_SCHEMA_VERSION}."
        )
    return gold_set


def write_gold_set(gold_set: GoldSet, path: Path = DEFAULT_GOLD_SET_PATH) -> None:
    """Write the gold set deterministically: pretty JSON, no wall-clock content.

    Same discipline as ``pipeline.write_records`` and ``VectorStore.save`` — a re-run
    over unchanged inputs rewrites a byte-identical file (ASSUMPTIONS_LOG RULE 7).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = gold_set.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
