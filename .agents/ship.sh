#!/usr/bin/env bash
# Antigravity stages 1-3 of the Quality Platform ship pipeline.
# Usage: ./.agents/ship.sh "<issue number or feature description>"
# Stops at the first failing stage. Never touches git.
set -euo pipefail

REPO="/Users/sid/Documents/Claude/Projects/Quality Platform/quality-platform"
cd "$REPO"

TASK="${1:?usage: ship.sh \"<issue or description>\"}"
MODEL="${AGY_MODEL:-}"                     # optional: export AGY_MODEL=... to pin
EFFORT="${AGY_EFFORT:-high}"
MODEL_FLAG=""; [ -n "$MODEL" ] && MODEL_FLAG="--model $MODEL"

# The Team Lead owns .pipeline/ creation and clearing. We only require it exists.
[ -d .pipeline ] || { echo "ERROR: .pipeline/ missing — the Claude Team Lead creates it."; exit 2; }

# Refuse to run on a branch we shouldn't be on.
BRANCH=$(git rev-parse --abbrev-ref HEAD)
case "$BRANCH" in
  main|dev|test) echo "ERROR: on protected branch '$BRANCH'. The Team Lead must create a feature branch first."; exit 2;;
esac
echo "Branch: $BRANCH"

run_stage () {          # run_stage <agent> <expected-output-file> <prompt>
  local agent="$1" out="$2" prompt="$3"
  echo "=== stage: $agent ==="
  if ! agy -p "$prompt" --agent "$agent" --effort "$EFFORT" $MODEL_FLAG --dangerously-skip-permissions --print-timeout 15m \
        --output-format text | tee ".pipeline/${agent}.stdout.log"; then
    echo "STAGE FAILED (non-zero exit): $agent"; exit 1
  fi
  [ -s "$out" ] || { echo "STAGE FAILED: $agent did not write $out"; exit 1; }
  echo "--- wrote $out ---"
}

run_stage research .pipeline/spec.md \
  "Task: ${TASK}. Follow your agent instructions exactly. Write .pipeline/spec.md and stop."

if grep -q "^## OPEN QUESTIONS" .pipeline/spec.md; then
  echo; echo "STOP: spec.md has OPEN QUESTIONS. Escalate to the SME before coding."
  sed -n '/^## OPEN QUESTIONS/,/^## /p' .pipeline/spec.md
  exit 3
fi

run_stage coder  .pipeline/changes.md \
  "Implement .pipeline/spec.md exactly. Write .pipeline/changes.md and stop."

run_stage tester .pipeline/test-results.md \
  "Test the changes in .pipeline/changes.md. Negative controls are mandatory. Write .pipeline/test-results.md and stop."

if ! head -5 .pipeline/test-results.md | grep -qi "PASS"; then
  echo; echo "STOP: tester verdict is not PASS. Do not hand off to review."; exit 4
fi

# Residue guard — a stage that died mid-mutation can leave the tree dirty.
# NOTE: exclude-dirs are load-bearing. Plain `grep -r --include="*.py" .` in this repo
# walks ~15,500 files (7,400+ inside .venv) and can false-positive on vendored code.
echo "=== residue check ==="
git status --short
if grep -rn "# MUTATION" --include="*.py" \
     --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=.git \
     --exclude-dir=node_modules --exclude-dir=spikes --exclude-dir=marketing . ; then
  echo "ERROR: mutation residue left in the tree. Clean before handing off."; exit 5
fi

echo
echo "STAGES 1-3 COMPLETE on $BRANCH."
echo "Hand off to the Claude Team Lead for stage 4 (reviewer)."
