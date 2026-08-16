"""Schema unit coverage (M4-2, #283): confidence mapping + the agreement invariant."""

from __future__ import annotations

import pydantic
import pytest
from quality_database_app.schema import CorpusRecord, confidence_for


def test_confidence_for_only_clean_is_high() -> None:
    assert confidence_for("clean") == "high"
    for bad in ("mangled", "not-extracted", "n/a", "anything-else"):
        assert confidence_for(bad) == "low"


def _record(**overrides: object) -> CorpusRecord:
    base = dict(
        source_id="s", region="r", standard="Std", text="t",
        confidence="high", low_confidence=False,
        extraction_quality="clean", serving_flag="quote", license_class="public-standard",
    )
    base.update(overrides)
    return CorpusRecord(**base)  # type: ignore[arg-type]


def test_low_confidence_flag_must_agree_with_confidence() -> None:
    # high + low_confidence=False is fine; low + True is fine.
    assert _record().confidence == "high"
    assert _record(confidence="low", low_confidence=True).low_confidence is True


def test_contradictory_flag_is_rejected() -> None:
    # confidence='high' but low_confidence=True must raise (schema.py check_confidence_flag_agrees).
    with pytest.raises(pydantic.ValidationError, match="contradicts"):
        _record(confidence="high", low_confidence=True)
    with pytest.raises(pydantic.ValidationError, match="contradicts"):
        _record(confidence="low", low_confidence=False)
