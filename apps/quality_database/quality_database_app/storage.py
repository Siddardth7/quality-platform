"""The sanctioned read path into the private corpus store (M4-5, #286).

**Storage location (OQ1, SME-locked 2026-08-16).** M4-5 creates no new location and
adds no dependency. The corpus store is what M4-2/M4-3 already write: the gitignored
``apps/quality_database/.corpus_out/`` (``corpus.json`` + ``index/``), derived from the
on-machine ``$CORPUS_ROOT`` source tree. Both are outside version control, and
``tests/test_no_corpus_content.py`` is the machine check that keeps them there.

**One reader (OQ3).** This module is the one intended caller of
:meth:`~quality_database_app.store.VectorStore.load` outside this app's own tests. M5-2
(the query endpoint) is meant to import :func:`load_index` and nothing else should reach
into ``.corpus_out/`` directly. This module does **not** enforce that — it cannot: M5-2
does not exist yet, so there is no caller to gate. Full "only the endpoint can read it"
enforcement is M5-2's job; do not read this module as having already done it. What is
enforced here is the third leg: :func:`load_index` **fails closed**, so a missing index
is an error rather than a silently empty store.

**No new secret (OQ2).** This is a local filesystem read; there is no caller identity to
authenticate, so #286 adds no auth code. When M5-2 stands up network access over this
reader it should reuse M1-8's shared-secret bearer posture —
``apps/mcp/mcp_app/transport.py`` (``MCP_AUTH_TOKEN``, fail-closed on an empty token,
``hmac.compare_digest``), issue #267 — not invent a second auth scheme. See
``docs/ASSUMPTIONS_LOG.md`` RULE 14.

# ponytail: local filesystem only, no CorpusStorage interface — one implementation.
# Add the seam if/when M5/M6 needs a remote backend (OQ4).
"""

from __future__ import annotations

import os
from pathlib import Path

from quality_database_app.index import DEFAULT_INDEX_DIR
from quality_database_app.schema import IngestionError
from quality_database_app.store import VectorStore

#: Optional override pointing at a relocated ``.corpus_out`` directory (the store as a
#: whole, not the ``index/`` subdirectory) — for a machine that keeps the private
#: artefacts off this checkout. Unset is the normal case.
CORPUS_OUT_DIR_ENV = "QUALITY_DATABASE_CORPUS_OUT"

INDEX_SUBDIR = "index"


def resolve_index_dir() -> Path:
    """The private index dir: ``.corpus_out/index``, or ``$QUALITY_DATABASE_CORPUS_OUT/index``."""
    override = os.environ.get(CORPUS_OUT_DIR_ENV)
    if override:
        return Path(override) / INDEX_SUBDIR
    return DEFAULT_INDEX_DIR


def load_index() -> VectorStore:
    """Load the saved index from :func:`resolve_index_dir`.

    Raises:
        IngestionError: if the index directory does not exist (nothing indexed yet), or
            if ``VectorStore.load`` rejects what is there (missing, corrupt, or
            schema-mismatched files) — propagated unchanged, not swallowed. Failing
            closed is the point: an endpoint answering "no results" because the index
            was never built, rather than surfacing the real cause, is the failure mode
            this guards.
    """
    index_dir = resolve_index_dir()
    if not index_dir.is_dir():
        raise IngestionError(
            f"'{index_dir}' does not exist — no index has been built yet. Run "
            f"quality_database_app.index.run() locally (the corpus is private and is "
            f"never on CI), or set ${CORPUS_OUT_DIR_ENV} to the store's location."
        )
    return VectorStore.load(index_dir)
