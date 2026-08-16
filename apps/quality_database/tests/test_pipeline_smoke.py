"""Acceptance smoke test for the ingestion pipeline (#283).

Synthetic fixtures only — no licensed corpus — so this runs on CI. It covers the four
acceptance behaviours in one pass: a clean row is trusted, the mangled row is flagged
(not dropped), a non-`md` row is skipped and logged, and a re-run is byte-identical.
The full per-module suite is the tester's.
"""

import hashlib
import logging
from pathlib import Path

from quality_database_app.ledger import COLUMNS
from quality_database_app.pipeline import run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "source_id": "fmea-vda-2019",
        "title": "AIAG & VDA FMEA Handbook",
        "edition": "1st Edition (June 2019)",
        "on_machine_path": str(FIXTURES / "clean_source.md"),
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


def _write_ledger(path: Path, rows: list[dict[str, str]]) -> Path:
    lines = ["\t".join(COLUMNS)] + ["\t".join(row[column] for column in COLUMNS) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_pipeline_flags_mangled_skips_pdf_and_is_deterministic(tmp_path, caplog):
    ledger = _write_ledger(
        tmp_path / "ledger.tsv",
        [
            _row(),
            _row(
                region="PFMEA-O-D-tables-and-AP-band-labels",
                on_machine_path=str(FIXTURES / "mangled_source.md"),
                extraction_quality="mangled",
                serving_flag="never-ship",
            ),
            _row(
                source_id="aiag-spc-2nd",
                region="whole-document",
                on_machine_path="/nowhere/spc.pdf",
                format="pdf",
                extraction_quality="not-extracted",
            ),
        ],
    )
    out = tmp_path / "out" / "corpus.json"

    with caplog.at_level(logging.INFO):
        corpus = run(ledger_path=ledger, root=tmp_path, out_path=out)

    clean = [record for record in corpus.records if record.extraction_quality == "clean"]
    mangled = [record for record in corpus.records if record.extraction_quality == "mangled"]

    assert clean and all(r.confidence == "high" and not r.low_confidence for r in clean)
    assert mangled and all(r.confidence == "low" and r.low_confidence for r in mangled)
    assert all(r.serving_flag == "never-ship" for r in mangled)
    # Format-only cleaning: the OCR damage survives verbatim, it is never repaired.
    assert "Hih<br>g" in mangled[0].text
    # Page footer and clause metadata are carried.
    assert [(r.clause, r.page) for r in clean] == [
        (None, 1),
        ("Chapter One", 1),
        ("Section A", 2),
    ]
    # A non-md row is skipped, and the skip is observable.
    assert not [r for r in corpus.records if r.source_id == "aiag-spc-2nd"]
    assert "skipping aiag-spc-2nd/whole-document" in caplog.text

    first = hashlib.sha256(out.read_bytes()).hexdigest()
    run(ledger_path=ledger, root=tmp_path, out_path=out)
    assert hashlib.sha256(out.read_bytes()).hexdigest() == first
