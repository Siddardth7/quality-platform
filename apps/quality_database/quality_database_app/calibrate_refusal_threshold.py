"""Hand-run: derive ``REFUSAL_SCORE_THRESHOLD`` from a real embedder + the real corpus
(M5-1, #287).

Not on the CI path and not in the coverage gate, the same posture as
``build_gold_set.py`` / ``embed_fastembed.py`` — it needs the optional ``embed`` extra
and a real ingested corpus, neither present on CI. ``FakeEmbedder`` carries no semantic
similarity (RULE 10), so no CI run can ever validate a real cosine cutoff; this script is
how the number is measured instead of guessed.

    uv sync --extra embed
    uv run python -c "
    from quality_database_app.embed_fastembed import FastEmbedEmbedder
    from quality_database_app.index import run
    run(FastEmbedEmbedder())
    "                                                    # once, to build the real index
    uv run python -m quality_database_app.calibrate_refusal_threshold

The printed threshold is pasted **by hand** into ``query.REFUSAL_SCORE_THRESHOLD``, and
the printed distributions into ``docs/ASSUMPTIONS_LOG.md`` RULE 16, in the same commit —
this script writes a report, never source. See RULE 16 for how the number was used.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from quality_database_app import storage
from quality_database_app.embed import Embedder
from quality_database_app.embed_fastembed import DEFAULT_MODEL, FastEmbedEmbedder
from quality_database_app.evalset import DEFAULT_GOLD_SET_PATH, load_gold_set
from quality_database_app.store import VectorStore

OUT_OF_CORPUS_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "eval" / "out_of_corpus_questions.json"
)

CLEAN_SEPARATION = "clean_separation"
OVERLAP = "overlap"


@dataclass(frozen=True)
class Calibration:
    """One calibration run: its inputs, both score distributions, and the cutoff."""

    model_name: str
    corpus_size: int
    in_corpus_scores: list[float]
    out_of_corpus_scores: list[float]
    branch: str
    threshold: float


def load_out_of_corpus_questions(path: Path = OUT_OF_CORPUS_PATH) -> list[str]:
    """The committed out-of-corpus fixture: a plain ``{"questions": [...]}`` JSON list.

    No ``StrictModel`` schema on purpose — it is a hand-run-only fixture never validated
    on CI, the same informality as ``build_gold_set.py``'s ``Seed`` dataclass.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    questions: list[str] = payload["questions"]
    return questions


def top1_scores(questions: list[str], store: VectorStore, embedder: Embedder) -> list[float]:
    """Each question's top-1 (``k=1``) cosine score against ``store``.

    ``exclude_never_ship`` is left at its default, exactly as the shipped engine queries.
    """
    return [store.search(vector, k=1)[0].score for vector in embedder.embed(questions)]


def derive_threshold(in_scores: list[float], out_scores: list[float]) -> tuple[float, str]:
    """The cutoff between the two distributions, and which branch produced it.

    Clean separation (the expected case for a real model on an in-domain corpus): the
    midpoint between the weakest legitimate query and the strongest false-positive risk.

    Overlap: sweep every observed score as a candidate cutoff and take the one that
    classifies most questions correctly on both sides, breaking ties toward the *higher*
    candidate — the conservative choice, refusing more rather than answering more,
    consistent with "refuse rather than guess". Never resolve a tie downward.
    """
    in_min, out_max = min(in_scores), max(out_scores)
    if in_min > out_max:
        return (in_min + out_max) / 2, CLEAN_SEPARATION
    candidates = sorted(set(in_scores) | set(out_scores))
    best = max(
        candidates,
        key=lambda t: (
            sum(1 for score in in_scores if score >= t)
            + sum(1 for score in out_scores if score < t),
            t,
        ),
    )
    return best, OVERLAP


def calibrate() -> Calibration:
    """Run the whole measurement against the real index and the real embedder."""
    store = storage.load_index()
    embedder = FastEmbedEmbedder()
    in_questions = [
        item.question for item in load_gold_set(DEFAULT_GOLD_SET_PATH).items if item.answerable
    ]
    out_questions = load_out_of_corpus_questions()
    in_scores = top1_scores(in_questions, store, embedder)
    out_scores = top1_scores(out_questions, store, embedder)
    threshold, branch = derive_threshold(in_scores, out_scores)
    return Calibration(DEFAULT_MODEL, len(store.chunks), in_scores, out_scores, branch, threshold)


def report(result: Calibration) -> str:
    """The printed summary, including the misclassification counts on each side.

    The counts are printed whichever branch fired, so a threshold derived from
    overlapping distributions is never read as a clean one.
    """
    return json.dumps(
        {
            "model_name": result.model_name,
            "corpus_size": result.corpus_size,
            "in_corpus": {
                "n": len(result.in_corpus_scores),
                "min": min(result.in_corpus_scores),
                "max": max(result.in_corpus_scores),
                "below_threshold": sum(
                    1 for score in result.in_corpus_scores if score < result.threshold
                ),
            },
            "out_of_corpus": {
                "n": len(result.out_of_corpus_scores),
                "min": min(result.out_of_corpus_scores),
                "max": max(result.out_of_corpus_scores),
                "at_or_above_threshold": sum(
                    1 for score in result.out_of_corpus_scores if score >= result.threshold
                ),
            },
            "branch": result.branch,
            "threshold": result.threshold,
        },
        indent=2,
    )


def demo() -> None:
    """Self-check for derive_threshold's two branches, runnable without the corpus."""
    threshold, branch = derive_threshold([0.6, 0.7], [0.2, 0.3])
    assert branch == CLEAN_SEPARATION and threshold == (0.6 + 0.3) / 2, (threshold, branch)
    # Overlap: in=[0.5], out=[0.4, 0.6] — 0.5 is the only cutoff classifying two of the
    # three correctly, and the branch must fire rather than fall back to the midpoint.
    threshold, branch = derive_threshold([0.5], [0.4, 0.6])
    assert branch == OVERLAP, branch
    assert threshold == 0.5, threshold
    # Tie-break: in=[0.5], out=[0.5] — every candidate scores the same; take the higher.
    threshold, branch = derive_threshold([0.5, 0.9], [0.5, 0.9])
    assert branch == OVERLAP and threshold == 0.9, (threshold, branch)
    print("calibrate_refusal_threshold self-check OK")


if __name__ == "__main__":
    demo()
    print(report(calibrate()))
