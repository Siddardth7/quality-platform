"""Quality knowledge base — corpus ingestion and cleaning (M4-2, #283).

**Engine-only by decision**, like ``apps/secom`` (#206): a tested library with no
Streamlit entry script and no UI dependency. It reads ``docs/CORPUS_LEDGER.tsv``
(M4-1, #282) as its input contract, extracts and segments the Markdown sources it
names, and writes a clean intermediate corpus for M4-3 to embed.

`__version__` is the single source of truth for this app's version; keep it in sync
with ``apps/quality_database/pyproject.toml`` at release (bump both together).
"""

__version__ = "1.0.0"
