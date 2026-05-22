#!/usr/bin/env python3
"""Select 10 stratified SWE-bench Verified instances for harness evaluation.

Strategy (configurable below in pick_instances):
  - Stratify by difficulty: 3 easy + 4 medium + 3 hard
  - Within each tier, mix instances by baseline "hardness":
    * "all-solved"   — every baseline resolved it (sanity check)
    * "majority"     — 3-4 of 5 baselines resolved it
    * "split"        — exactly half resolved (1-2 of 5)
    * "few-solved"   — only 0-1 baseline resolved it (stress test)
  - Prefer diverse repos (avoid all-django bias)
  - Output: instances/selected.json with full per-instance metadata

The selection strategy is the load-bearing choice — it determines what kind of
signal we can extract from only 10 instances. See pick_instances() for the
exact rule.
"""
import json
import random
from collections import Counter
from pathlib import Path
from typing import Iterator

from datasets import load_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINES_PATH = REPO_ROOT / "baselines" / "per_instance.json"
OUT_PATH = REPO_ROOT / "instances" / "candidates.json"

# Difficulty tiers in SWE-bench Verified (free-text labels in dataset).
TIER_EASY = "<15 min fix"
TIER_MED = "15 min - 1 hour"
TIER_HARD = "1-4 hours"
TIER_VERY_HARD = ">4 hours"

# Deterministic seed so re-running yields the same 10 instances.
SEED = 42


def baseline_score(per_instance: dict, iid: str) -> tuple[int, list[str]]:
    """Return (resolved_count, list_of_baselines_that_resolved)."""
    rec = per_instance.get(iid, {})
    resolved_by = [b for b, v in rec.items() if v == "resolved"]
    return len(resolved_by), resolved_by


def hardness_bucket(resolved_count: int, total_baselines: int) -> str:
    """Group instances by how hard they are FOR PUBLIC BASELINES."""
    if resolved_count == total_baselines:
        return "all-solved"
    if resolved_count >= total_baselines - 1:
        return "majority"
    if resolved_count >= 2:
        return "split"
    return "few-solved"


def pick_from_tier(
    pool: list[dict],
    n: int,
    desired_hardness: list[str],
    rng: random.Random,
) -> list[dict]:
    """Pick n instances from pool, trying to satisfy desired_hardness mix.

    desired_hardness is a list of hardness-bucket strings the same length as n.
    For each desired bucket, sample one instance with that bucket label. If
    none available, fall back to closest bucket.
    """
    by_bucket: dict[str, list[dict]] = {}
    for ex in pool:
        by_bucket.setdefault(ex["_hardness"], []).append(ex)

    picked = []
    seen_repos: Counter[str] = Counter()
    for want in desired_hardness:
        candidates = by_bucket.get(want, [])
        # Prefer repo diversity within the same bucket
        candidates_sorted = sorted(candidates, key=lambda e: seen_repos[e["repo"]])
        if not candidates_sorted:
            # Fallback: take any remaining instance regardless of bucket
            remaining = [e for e in pool if e not in picked]
            if not remaining:
                break
            candidates_sorted = sorted(remaining, key=lambda e: seen_repos[e["repo"]])
        chosen = candidates_sorted[0]
        picked.append(chosen)
        seen_repos[chosen["repo"]] += 1
        by_bucket[chosen["_hardness"]] = [
            e for e in by_bucket.get(chosen["_hardness"], []) if e is not chosen
        ]
    return picked


def main() -> int:
    per_instance = json.loads(BASELINES_PATH.read_text())
    n_baselines = max(len(v) for v in per_instance.values())

    print(f"Loaded {len(per_instance)} instances across {n_baselines} baselines")

    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    rng = random.Random(SEED)

    # Annotate every example with baseline hardness info
    annotated = []
    for ex in ds:
        iid = ex["instance_id"]
        resolved_count, resolved_by = baseline_score(per_instance, iid)
        annotated.append({
            "instance_id": iid,
            "repo": ex["repo"],
            "difficulty": ex["difficulty"],
            "problem_statement_preview": ex["problem_statement"][:160],
            "_hardness": hardness_bucket(resolved_count, n_baselines),
            "baselines_resolved": resolved_count,
            "baselines_resolved_by": resolved_by,
            "n_baselines": n_baselines,
        })

    # Split by difficulty tier
    by_tier = {
        "easy": [e for e in annotated if e["difficulty"] == TIER_EASY],
        "medium": [e for e in annotated if e["difficulty"] == TIER_MED],
        "hard": [e for e in annotated if e["difficulty"] in (TIER_HARD, TIER_VERY_HARD)],
    }

    # ===== STRATEGY =====
    # 3 easy:    1 sanity-check (all baselines solved) + 1 split + 1 few-solved
    # 4 medium:  1 majority + 2 split + 1 few-solved
    # 3 hard:    1 split + 2 few-solved (stress test where harness should excel)
    # ====================
    picks = []
    picks += pick_from_tier(by_tier["easy"], 3,
                            ["all-solved", "split", "few-solved"], rng)
    picks += pick_from_tier(by_tier["medium"], 4,
                            ["majority", "split", "split", "few-solved"], rng)
    picks += pick_from_tier(by_tier["hard"], 3,
                            ["split", "few-solved", "few-solved"], rng)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(picks, indent=2))

    print(f"\nSelected {len(picks)} instances → {OUT_PATH}\n")
    print(f"{'#':>2} {'difficulty':<18} {'hardness':<12} {'baseln':>6} {'repo':<28} instance_id")
    print("-" * 110)
    for i, p in enumerate(picks, 1):
        print(f"{i:>2} {p['difficulty']:<18} {p['_hardness']:<12} "
              f"{p['baselines_resolved']}/{p['n_baselines']:<3} "
              f"{p['repo']:<28} {p['instance_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
