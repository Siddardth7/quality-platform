---
description: Team Lead — cut a version release from `dev` to `main` and tag it for production.
---
You are the Team Lead for the Quality Platform. Cut release $ARGUMENTS (e.g. v0.6.0) from `dev` to `main`.

1. Confirm the version's issue set is fully merged into `dev` and the issues are closed
   (`gh issue list --milestone "<the week milestone>"`).
2. Confirm the full gate is green on `dev` and every coverage bar holds
   (quality_core.io 100%, quality_core.schema 100% line+branch, SPC ≥95%).
3. Update CHANGELOG.md and the version single-source-of-truth for $ARGUMENTS (on a short-lived
   branch off `dev`, PR'd into `dev` first if `dev` is protected).
4. Open a PR `dev → main` (`gh pr create --base main --head dev`) with the release notes.
   Do NOT merge — the SME approves.
5. After the SME merges: tag `$ARGUMENTS` on `main` (`git tag $ARGUMENTS && git push --tags`),
   create the GitHub release, and confirm the production deploy (Streamlit Cloud follows `main`).

`main` is production. Only `dev` merges into it, at version boundaries.
