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
PREDICTIONS_DIR="$REPO_ROOT/predictions/_individual"  # one JSONL line per file
PREDICTIONS="$REPO_ROOT/predictions/harness.jsonl"    # consolidated, built by consolidate.py
LOGS_DIR="$REPO_ROOT/logs"
CANDIDATES="$REPO_ROOT/instances/candidates.json"

MODEL_NAME="${MODEL_NAME:-harness-lite-claude-opus-4-7}"
MAX_BUDGET_USD="${MAX_BUDGET_USD:-50}"
MAX_TURNS="${MAX_TURNS:-200}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-1800}"  # 30 min/instance

mkdir -p "$WORKDIRS" "$LOGS_DIR" "$PREDICTIONS_DIR"
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

# Already-completed instances (avoid re-running).
# Source of truth is the per-instance prediction file: one file == one
# completed run. This is parallel-safe (no shared file to grep against)
# and also catches predictions already merged into the consolidated JSONL.
already_done() {
  local iid="$1"
  # Mode-aware filename — harness-full writes to a -full-codex-peer suffix
  # so a prior harness-lite run doesn't cause it to skip.
  local suffix=""
  if [[ "${HARNESS_FULL:-0}" == "1" ]]; then
    suffix="-full-codex-peer"
  fi
  if [[ -s "$PREDICTIONS_DIR/${iid}${suffix}.jsonl" ]]; then
    return 0
  fi
  return 1
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

  # Force config. Two modes controlled by HARNESS_FULL env var:
  #   harness-lite (default): Gen+Eval loop only, no cross-model peer
  #   harness-full (HARNESS_FULL=1): adds Codex cross-model review-loop
  #
  # In both modes we skip full-verify (no upstream PR target) and retro
  # (single-task eval). Spec rounds=1 because spec is pre-generated offline.
  local cross_model="false"
  local model_label_suffix=""
  if [[ "${HARNESS_FULL:-0}" == "1" ]]; then
    cross_model="true"
    model_label_suffix="-full-codex-peer"
  fi
  cat > "$work/.harness/config.json" <<EOF
{
  "max_spec_rounds": 1,
  "max_eval_rounds": 3,
  "cross_model_review": $cross_model,
  "cross_model_peer": "codex",
  "cross_model_read_only": false,
  "auto_retro": false,
  "skip_full_verify": true,
  "autonomous_pr": false,
  "coverage_threshold": 0
}
EOF
  # Mode-specific suffix so harness-full predictions don't collide with
  # harness-lite ones in _individual/
  local mode_iid="${iid}${model_label_suffix}"

  # Invoke harness in headless mode
  local prompt="harness execute $tid

The spec is already approved at .harness/$tid/spec.md. Skip the planning
phase entirely (it was completed offline). Begin Checkpoint 01 immediately:
read the spec, follow its Goal/Acceptance criteria exactly, and complete
through the per-checkpoint Evaluator loop. Do NOT run E2E, review-loop,
full-verify, PR, or retro — config.json has them disabled. Stop after the
Evaluator returns PASS on Checkpoint 01."

  # Retry on Anthropic 529 "Overloaded" errors with exponential backoff.
  # The harness's first ~30s is loading plugin context; if API is overloaded
  # at that exact moment, we get a 529 and fail fast. A short retry typically
  # recovers because parallel clients don't stay in lockstep.
  local rc=1 attempt=0
  while (( attempt < 3 )); do
    attempt=$((attempt + 1))
    echo "[$iid] claude attempt $attempt/3" | tee -a "$log"
    timeout "$TIMEOUT_SECONDS" claude -p "$prompt" \
      --add-dir "$work" \
      --dangerously-skip-permissions \
      --max-turns "$MAX_TURNS" \
      --max-budget-usd "$MAX_BUDGET_USD" \
      --append-system-prompt "You are operating inside $work. All file operations stay inside that directory. Do not modify files under tests/, testing/, or **/*_test.py — the grader supplies its own." \
      </dev/null >>"$log" 2>&1
    rc=$?
    if (( rc == 0 )); then
      break
    fi
    if tail -5 "$log" | grep -qiE "529|Overloaded|rate limit|too many requests"; then
      local sleep_for=$(( 30 * attempt ))   # 30s, 60s, 90s
      echo "[$iid] overload detected, sleeping ${sleep_for}s before retry" | tee -a "$log"
      sleep "$sleep_for"
    else
      # Different failure mode — no point retrying
      break
    fi
  done
  echo "[$iid] claude final exit code: $rc" | tee -a "$log"

  # Capture the prediction patch (diff from base_commit on tracked source files,
  # excluding any test files in case the generator misbehaved despite the spec).
  local patch_file; patch_file="$(mktemp)"
  # Excludes:
  #  - test files (grader supplies its own test_patch)
  #  - .gitignore (engine init mutates it; pure infrastructure noise)
  #  - .harness/ (entirely our scaffolding, never part of a real fix)
  (cd "$work" && git diff "$sha" -- . \
      ':(exclude)tests' ':(exclude)testing' ':(exclude)**/*_test.py' \
      ':(exclude)**/test_*.py' \
      ':(exclude).gitignore' ':(exclude).harness' \
      > "$patch_file") 2>>"$log"

  local nlines; nlines=$(wc -l < "$patch_file" | tr -d ' ')

  # Capture which mode produced this for the filename suffix
  : "${mode_iid:=$iid}"

  # Only write the per-instance prediction if we actually got a non-empty
  # patch. Empty patches are noise — they'd make already_done() falsely skip
  # the instance on rerun, and the grader would treat them as no_generation.
  local out_path="$PREDICTIONS_DIR/${mode_iid}.jsonl"
  local model_for_record="${MODEL_NAME}${model_label_suffix:-}"
  if (( nlines > 0 )); then
    "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/_append_prediction.py" \
        --iid "$iid" --model "$model_for_record" --patch-file "$patch_file" \
        > "$out_path"
    echo "[$iid] === done (patch=$nlines lines, exit=$rc, prediction → $(basename "$out_path")) ===" | tee -a "$log"
  else
    rm -f "$out_path"
    echo "[$iid] === FAILED (empty patch, exit=$rc) — no prediction written, retry next run ===" | tee -a "$log"
    rm -f "$patch_file"
    return 1
  fi
  rm -f "$patch_file"
}

main() {
  prefetch_metadata
  if [[ $# -gt 0 ]]; then
    run_one "$1"
    return
  fi
  # Iterate via an array instead of pipe-to-while. The pipe pattern fails
  # silently when any inner command (e.g. claude -p) consumes stdin from the
  # pipe and drains the remaining iids.
  local iids=()
  while IFS= read -r line; do
    iids+=("$line")
  done < <("$REPO_ROOT/.venv/bin/python" -c "
import json, sys
for c in json.load(open('$CANDIDATES')):
    print(c['instance_id'])
")
  echo "Will process ${#iids[@]} instances: ${iids[*]}" >&2
  for iid in "${iids[@]}"; do
    run_one "$iid" || echo "[$iid] FAILED" >&2
  done
}

main "$@"
