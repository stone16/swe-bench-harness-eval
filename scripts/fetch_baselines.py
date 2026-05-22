#!/usr/bin/env python3
"""Fetch per-instance pass/fail results from public SWE-bench Verified baselines.

Pulls results.json from swe-bench/experiments repo for a curated set of baselines
that are roughly comparable to a Claude-Opus-4.5-class harness. Writes a single
joined matrix to baselines/per_instance.json keyed by instance_id.

Output schema:
  {
    "instance_id": {
      "openhands_opus_4_5":   "resolved" | "failed" | "no_generation",
      "openhands_sonnet_4":   ...,
      "sweagent_sonnet_4":    ...,
      "tools_opus_4":         ...,   # bash-only "naive" Claude
      "sonar_opus_4_5":       ...,   # state-of-the-art reference
    }
  }
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "baselines" / "per_instance.json"

# Curated baselines. Each entry: (alias, experiment_directory_name)
# Picked for: (a) same model class as harness would use, (b) diversity of
# agent frameworks (single-agent tools / classical SWE-Agent / multi-agent
# OpenHands / state-of-the-art Sonar), (c) recent enough to be relevant.
BASELINES = [
    ("openhands_opus_4_5",  "20251127_openhands_claude-opus-4-5"),
    ("sonar_opus_4_5",      "20251205_sonar-foundation-agent_claude-opus-4-5"),
    ("openhands_sonnet_4",  "20250524_openhands_claude_4_sonnet"),
    ("sweagent_sonnet_4",   "20250522_sweagent_claude-4-sonnet-20250514"),
    ("tools_opus_4",        "20250522_tools_claude-4-opus"),
]


def fetch_results(experiment_dir: str) -> dict:
    """Fetch results.json for an experiment via gh api (auth, no rate limit)."""
    path = f"evaluation/verified/{experiment_dir}/results/results.json"
    raw = subprocess.run(
        ["gh", "api", f"repos/swe-bench/experiments/contents/{path}",
         "-H", "Accept: application/vnd.github.raw"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(raw)


def main() -> int:
    matrix: dict[str, dict[str, str]] = {}
    for alias, exp_dir in BASELINES:
        print(f"Fetching {alias} ({exp_dir})...", file=sys.stderr)
        try:
            data = fetch_results(exp_dir)
        except subprocess.CalledProcessError as e:
            print(f"  FAILED: {e.stderr}", file=sys.stderr)
            continue
        resolved = set(data.get("resolved", []))
        no_gen = set(data.get("no_generation", []))
        # Union of all instances mentioned across all baselines
        all_ids = resolved | no_gen | set(data.get("no_logs", []))
        for iid in all_ids:
            if iid not in matrix:
                matrix[iid] = {}
            if iid in resolved:
                matrix[iid][alias] = "resolved"
            elif iid in no_gen:
                matrix[iid][alias] = "no_generation"
            else:
                matrix[iid][alias] = "failed"
        print(f"  resolved={len(resolved)} no_gen={len(no_gen)}", file=sys.stderr)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(matrix, indent=2, sort_keys=True))
    print(f"\nWrote {len(matrix)} instances × {len(BASELINES)} baselines to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
