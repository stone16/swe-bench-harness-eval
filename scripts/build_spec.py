#!/usr/bin/env python3
"""Build harness spec.md from SWE-bench problem_statement.

For each selected instance, emit `specs/<instance_id>.spec.md` that the
harness can ingest autonomously (no human in the loop). The harness expects
a YAML frontmatter + sections: Goal / Success Criteria / Checkpoints /
Technical Approach / Out of Scope / Open Questions.

The translation is intentionally MINIMAL — we only see what a developer
opening the GitHub issue would see. We do NOT include FAIL_TO_PASS test
names or test code; doing so would invalidate comparison against the
public baselines that played by the same rule.
"""
import datetime as dt
import json
import re
import uuid
from pathlib import Path

from datasets import load_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_PATH = REPO_ROOT / "instances" / "candidates.json"
SPECS_DIR = REPO_ROOT / "specs"


def clean_issue_text(text: str) -> str:
    """Strip GitHub HTML comment templates and excessive whitespace.

    Real SWE-bench problem_statements are pasted directly from GitHub
    issues, so they contain `<!-- ... -->` template comments that the
    issuer didn't fill in. These are pure noise for the LLM.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ===========================================================================
# >>> USER CONTRIBUTION POINT <<<
# ===========================================================================
# This is the load-bearing prompt template. The wording here decides whether
# the harness behaves like:
#   - a focused bug-fixer (good for SWE-bench: minimal diffs)
#   - a feature-developer (will add tests, refactors → larger diff, more
#     chances to break PASS_TO_PASS)
#   - a defensive maintainer (over-broad guard clauses)
#
# Constraints to encode:
#   1. The harness MUST NOT add new public APIs or features.
#   2. The harness MUST NOT modify or add tests under tests/ (the grader
#      will overlay its own test_patch — any test changes we make will be
#      overwritten and may confuse the grader).
#   3. The harness SHOULD reproduce the bug first, then fix.
#   4. The patch should be the MINIMUM diff that resolves the symptom.
#
# Recommended wording is below — feel free to tighten it.
# ===========================================================================
GOAL_TEMPLATE = """\
Resolve the bug described in the GitHub issue below. The fix must:

1. Reproduce the reported failure first (write a minimal repro script in
   `/tmp/repro.py`), then implement the fix, then confirm the repro now
   passes.
2. Change ONLY library/source files — do not modify, add, or remove anything
   under `tests/`, `testing/`, or any `*_test.py` file. The grader supplies
   its own tests.
3. Preserve all existing public API signatures and behavior unrelated to the
   bug. The smallest diff that makes the issue's repro pass without breaking
   any other behavior wins.
4. NOT add new public APIs, configuration options, or features.

## Original issue

{issue_body}
"""

SUCCESS_CRITERIA_TEMPLATE = """\
- [ ] The repro script in `/tmp/repro.py` (written during the reproduce step) ran red before the fix and runs green after.
- [ ] No files under `tests/`, `testing/`, or matching `*_test.py` were modified.
- [ ] No new public API symbols were added (verify via `git diff --stat` review).
- [ ] The diff is scoped to the minimum number of source files necessary.
"""
# ===========================================================================
# >>> END USER CONTRIBUTION POINT <<<
# ===========================================================================


def build_spec(instance: dict, problem_statement: str) -> str:
    """Assemble a complete harness spec.md from an instance row."""
    iid = instance["instance_id"]
    repo = instance["repo"]
    short_id = uuid.uuid5(uuid.NAMESPACE_DNS, iid).hex[:8]
    now = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    title = f"Fix {iid}"
    cleaned = clean_issue_text(problem_statement)

    goal_section = GOAL_TEMPLATE.format(issue_body=cleaned)

    return f"""---
task_id: {short_id}
title: {title}
version: 1
status: approved
branch: eval/{iid}
created: {now}
updated: {now}
source_repo: {repo}
source_instance: {iid}
---

# {title}

## Goal
{goal_section}

## Success Criteria
{SUCCESS_CRITERIA_TEMPLATE}

## Checkpoints

### Checkpoint 01: Reproduce and fix
- Scope: Reproduce the failure from the issue, then make the smallest possible source-code change that eliminates the failure without modifying tests or adding new public API.
- Acceptance criteria:
  - [ ] `/tmp/repro.py` exists and runs cleanly (exit 0) after the fix.
  - [ ] `git diff --stat HEAD~ -- tests/ testing/ '**/*_test.py'` is empty.
  - [ ] Imports unchanged for any module not central to the bug.
  - [ ] Generator's output-summary.md identifies the single root cause and explains why this diff is minimal.
- Depends on: none
- Type: backend

## Technical Approach
1. Read the failing stack trace / repro from the issue body.
2. Write `/tmp/repro.py` that triggers the exact failure cited.
3. Locate the smallest set of source files implicated by the trace.
4. Apply the minimum change that makes the repro pass.
5. Spot-check related code paths (Evaluator's Tier-2 review) for regression risk.

## Out of Scope
- Refactoring unrelated code, even if "while we're here" temptation arises.
- Adding new tests, fixtures, or test utilities.
- Updating documentation or changelogs.
- Modifying CI configuration, dependencies, or build files.

## Open Questions
(None — the issue body is the authoritative spec. Generator should
treat any ambiguity as "preserve existing behavior".)
"""


def main() -> int:
    candidates = json.loads(CANDIDATES_PATH.read_text())
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    by_id = {ex["instance_id"]: ex for ex in ds}

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    for inst in candidates:
        iid = inst["instance_id"]
        row = by_id[iid]
        spec_md = build_spec(inst, row["problem_statement"])
        out = SPECS_DIR / f"{iid}.spec.md"
        out.write_text(spec_md)
        print(f"  wrote {out.relative_to(REPO_ROOT)}  ({len(spec_md)} bytes)")
    print(f"\n{len(candidates)} specs written to {SPECS_DIR.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
