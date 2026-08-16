"""Unit tests for embed.py (#284) — determinism lives in the hash, not in state."""

import math

from quality_database_app.embed import FAKE_DIMENSION, Embedder, FakeEmbedder


def test_same_text_embeds_identically_across_instances():
    first = FakeEmbedder().embed(["severity"])
    second = FakeEmbedder().embed(["severity"])
    assert first == second == FakeEmbedder().embed(["severity"])


def test_different_texts_embed_differently():
    [severity, occurrence] = FakeEmbedder().embed(["severity", "occurrence"])
    assert severity != occurrence


def test_vectors_are_unit_length_and_the_declared_width():
    embedder = FakeEmbedder()
    vectors = embedder.embed(["a", "b b b", "c" * 5000])
    assert embedder.dimension == FAKE_DIMENSION
    for vector in vectors:
        assert len(vector) == FAKE_DIMENSION
        assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0)


def test_empty_input_gives_empty_output():
    assert FakeEmbedder().embed([]) == []


def test_fake_embedder_satisfies_the_protocol():
    embedder: Embedder = FakeEmbedder()
    assert embedder.dimension == FAKE_DIMENSION
