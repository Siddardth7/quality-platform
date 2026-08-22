"""The RAG query engine: retrieve, ground, cite, refuse (M5-1, #287).

Four things happen here, in this order, and the order is the design:

1. **Retrieve** through the M4-3 store (``exclude_never_ship`` left at its safe default —
   RULE 12's ceiling stands, never-ship stays invisible to this layer).
2. **Gate** on the top-1 cosine score *before* any generator call
   (:data:`REFUSAL_SCORE_THRESHOLD`, a measured constant — ASSUMPTIONS_LOG RULE 16). A
   weak or empty retrieval refuses deterministically, with no model in the loop at all.
3. **Verify** every locator the generated text cites against the chunks actually
   retrieved. A citation is *parsed out of the answer and checked*, never trusted from
   the generator — an unverifiable citation is exactly as unusable as no retrieval.
4. **Enforce** ``docs/CORPUS_LEDGER.md``'s quote cap in code, fail-closed, reusing
   ``evalset.QUOTABLE_FLAGS`` / ``evalset.within_quote_cap`` verbatim rather than
   re-deriving a second serving-policy heuristic (the mistake RULE 1 exists to prevent).

There is **no LLM here either.** The generator is an injected callable and CI only ever
exercises a fake one — the same "no default backend, CI never touches a real one" split
as ``embed.py``'s ``Embedder``/``FakeEmbedder``. The output is
``generation_metrics.CandidateAnswer``, unchanged, so M4-4's scorers grade a live answer
and a scripted fixture identically, and M5-2 can wrap :func:`answer_question` as an MCP
tool with no new plumbing.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable

from quality_database_app.embed import Embedder
from quality_database_app.evalset import QUOTABLE_FLAGS, within_quote_cap
from quality_database_app.generation_metrics import CandidateAnswer, quoted_spans
from quality_database_app.store import SearchResult, VectorStore

DEFAULT_K = 5

#: Minimum top-1 cosine score for retrieval to be considered "found." A **measured**
#: constant, not a placeholder — derived by
#: :mod:`quality_database_app.calibrate_refusal_threshold` from a real
#: ``FastEmbedEmbedder`` run against the real corpus and a committed out-of-corpus
#: question set. The run's inputs, distributions and this exact value are recorded in
#: ``docs/ASSUMPTIONS_LOG.md`` RULE 16 — read that entry, and re-run the script (never
#: hand-edit this number), before changing it.
REFUSAL_SCORE_THRESHOLD = 0.6383290503624621

NOT_FOUND_TEXT = "Not found in the corpus."

#: A generator turns (question, retrieved context) into raw answer text carrying its own
#: inline locator tokens, ``[source_id:region:page]`` (``page`` literally ``None`` when
#: the chunk has none) — one token per claim the answer makes. Deliberately narrower than
#: ``generation_metrics.AnswerGenerator``: that Protocol returns a whole pre-built
#: ``CandidateAnswer`` (the M4-4 eval harness scripts the citation straight into the
#: fixture), which would let a generator self-report an unverified citation. Here the
#: citation must be parsed out of generated text and checked against retrieval, so the
#: seam is the narrowest thing that lets a test inject a fake: text in, text out.
Generator = Callable[[str, str], str]

#: One inline locator token, e.g. ``[msa-4th:whole-document:78]`` or
#: ``[msa-4th:whole-document:None]``.
_LOCATOR = re.compile(r"\[([^\]:]+):([^\]:]+):(\d+|None)\]")


def _default_item_id(question: str) -> str:
    """A deterministic id for a live caller who has no gold item to name.

    Content-derived, not wall-clock or counter derived, for the same reason every other
    artefact in this app is (RULE 7): the same question re-asked is the same id.
    """
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


def format_context(hits: list[SearchResult]) -> str:
    """Render retrieved chunks as the generator's prompt context.

    One block per hit, each stamped with the exact locator token the generator must cite
    verbatim if it uses that chunk, and with the chunk's serving flag so the prompt says
    what the policy already enforces in code (:func:`violates_quote_policy` is the
    enforcement; this line is only the instruction).
    """
    return "\n\n".join(
        f"[{hit.chunk.source_id}:{hit.chunk.region}:{hit.chunk.page}] "
        f"(serving_flag: {hit.chunk.serving_flag})\n{hit.chunk.text}"
        for hit in hits
    )


def passes_retrieval_gate(hits: list[SearchResult]) -> bool:
    """The refusal rule: at least one hit, and the top score clears the threshold.

    Computed from ``hits`` alone — no model call, deterministic, and directly testable
    against a synthetic ``SearchResult`` list.
    """
    return bool(hits) and hits[0].score >= REFUSAL_SCORE_THRESHOLD


def extract_locators(text: str) -> list[tuple[str, str, int | None]]:
    """Every ``(source_id, region, page)`` the generated text cites, in order.

    The literal token ``None`` parses back to Python ``None`` — a coarse source that was
    never page-pinned still cites a well-formed locator. Malformed brackets simply do
    not match; this never raises.
    """
    return [
        (source_id, region, None if page == "None" else int(page))
        for source_id, region, page in _LOCATOR.findall(text)
    ]


def _verified_locator(
    locators: list[tuple[str, str, int | None]], hits: list[SearchResult]
) -> tuple[str, str, int | None] | None:
    """The first cited locator, if *every* cited locator was actually retrieved.

    ``None`` when nothing was cited or when any cited locator is absent from ``hits`` —
    a hallucinated citation condemns the whole answer, not just its own sentence.
    """
    if not locators:
        return None
    retrieved = {(hit.chunk.source_id, hit.chunk.region, hit.chunk.page) for hit in hits}
    if any(locator not in retrieved for locator in locators):
        return None
    # ponytail: CandidateAnswer holds one locator, so a multi-citation answer reports its
    # first — still individually verified, so this is a granularity limit, not a
    # fabrication risk. Upgrade path: a list-valued citation field, when M5 needs one.
    return locators[0]


def violates_quote_policy(text: str, hits: list[SearchResult]) -> bool:
    """Whether ``text`` quotes something the retrieved set does not license.

    Fail-closed across the *whole* retrieved set rather than per chunk: the answer may
    draw on several hits with different serving flags, and a quoted span in generated
    text cannot be attributed back to the chunk it came from without a second parsing
    layer this issue does not build. So the most restrictive hit governs the whole
    answer — if any hit is not quotable, no quoted span is allowed anywhere; otherwise
    every span must fit ``docs/CORPUS_LEDGER.md``'s cap.
    """
    spans = quoted_spans(text)
    if not spans:
        return False
    if any(hit.chunk.serving_flag not in QUOTABLE_FLAGS for hit in hits):
        return True
    return any(not within_quote_cap(span) for span in spans)


def answer_question(
    question: str,
    store: VectorStore,
    embedder: Embedder,
    generate: Generator | None = None,
    k: int = DEFAULT_K,
    standard: str | None = None,
    source_id: str | None = None,
    region: str | None = None,
    item_id: str | None = None,
) -> CandidateAnswer:
    """Retrieve -> gate -> generate -> verify -> ground, or refuse.

    ``item_id`` defaults to a deterministic sha256 prefix of ``question`` so a live
    caller need not invent one; the eval harness passes the gold item's own id.

    ``generate`` is never called when the retrieval gate fails. It has no default
    implementation on purpose (``index.py``'s "there is deliberately no default
    embedder" precedent): a real query answered by a silently degraded stand-in is worse
    than one that fails.

    Raises:
        ValueError: if retrieval clears the gate but no ``generate`` was supplied.
    """
    answer_id = item_id or _default_item_id(question)
    refusal = CandidateAnswer(item_id=answer_id, text=NOT_FOUND_TEXT, refused=True)

    vector = embedder.embed([question])[0]
    hits = store.search(vector, k=k, standard=standard, source_id=source_id, region=region)
    if not passes_retrieval_gate(hits):
        return refusal
    if generate is None:
        raise ValueError(
            "retrieval cleared the refusal gate but no generator was supplied — "
            "answer_question() has no default generator by design."
        )

    raw = generate(question, format_context(hits))
    verified = _verified_locator(extract_locators(raw), hits)
    if verified is None or violates_quote_policy(raw, hits):
        return refusal
    return CandidateAnswer(
        item_id=answer_id,
        text=raw,
        cited_source_id=verified[0],
        cited_region=verified[1],
        cited_page=verified[2],
        refused=False,
    )
