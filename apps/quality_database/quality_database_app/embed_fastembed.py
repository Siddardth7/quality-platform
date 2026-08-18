"""Real local embedder — optional, hand-run only (M4-3, #284).

**Not on the CI path and not in the coverage gate**, the same posture as the Streamlit
``pages/`` exclusions: it needs the optional ``embed`` dependency group, which CI does
not install. Install it for a real indexing run:

```bash
uv sync --extra embed
uv run python -c "
from quality_database_app.embed_fastembed import FastEmbedEmbedder
from quality_database_app.index import run
print(len(run(FastEmbedEmbedder()).chunks))
"
```

fastembed runs the model on ONNX Runtime rather than PyTorch, which is why it is the
pick here — a torch-backed stack is a multi-gigabyte install for one hand-run job. The
first call downloads the model, so this needs a network; that is exactly why it is
never imported by anything CI executes. Swapping it for another backend touches this
file only: :class:`~quality_database_app.embed.Embedder` is the seam.
"""

from __future__ import annotations

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class FastEmbedEmbedder:
    """`quality_database_app.embed.Embedder` backed by a local fastembed ONNX model."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "fastembed is not installed. Run `uv sync --extra embed` for a real "
                "indexing run; CI uses quality_database_app.embed.FakeEmbedder."
            ) from exc
        self._model = TextEmbedding(model_name=model_name)
        self.dimension = len(self.embed(["dimension probe"])[0])

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(value) for value in vector] for vector in self._model.embed(texts)]
