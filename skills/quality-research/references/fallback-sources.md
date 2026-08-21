# Local fallback sources (reference)

What to do when `qdb_answer_question` cannot be reached — SKILL.md step 3. Today's actual
state is that the hosted endpoint is unprovisioned, so this is the path most sessions take;
it is the other half of one contract, not a degraded afterthought.

The private corpus is never the fallback material. `docs/CORPUS_LEDGER.md` is explicit: the
corpus is private, only *our derivations* are public. What is public, committed and reviewed
is each app's `docs/ASSUMPTIONS_LOG.md` — every AIAG/ISO constant, threshold and quotation the
platform relies on, as a numbered RULE with its own primary-source citation and a file:line
pointer into the engine that applies it.

## The procedure

1. **Say it is a fallback.** State plainly that the private corpus / hosted endpoint is
   unavailable, so this answer comes from the project's own public citations, not from the
   endpoint. Never let a fallback answer read as an endpoint answer.
2. **Name the owning app** from the question's topic:

   | Topic | App |
   |---|---|
   | FMEA, AIAG-VDA, RPN, Action Priority, severity/occurrence/detection scales | `apps/fmea` |
   | SPC, control charts, Cp/Cpk/Pp/Ppk, stability, run rules | `apps/spc` |
   | MSA, Gage R&R, %GRR, ndc, EV/AV/PV | `apps/msa` |
   | Control Plan, chart selection, reaction plans | `apps/controlplan` |
   | The corpus, tiering, quote caps, serving policy | `docs/CORPUS_LEDGER.md` |

   Each app's file is `apps/<app>/docs/ASSUMPTIONS_LOG.md`. `apps/secom` and
   `apps/quality_database` have one too, for case-study and corpus questions respectively.
3. **Read that file and find the matching RULE.** Answer from that RULE's own prose and its
   own citation. Do not answer from the raw on-machine manual — root `CLAUDE.md` designates
   it as the source of truth for *verifying* a claim during doc maintenance, which is not a
   licence to reproduce it in a chat answer.
4. **Quote only what the RULE already quotes.** If the ASSUMPTIONS_LOG entry carries a
   verbatim passage, it is already inside the app's reviewed quote cap — reuse it and cite it.
   Otherwise paraphrase and point at the RULE number and file:line. That is
   `docs/CORPUS_LEDGER.md`'s `paraphrase-and-point` tier, applied as an editorial rule here
   rather than as code. Never dump a `CITATIONS.tsv` row verbatim as though it were a newly
   generated answer.
5. **If no RULE matches, say so.** "This is not covered by the project's cited rules" is the
   correct answer — the same refusal discipline the endpoint applies with its measured
   threshold, applied by instruction because there is no threshold to gate on locally. Do not
   reconstruct a standard from recollection.

**Two-app questions** (e.g. "does AIAG allow RPN thresholds the way it allows %GRR bands?"):
read both apps' files rather than picking one. If the two standards disagree or simply do not
overlap, say that — do not blend them into a single claim.

## Why there is no fallback script

The "retrieval" here is a file read over about half a dozen small, human-curated files. The
host running this skill already has file-read and grep tools. A keyword-search Python script
over `ASSUMPTIONS_LOG.md` would be a second, hand-rolled retrieval engine duplicating them.
Add one only if a host without file tools ever needs this skill; none of the hosts in
`skills/COMPATIBILITY.md` is in that position.

## The four worked examples, fallback path in full

### 1. MSA — the ndc threshold of 5

