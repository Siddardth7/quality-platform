"""The embedding seam (M4-3, #284).

:class:`Embedder` is the only embedding surface ``chunk.py`` / ``index.py`` /
``store.py`` know about. Swapping in a real model must never touch them.

:class:`FakeEmbedder` is the **only embedder CI runs** (SME-locked, #284): it is
deterministic, offline, and needs no model download, so the whole index -> search path
is exercised on CI without a network or a multi-gigabyte wheel. A real local model
lives in ``embed_fastembed.py`` behind the optional ``embed`` dependency group and is
never imported by the CI path.

The vectors are hash-derived, so they carry **no semantic similarity** — near-duplicate
texts get unrelated vectors. That is deliberate: these tests assert the plumbing
(metadata survives, filters apply, results are ordered and deterministic), not
retrieval quality, which is M4-4's eval harness.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

#: sha256 emits exactly 32 bytes, one per dimension — the digest size *is* the width.
FAKE_DIMENSION = 32


class Embedder(Protocol):
    """Anything that turns texts into equal-length vectors."""

    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed ``texts``, returning one vector per input, in input order."""


def _fake_vector(text: str) -> list[float]:
    """A deterministic unit vector for ``text``: sha256 bytes centred and normalized."""
    raw = [byte / 255.0 - 0.5 for byte in hashlib.sha256(text.encode("utf-8")).digest()]
    # A byte is an integer, so no component can be exactly 0.5*255 -> the norm is never 0.
    norm = math.sqrt(sum(value * value for value in raw))
    return [value / norm for value in raw]


class FakeEmbedder:
    """Deterministic, offline embedder: the same text always yields the same vector.

    Determinism lives in the hash, not in instance state, so two independent
    ``FakeEmbedder()`` objects agree.
    """

    dimension: int = FAKE_DIMENSION

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_fake_vector(text) for text in texts]
