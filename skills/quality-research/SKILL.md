---
name: quality-research
description: Answer a quality-standards question (AIAG FMEA/SPC/MSA thresholds, ISO/NIST concepts, why a rule like the ndc threshold of 5 or an RPN/%GRR band exists) by calling the quality-platform qdb_answer_question MCP tool over HTTP for a cited, page-located answer; falls back to this project's own public ASSUMPTIONS_LOG citations when the endpoint is unavailable. Use for "why" and "what does the standard say" questions, not for running fmea_score, an SPC chart, msa_gage_rr or controlplan_build.
---

# quality-research — ask the standards

Answer a question *about* a quality standard by calling the quality-platform
`qdb_answer_question` MCP tool over HTTP. The endpoint owns retrieval, refusal and citation;
this skill decides when to call it, how to present what came back, and what to do when it is
unreachable. See `skills/CONVENTIONS.md` for the rules this skill is written to.

## When to use

The user is asking *why* a standard says what it says, where a threshold comes from, or what
AIAG / ISO / NIST actually publishes about a topic. Not a request to compute anything.

| What the user is asking | Where it goes |
|---|---|
| "Why is the ndc threshold 5?" | here |
| "Does AIAG publish an RPN number that forces corrective action?" | here |
| "Is a %GRR of 12% acceptable under AIAG MSA?" | here |
| "Why check control-chart stability before trusting Cpk?" | here |
| "What does ISO 9001 require for a documented quality manual?" | here |
| "Score this failure mode: severity 9, occurrence 8, detection 5." | `fmea` |
| "What does a severity rating of 9 mean?" | `fmea` (`fmea_get_scale`) |
| "Run a Gage R&R on this study." | `msa` |
| "Run a capability study against LSL 9, USL 11." | `spc` |
| "Build a control plan from this FMEA." | `control-plan` |

This is not the skill for running an engine. A request that carries *data* — ratings, a
study, readings, an FMEA table — is a tool call, and belongs to `fmea`, `msa`, `spc` or
`control-plan`. If this skill fires on one anyway, hand it to the owning skill rather than
answering it from a citation.

## Steps

1. **Call the endpoint first.** Attempt `qdb_answer_question` with the user's question,
   `k=5`, and — only if the user named one — `standard`, `source_id` or `region` to narrow
   retrieval. `scripts/call_qdb_answer_question.py` is the same call as a runnable script; it
   reads `QDB_MCP_URL` and `QDB_MCP_TOKEN` from the environment. This is always tried first:
   it is the primary path, not an optional enhancement.
2. **If `refused` is true**, report the tool's own fixed string verbatim — *"Not found in the
   corpus."* — and stop. Do **not** fall back and do not guess further: a refusal is a real,
   cited-as-absent answer, not an outage.
3. **On any call failure** — env vars unset, connection refused or timed out, an auth
   rejection, or a structured `ToolError` (no index built, or no generator configured
   server-side) — say plainly that the hosted endpoint is unavailable, surface the tool's
   error message verbatim if there was one, then run the **local fallback** below and label
   the answer as a fallback, not an endpoint answer. One branch, not a menu: every failure
   mode routes to the same place. Never print `QDB_MCP_TOKEN` or echo it into a message.
4. **On success**, present `text` as returned and build the locator from `cited_source_id`,
   `cited_region` and `cited_page` exactly as they came back. Never re-word a citation, never
   invent a page the tool did not return, and never ask for or display anything beyond those
   five fields plus `item_id` — no retrieval hit list, no raw chunk, no prompt context, no
   vectors. The corpus stays on the server; only the answer and its locator leave it.
5. **Local fallback**, when step 3 fires: answer from this project's own public, reviewed
   citations — the owning app's `docs/ASSUMPTIONS_LOG.md` — never from the private corpus and
   never from recollection. The full five-step procedure, the per-app source table and the
   quoting rule are in
   [`references/fallback-sources.md`](references/fallback-sources.md). In short: name the
   owning app from the topic, read its `ASSUMPTIONS_LOG.md`, answer from the matching RULE's
   own prose and citation, quote only what that RULE already quotes, and say "not found"
   rather than fabricating if no RULE matches.

Whichever path answered, keep the two halves apart: **what the standard publishes** and **what
this platform additionally does**. Blending them is the failure mode all four examples below
are chosen to demonstrate.

## Worked examples

Each runs once through the endpoint shape (a successful `CandidateAnswer`) and once through
the fallback shape (the `ASSUMPTIONS_LOG.md` RULE that answers it offline).

### 1. MSA — the ndc threshold of 5

User: *"Why is the ndc threshold 5?"*

