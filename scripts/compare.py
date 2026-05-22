#!/usr/bin/env python3
"""Compare harness verdicts against the 5 public baselines, per-instance.

Reads:
  - results/eval.<run_id>.json   (swebench official grader output)
  - predictions/harness.jsonl    (the patches we submitted)
  - baselines/per_instance.json  (5 public baselines × all instances)
  - instances/candidates.json    (our 10 selected, with difficulty + repo)

Writes:
  - results/compare.md           (human-readable verdict matrix + analysis)
  - results/compare.json         (machine-readable summary for further analysis)

The output is designed to answer four specific questions:
  Q1. How often does harness match the strongest baseline (Sonar)?
  Q2. On instances 0-1 baselines solved, does harness break through?
  Q3. On instances all 5 baselines solved, does harness regress?
  Q4. Per-tier: easy/medium/hard resolve rate vs comparable baselines?
"""
import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Difficulty buckets in SWE-bench Verified
TIER_LABELS = {
    "<15 min fix": "easy",
    "15 min - 1 hour": "medium",
    "1-4 hours": "hard",
    ">4 hours": "hard",
}

BASELINE_ALIASES = [
    "sonar_opus_4_5",
    "openhands_opus_4_5",
    "openhands_sonnet_4",
    "tools_opus_4",
    "sweagent_sonnet_4",
]

# Compact display labels for the verdict matrix (disambiguates duplicate
# agent names that differ only by model).
BASELINE_LABELS = {
    "sonar_opus_4_5":      "sonar/o45",
    "openhands_opus_4_5":  "oh/o45",
    "openhands_sonnet_4":  "oh/s4",
    "tools_opus_4":        "tools/o4",
    "sweagent_sonnet_4":   "swea/s4",
}


def load_harness_results(run_id: str) -> dict[str, str]:
    """Load swebench per-instance reports → {instance_id: verdict}.

    We read `logs/run_evaluation/<run_id>/*/<iid>/report.json` directly
    instead of the top-level summary, because swebench's `make_run_report`
    walks the entire dataset to build comparison test_specs (not just our
    predicted instances), and a single transient network failure to any
    upstream repo will abort summary generation. The per-instance reports
    are unaffected — they're written as each evaluation completes.
    """
    base = REPO_ROOT / "logs" / "run_evaluation" / run_id
    if not base.exists():
        raise FileNotFoundError(f"No grader output dir for run_id={run_id} at {base}")

    out: dict[str, str] = {}
    for report_path in base.glob("*/*/report.json"):
        data = json.loads(report_path.read_text())
        for iid, rec in data.items():
            if not rec.get("patch_exists") or rec.get("patch_is_None"):
                out[iid] = "no_generation"
            elif not rec.get("patch_successfully_applied", False):
                out[iid] = "error"
            elif rec.get("resolved", False):
                out[iid] = "resolved"
            else:
                out[iid] = "failed"
    return out


def verdict_glyph(v: str) -> str:
    return {
        "resolved": "✓",
        "failed": "✗",
        "no_generation": "∅",
        "error": "!",
        None: "-",
    }.get(v, "?")


def build_matrix(
    candidates: list[dict],
    harness_verdicts: dict[str, str],
    baselines: dict[str, dict[str, str]],
) -> list[dict]:
    rows = []
    for c in candidates:
        iid = c["instance_id"]
        row = {
            "instance_id": iid,
            "repo": c["repo"],
            "tier": TIER_LABELS.get(c["difficulty"], "unknown"),
            "difficulty": c["difficulty"],
            "baseline_hardness": c["_hardness"],
            "harness": harness_verdicts.get(iid),
        }
        per_baseline = baselines.get(iid, {})
        for alias in BASELINE_ALIASES:
            row[alias] = per_baseline.get(alias)
        rows.append(row)
    return rows


