"""Citation integrity for the FMEA docs — every AIAG & VDA quotation is real and located (#197).

`apps/fmea/docs/ASSUMPTIONS_LOG.md` is the artifact the FMEA domain-correctness argument
rests on. It carried, for months, a quotation-shaped claim attributed to an "AIAG FMEA 5th
Edition" — a document that does not exist — asserting that Severity 9-10 requires action
independent of Occurrence and Detection. The handbook's own Table AP says the opposite
(S 9-10 / O 1 is Low). A misattributed claim is worse than a wrong number: a wrong number is
falsifiable by recomputation, a citation looks like verified evidence and every downstream
decision inherits unearned confidence.

`apps/fmea/docs/CITATIONS.tsv` is the manifest — one row per quotation that survives in the
log or in FMEA docs, recording the line of the primary handbook it came from. This module
re-asserts every row against that handbook. It is a deliberate copy of the MSA precedent
(`apps/msa/tests/test_citations.py`, #223); the two apps cite different manuals, so the
shared part is the technique, not code worth hoisting into `quality_core`.

The check pins the **line number** (+/-2 for wrapping), not mere substring presence. A
substring test would pass for a quote lifted from the wrong chapter; a line-pinned test is
a citation index, which is what a reader auditing the log actually needs.

The handbook is licensed and is NOT in the repo, so these tests **skip** (never fail) when
it is absent — CI has no copy. Point ``FMEA_HANDBOOK_PATH`` at a local copy to run them.

Matching is formatting-tolerant by necessity: the markdown renders emphasis inline, so the
genuine passage at line 3031 is wrapped in ``**``. A naive substring search reports that
real quotation as fabricated — a false "fabricated" verdict is the same sin as a fabricated
quote, in the opposite direction. `_normalise` removes that whole class of false negative
before matching.

Scope note: the handbook's PFMEA Occurrence/Detection tables and Table AP's band-label cells
are OCR cell-merge-mangled in the available conversion (``Hih``/``g``, ``Mdt``/``oerae``).
Nothing is quoted from them here, deliberately — a manifest row built from a mangled cell
would read as fabricated. Only clean body prose is cited.
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from pathlib import Path

import pytest

HANDBOOK_ENV_VAR = "FMEA_HANDBOOK_PATH"
DEFAULT_HANDBOOK = (
    "/Users/sid/Documents/Upskill/SixSigma/"
    "pdfcoffee.com_aiag-vda-fmea-handbook-1-version-juni-2019-englisch-pdf-free.md"
)
HANDBOOK = Path(os.environ.get(HANDBOOK_ENV_VAR, DEFAULT_HANDBOOK))

MANIFEST = Path(__file__).resolve().parents[1] / "docs" / "CITATIONS.tsv"

# How far the located line may drift from the recorded one. The handbook is one paragraph
# per line, but a quote spanning a paragraph break lands on the line where it *starts*.
LINE_TOLERANCE = 2

_HTML_TAG = re.compile(r"<[^>]+>")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def _normalise(text: str) -> str:
    """Reduce text to lowercase alphanumeric words separated by single spaces.

    Everything that differs between the handbook's markdown and a quotation copied out of
    it is discarded: NFKC folds compatibility forms; soft hyphens and zero-width spaces are
    dropped; HTML tags (``<br>``, ``<sup>``) become whitespace; and every remaining
    non-alphanumeric character — markdown emphasis, curly vs straight quotes, en/em dashes,
    non-breaking spaces, punctuation — collapses to a single space.

    This is deliberately lossy. It cannot tell ``9-10`` from ``9 10``, so a manifest quote
    must carry enough *words* to be distinctive; symbols alone will not do.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("­", "").replace("​", "")
    text = _HTML_TAG.sub(" ", text)
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def _load_manifest() -> list[tuple[str, int, str]]:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [(r["site"], int(r["src_line"]), r["quote"]) for r in reader]


MANIFEST_ROWS = _load_manifest()


def _flatten_handbook() -> tuple[str, list[int]]:
    """Normalise the handbook into one searchable string plus a char-index -> line map.

    Flattening is what makes the search wrap-tolerant: a quotation broken across source
    lines is contiguous here. The parallel `owners` list is what keeps it a *citation* check
    rather than a substring check — it turns a match offset back into a source line.
    """
    raw_lines = HANDBOOK.read_text(encoding="utf-8").splitlines()
    chunks: list[str] = []
    owners: list[int] = []
    for line_number, raw in enumerate(raw_lines, start=1):
        normalised = _normalise(raw)
        if not normalised:
            continue
        chunks.append(normalised)
        # +1 for the space `" ".join` will insert after this chunk, so every character of
        # the joined string (and the separator that follows it) maps back to this line.
        owners.extend([line_number] * (len(normalised) + 1))
    return " ".join(chunks), owners


@pytest.fixture(scope="module")
def handbook() -> tuple[str, list[int]]:
    if not HANDBOOK.exists():
        pytest.skip(
            f"AIAG & VDA FMEA Handbook (1st Ed., 2019) not found at {HANDBOOK}. It is "
            f"licensed and is not committed to this repo, so the citation check did NOT "
            f"run. Set ${HANDBOOK_ENV_VAR} to a local copy to run it."
        )
    return _flatten_handbook()


