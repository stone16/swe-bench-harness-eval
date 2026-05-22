#!/usr/bin/env bash
#
# run_harness.sh — Drive harness execution across the 10 selected instances.
#
# For each instance:
#   1. Clone the source repo at base_commit into workdirs/<instance_id>/
#   2. Copy the pre-built spec.md into .harness/<task-id>/
#   3. Seed .harness/config.json (autonomous_pr=false, all else default)
#   4. Invoke `claude -p "harness execute <task-id>"` in headless mode
#   5. Capture git diff base_commit..HEAD as the prediction patch
#   6. Append one JSONL line to predictions/harness.jsonl
#
# Resumable: skips instances that already have a prediction in the JSONL.
# Cost-bounded: respects MAX_BUDGET_USD per instance (default $30).
#
# Usage:
#   scripts/run_harness.sh                # run all 10
#   scripts/run_harness.sh <instance_id>  # run a single one (smoke test)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKDIRS="$REPO_ROOT/workdirs"
SPECS_DIR="$REPO_ROOT/specs"
PREDICTIONS="$REPO_ROOT/predictions/harness.jsonl"
LOGS_DIR="$REPO_ROOT/logs"
CANDIDATES="$REPO_ROOT/instances/candidates.json"

MODEL_NAME="${MODEL_NAME:-harness-claude-opus-4-5}"
MAX_BUDGET_USD="${MAX_BUDGET_USD:-50}"
MAX_TURNS="${MAX_TURNS:-200}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-1800}"  # 30 min/instance

mkdir -p "$WORKDIRS" "$LOGS_DIR" "$(dirname "$PREDICTIONS")"
touch "$PREDICTIONS"

# Resolve the harness engine script once
ENGINE="$(find ~/.claude/plugins/cache -path "*/harness/scripts/harness-engine.sh" -type f 2>/dev/null | head -1)"
if [[ -z "$ENGINE" ]]; then
  ENGINE="$HOME/dev/harness-engineering-skills/plugins/harness-engineering-skills/skills/harness/scripts/harness-engine.sh"
fi
if [[ ! -x "$ENGINE" ]]; then
  echo "FATAL: cannot find harness-engine.sh" >&2
  exit 1
fi
echo "Engine: $ENGINE" >&2

# Already-completed instances (avoid re-running)
already_done() {
  local iid="$1"
  grep -q "\"instance_id\": \"$iid\"" "$PREDICTIONS" 2>/dev/null
}

# Read base_commit + repo for an instance (one HF fetch is faster than per-call)
declare -A BASE_COMMIT REPO_URL TASK_ID
prefetch_metadata() {
  "$REPO_ROOT/.venv/bin/python" - <<'PY' > "$LOGS_DIR/.metadata.tsv"
import json
from datasets import load_dataset
from pathlib import Path
candidates = json.loads(Path("instances/candidates.json").read_text())
wanted = {c["instance_id"] for c in candidates}
ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
for ex in ds:
    if ex["instance_id"] in wanted:
        print("\t".join([ex["instance_id"], ex["repo"], ex["base_commit"]]))
PY
  while IFS=$'\t' read -r iid repo sha; do
    BASE_COMMIT[$iid]="$sha"
    REPO_URL[$iid]="https://github.com/${repo}.git"
  done < "$LOGS_DIR/.metadata.tsv"
}

# Extract task_id from the spec frontmatter
read_task_id() {
  local spec="$1"
  awk '/^task_id:/{print $2; exit}' "$spec"
}

