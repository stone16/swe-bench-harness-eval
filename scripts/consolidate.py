#!/usr/bin/env python3
"""Merge per-instance prediction files into the consolidated predictions.jsonl.

Each parallel worker writes its result to predictions/_individual/<iid>.jsonl
(one line). This script collects them and produces predictions/harness.jsonl
sorted by instance_id for stable diffs.

Idempotent. Safe to run while workers are still producing files (it just
won't pick up files written after it starts).
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDIV_DIR = REPO_ROOT / "predictions" / "_individual"
OUT = REPO_ROOT / "predictions" / "harness.jsonl"


def main() -> int:
    if not INDIV_DIR.exists():
        print(f"No individual predictions dir at {INDIV_DIR}")
        return 1
    records = []
    for f in sorted(INDIV_DIR.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    records.sort(key=lambda r: r["instance_id"])
    OUT.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    print(f"Consolidated {len(records)} predictions → {OUT}")
    for r in records:
        nlines = r["model_patch"].count("\n")
        print(f"  {r['instance_id']}  ({nlines} patch lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
