#!/usr/bin/env bash
# Fallback grader for instances whose env image won't build locally on
# Apple Silicon (typically the matplotlib repo's conda env can't resolve
# packages under amd64 emulation). We pull SWE-bench's official prebuilt
# images from Docker Hub instead.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_ID="${1:-harness_v1_fallback}"

cd "$REPO_ROOT"

# Build a slim predictions file with just the env-failed instances
.venv/bin/python -c "
import json
from pathlib import Path
src = Path('predictions/harness.jsonl').read_text().splitlines()
recs = [json.loads(l) for l in src if l.strip()]
keep = {'matplotlib__matplotlib-20488', 'matplotlib__matplotlib-20676'}
out = [r for r in recs if r['instance_id'] in keep]
Path('predictions/harness.matplotlib.jsonl').write_text(
    '\n'.join(json.dumps(r) for r in out) + '\n'
)
print(f'Wrote {len(out)} predictions to predictions/harness.matplotlib.jsonl')
"

# --namespace swebench tells the grader to PULL official images from
# Docker Hub (swebench/sweb.eval.*) instead of building locally.
.venv/bin/python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Verified \
    --predictions_path predictions/harness.matplotlib.jsonl \
    --max_workers 1 \
    --run_id "$RUN_ID" \
    --namespace 'swebench' 2>&1 | tee "logs/grade.$RUN_ID.log"

mkdir -p results
mv *."$RUN_ID".json results/ 2>/dev/null || true
echo "---"
echo "Done. Reports at: logs/run_evaluation/$RUN_ID/"
