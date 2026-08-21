# In-project context (reference)

How to answer a standards question *against the user's own project* — SKILL.md step 1b. The
standards half of the answer is unchanged: `qdb_answer_question` still runs, and the fallback in
[`fallback-sources.md`](fallback-sources.md) still applies. This file only covers the other half:
reading one already-computed number off disk so the answer can say what *this* project's value is.

**Read-only, and only one file.** This skill never writes a project artifact, never proposes an
edit to one, and never re-runs a study to refresh one. A stale artifact is reported as what it is —
the file's own value — not silently regenerated. The full project-aware co-pilot (propose a rating
change, re-run the arrow, write back) is out of scope for 1.0.

## Detecting a loaded project

A project is "loaded" when the user names a project directory (or one is already established as
the working directory of the conversation) **and** `<project-root>/project.yaml` exists and parses.
That file is `ProjectMeta` — `project_id`, `name`, `characteristics`. Note the `project_id` and
move on. If the file is absent, or no project directory was named at all, there is no project:
skip the whole project half and answer the standards question exactly as SKILL.md's four worked
examples do. That branch must be indistinguishable from the skill's behaviour before this step
existed.

The on-disk shape — the seven artifacts, their envelopes, which arrow writes which — is documented
canonically in [`docs/PROJECT_FILE_CONTRACT.md`](../../../docs/PROJECT_FILE_CONTRACT.md). Read it
there rather than expecting a copy here; only the topic mapping below is this skill's own.

## Topic → artifact → field

All paths are relative to `<project-root>`. Open **only** the one file the topic maps to.

| Topic | Artifact | Field(s) to read |
|---|---|---|
| %GRR, Gage R&R, ndc, EV/AV/PV | `msa/gage-rr.json` | `pgrr_study`, `pgrr_tolerance`, `ndc`, `verdict`, `characteristic` |
| RPN, Action Priority, severity/occurrence/detection | `fmea/fmea.json` | the relevant `FailureLink` row's already-scored ratings, inside `RelationalFMEA` |
| Cp/Cpk/Pp/Ppk, capability | `spc/results/<characteristic>.json` (`kind: "capability"`) | the `capability` dict, `oos_signal_count` |
| control-chart stability, run rules | `spc/results/<characteristic>.json` (`kind: "control_chart"`) | `violations`, `metrics` |
| measurement-system trust of an SPC result | `spc/msa-gate.json` | the row's `gate_status`, `reason` |
| control-plan content, chart selection, reaction plans | `control-plan/plan.json` | the row for the characteristic in question |

If the mapped file does not exist — a project with `project.yaml` but no `msa/gage-rr.json`, say —
state that the project carries no data for that artifact and fall through to the standards-only
answer. Do not substitute a different artifact, and do not fabricate a value.

**No compute.** Every field named above is copied from the artifact file as written; the engines
(`msa_app`, `spc_app`, `fmea_app`) already computed them and the file is their output. If a
question needs a number the file does not carry — `pgrr_tolerance` is `null` because the project
declared no tolerance, for instance — say that plainly rather than deriving it. Do not re-derive a
percentage from its components, do not re-round a stored value, and do not re-run the engine's
verdict logic by hand. This is `skills/CONVENTIONS.md` section 2 ("Engine decides, skill
orchestrates... Engine results are presented verbatim") applied to a file read.

## Worked example — "is my %GRR acceptable?"

User: *"I have `examples/secom-quality-loop` loaded. Is my %GRR acceptable?"*

1. **Detect the project.** `examples/secom-quality-loop/project.yaml` exists and parses → project
   loaded; take `project_id` from it.
2. **Map the topic.** %GRR/MSA → `msa/gage-rr.json`. Read
   `examples/secom-quality-loop/msa/gage-rr.json` and take only the fields the question needs:

   ```json
   {
     "characteristic": "Etch chamber — Chamber parameter drift",
     "pgrr_study": 8.44,
     "pgrr_tolerance": null,
     "ndc": 16,
     "verdict": "Accept"
   }
   ```

   (The file carries more than this — read what the question needs, nothing else.)
3. **Still ask the standard.** Call
   `qdb_answer_question("Is a %GRR acceptable under AIAG MSA?", standard="MSA")`. If the endpoint
   is unavailable, fall back to `apps/msa/docs/ASSUMPTIONS_LOG.md` RULE 8 / RULE 10 per
   [`fallback-sources.md`](fallback-sources.md). The project read augments the endpoint call; it
   never replaces it.
4. **Compose, two halves apart.**
   - **Project:** this project's Gage R&R study for "Etch chamber — Chamber parameter drift"
     reports a study-basis %GRR of **8.44%** with ndc = 16. Both were computed by `msa_app` and
     stored in `msa/gage-rr.json`; they are read here, not recomputed. `pgrr_tolerance` is `null` —
     this project declares no tolerance, so there is no tolerance-basis figure to report.
   - **Standard:** AIAG MSA (4th Ed.), Ch. II Sec. D, Table II-D 1 "GRR Criteria" — under
     10 percent is *"Generally considered to be an acceptable measurement system"*; 10 percent to
     30 percent *"May be acceptable for some applications"*. AIAG's published ndc criterion is
     `>= 5` (same chapter and section).
   - **Verdict:** 8.44% falls under 10 percent and ndc = 16 clears the ndc floor of 5, which is why
     the file's own recorded `verdict` is `"Accept"`. Present that as agreement between the
     project's stored verdict and the standard's bands — not as a fresh judgement made here — and
     keep AIAG's own caveat attached (RULE 8): *"The use of the GRR guidelines as threshold
     criteria alone is NOT an acceptable practice for determining the acceptability of a
     measurement system."* %GRR is one input; ndc and process context matter too, and both are
     present here.
5. **Trace every number.** Each figure above came either from a `Read` of the artifact file or from
   the endpoint / `ASSUMPTIONS_LOG.md` citation. This skill states no %GRR number it computed
   itself.

**Still not a study runner.** A question that carries *data* — "run a Gage R&R on this study",
"re-score this failure mode" — remains `msa`'s or `fmea`'s job even with a project loaded. Having a
project on disk widens what this skill can *read*, not what it may *compute*.
