"""Pipeline coverage + acceptance (M4-2 #283, PDF sources M4-2b #329), on synthetic tmp
fixtures only (CI-safe).

Covers run()'s skip/OSError paths and the full load_records() error surface, and encodes
the acceptance criteria: byte-identical re-run, mangled -> flagged (never trusted),
clean -> trusted, unreadable-format rows skipped-and-logged, serving_flag + locator
carried through, and (#329) a text-layer PDF extracted with real page numbers but still
low-confidence, while an image-only one is skipped-and-logged rather than vanishing.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from quality_database_app.ledger import COLUMNS
from quality_database_app.pipeline import load_records, run
from quality_database_app.schema import (
    SCHEMA_VERSION,
    Corpus,
    CorpusEnvelope,
    CorpusRecord,
    IngestionError,
)


def _row(**over: str) -> dict[str, str]:
    base = dict(
        source_id="demo", title="Demo Std", edition="1st", on_machine_path="x.md",
        format="md", region="whole-document", status="cited",
        extraction_quality="clean", license_class="licensed-commercial",
        serving_flag="paraphrase-and-point", rationale="illustrative", cited_by="none",
    )
    base.update(over)
    return base


def _write_ledger(path: Path, rows: list[dict[str, str]]) -> None:
    lines = ["\t".join(COLUMNS)] + ["\t".join(r[c] for c in COLUMNS) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path, synthetic_pdf) -> tuple[Path, Path]:
    (tmp_path / "clean.md").write_text("# Intro\nHello world\n\n# Body\nmore\n", encoding="utf-8")
    (tmp_path / "mangled.md").write_text("# Tbl\nHih g Mdt oerae\n", encoding="utf-8")
    (tmp_path / "text.pdf").write_bytes(synthetic_pdf(["Page one text", "Page two text"]))
    (tmp_path / "scan.pdf").write_bytes(synthetic_pdf(["", ""]))
    ledger = tmp_path / "CORPUS_LEDGER.tsv"
    _write_ledger(ledger, [
        _row(source_id="demo-clean", on_machine_path=str(tmp_path / "clean.md"),
             extraction_quality="clean", serving_flag="paraphrase-and-point"),
        _row(source_id="demo-mangled", on_machine_path=str(tmp_path / "mangled.md"),
             extraction_quality="mangled", serving_flag="never-ship"),
        # #329: a text-layer PDF, still `not-extracted` in the ledger (never auto-flipped),
        # and `never-ship` — extracted and flagged, never silently dropped.
        _row(source_id="demo-pdf", on_machine_path=str(tmp_path / "text.pdf"), format="pdf",
             extraction_quality="not-extracted", serving_flag="never-ship"),
        # An image-only scan: readable, but no text layer — skipped and logged (#335).
        _row(source_id="demo-pdf-scan", on_machine_path=str(tmp_path / "scan.pdf"),
             format="pdf", extraction_quality="not-extracted"),
        _row(source_id="demo-docx", on_machine_path=str(tmp_path / "x.docx"), format="docx"),
        _row(source_id="demo-missing", on_machine_path=str(tmp_path / "gone.md")),
    ])
    return ledger, tmp_path / "out" / "corpus.json"


def test_run_ingests_md_flags_mangled_and_skips_the_rest(tmp_path: Path, synthetic_pdf, caplog) -> None:
    ledger, out = _fixture(tmp_path, synthetic_pdf)
    with caplog.at_level(logging.INFO):
        corpus = run(ledger_path=ledger, root=tmp_path, out_path=out)

    by_source = {r.source_id for r in corpus.records}
    # docx, the image-only scan and the missing file are excluded; the text PDF is not
    assert by_source == {"demo-clean", "demo-mangled", "demo-pdf"}

    clean = [r for r in corpus.records if r.source_id == "demo-clean"]
    mangled = [r for r in corpus.records if r.source_id == "demo-mangled"]
    # clean -> trusted; mangled -> flagged, never silently trusted (the #256 guard)
    assert all(r.confidence == "high" and r.low_confidence is False for r in clean)
    assert all(r.confidence == "low" and r.low_confidence is True for r in mangled)
    # OCR damage survives verbatim, and the never-ship flag + locator are carried through
    assert "Hih g Mdt oerae" in mangled[0].text
    assert mangled[0].serving_flag == "never-ship"
    assert clean[0].standard == "Demo Std" and clean[0].clause == "Intro"

    text = caplog.text
    assert "demo-docx" in text and "no reader for it" in text  # format skip logged
    assert "demo-missing" in text and "could not be read" in text  # OSError skip logged (run 90-94)
    # the image-only row is skipped *observably*, pointing at the OCR follow-up
    assert "demo-pdf-scan" in text and "no text" in text and "#335" in text


def test_pdf_rows_are_extracted_with_pages_and_stay_flagged(tmp_path: Path, synthetic_pdf) -> None:
    ledger, out = _fixture(tmp_path, synthetic_pdf)
    corpus = run(ledger_path=ledger, root=tmp_path, out_path=out)

    pdf = [r for r in corpus.records if r.source_id == "demo-pdf"]
    assert [r.page for r in pdf] == [1, 2]                       # real page numbers
    assert all(r.clause is None for r in pdf)                    # no heading structure
    assert "Page one text" in pdf[0].text
    # extraction_quality is never auto-flipped, so every PDF record stays low-confidence
    assert all(r.extraction_quality == "not-extracted" for r in pdf)
    assert all(r.confidence == "low" and r.low_confidence is True for r in pdf)
    # never-ship is extracted and flagged, never silently dropped (RULE 11)
    assert all(r.serving_flag == "never-ship" for r in pdf)


def test_rerun_is_byte_identical(tmp_path: Path, synthetic_pdf) -> None:
    ledger, out = _fixture(tmp_path, synthetic_pdf)
    run(ledger_path=ledger, root=tmp_path, out_path=out)
    first = out.read_bytes()
    run(ledger_path=ledger, root=tmp_path, out_path=out)
    assert out.read_bytes() == first          # determinism / no wall-clock content


def test_write_then_load_roundtrips(tmp_path: Path, synthetic_pdf) -> None:
    ledger, out = _fixture(tmp_path, synthetic_pdf)
    written = run(ledger_path=ledger, root=tmp_path, out_path=out)
    assert load_records(out) == written


def _valid_corpus() -> Corpus:
    return Corpus(
        envelope=CorpusEnvelope(schema_version=SCHEMA_VERSION, generated_by="test"),
        records=[CorpusRecord(
            source_id="s", region="r", standard="S", text="t", confidence="high",
            low_confidence=False, extraction_quality="clean", serving_flag="quote",
            license_class="public-standard",
        )],
    )


def test_load_records_missing_file(tmp_path: Path) -> None:
    with pytest.raises(IngestionError, match="could not be read"):
        load_records(tmp_path / "nope.json")


def test_load_records_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(IngestionError, match="not valid JSON"):
        load_records(p)


def test_load_records_wrong_shape(tmp_path: Path) -> None:
    p = tmp_path / "shape.json"
    p.write_text(json.dumps({"unexpected": 1}), encoding="utf-8")
    with pytest.raises(IngestionError, match="not a valid Corpus"):
        load_records(p)


def test_load_records_schema_version_mismatch(tmp_path: Path) -> None:
    corpus = _valid_corpus()
    payload = corpus.model_dump(mode="json")
    payload["envelope"]["schema_version"] = SCHEMA_VERSION + 999
    p = tmp_path / "ver.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(IngestionError, match="schema_version"):
        load_records(p)
