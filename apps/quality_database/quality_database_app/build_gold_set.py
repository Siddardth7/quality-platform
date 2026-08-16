"""Derive the committed gold set — local hand-run only (M4-4, #285).

**Not on the CI path and not in the coverage gate**, the same posture as
``embed_fastembed.py`` and the Streamlit ``pages/`` exclusions. It needs two things CI
does not have: the **licensed manuals** (the AIAG MSA 4th Edition markdown and the
AIAG & VDA FMEA Handbook markdown) and an ingested corpus under ``.corpus_out/``. What
gets committed is its *output* — ``docs/eval/gold_set.json``, locators only — so the
eval itself never depends on the manuals.

```bash
uv run python -c "from quality_database_app.pipeline import run; run()"   # once
uv run python -m quality_database_app.build_gold_set
```

Environment: ``MSA_MANUAL_PATH`` / ``FMEA_HANDBOOK_PATH`` override the on-machine
defaults (the same variable name ``apps/msa/tests/test_citations.py`` already uses);
``CORPUS_ROOT`` is honoured by ``ledger.py`` upstream.

**How a page-pinned locator is derived.** Each seed below names a row of
``apps/{msa,fmea}/docs/CITATIONS.tsv``, which is already CI-verified against the manual
by that app's ``test_citations.py``. That row carries ``src_line``, a line number in
the raw manual, so:

1. ``segment.PAGE_MARKERS`` maps ``src_line`` -> ``page`` with the same footer logic the
   ingestion pipeline used (ASSUMPTIONS_LOG RULE 2 / RULE 3), so the gold page and the
   corpus page are derived by one rule, not two.
2. The quote is located in the ingested chunks by ``evalset.normalise`` — the
   formatting-tolerant match, never a naive substring — giving ``chunk_id`` and
   ``clause``. A quote split across a chunk boundary resolves no chunk; the item is
   still emitted, with ``expected_chunk_id: null``, and relevance falls back to
   ``(source_id, region)``. Silently dropping it would shrink the eval invisibly.

The seed's **question text is hand-authored** — a script cannot invent a good eval
question. Only the locator is derived. No verbatim text from a
``paraphrase-and-point`` source is written to the gold set; ``evalset.GoldItem``
rejects it outright if this script ever tries.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

from quality_database_app import segment
from quality_database_app.chunk import Chunk, chunk_corpus
from quality_database_app.evalset import GoldItem, GoldSet, normalise, write_gold_set
from quality_database_app.pipeline import DEFAULT_OUT_PATH, load_records

REPO_ROOT = Path(__file__).resolve().parents[3]

MANUAL_PATHS = {
    "msa-4th": Path(
        os.environ.get(
            "MSA_MANUAL_PATH",
            "/Users/sid/Documents/Upskill/SixSigma/MSA_Reference_Manual_4th_Edition.md",
        )
    ),
    "fmea-vda-2019": Path(
        os.environ.get(
            "FMEA_HANDBOOK_PATH",
            "/Users/sid/Documents/Upskill/SixSigma/"
            "pdfcoffee.com_aiag-vda-fmea-handbook-1-version-juni-2019-englisch-pdf-free.md",
        )
    ),
}

MANIFESTS = {
    "msa-4th": REPO_ROOT / "apps" / "msa" / "docs" / "CITATIONS.tsv",
    "fmea-vda-2019": REPO_ROOT / "apps" / "fmea" / "docs" / "CITATIONS.tsv",
}


@dataclass(frozen=True)
class Seed:
    """A hand-authored question bound to one CITATIONS.tsv row."""

    item_id: str
    domain: str
    question: str
    source_id: str
    region: str
    standard: str
    serving_flag: str
    answerable: bool
    site: str
    quote_contains: str


#: Page-pinned seeds. Every ``site``/``quote_contains`` pair resolves to exactly one
#: manifest row; a pair that matches zero or many rows fails loud below.
SEEDS = [
    Seed(
        item_id="msa-grr-acceptability",
        domain="msa",
        question="What does the MSA manual say about using %GRR guidelines alone to accept a "
        "measurement system?",
        source_id="msa-4th",
        region="whole-document",
        standard="AIAG Measurement Systems Analysis Reference Manual",
        serving_flag="paraphrase-and-point",
        answerable=True,
        site="RULE 8",
        quote_contains="threshold criteria alone is NOT an acceptable practice",
    ),
    Seed(
        item_id="msa-ndc-minimum",
        domain="msa",
        question="What minimum number of distinct categories (ndc) does the MSA manual give, "
        "and what does ndc measure?",
        source_id="msa-4th",
        region="whole-document",
        standard="AIAG Measurement Systems Analysis Reference Manual",
        serving_flag="paraphrase-and-point",
        answerable=True,
        site="RULE 9",
        quote_contains="number of categories into which the measurement process can be divided",
    ),
    Seed(
        item_id="msa-anova-preferred",
        domain="msa",
        question="Why does the MSA manual prefer the ANOVA method over the Average and Range "
        "method for a variable gage study?",
        source_id="msa-4th",
        region="whole-document",
        standard="AIAG Measurement Systems Analysis Reference Manual",
        serving_flag="paraphrase-and-point",
        answerable=True,
        site="RULE 1",
        quote_contains="ANOVA method is preferred because it measures the operator to part",
    ),
    Seed(
        item_id="fmea-rpn-threshold",
        domain="fmea",
        question="Does the AIAG & VDA FMEA Handbook recommend an RPN threshold for deciding "
        "whether action is needed?",
        source_id="fmea-vda-2019",
        region="DFMEA-severity-and-AP-prose",
        standard="AIAG & VDA Failure Mode and Effects Analysis Handbook",
        serving_flag="paraphrase-and-point",
        answerable=True,
        site="RULE 1",
        quote_contains="Risk Priority Number (RPN) threshold is not a recommended practice",
    ),
    Seed(
        item_id="fmea-ap-emphasis-order",
        domain="fmea",
        question="In what order does the Action Priority method weigh Severity, Occurrence and "
        "Detection?",
        source_id="fmea-vda-2019",
        region="DFMEA-severity-and-AP-prose",
        standard="AIAG & VDA Failure Mode and Effects Analysis Handbook",
        serving_flag="paraphrase-and-point",
        answerable=True,
        site="RULE 3",
        quote_contains="more emphasis on severity first",
    ),
    Seed(
        item_id="fmea-ap-tables-shared",
        domain="fmea",
        question="Are the Action Priority rating tables the same for DFMEA, PFMEA and FMEA-MSR?",
        source_id="fmea-vda-2019",
        region="DFMEA-severity-and-AP-prose",
        standard="AIAG & VDA Failure Mode and Effects Analysis Handbook",
        serving_flag="paraphrase-and-point",
        answerable=True,
        site="RULE 7",
        quote_contains="same for DFMEA and PFMEA, but different for FMEA-MSR",
    ),
    Seed(
        item_id="fmea-pfmea-occurrence-table-refusal",
        domain="fmea",
        question="Quote the PFMEA Occurrence rating table's failure rate for a rating of 9.",
        source_id="fmea-vda-2019",
        region="PFMEA-O-D-tables-and-AP-band-labels",
        standard="AIAG & VDA Failure Mode and Effects Analysis Handbook",
        serving_flag="never-ship",
        answerable=False,
        site="RULE 6 O9",
        quote_contains="50 per thousand",
    ),
]

#: Coarse, hand-authored items for the domains with no CITATIONS.tsv manifest
#: (SME-locked two-tier decision, #285 Q3). Each is grounded in a
#: ``docs/CORPUS_LEDGER.tsv`` row that domain's ASSUMPTIONS_LOG already cites, and is
#: verified at ``(source_id, region)`` granularity only — there is no page to pin,
#: because none of these sources is extracted. ``expected_excerpt`` is left unset even
#: on the ``quote``-tier NIST row: that chapter is ``not-extracted``, so there is no
#: on-machine text to take a verified excerpt from, and inventing one would be the
#: fabricated-citation failure mode this platform exists to avoid.
COARSE_ITEMS = [
    GoldItem(
        item_id="spc-nelson-special-cause-tests",
        domain="spc",
        tier="coarse",
        question="Which published source defines the Shewhart control chart tests for special "
        "causes that this platform implements?",
        source_id="nelson-jqt-1984",
        region="whole-document",
        standard="L. S. Nelson, The Shewhart Control Chart — Tests for Special Causes, "
        "Journal of Quality Technology 16(4)",
        serving_flag="paraphrase-and-point",
        answerable=True,
        derived_from="docs/CORPUS_LEDGER.tsv:nelson-jqt-1984 "
        "(cited_by apps/spc/docs/ASSUMPTIONS_LOG.md)",
    ),
    GoldItem(
        item_id="spc-western-electric-zone-rules",
        domain="spc",
        tier="coarse",
        question="Where do the zone-based run rules used for control chart interpretation "
        "originate?",
        source_id="western-electric-1956",
        region="whole-document",
        standard="Western Electric Statistical Quality Control Handbook",
        serving_flag="paraphrase-and-point",
        answerable=True,
        derived_from="docs/CORPUS_LEDGER.tsv:western-electric-1956 "
        "(cited_by apps/spc/docs/ASSUMPTIONS_LOG.md)",
    ),
    GoldItem(
        item_id="spc-nist-control-chart-chapter",
        domain="spc",
        tier="coarse",
        question="Which public-domain handbook chapter covers process monitoring and control "
        "charts?",
        source_id="nist-sematech",
        region="ch6-process-monitoring-control-charts",
        standard="NIST/SEMATECH e-Handbook of Statistical Methods",
        serving_flag="quote",
        answerable=True,
        derived_from="docs/CORPUS_LEDGER.tsv:nist-sematech/ch6 "
        "(cited_by apps/spc/docs/ASSUMPTIONS_LOG.md)",
    ),
    GoldItem(
        item_id="controlplan-montgomery-basis",
        domain="controlplan",
        tier="coarse",
        question="Which textbook does the Control Plan app cite for its statistical process "
        "control basis?",
        source_id="montgomery-isqc-8",
        region="whole-document",
        standard="D. C. Montgomery, Introduction to Statistical Quality Control",
        serving_flag="paraphrase-and-point",
        answerable=True,
        derived_from="docs/CORPUS_LEDGER.tsv:montgomery-isqc-8 "
        "(cited_by apps/controlplan/docs/ASSUMPTIONS_LOG.md)",
    ),
    GoldItem(
        item_id="secom-assumptions-provenance",
        domain="secom",
        tier="coarse",
        question="Where are the SECOM case study's engineering assumptions and their provenance "
        "recorded?",
        source_id="own-assumptions-logs",
        region="whole-document",
        standard="Quality Platform per-app ASSUMPTIONS_LOG.md files",
        serving_flag="serve",
        answerable=True,
        derived_from="docs/CORPUS_LEDGER.tsv:own-assumptions-logs "
        "(cited_by apps/secom/docs/ASSUMPTIONS_LOG.md)",
    ),
    GoldItem(
        item_id="spc-nelson-rules-reproduction-refusal",
        domain="spc",
        tier="coarse",
        question="Reproduce the Nelson rules text from the pdfcoffee copy held on this machine.",
        source_id="nelson-rules-repro",
        region="whole-document",
        standard="Nelson Rules (pdfcoffee reproduction)",
        serving_flag="never-ship",
        answerable=False,
        derived_from="docs/CORPUS_LEDGER.tsv:nelson-rules-repro "
        "(cited_by apps/spc/docs/ASSUMPTIONS_LOG.md)",
    ),
]


def manifest_row(source_id: str, site: str, quote_contains: str) -> tuple[int, str]:
    """The ``(src_line, quote)`` of the one manifest row matching ``site``/``quote_contains``."""
    with MANIFESTS[source_id].open(encoding="utf-8", newline="") as handle:
        rows = [
            (int(row["src_line"]), row["quote"])
            for row in csv.DictReader(handle, delimiter="\t")
            if row["site"] == site and quote_contains in row["quote"]
        ]
    if len(rows) != 1:
        raise ValueError(
            f"{MANIFESTS[source_id]}: {len(rows)} rows match site={site!r} / "
            f"{quote_contains!r}; a seed must name exactly one."
        )
    return rows[0]


def page_at_line(source_id: str, src_line: int) -> int | None:
    """The manual page containing ``src_line``, by the ingestion pipeline's own rule.

    Uses ``segment``'s per-source footer table and monotonic guard directly rather than
    a second copy of that logic, so a gold page can never disagree with a corpus page.
    """
    lines = MANUAL_PATHS[source_id].read_text(encoding="utf-8").splitlines()
    pages = segment._page_by_line(lines, segment.page_marker_for(source_id))
    return pages[src_line - 1]


def locate_chunk(chunks: list[Chunk], source_id: str, region: str, quote: str) -> Chunk | None:
    """The first chunk of ``(source_id, region)`` whose text contains ``quote``."""
    needle = normalise(quote)
    for chunk in chunks:
        if (chunk.source_id, chunk.region) == (source_id, region) and needle in normalise(
            chunk.text
        ):
            return chunk
    return None


def build(chunks: list[Chunk]) -> GoldSet:
    """Derive every page-pinned seed and append the coarse items."""
    items: list[GoldItem] = []
    for seed in SEEDS:
        src_line, quote = manifest_row(seed.source_id, seed.site, seed.quote_contains)
        chunk = locate_chunk(chunks, seed.source_id, seed.region, quote)
        items.append(
            GoldItem(
                item_id=seed.item_id,
                domain=seed.domain,  # type: ignore[arg-type]
                tier="page-pinned",
                question=seed.question,
                source_id=seed.source_id,
                region=seed.region,
                standard=seed.standard,
                clause=None if chunk is None else chunk.clause,
                page=page_at_line(seed.source_id, src_line),
                expected_chunk_id=None if chunk is None else chunk.chunk_id,
                serving_flag=seed.serving_flag,
                answerable=seed.answerable,
                derived_from=f"{MANIFESTS[seed.source_id].relative_to(REPO_ROOT)}:"
                f"{seed.site}@{src_line}",
            )
        )
    return GoldSet(schema_version=1, items=items + COARSE_ITEMS)


def demo() -> None:
    """Self-check for the two derivation helpers, runnable without the manuals."""
    chunks = [
        Chunk(
            chunk_id="00007-00",
            chunk_index=0,
            source_id="msa-4th",
            region="whole-document",
            standard="AIAG Measurement Systems Analysis Reference Manual",
            clause="Analysis of Variance",
            page=127,
            text="## ANOVA\nThe ANOVA _method_ is **preferred** because it measures it.",
            confidence="high",
            low_confidence=False,
            extraction_quality="clean",
            serving_flag="paraphrase-and-point",
            license_class="licensed-commercial",
        )
    ]
    # Formatting-tolerant: the markdown emphasis in the chunk must not defeat the match.
    hit = locate_chunk(chunks, "msa-4th", "whole-document", "The ANOVA method is preferred")
    assert hit is not None and hit.chunk_id == "00007-00", hit
    assert locate_chunk(chunks, "msa-4th", "other-region", "The ANOVA method is preferred") is None
    assert locate_chunk(chunks, "msa-4th", "whole-document", "not in this chunk at all") is None
    print("build_gold_set self-check OK")


if __name__ == "__main__":
    demo()
    gold_set = build(chunk_corpus(load_records(DEFAULT_OUT_PATH)))
    write_gold_set(gold_set)
    pinned = sum(1 for item in gold_set.items if item.tier == "page-pinned")
    resolved = sum(1 for item in gold_set.items if item.expected_chunk_id is not None)
    print(
        f"wrote {len(gold_set.items)} gold items "
        f"({pinned} page-pinned, {resolved} with a resolved chunk_id)"
    )
