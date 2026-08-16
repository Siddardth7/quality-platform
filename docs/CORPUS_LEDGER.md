# Corpus Ledger — sourcing, licensing and serving policy

Issue #282 (M4-1). The foundation of M4 (Quality Knowledge Base): every source the RAG may
draw on is enumerated once, with its licensing class and an explicit rule for what a
generated answer may do with it.

Copyright is this project's largest non-technical risk. M4-2 (ingestion) onward consume this
file's decisions; they do not re-derive them.

- **Policy** (definitions, tiers, quote cap): this document.
- **Manifest** (one row per source region): [`CORPUS_LEDGER.tsv`](CORPUS_LEDGER.tsv),
  validated by [`tests/test_corpus_ledger.py`](../tests/test_corpus_ledger.py).

The manifest is the single source of truth for per-row classification. This document
deliberately does **not** repeat the table — a hand-copied second copy would drift.

## The corpus is private; only our derivations are public

The corpus files (`/Users/sid/Documents/Upskill/SixSigma/**`) live **outside this repository**
and are never committed. This continues the pattern already in use for the licensed AIAG
manuals: `MSA_MANUAL_PATH` / `FMEA_HANDBOOK_PATH` point the citation tests at out-of-repo
copies, and CI — which holds no licensed manual — *skips* those checks rather than failing.

What is public is only:

1. **Metadata about the sources** — title, edition, path, format, licensing class, extraction
   quality, serving flag. Bibliographic fact, of the same class as the "Sources referenced"
   sections already committed in every `apps/*/docs/ASSUMPTIONS_LOG.md`.
2. **This project's own derivations** — assumption logs, module docstrings, engine code, and
   this ledger.

