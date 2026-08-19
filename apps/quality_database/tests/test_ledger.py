"""Ledger reader: what may be ingested, and every reason a row is skipped (#283).

The ledger is the SME-reviewed source of truth (#282); this module only reads and
filters it. These tests pin the skip discipline (an unreadable-format / not-held / sentinel-path row
is skipped *observably*), the load-time validation errors, and the ``$CORPUS_ROOT``
re-rooting — none of which touch the private corpus, so all run on CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from quality_database_app.ledger import (
    COLUMNS,
    DEFAULT_CORPUS_ROOT,
    PATH_SENTINELS,
    LedgerRow,
    corpus_root,
    ingestible_rows,
    load_ledger,
    resolve_path,
    skip_reason,
)
from quality_database_app.schema import IngestionError


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "source_id": "fmea-vda-2019",
        "title": "AIAG & VDA FMEA Handbook",
        "edition": "1st Edition (June 2019)",
        "on_machine_path": "/Users/sid/Documents/Upskill/SixSigma/fmea.md",
        "format": "md",
        "region": "DFMEA-severity-and-AP-prose",
        "status": "cited",
        "extraction_quality": "clean",
        "license_class": "licensed-commercial",
        "serving_flag": "paraphrase-and-point",
        "rationale": "synthetic fixture",
        "cited_by": "none",
    }
    row.update(overrides)
    return row


def _write_ledger(path: Path, rows: list[dict[str, str]], header: tuple[str, ...] = COLUMNS) -> Path:
    lines = ["\t".join(header)] + ["\t".join(row[column] for column in COLUMNS) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# --- load_ledger -------------------------------------------------------------


def test_load_ledger_reads_valid_rows(tmp_path):
    ledger = _write_ledger(tmp_path / "ledger.tsv", [_row(), _row(region="other")])
    rows = load_ledger(ledger)
    assert [r.region for r in rows] == ["DFMEA-severity-and-AP-prose", "other"]
    assert rows[0].key == "fmea-vda-2019/DFMEA-severity-and-AP-prose"


def test_load_ledger_rejects_a_wrong_header(tmp_path):
    bad = (*COLUMNS[:-1], "renamed_last_column")
    ledger = _write_ledger(tmp_path / "ledger.tsv", [_row()], header=bad)
    with pytest.raises(IngestionError, match="header is"):
        load_ledger(ledger)


def test_load_ledger_rejects_a_missing_file(tmp_path):
    with pytest.raises(IngestionError, match="could not be read"):
        load_ledger(tmp_path / "does-not-exist.tsv")


def test_load_ledger_rejects_a_row_with_a_blank_cell(tmp_path):
    # StrictModel rejects blank strings, so a blank cell fails row validation.
    ledger = _write_ledger(tmp_path / "ledger.tsv", [_row(rationale="   ")])
    with pytest.raises(IngestionError, match="invalid row"):
        load_ledger(ledger)


# --- skip_reason / ingestible_rows -------------------------------------------


def test_skip_reason_is_none_for_an_ingestible_row():
    assert skip_reason(LedgerRow.model_validate(_row())) is None


def test_skip_reason_is_none_for_a_pdf_row():
    # #329 made pdf ingestible; a pdf row with no text layer is skipped later, by run().
    assert skip_reason(LedgerRow.model_validate(_row(format="pdf"))) is None


def test_skip_reason_flags_a_format_with_no_reader():
    reason = skip_reason(LedgerRow.model_validate(_row(format="docx")))
    assert reason is not None and "no reader for it" in reason


def test_skip_reason_flags_a_not_held_row():
    reason = skip_reason(LedgerRow.model_validate(_row(status="not-held")))
    assert reason == "status='not-held' — no copy to read"


@pytest.mark.parametrize("sentinel", sorted(PATH_SENTINELS))
def test_skip_reason_flags_a_sentinel_path(sentinel):
    reason = skip_reason(LedgerRow.model_validate(_row(on_machine_path=sentinel)))
    assert reason is not None and "no file under the corpus root" in reason


def test_ingestible_rows_keeps_only_ingestible_rows_in_order():
    rows = [
        LedgerRow.model_validate(_row(region="a")),
        LedgerRow.model_validate(_row(region="b", format="docx")),
        LedgerRow.model_validate(_row(region="c", status="not-held", serving_flag="N/A")),
        LedgerRow.model_validate(_row(region="d")),
    ]
    assert [r.region for r in ingestible_rows(rows)] == ["a", "d"]


# --- corpus_root / resolve_path ----------------------------------------------


def test_corpus_root_defaults_and_honours_the_env_var(monkeypatch):
    monkeypatch.delenv("CORPUS_ROOT", raising=False)
    assert corpus_root() == DEFAULT_CORPUS_ROOT
    monkeypatch.setenv("CORPUS_ROOT", "/elsewhere/corpus")
    assert corpus_root() == Path("/elsewhere/corpus")


def test_resolve_path_rerootsa_default_rooted_path_under_a_custom_root():
    resolved = resolve_path(str(DEFAULT_CORPUS_ROOT / "fmea.md"), Path("/elsewhere"))
    assert resolved == Path("/elsewhere/fmea.md")


def test_resolve_path_leaves_a_path_untouched_when_root_is_default():
    original = str(DEFAULT_CORPUS_ROOT / "fmea.md")
    assert resolve_path(original, DEFAULT_CORPUS_ROOT) == Path(original)


def test_resolve_path_leaves_an_out_of_tree_path_untouched():
    # Custom root, but the path is not under the default root: nothing to re-root.
    assert resolve_path("/somewhere/else/fmea.md", Path("/elsewhere")) == Path(
        "/somewhere/else/fmea.md"
    )