run_one() {
  local iid="$1"
  local spec="$SPECS_DIR/$iid.spec.md"
  local work="$WORKDIRS/$iid"
  local log="$LOGS_DIR/$iid.log"

  if already_done "$iid"; then
    echo "[$iid] already in predictions — skip" >&2
    return 0
  fi
  if [[ ! -f "$spec" ]]; then
    echo "[$iid] missing spec $spec — skip" >&2
    return 1
  fi

  local tid; tid="$(read_task_id "$spec")"
  local sha="${BASE_COMMIT[$iid]:-}"
  local url="${REPO_URL[$iid]:-}"
  if [[ -z "$sha" || -z "$url" ]]; then
    echo "[$iid] no metadata — skip" >&2
    return 1
  fi

  echo "[$iid] === starting (task_id=$tid, base=$sha) ===" | tee -a "$log"

  # Fresh clone (shallow with --filter=blob:none to keep it light)
  if [[ -d "$work" ]]; then
    rm -rf "$work"
  fi
  git clone --filter=blob:none "$url" "$work" >>"$log" 2>&1
  (cd "$work" && git checkout -q "$sha" && git checkout -b "eval/$iid") >>"$log" 2>&1

  # Seed .harness/ directory tree using the engine
  (cd "$work" && "$ENGINE" init --task-id "$tid") >>"$log" 2>&1 || true
  mkdir -p "$work/.harness/$tid"
  cp "$spec" "$work/.harness/$tid/spec.md"

  # Force config: no PR, no full-verify (no upstream to verify against),
  # skip cross-model review (we want to compare base harness vs single-agent)
  # — but keep the per-checkpoint Evaluator loop, which IS the load-bearing
  # anti-drift mechanism.
  cat > "$work/.harness/config.json" <<EOF
{
  "max_spec_rounds": 1,
  "max_eval_rounds": 3,
  "cross_model_review": false,
  "auto_retro": false,
  "skip_full_verify": true,
  "autonomous_pr": false,
  "coverage_threshold": 0
}
EOF

  # Invoke harness in headless mode
  local prompt="harness execute $tid

The spec is already approved at .harness/$tid/spec.md. Skip the planning
phase entirely (it was completed offline). Begin Checkpoint 01 immediately:
read the spec, follow its Goal/Acceptance criteria exactly, and complete
through the per-checkpoint Evaluator loop. Do NOT run E2E, review-loop,
full-verify, PR, or retro — config.json has them disabled. Stop after the
Evaluator returns PASS on Checkpoint 01."

  timeout "$TIMEOUT_SECONDS" claude -p "$prompt" \
    --add-dir "$work" \
    --dangerously-skip-permissions \
    --max-turns "$MAX_TURNS" \
    --max-budget-usd "$MAX_BUDGET_USD" \
    --append-system-prompt "You are operating inside $work. All file operations stay inside that directory. Do not modify files under tests/, testing/, or **/*_test.py — the grader supplies its own." \
    >>"$log" 2>&1
  local rc=$?
  echo "[$iid] claude exit code: $rc" | tee -a "$log"

  # Capture the prediction patch (diff from base_commit on tracked source files,
  # excluding any test files in case the generator misbehaved despite the spec).
  local patch_file; patch_file="$(mktemp)"
  (cd "$work" && git diff "$sha" -- . \
      ':(exclude)tests' ':(exclude)testing' ':(exclude)**/*_test.py' \
      ':(exclude)**/test_*.py' \
      > "$patch_file") 2>>"$log"

  "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/_append_prediction.py" \
      --iid "$iid" --model "$MODEL_NAME" --patch-file "$patch_file" \
      >> "$PREDICTIONS"

  local nlines; nlines=$(wc -l < "$patch_file" | tr -d ' ')
  rm -f "$patch_file"
  echo "[$iid] === done (patch=$nlines lines, exit=$rc) ===" | tee -a "$log"
}

main() {
  prefetch_metadata
  if [[ $# -gt 0 ]]; then
    run_one "$1"
  else
    "$REPO_ROOT/.venv/bin/python" -c "
import json, sys
for c in json.load(open('$CANDIDATES')):
    print(c['instance_id'])
" | while read -r iid; do
      run_one "$iid" || echo "[$iid] FAILED" >&2
    done
  fi
}

main "$@"
