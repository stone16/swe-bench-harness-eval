# A/B Experiment — Does cross-model peer review fix harness-lite's failures?

> **TL;DR**: We took the 3 instances harness-lite failed and re-ran them with
> `cross_model_review=true` (Codex peer review enabled). **Result: 0/3
> resolved.** Cross-model peer review changed the patch strategy on 2 of 3
> instances but **could not flip any failure to a pass**. This is a strong
> negative result with concrete implications for harness's roadmap.

## Hypothesis

> "Harness-lite's failures (`astropy-14369`, `django-10097`,
> `matplotlib-20676`) all involve over-/under-restrictive fixes that a
> single-LLM Evaluator missed. **If we add a different-vendor peer (Codex)
> via the harness's `review-loop` skill, the peer should catch at least some
> of these failures by reasoning from a different bias point.**"

## Setup

Identical conditions to the main run except for one bit-flip in config:

| Setting | Harness-lite | Harness-full | 
|---|:-:|:-:|
| `max_spec_rounds` | 1 | 1 |
| `max_eval_rounds` | 3 | 3 |
| **`cross_model_review`** | **false** | **true** ← only change |
| `cross_model_peer` | — | `codex` |
| `auto_retro` | false | false |
| `skip_full_verify` | true | true |
| Host model | Opus 4.7 | Opus 4.7 |
| Peer model | — | Codex (codex-cli 0.130.0) |

Each harness-full run budget: $80 (vs $50 for lite). Timeout: 60 min/instance.

## Results

| # | Instance | Lite verdict | Full verdict | Patch differed? | Strategy delta |
|---|---|:-:|:-:|:-:|---|
| 1 | `astropy-14369` | ✗ 2/3 FAIL_TO_PASS | ✗ 2/3 FAIL_TO_PASS | **YES** | 61-line string preprocessor → **108-line LALR grammar rewrite** |
| 2 | `django-10097` | ✗ 431/438 FAIL + 5 reg | ✗ 431/438 FAIL + 5 reg | **NO** | identical regex patch |
| 3 | `matplotlib-20676` | ✗ 0/2 FAIL_TO_PASS | ✗ 0/2 FAIL_TO_PASS | **YES** | ToolLineHandles internal rewrite → **SpanSelector wrapper with view-limit save/restore** |

**Score: 0/3 resolved. Strategy changed on 2/3. Outcome changed on 0/3.**

## Per-instance analysis

### `astropy__astropy-14369` — sophisticated patch, same failure

Harness-lite added a `_normalize_chained_division()` helper that rewrites
`a/b/c/d` → `a/(b.c.d)` at the string level **before** parsing. Crude but
effective for the documented positive cases.

Harness-full (with Codex peer) **escalated to a structurally correct fix**:
it modified the LALR grammar's `division_of_units` rule from right-recursive
(`unit_expression DIVISION combined_units`) to left-recursive
(`combined_units DIVISION product_of_units`), and regenerated the parser
table (`cds_parsetab.py`).

**This is the "right" fix in a textbook sense** — left-recursion is how
LALR parsers encode left-associativity. But the failing hidden test is
`test_cds_grammar_fail[km/s.Mpc-1]` — a string that the CDS standard
**explicitly requires to be rejected as invalid**. Both fixes made it
parsable.

**Conclusion**: The peer reviewer didn't probe "what should remain
invalid?" — Codex agreed with Claude that the fix was complete.

### `django__django-10097` — peer agreed with the over-restrictive regex

Harness-lite changed URLValidator regex from
`(?:\S+(?::\S*)?@)?` to `(?:[^\s:@/]+(?::[^\s:@/]*)?@)?`.

Harness-full (with Codex peer) produced **the literally identical patch**.
Diff: empty.

This means the Codex peer reviewed the regex, considered the alternatives,
and **agreed** with the over-restrictive `[^\s:@/]+` pattern. Both LLMs
optimized for "reject the bad cases the issue lists" and neither asked
"what about valid characters like `.`, `+`, `%`, `~`?"

**Conclusion**: When the spec describes positive cases ("reject X") but
not negative cases ("but keep accepting Y, Z"), both vendors have the same
blind spot.