def _located_lines(flat: str, owners: list[int], quote: str) -> list[int]:
    """Every source line at which `quote` occurs in the flattened handbook."""
    needle = _normalise(quote)
    assert needle, "manifest quote normalises to nothing"
    lines: list[int] = []
    start = flat.find(needle)
    while start >= 0:
        lines.append(owners[start])
        start = flat.find(needle, start + 1)
    return lines


@pytest.mark.parametrize(
    ("site", "src_line", "quote"),
    MANIFEST_ROWS,
    ids=[f"{site}:{src_line}" for site, src_line, _ in MANIFEST_ROWS],
)
def test_citation_is_verbatim_in_the_primary_source(
    site: str, src_line: int, quote: str, handbook: tuple[str, list[int]]
) -> None:
    """Each manifest quote occurs in the handbook AND at the line the manifest records.

    Two distinct failures, reported distinctly: a quote that is nowhere in the handbook is
    fabricated (or misquoted); a quote that is present but at a different line has a wrong
    locator — the reader is sent to a passage that does not say what the log claims.
    """
    flat, owners = handbook
    found_at = _located_lines(flat, owners, quote)

    assert found_at, (
        f"{site}: quotation NOT FOUND in the primary source under formatting-tolerant "
        f"search. Either it is fabricated or it is misquoted. Quote: {quote!r}"
    )
    assert any(abs(line - src_line) <= LINE_TOLERANCE for line in found_at), (
        f"{site}: quotation found at line(s) {found_at} but the manifest records "
        f"{src_line} (tolerance +/-{LINE_TOLERANCE}). The locator is wrong. Quote: {quote!r}"
    )


def test_manifest_is_populated_and_has_no_duplicate_rows() -> None:
    """The manifest must be non-empty and each (site, quote) pair recorded once.

    Runs with or without the handbook: it guards the manifest itself. Emptiness would make
    every citation assertion above vacuously pass, and a duplicated pair means one site
    carries the same quote with two line numbers — at most one of which can be right.
    """
    assert MANIFEST_ROWS, f"{MANIFEST} is empty — the citation check would be vacuous."

    pairs = [(site, _normalise(quote)) for site, _, quote in MANIFEST_ROWS]
    duplicates = {pair for pair in pairs if pairs.count(pair) > 1}
    assert not duplicates, f"duplicate (site, quote) rows in {MANIFEST}: {sorted(duplicates)}"


_ASSUMPTIONS_LOG = Path(__file__).resolve().parents[1] / "docs" / "ASSUMPTIONS_LOG.md"


def _blockquote_blocks(markdown: str) -> list[tuple[int, str]]:
    """Return (first_line_number, text) for each contiguous `> ` blockquote block.

    Fenced blocks are skipped: the convention (inherited from the MSA log) is that a fenced
    block holds a *withdrawn* citation, preserved verbatim as evidence of what was removed.
    Those must NOT be treated as live citations — that is the whole point of fencing them.
    """
    blocks: list[tuple[int, str]] = []
    current: list[str] = []
    start = 0
    fenced = False
    for number, raw in enumerate(markdown.splitlines(), start=1):
        if raw.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if raw.lstrip().startswith(">"):
            if not current:
                start = number
            current.append(raw.lstrip().lstrip("> ").rstrip())
        elif current:
            blocks.append((start, " ".join(current)))
            current = []
    if current:
        blocks.append((start, " ".join(current)))
    return blocks


def test_every_live_quotation_in_the_log_has_a_manifest_row() -> None:
    """No quotation may exist in the log without a manifest row backing it (#197).

    The per-row test above proves *every row the manifest contains is real*. It cannot
    prove *the log contains no quotation outside the manifest* — so a blockquote added
    later, citing nothing, would pass every other check. This closes that direction, and it
    is the reason the log must not use `>` for editorial callouts: in this file a
    blockquote means "primary source", nothing else.

    Runs with or without the handbook, so it is the one substantive citation check that
    executes on CI, where the licensed handbook is absent.
    """
    rows = [_normalise(quote) for _, _, quote in MANIFEST_ROWS]

    def backed(block: str) -> bool:
        # Either direction counts: the manifest may hold a shorter excerpt of a long
        # blockquote, or a long quote may be split across rows, in which case each row
        # sits inside the block.
        return any(row and (row in block or block in row) for row in rows)

    unbacked = [
        (line, text)
        for line, text in _blockquote_blocks(_ASSUMPTIONS_LOG.read_text(encoding="utf-8"))
        if _normalise(text) and not backed(_normalise(text))
    ]
    assert not unbacked, (
        "quotation(s) in ASSUMPTIONS_LOG.md with no row in CITATIONS.tsv — either add a "
        "verified manifest row, or fence the block to mark it withdrawn:\n"
        + "\n".join(f"  ASSUMPTIONS_LOG.md:{line}: {text[:100]!r}" for line, text in unbacked)
    )
