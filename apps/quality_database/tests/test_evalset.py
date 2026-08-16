"""Gold-set schema + serving-policy enforcement (M4-4, #285)."""

from __future__ import annotations

import pydantic
import pytest
from quality_database_app.evalset import (
    GoldItem,
    GoldSet,
    load_gold_set,
    normalise,
    within_quote_cap,
    write_gold_set,
)
from quality_database_app.schema import IngestionError


def _item(**over: object) -> GoldItem:
    base = dict(
        item_id="i1", domain="msa", tier="coarse", question="q?",
        source_id="msa-4th", region="whole-document", standard="MSA",
        serving_flag="paraphrase-and-point", answerable=True, derived_from="RULE 1",
    )
    base.update(over)
    return GoldItem(**base)  # type: ignore[arg-type]


def test_committed_gold_set_loads_and_covers_every_domain() -> None:
    gold = load_gold_set()
    domains = {i.domain for i in gold.items}
    assert domains == {"msa", "fmea", "spc", "controlplan", "secom"}


def test_expected_excerpt_barred_for_paraphrase_and_point() -> None:
    with pytest.raises(pydantic.ValidationError, match="bars verbatim reproduction"):
        _item(serving_flag="paraphrase-and-point", expected_excerpt="some text")


def test_expected_excerpt_allowed_for_quote_within_cap() -> None:
    ok = _item(serving_flag="quote", expected_excerpt="a short cited phrase")
    assert ok.expected_excerpt == "a short cited phrase"


def test_expected_excerpt_over_cap_rejected() -> None:
    with pytest.raises(pydantic.ValidationError, match="exceeds the quote cap"):
        _item(serving_flag="quote", expected_excerpt=" ".join(["w"] * 51))


def test_page_pinned_requires_a_page() -> None:
    with pytest.raises(pydantic.ValidationError, match="page is null"):
        _item(tier="page-pinned", page=None)


def test_never_ship_cannot_be_answerable() -> None:
    with pytest.raises(pydantic.ValidationError, match="refusal is the only correct"):
        _item(serving_flag="never-ship", answerable=True)
    # the correct shape: never-ship + refusal expected
    assert _item(serving_flag="never-ship", answerable=False).answerable is False


def test_gold_set_rejects_empty_and_duplicate() -> None:
    with pytest.raises(pydantic.ValidationError, match="empty"):
        GoldSet(schema_version=1, items=[])
    with pytest.raises(pydantic.ValidationError, match="duplicate item_id"):
        GoldSet(schema_version=1, items=[_item(item_id="dup"), _item(item_id="dup")])


def test_within_quote_cap_and_normalise() -> None:
    assert within_quote_cap("short phrase")
    assert not within_quote_cap(" ".join(["w"] * 60))
    assert normalise("Under <sup>1</sup> 10%  PERCENT") == "under 1 10 percent"


def test_write_then_load_roundtrips_and_is_deterministic(tmp_path) -> None:
    gs = GoldSet(schema_version=1, items=[_item()])
    p = tmp_path / "g.json"
    write_gold_set(gs, p)
    first = p.read_bytes()
    write_gold_set(gs, p)
    assert p.read_bytes() == first          # byte-identical re-write
    assert load_gold_set(p) == gs


def test_load_errors(tmp_path) -> None:
    with pytest.raises(IngestionError, match="could not be read"):
        load_gold_set(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(IngestionError, match="not valid JSON"):
        load_gold_set(bad)
    shape = tmp_path / "shape.json"
    shape.write_text('{"unexpected": 1}', encoding="utf-8")
    with pytest.raises(IngestionError, match="not a valid gold set"):
        load_gold_set(shape)
    ver = tmp_path / "ver.json"
    write_gold_set(GoldSet(schema_version=1, items=[_item()]), ver)
    ver.write_text(ver.read_text().replace('"schema_version": 1', '"schema_version": 999'))
    with pytest.raises(IngestionError, match="schema_version"):
        load_gold_set(ver)