No corpus text is committed by #282, and no new storage location is created. Storage for the
embedded/ingested corpus is M4-5 (#286), which also adds the repo-scan test that fails if
corpus text is ever committed.

## Serving flags

Four values plus one not-applicable case. The flag answers one question: **what may a
generated answer do with this source?**

| Flag | The RAG may … | The RAG may not … |
|---|---|---|
| `serve` | reproduce the text freely, at any length | — |
| `quote` | return a short verbatim excerpt **within the cap below**, with a locator | exceed the cap; reproduce a whole section |
| `paraphrase-and-point` | answer **in its own words** and cite a **locator only** (standard name, edition, clause / table / page) | emit any verbatim excerpt, however short |
| `never-ship` | use it only to inform this project's own engineering derivations | cite it, point at it, or paraphrase it in any user-facing output |
| `N/A` | — (nothing is held) | — |

### The quote cap

> A quoted excerpt in a generated answer is **at most 50 words and at most 2 sentences**, and
> always carries a locator (source, edition, section / table / page).

**SME-ratified quotable exception (ISO / SAE-class consensus standards).** ISO 9001 and
similar consensus standards are `public-standard`, hence in the `quote` tier — even though
ISO texts are *sold commercially* rather than public-domain like NIST. SME ratified this
2026-08-15: short cited excerpts of such standards, **within the cap above and cited to the
published clause/section number (never to any local copy)**, are accepted quotable exposure.
This is a deliberate, recorded exception to the general "quote only genuinely free-to-republish
text" intent — not a silent classification. Provenance of any local copy is treated as
unverified; the locator is always the published standard.

This is deliberately tighter than the de-facto ceiling in the static
`apps/*/docs/CITATIONS.tsv` manifests (which run to ~80 words). Those are a fixed, reviewed
set of rows in a repo; generated answers face reuse and scale risk that a fixed doc does not.

## The tiering rule (SME-locked, 2026-08-15)

Every row's flag is derived from **what the source is**, not from how it was obtained:

- **Tier 1 — public consensus standards (ISO / SAE / NIST) → `quote`.**
  NIST/SEMATECH is a US government work and public domain. ISO texts are published consensus
  standards; they are quotable under the cap, with a clause-number locator.
- **Tier 2 — licensed handbooks and textbooks → `paraphrase-and-point`.**
  AIAG manuals, the AIAG & VDA FMEA Handbook, IATF 16949, Montgomery, ASQ/CSSC training
  material, Kuhn & Johnson, Juran's Handbook. The project holds personal study copies with no
  redistribution licence, so no verbatim text is served — only our own words plus a locator.
  **This is the default** for anything not affirmatively placed in Tier 1 or Tier 3.
- **Tier 3 — this project's own derivations → `serve`.**
  Assumption logs, citation-manifest prose, the generated statistical tables and formula
  sheet, `gen_tables.py`, the NotebookLM evaluation set, this ledger.

Two rules cut across the tiers:

- **`never-ship` overrides the tier** where the material cannot be cited responsibly at all:
  OCR-mangled extraction regions (a mangled extraction cannot be safely *paraphrased* either —
  the extraction may misstate the standard), third-party scrapes of a paywalled primary,
  vendor marketing, and sources of unknown provenance and licensing.
- **A locator names the published standard, never the local file.** Several on-machine copies
  are `pdfcoffee.com` scrapes. The scrape's page numbers are not a citable location; the
  ledger records the provenance so a locator is never built from it.

### Not-held sources

Sources cited by an app log but with no local copy (paywalled journal articles reached only
via NIST/Montgomery, AIAG FMEA-4 2008, ISO 22514-2, Juran, Kuhn & Johnson) are ledgered with
`status: not-held` and `serving_flag: N/A`. They are kept for the audit trail: the ledger's
completeness claim is about *everything the project relies on*, not only what is on disk.

### Gathered but not yet cited

Material in the corpus that no `ASSUMPTIONS_LOG.md` cites yet — the `_new/` directory, PPAP,
APQP, IATF 16949, ISO 9001, the ASQ/CSSC training material — is ledgered now with
`status: not-yet-cited` and a flag already assigned, so M4-2 does not have to guess whether
it is in scope.

## Sub-source granularity

A source can be **partially** usable, so a row is one **(source, region)** pair, not one file.
The precedent is issue #256: in the AIAG & VDA FMEA Handbook extraction, the DFMEA Severity
table and the Action Priority prose are clean and CI-verified, while the PFMEA Occurrence /
Detection tables and the Table AP band-label cells are OCR cell-merge-mangled (`Hih`/`g`,
`Mdt`/`oerae`, around lines 2939 / 3001 / 4717 / 4814) and were deliberately left unquoted
rather than transcribed with risk. The handbook therefore carries two rows with different
`extraction_quality` and different `serving_flag`. `extraction_quality` is the field M4-2
reads to flag low-confidence extractions instead of trusting them.

## Known gaps, recorded rather than hidden

- **Edition mismatch — AIAG SPC.** `apps/spc` and `apps/controlplan` cite the *4th Edition
  (2005)*; the only on-machine copy is the *2nd Edition*. Both are ledgered as separate rows
  (`aiag-spc-4th` not-held, `aiag-spc-2nd` held) rather than silently merged.
- **AIAG FMEA-4 (2008)** is cited but no local copy was located.
- **Possible primaries logged as reproductions.** `Western_Electric_SQC_Handbook.pdf` and the
  Nelson JQT article may be the primaries, while `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 15
  still flags both as `UNVERIFIED — third-party reproduction only`. Re-verifying those
  quotations is a separate ticket; #282 records the possibility and changes no app log.
- **Pre-existing exposure, and how the ledger treats it.** `apps/msa/docs/CITATIONS.tsv` and
  `apps/fmea/docs/CITATIONS.tsv` commit short verbatim excerpts from *licensed* (Tier 2) manuals
  into a repo that may become public. The ledger therefore flags `own-citation-manifests` as
  **`paraphrase-and-point`, not `serve`**: the manifest *prose* is this project's own, but its
  verbatim excerpt column is upstream-licensed text that generated output must not reproduce
  wholesale. SME reviewed 2026-08-15: the short, CI-verified excerpts already committed are left
  in place (#282 does not unwind them), but the policy above bars any *generated* answer from
  reproducing them freely. Re-verifying or minimizing those committed excerpts is a separate
  ticket; #282 changes no app `CITATIONS.tsv`.

## What is machine-enforced

`tests/test_corpus_ledger.py` runs on CI with no corpus present and asserts: the manifest is
non-empty with unique `(source_id, region)` keys; every enumerated column holds an allowed
value; every row has a non-blank rationale; `quote` implies a Tier 1 licence class and `serve`
implies `project-own-derivation`; `not-held` implies `N/A` and no local path (and the
converse). Checks that need the corpus on disk **skip**, never fail.

Policy judgement — whether each row's tier is the *right* one — is not machine-checkable and
is signed off by the SME at review.
