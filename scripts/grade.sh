#!/usr/bin/env bash
# grade.sh — Run the official SWE-bench grader on predictions/harness.jsonl
#
# Requires Docker. On Apple Silicon, --namespace '' tells swebench to
# build images locally (the prebuilt linux/amd64 images are sluggish under
# emulation but still functional).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_ID="${1:-harness_v1}"

cd "$REPO_ROOT"
.venv/bin/python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Verified \
    --predictions_path predictions/harness.jsonl \
    --max_workers "${MAX_WORKERS:-1}" \
    --run_id "$RUN_ID" \
    --namespace '' \
    --instance_image_tag latest 2>&1 | tee "logs/grade.$RUN_ID.log"

# swebench writes summary to ./<model>.<run_id>.json
echo "---"
echo "Grader summary files:"
ls -la *."$RUN_ID".json 2>/dev/null | head -5

# Move them under results/ so compare.py finds them
mkdir -p results
mv *."$RUN_ID".json results/ 2>/dev/null || true
echo "Moved to results/"