def render_markdown(rows: list[dict]) -> str:
    lines = ["# Harness vs Public Baselines — per-instance verdict matrix", ""]
    lines.append("Legend: ✓ resolved · ✗ failed · ∅ no patch generated · ! error · - missing")
    lines.append("")

    # Header
    header = ["#", "instance", "tier", "diff", "harness"] + [
        BASELINE_LABELS[a] for a in BASELINE_ALIASES
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    for i, r in enumerate(rows, 1):
        cells = [
            str(i),
            r["instance_id"].split("__")[-1],
            r["tier"],
            r["baseline_hardness"][:3],
            verdict_glyph(r["harness"]),
            *[verdict_glyph(r[a]) for a in BASELINE_ALIASES],
        ]
        lines.append("| " + " | ".join(cells) + " |")

    # Aggregates
    lines.append("")
    lines.append("## Aggregate resolve rates")
    lines.append("")
    lines.append("| system | overall | easy | medium | hard |")
    lines.append("|---|---|---|---|---|")

    def rate(rows_in: list[dict], key: str) -> str:
        n = sum(1 for r in rows_in if r.get(key) is not None)
        ok = sum(1 for r in rows_in if r.get(key) == "resolved")
        if n == 0:
            return "n/a"
        return f"{ok}/{n} ({100*ok/n:.0f}%)"

    systems = [("harness", "harness")] + [(BASELINE_LABELS[a], a) for a in BASELINE_ALIASES]
    for label, key in systems:
        easy = [r for r in rows if r["tier"] == "easy"]
        med = [r for r in rows if r["tier"] == "medium"]
        hard = [r for r in rows if r["tier"] == "hard"]
        lines.append(
            f"| {label} | {rate(rows, key)} | {rate(easy, key)} | {rate(med, key)} | {rate(hard, key)} |"
        )

    # Differentiation analysis
    lines.append("")
    lines.append("## Differentiation analysis")
    lines.append("")

    breakthrough = [r for r in rows if r["harness"] == "resolved" and r["baseline_hardness"] == "few-solved"]
    regression = [r for r in rows if r["harness"] != "resolved" and r["baseline_hardness"] == "all-solved"]
    unique_solve = [
        r for r in rows
        if r["harness"] == "resolved"
        and all(r.get(a) != "resolved" for a in BASELINE_ALIASES)
    ]
    unique_fail = [
        r for r in rows
        if r["harness"] != "resolved"
        and all(r.get(a) == "resolved" for a in BASELINE_ALIASES)
    ]

    lines.append(f"- **Breakthroughs** (harness solved a 0-1 baseline instance): {len(breakthrough)}")
    for r in breakthrough:
        lines.append(f"  - `{r['instance_id']}` ({r['tier']})")
    lines.append(f"- **Regressions** (harness failed an all-solved instance): {len(regression)}")
    for r in regression:
        lines.append(f"  - `{r['instance_id']}` ({r['tier']}) — harness verdict: {r['harness']}")
    lines.append(f"- **Uniquely solved by harness**: {len(unique_solve)}")
    for r in unique_solve:
        lines.append(f"  - `{r['instance_id']}`")
    lines.append(f"- **Uniquely failed by harness**: {len(unique_fail)}")
    for r in unique_fail:
        lines.append(f"  - `{r['instance_id']}` — harness: {r['harness']}")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="harness_v1",
                    help="run_id passed to swebench grader")
    args = ap.parse_args()

    candidates = json.loads((REPO_ROOT / "instances" / "candidates.json").read_text())
    baselines = json.loads((REPO_ROOT / "baselines" / "per_instance.json").read_text())
    harness_verdicts = load_harness_results(args.run_id)

    rows = build_matrix(candidates, harness_verdicts, baselines)
    md = render_markdown(rows)

    out_md = REPO_ROOT / "results" / "compare.md"
    out_json = REPO_ROOT / "results" / "compare.json"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md)
    out_json.write_text(json.dumps(rows, indent=2))

    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