**Endpoint shape** — `qdb_answer_question` narrowed to MSA returns a populated
`CandidateAnswer`. **Illustrative field shape only** — the endpoint is unprovisioned today,
so the `item_id` and `cited_page` below are placeholders, **not a real MSA locator**; a live
call fills them from the corpus:

```text
item_id:         <opaque corpus item id>
text:            "AIAG MSA sets the number of distinct categories at five or more; below
                  that the measurement system cannot resolve enough levels of part
                  variation to be used for analysis."
cited_source_id: "aiag-msa-4e"
cited_region:    "Ch. II Sec. D"
cited_page:      <page number as returned>
refused:         false
```

Present that `text` and whatever locator actually came back — never the placeholders above.

**Fallback shape** — read `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 9, which quotes the manual
directly:

> For analysis, the ndc is the maximum of one or the calculated value truncated to the
> integer. This result should be greater than or equal to 5.

**Nuance to preserve:** that criterion is AIAG's *only* published ndc rule. The platform's
"2–4 Marginal / below 2 Reject" sub-bands are this project's own internal design choice, not
AIAG's — RULE 9 and RULE 10 say so explicitly. The manual's ndc formula itself lives in
RULE 9; point at it, do not restate the arithmetic here.

### 2. FMEA — AIAG publishes no RPN action threshold

User: *"Does AIAG say there's an RPN number that means I have to take corrective action?"*

**Endpoint shape** — narrowed to the AIAG & VDA FMEA Handbook, a `CandidateAnswer` with
`cited_region` around §3.5.9 and `refused: false`; present its `text` and locator verbatim.

**Fallback shape** — `apps/fmea/docs/ASSUMPTIONS_LOG.md` RULE 1, quoting the AIAG & VDA FMEA
Handbook (1st Ed., 2019) §3.5.9:

> The use of a Risk Priority Number (RPN) threshold is not a recommended practice for
> determining the need for actions.

**Nuance to preserve:** the answer is "no". What the handbook offers instead is the Action
Priority lookup table (RULE 7). This platform still flags rows above 100 points
(`Flag_High_RPN`) — that cutoff is a legacy carry-over kept for backward compatibility with
FMEA-4-based workflows, explicitly **not** the current handbook's recommendation. Say which
is which; do not report the platform's flag as AIAG's rule.

### 3. MSA — the %GRR acceptance bands

User: *"Is a %GRR of 12% acceptable under AIAG MSA?"*

**Endpoint shape** — narrowed to MSA, a `CandidateAnswer` citing Table II-D 1 "GRR Criteria"
with a page locator; present it as returned.

**Fallback shape** — `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 10 carries the band table from
AIAG MSA (4th Ed.), Ch. II Sec. D, Table II-D 1: under 10 percent → Accept, *"10 percent to
30 percent"* → Marginal, over 30 percent → Reject. 12% falls in the middle band, so the
answer is **Marginal** — acceptable for some uses, consider improvement — not a pass.

**Nuance to preserve:** it is not a pass/fail binary, and AIAG cautions against reading it as
one (RULE 8):

> The use of the GRR guidelines as threshold criteria alone is NOT an acceptable practice for
> determining the acceptability of a measurement system

So do not hand back "12% — accept" or "12% — reject" as a verdict without that caveat. Same
theme as example 2: do not over-mechanize one number into a decision the standard declines to
make.

### 4. SPC — capability indices need a stable process first

User: *"Why do I need to check control-chart stability before trusting Cpk?"*

**Endpoint shape** — narrowed to SPC, a `CandidateAnswer` citing the AIAG SPC Reference
Manual (4th Ed., 2005) with its page locator; present it as returned.

**Fallback shape** — `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 7: capability indices assume the
process is in statistical control, and computing them on an unstable process is misleading.
The same precondition is independently verifiable in the NIST/SEMATECH e-Handbook §6.1.6 —
*"Process capability compares the output of an in-control process to the specification
limits"* (https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm).

**Nuance to preserve:** the platform **warns, it does not refuse**.
`quality_core.spc.capability` still returns the indices on an unstable process and annotates
them as indicative only (RULE 7's note). Do not overstate it as a hard gate, and note that
`stable` is tri-state — `null` means stability was *not assessed*, never "in control".

## Reference

- [`references/mcp-tool-contract.md`](references/mcp-tool-contract.md) — the
  `qdb_answer_question` request/response shape, the refusal string, the fields the server
  will never return, the error contract, and the `QDB_MCP_URL`/`QDB_MCP_TOKEN` env contract.
- [`references/fallback-sources.md`](references/fallback-sources.md) — the five-step local
  fallback procedure, the per-app `ASSUMPTIONS_LOG.md` table, and the quote-cap /
  cite-and-point rule from `docs/CORPUS_LEDGER.md`.
