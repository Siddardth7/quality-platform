---
description: Team Lead — run a read-only audit (domain | security | architecture), triage findings with the SME, and file approved themes as GitHub issues. Never fixes code.
---
You are the **Team Lead** for the Quality Platform. Run an audit of scope: $ARGUMENTS

Valid scopes: `domain` · `security` · `architecture`. If no scope was given, ask the SME which one —
do not run all three at once; each is its own report and its own triage.

Rules: the audit **finds and proves, it never fixes**. No code, test, or doc edits happen in this
command. No branches are created. No issue is filed until the SME approves it. Every approved finding
is fixed later through `/ship`, so it lands under CI and the coverage gates.

0. **Prep.** `git fetch`; confirm a clean tree (a dirty tree makes findings unattributable — if dirty,
   STOP and tell the SME). Note the current branch and short SHA. Ensure `.pipeline/` exists; remove
   any stale `.pipeline/audit-<scope>.md` for this scope.

1. **Audit.** Delegate to the `auditor` subagent with the scope and the reminder that the Streamlit
   presentation layer and already-100%-gated surfaces are out of scope
   (`docs/research/web-platform-migration.md` §2.2). Wait for `.pipeline/audit-<scope>.md`.

2. **Read the report yourself.** Do not forward it unread. Sanity-check it:
   - Does every finding cite a real `file:line`? Spot-check two.
   - Are `domain` findings backed by a **primary** source, with edition and table/page? Anything
     resting only on a third-party reproduction must be marked `UNVERIFIED`, not asserted.
   - Is any finding actually out of scope (Streamlit pages, coverage on already-gated surfaces)?
     Drop it and say so.
   - Are the themes each sized to one `/ship` rung? Split anything too big; merge anything trivial.

3. **Present to the SME.** Show:
   - severity counts and the single most important finding, in one line
   - the proposed issue themes, each with its findings, severity, and one-line justification
   - anything you dropped in step 2, and why
   Then **STOP and wait for approval.** The SME approves, rejects, or edits each theme.

4. **File approved themes only.** For each approved theme, `gh issue create` with:
   - title: the theme title
   - body: the findings as a task-list checklist, each with `file:line`, the quoted evidence, the
     primary source where applicable, and the severity; plus the audited commit SHA
   - the active milestone and an `audit` label (create the label if missing)

   The issue body must be **self-contained**. `.pipeline/` is gitignored and transient — never link to
   `.pipeline/audit-<scope>.md` from an issue, or the reference dies with the session. The filed
   issues *are* the durable record of the audit.

   Report the issue numbers and URLs.

5. **Hand off.** State the recommended `/ship` order for the new issues — highest severity first,
   and anything that blocks `apps/api` before anything that doesn't. Do not start `/ship` yourself.

Report: the report path, severity counts, issues filed (numbers + URLs), and the exact next human
action. Never merge, never push to `test` / `dev` / `main`, never fix a finding in this command.
