"""Corpus ledger integrity — every source is classified, and the classification is coherent (#282, M4-1).

`docs/CORPUS_LEDGER.tsv` is the manifest of every source the M4 knowledge base may draw on;
`docs/CORPUS_LEDGER.md` is the policy it encodes. Copyright is this project's largest
non-technical risk, so "every gathered item carries a serving flag and a rationale" has to be
an assertion, not a promise in prose — a ledger row added later without a flag would otherwise
sail through review.

Shape follows `apps/msa/tests/test_citations.py`: manifest-shape checks that run everywhere
(including CI, which holds no licensed manual), plus corpus-presence-gated checks that
**skip** rather than fail when the private corpus is absent. Point ``CORPUS_ROOT`` at a local
copy of the corpus tree to exercise the gated checks.

The cross-field rules asserted here are exactly the ones the policy states, so the doc and
the data cannot drift apart silently:

- ``quote`` implies a Tier 1 licence class (public standard / public domain).
- ``serve`` implies the row is this project's own derivation.
- ``not-held`` implies there is nothing to serve, and nothing to serve implies ``not-held``.
"""

from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path

import pytest

LEDGER = Path(__file__).resolve().parents[1] / "docs" / "CORPUS_LEDGER.tsv"

CORPUS_ROOT_ENV_VAR = "CORPUS_ROOT"
DEFAULT_CORPUS_ROOT = "/Users/sid/Documents/Upskill/SixSigma"
CORPUS_ROOT = Path(os.environ.get(CORPUS_ROOT_ENV_VAR, DEFAULT_CORPUS_ROOT))

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

# `not-located` = cited by an app log but no copy found; `in-repo` = this project's own
# committed prose. Neither names a file under the corpus root, so both are exempt from the
# presence-gated checks below.
PATH_SENTINELS = frozenset({"not-located", "in-repo"})

FORMATS = frozenset({"md", "pdf", "py", "none"})
STATUSES = frozenset({"cited", "not-yet-cited", "not-held"})
EXTRACTION_QUALITIES = frozenset({"clean", "mangled", "not-extracted", "n/a"})
LICENSE_CLASSES = frozenset(
    {
        "public-domain",
        "public-standard",
        "licensed-commercial",
        "paywalled-journal",
        "third-party-reproduction",
        "project-own-derivation",
        "vendor-marketing",
        "unknown",
    }
)
SERVING_FLAGS = frozenset({"serve", "quote", "paraphrase-and-point", "never-ship", "N/A"})

# Tier 1 of the SME-locked rule: only a public standard may be quoted verbatim.
QUOTABLE_LICENSE_CLASSES = frozenset({"public-domain", "public-standard"})

SUFFIX_BY_FORMAT = {"md": ".md", "pdf": ".pdf", "py": ".py"}


def _resolve(on_machine_path: str) -> Path:
    """Re-root a ledger path under ``$CORPUS_ROOT`` when it points elsewhere.

    The ledger records absolute paths (SME-reviewable as written). Re-rooting is what makes
    ``$CORPUS_ROOT`` do what its skip message promises on a machine that keeps the corpus
    somewhere else, instead of the env var being decorative.
    """
    path = Path(on_machine_path)
    if CORPUS_ROOT != Path(DEFAULT_CORPUS_ROOT) and path.is_relative_to(DEFAULT_CORPUS_ROOT):
        return CORPUS_ROOT / path.relative_to(DEFAULT_CORPUS_ROOT)
    return path


def _load_ledger() -> list[dict[str, str]]:
    with LEDGER.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames is not None, f"{LEDGER} has no header row."
        assert tuple(reader.fieldnames) == COLUMNS, (
            f"{LEDGER} header is {reader.fieldnames}, expected {list(COLUMNS)}."
        )
        return list(reader)


ROWS = _load_ledger()


def _key(row: dict[str, str]) -> str:
    return f"{row['source_id']}/{row['region']}"


def test_ledger_is_populated_and_has_no_duplicate_rows() -> None:
    """Non-empty, and each (source_id, region) pair appears once.

    Runs with or without the corpus — it guards the manifest itself. An empty ledger would
    make every per-row assertion below vacuously pass, and a duplicated key means one source
    region carries two classifications, at most one of which can be the policy's.
    """
    assert ROWS, f"{LEDGER} is empty — every ledger assertion would be vacuous."

    duplicates = [key for key, count in Counter(_key(row) for row in ROWS).items() if count > 1]
    assert not duplicates, f"duplicate (source_id, region) rows in {LEDGER}: {sorted(duplicates)}"


def test_every_row_is_completely_filled_in() -> None:
    """No blank cell anywhere. A blank is an unclassified source pretending to be classified."""
    blanks = [
        f"{_key(row)}: {column}"
        for row in ROWS
        for column in COLUMNS
        if not (row.get(column) or "").strip()
    ]
    assert not blanks, f"blank cells in {LEDGER}:\n  " + "\n  ".join(blanks)


