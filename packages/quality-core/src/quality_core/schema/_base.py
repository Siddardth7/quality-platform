"""
_base.py
Shared building blocks for the FMEA schema models: a strict base that strips and
rejects blank strings, and a generic duplicate finder. Kept in one place so the
flat (`fmea`) and relational (`relational`) models can't drift on either rule.
"""
from __future__ import annotations

from collections.abc import Hashable, Iterable
from typing import TypeVar

import pydantic

T = TypeVar("T", bound=Hashable)


class StrictModel(pydantic.BaseModel):
    """Strict-typed model that strips strings and rejects blank/whitespace ones."""

    model_config = pydantic.ConfigDict(strict=True)

    @pydantic.field_validator("*", mode="before")
    @classmethod
    def reject_blank(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            raise ValueError("field must not be blank or whitespace-only")
        return v.strip() if isinstance(v, str) else v


def find_duplicates(items: Iterable[T]) -> list[T]:
    """Return the items that appear more than once, in order of first repeat."""
    seen: set[T] = set()
    dupes: list[T] = []
    for item in items:
        if item in seen:
            dupes.append(item)
        else:
            seen.add(item)
    return dupes