### `matplotlib__matplotlib-20676` — wrong-layer fix, escalated to right-layer, still wrong

Harness-lite rewrote `ToolLineHandles` internals to use manual
`axhline`/`axvline` transforms (wrong layer — the bug isn't in
`ToolLineHandles`).

Harness-full **escalated to the right layer**: it modified
`SpanSelector._setup_edge_handle` to **snapshot and restore view limits**
around the `ToolLineHandles` construction. This is exactly the kind of
"the bug is at the call site, not the callee" insight that cross-model
review should catch.

But the hidden tests still fail 0/2 — meaning even the right-layer fix
doesn't satisfy the test expectations. The bug needs a deeper structural
change neither LLM proposed.

**Conclusion**: Codex peer correctly identified the layer mismatch, but
both LLMs still produced a fix that doesn't satisfy the tests.

## What this tells us

### What cross-model peer review DOES do (qualitative)

- **Pushed back on wrong-file/wrong-layer choices** (matplotlib-20676)
- **Pushed back on hacky vs structural fixes** (astropy-14369 went from
  string preprocessor to grammar rule)
- Produces **better-quality patches** (more structurally correct)

### What cross-model peer review DOES NOT do (this experiment)

- **Catch over-/under-restrictive fixes when both LLMs share the bias**
  (django-10097)
- **Probe negative-case regression risk** that the spec doesn't enumerate
  (astropy-14369, all 3 instances)
- **Flip a FAIL → PASS** when the underlying ground-truth tests have
  edge cases neither LLM anticipates

### Concrete recommendation for harness's roadmap

**Don't add more peer reviewers. Add explicit negative-case probes.**

The harness skill's next iteration should bake in:

1. **Negative-case fuzz step in `harness-evaluator.md`** — for any change to
   a parser, regex, validator, or function whose contract includes "must
   reject input X", auto-generate adversarial inputs from both the
   accept-side and the reject-side. Run them. Report mismatches.

2. **Spec template enhancement** — for bug-fix specs, the
   `Success Criteria` section should be required to include negatives:
   ```
   ### Must reject (regression guard)
   - input X (currently rejected; must remain rejected after fix)
   - input Y (was accepted incorrectly; must be rejected after fix)
   ```

3. **Wrong-file probe** — re-read the spec independently, nominate 2-3
   plausible fix locations, require Generator to justify its chosen one
   against the alternatives.

Cross-model peer review is still valuable for **strategy quality**
(picking the right layer, avoiding hacks), but it's **not sufficient for
correctness** when both LLMs share the same prior.

## Cost / time data

| Run | Total cost | Total wall time | Per-instance cost | Per-instance wall time |
|---|---|---|---|---|
| Harness-lite (this slice) | ~$60-90 | ~3.5h sequential | ~$6-9 | ~20 min |
| Harness-full (3 instances) | ~$100-130 | ~2h (parallel) | ~$33-43 | ~40-60 min |

**Cost ratio**: harness-full was ~5× more expensive per instance with no
correctness improvement on these 3 cases. (For the original 7 instances
harness-lite succeeded on, harness-full might marginally improve or
maintain — but that's a separate experiment we didn't run.)

## Reproduce

```bash
# Harness-lite (already in main run)
bash scripts/run_harness.sh <iid>

# Harness-full (this experiment) — only difference is HARNESS_FULL=1 env var
HARNESS_FULL=1 MAX_BUDGET_USD=80 TIMEOUT_SECONDS=3600 \
    bash scripts/run_harness.sh <iid>

# Grade
.venv/bin/python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Verified \
    --predictions_path predictions/harness_full.jsonl \
    --max_workers 1 --run_id harness_full_v1 --namespace ''
```

Predictions and grader reports for both runs are in:
- `predictions/_individual/*.jsonl` (lite) + `*-full-codex-peer.jsonl` (full)
- `logs/run_evaluation/harness_v1/...` (lite grader reports)
- `logs/run_evaluation/harness_full_v1/...` (full grader reports)
- `logs/run_evaluation/harness_full_v1_mpl/...` (matplotlib via Docker Hub)