**Source:** `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 9 (with RULE 10 for the verdict matrix),
citing AIAG MSA 4th Ed., Ch. II Sec. D:

> For analysis, the ndc is the maximum of one or the calculated value truncated to the
> integer. This result should be greater than or equal to 5.

**Answer shape:** five or more distinct categories is the point at which the measurement
system can resolve enough levels of part variation to be used for analysis; below it, it
cannot. RULE 9 carries the manual's own ndc formula and the truncation-and-floor-at-one
handling — point at the RULE, do not restate the arithmetic.

**Standard vs. platform:** `at least 5` is AIAG's *only* published ndc criterion. The
"2–4 Marginal" and "below 2 Reject" sub-bands are the platform's internal design choice built
on that single rule; RULE 9 and RULE 10 both flag them as *not* AIAG's. An answer that
presents the sub-bands as AIAG's is wrong even though the numbers are right.

### 2. FMEA — AIAG publishes no RPN action threshold

**Source:** `apps/fmea/docs/ASSUMPTIONS_LOG.md` RULE 1, citing the AIAG & VDA FMEA Handbook
(1st Ed., 2019) §3.5.9:

> The use of a Risk Priority Number (RPN) threshold is not a recommended practice for
> determining the need for actions.

**Answer shape:** no — the current handbook explicitly does not recommend a Risk Priority
Number threshold for deciding whether action is needed. What it publishes instead is the
Action Priority lookup table, transcribed and machine-diffed against the handbook in RULE 7.

**Standard vs. platform:** the platform's own `Flag_High_RPN` marks rows above 100 points.
RULE 1 documents that as a deliberate backward-compatibility carry-over for FMEA-4-based
workflows — widely used in industry, but not the handbook's rule. Report the platform flag as
the platform's, and lead with Action Priority as the standards-correct prioritization.

### 3. MSA — the %GRR acceptance bands

**Source:** `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 10 (bands) and RULE 7 / RULE 8 (the
quoted manual text), citing AIAG MSA 4th Ed., Ch. II Sec. D, Table II-D 1 "GRR Criteria":
*"Under 10 percent"* → Accept, *"10 percent to 30 percent"* → Marginal, over 30 percent →
Reject.

**Answer shape:** 12% sits in the middle band — **Marginal**: acceptable for some uses,
consider an improvement plan. It is neither a pass nor a failure.

**Standard vs. platform:** the three %GRR bands *are* AIAG's, unlike the ndc sub-bands above.
What is not AIAG's is treating them as a decision. RULE 8 quotes the manual against exactly
that:

> The use of the GRR guidelines as threshold criteria alone is NOT an acceptable practice for
> determining the acceptability of a measurement system

Table II-D 1's own wording for the middle band is *"May be acceptable for some
applications"* — a judgement to be made, not a result to be read off. So report the band, name
the caveat, and do not compress 12% into a verdict.

### 4. SPC — capability indices need a stable process first

**Source:** `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 7, citing the AIAG SPC Reference Manual
(4th Ed., 2005) — capability indices assume the process is in statistical control, and
computing them on an unstable process is misleading — with the same precondition
independently verifiable in the NIST/SEMATECH e-Handbook §6.1.6:

> Process capability compares the output of an in-control process to the specification limits

(https://www.itl.nist.gov/div898/handbook/pmc/section1/pmc16.htm)

**Answer shape:** an out-of-control process has no single stable distribution, so an index
computed from it describes a sample, not the process — which is why stability is assessed
first, from the stream's control chart.

**Standard vs. platform:** the platform **warns rather than blocks**.
`quality_core.spc.capability` still returns Cp/Cpk/Pp/Ppk on an unstable process and marks
them indicative only; the stability gate is an annotation, not a refusal. Do not describe it
as a hard gate. RULE 7's note also makes `stable` tri-state: `null` means stability was *not
assessed* (no control-chart context was supplied) and is never defaulted to "in control".

**Not the run rules.** The Western Electric and Nelson rule sets are deliberately *not* used
as a worked example here: `apps/spc/docs/ASSUMPTIONS_LOG.md` RULE 8 flags both as unverified
against a primary source (third-party reproduction only). Answering from an unverified rule is
exactly the behaviour this skill exists to avoid — do not substitute them back in without a
primary-source fix to RULE 8 itself.