@pytest.mark.parametrize(
    ("column", "allowed"),
    [
        ("format", FORMATS),
        ("status", STATUSES),
        ("extraction_quality", EXTRACTION_QUALITIES),
        ("license_class", LICENSE_CLASSES),
        ("serving_flag", SERVING_FLAGS),
    ],
)
def test_enumerated_columns_hold_only_allowed_values(column: str, allowed: frozenset[str]) -> None:
    """Every enumerated column is a closed vocabulary — catches typos and invented values.

    A misspelled `serving_flag` is the dangerous case: it reads as classified to a human
    skimming the file, but no downstream consumer would honour it.
    """
    offenders = [f"{_key(row)}: {row[column]!r}" for row in ROWS if row[column] not in allowed]
    assert not offenders, (
        f"{LEDGER} column {column!r} has values outside {sorted(allowed)}:\n  "
        + "\n  ".join(offenders)
    )


def test_quote_flag_requires_a_public_licence_class() -> None:
    """`quote` is Tier 1 only — a licensed handbook flagged `quote` is the classification slip
    with real copyright consequence, so it is asserted rather than reviewed for."""
    offenders = [
        f"{_key(row)}: license_class={row['license_class']}"
        for row in ROWS
        if row["serving_flag"] == "quote" and row["license_class"] not in QUOTABLE_LICENSE_CLASSES
    ]
    assert not offenders, (
        "serving_flag 'quote' requires license_class in "
        f"{sorted(QUOTABLE_LICENSE_CLASSES)} (see CORPUS_LEDGER.md, Tier 1):\n  "
        + "\n  ".join(offenders)
    )


def test_serve_flag_requires_project_own_derivation() -> None:
    """`serve` (unlimited reproduction) is Tier 3 only — our own content."""
    offenders = [
        f"{_key(row)}: license_class={row['license_class']}"
        for row in ROWS
        if row["serving_flag"] == "serve" and row["license_class"] != "project-own-derivation"
    ]
    assert not offenders, (
        "serving_flag 'serve' requires license_class 'project-own-derivation' "
        "(see CORPUS_LEDGER.md, Tier 3):\n  " + "\n  ".join(offenders)
    )


def test_not_held_rows_have_nothing_to_serve_and_no_local_path() -> None:
    """`status: not-held` <-> `serving_flag: N/A`, asserted in both directions.

    Forward: a source we do not hold cannot be served, so it must not carry a real flag.
    Reverse: `N/A` must not become a way to leave a *held* source unclassified — that is
    exactly the gap the acceptance criterion ("each item has a serving flag") closes.
    """
    wrong_flag = [
        f"{_key(row)}: status=not-held but serving_flag={row['serving_flag']}"
        for row in ROWS
        if row["status"] == "not-held" and row["serving_flag"] != "N/A"
    ]
    wrong_status = [
        f"{_key(row)}: serving_flag=N/A but status={row['status']}"
        for row in ROWS
        if row["serving_flag"] == "N/A" and row["status"] != "not-held"
    ]
    has_path = [
        f"{_key(row)}: status=not-held but on_machine_path={row['on_machine_path']}"
        for row in ROWS
        if row["status"] == "not-held" and row["on_machine_path"] != "not-located"
    ]
    assert not (wrong_flag + wrong_status + has_path), "\n  ".join(
        ["not-held/N/A inconsistencies in the ledger:", *wrong_flag, *wrong_status, *has_path]
    )


def test_known_extraction_quality_implies_a_text_extraction_exists() -> None:
    """`clean`/`mangled` are claims about an extraction, so the row must name an extractable format.

    `md`/`py` rows carry their text directly. `pdf` rows became extractable with #329's
    `extract_pdf` (text-layer extraction), so a `pdf` may honestly be `clean` once its layer has
    been read and reviewed — as the SME did for the 15 text-layer PDFs in #337. Formats with no
    extraction path (e.g. an image-only scan) still cannot be `clean`; those stay `not-extracted`
    until the SME reads #335's OCR output by hand. This is the structural half of the reality check
    below, and unlike
    that one it runs on CI.
    """
    offenders = [
        f"{_key(row)}: extraction_quality={row['extraction_quality']} format={row['format']}"
        for row in ROWS
        if row["extraction_quality"] in {"clean", "mangled"}
        and row["format"] not in {"md", "py", "pdf"}
    ]
    assert not offenders, (
        "extraction_quality 'clean'/'mangled' requires an extractable format (md/py/pdf):\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "row",
    [row for row in ROWS if row["on_machine_path"] not in PATH_SENTINELS],
    ids=[_key(row) for row in ROWS if row["on_machine_path"] not in PATH_SENTINELS],
)
def test_on_machine_paths_are_consistent_with_reality(row: dict[str, str]) -> None:
    """Where the corpus is present, the recorded path and format must match the disk.

    Skips (never fails) when the file is absent: the corpus is private and CI holds no copy,
    exactly as the MSA/FMEA citation tests skip without their manual.
    """
    path = _resolve(row["on_machine_path"])
    if not path.exists():
        pytest.skip(
            f"{row['on_machine_path']} not present. The corpus is private and is not committed, "
            f"so this row's reality check did NOT run. Set ${CORPUS_ROOT_ENV_VAR} (currently "
            f"{CORPUS_ROOT}) to a local copy of the corpus tree to run it."
        )
    assert path.is_file(), f"{_key(row)}: on_machine_path is not a file."
    assert path.suffix.lower() == SUFFIX_BY_FORMAT[row["format"]], (
        f"{_key(row)}: format={row['format']} but the file on disk is {path.suffix!r}."
    )
