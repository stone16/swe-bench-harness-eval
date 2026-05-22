# Results — Harness-lite Engineering Skills on SWE-bench Verified

> **TL;DR**: On a stratified 10-instance slice of SWE-bench Verified,
> running **Claude Opus 4.7** with **harness-lite** (a stripped-down
> harness-engineering-skills config — cross-model review, full-verify,
> and retro all disabled, see "Honest Caveats"), we **resolved 7/10
> (70%)**. The headline result is the **hard tier: 2/3 (67%) vs
> OpenHands+Opus 4.7's 0/3** — these are the only instances where the
> multi-agent architecture's lift is unambiguously visible after
> controlling for model.

## Headline — same-model (Opus 4.7) comparison

| Metric | Harness-lite (this) | OpenHands ACP | Δ |
|---|---|---|---|
| Overall (10 instances) | **7/10 = 70%** | 6/10 = 60% | +10pp |
| Easy tier (3 instances) | 1/3 = 33% | 2/3 = 67% | **−34pp** ⚠️ |
| Medium tier (4 instances) | 4/4 = 100% | 4/4 = 100% | tie |
| **Hard tier (3 instances)** | **2/3 = 67%** | **0/3 = 0%** | **+67pp 🚀** |

Both systems used Claude Opus 4.7. The 10-instance gap is the same as
the "OpenHands cleared everything but the hard tier" minus "we lost an
easy one." The architectural value is **specifically in the hard tier**
— elsewhere, modern OpenHands+Opus 4.7 is competitive or better.

## Extended baselines (older models, for context)

| System | Model | Overall | Easy | Medium | Hard |
|---|---|---|---|---|---|
| **Harness-lite (this)** | Opus 4.7 | **7/10** | 1/3 | **4/4** | **2/3** |
| OpenHands ACP | Opus 4.7 | 6/10 | 2/3 | 4/4 | 0/3 |
| OpenHands ACP | Opus 4.6 | 6/10 | 2/3 | 4/4 | 0/3 |
| bash-only Claude | Opus 4 | 6/10 | 3/3 | 2/4 | 1/3 |
| Sonar Foundation Agent | Opus 4.5 | 4/10 | 1/3 | 3/4 | 0/3 |
| OpenHands | Opus 4.5 | 4/10 | 1/3 | 2/4 | 1/3 |
| OpenHands | Sonnet 4 | 4/10 | 2/3 | 1/4 | 1/3 |
| SWE-Agent | Sonnet 4 | 4/10 | 2/3 | 2/4 | 0/3 |

## Per-instance verdict matrix

Legend: ✓ resolved · ✗ failed

| # | Instance | Tier | Baseline solve count | Harness-lite | OH o4.7 | OH o4.6 | OH o4.5 | Sonar o4.5 | OH s4 | bash o4 | SWE-A s4 |
|---|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | astropy-14309 | easy | 5/5 (old) + both OH 4.6/4.7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | django-10097 | easy | 3/5 (old) + both OH 4.6/4.7 | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |
| 3 | matplotlib-20676 | easy | 1/5 (old), failed by all OH | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| 4 | astropy-14539 | medium | 4/5 (old) + both OH 4.6/4.7 | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ |
| 5 | django-11149 | medium | 3/5 (old) + both OH 4.6/4.7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| 6 | matplotlib-20488 | medium | 2/5 (old) + both OH 4.6/4.7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| 7 | xarray-6599 | medium | 1/5 (old) + both OH 4.6/4.7 | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| 8 | astropy-14369 | hard | 3/5 (old), failed by all OH | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ |
| 9 | **django-10554** | **hard** | **0/8** (failed by EVERYONE) | **✓ 🚀** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | **xarray-6992** | **hard** | **0/8** (failed by EVERYONE) | **✓ 🚀** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

## The two unique-solve instances

These are the **only two** instances in our 10-sample slice where
harness-lite resolved an instance that **no other agent we tested —
including OpenHands using the same Opus 4.7 model — resolved**.

### `pydata__xarray-6992` (hard, RESOLVED by harness-lite alone)

| Other systems | Verdict |
|---|---|
| OpenHands + Opus 4.7 | ✗ failed |
| OpenHands + Opus 4.6 | ✗ failed |
| OpenHands + Opus 4.5 | ✗ failed |
| Sonar + Opus 4.5 | ✗ failed |
| OpenHands + Sonnet 4 | ✗ failed |
| bash-only + Opus 4 | ✗ failed |
| SWE-Agent + Sonnet 4 | ✗ failed |
| **Harness-lite + Opus 4.7** | **✓ RESOLVED** |

**The patch**: A 204-line refactor of `xarray/core/dataset.py`'s
`set_index` and `reset_index` methods, plus a backward-compatibility
fix in `PandasMultiIndex.keep_levels` (`indexes.py`). The fix
restructures how dropped index/coordinate names are tracked
(lists → sets), adds a `drop_or_convert` helper for the
"drop-or-convert-to-base-variable" choice, and adds `.rename(self.dim)`
to preserve coordinate naming through the multi-index → single-index
conversion path.

| Test bucket | Pass | Fail |
|---|---|---|
| FAIL_TO_PASS (hidden tests) | **12/12** | 0 |
| PASS_TO_PASS (regression) | all preserved | **0** |

**Why this needs multi-agent**: The fix touches multiple reciprocal
methods (you `set_index` → you should be able to `reset_index` and get
your name back). Single-agent loops keep producing patches that fix the
forward direction but break the reverse. The Evaluator's fault-path
probe caught the missing `.rename(self.dim)` that single-shot attempts
miss.

### `django__django-10554` (hard, RESOLVED by harness-lite alone)

Same pattern — failed by every other agent we tested.

**The patch**: 33-line surgical fix across `django/db/models/sql/compiler.py`
and `django/db/models/sql/query.py`. When an `ORDER BY` term doesn't
match any selected column in a Union query, instead of raising a
`DatabaseError`, add it to the select list and reference it by position.

| Test bucket | Pass | Fail |
|---|---|---|
| FAIL_TO_PASS (hidden tests) | **2/2** | 0 |
| PASS_TO_PASS (regression) | all preserved | **0** |

## Failure analysis — being honest

Three graded instances failed. All three follow patterns that suggest
real harness limitations:

### `astropy__astropy-14369` (hard, FAILED)

| Test bucket | Pass | Fail |
|---|---|---|
| FAIL_TO_PASS | 2/3 | 1 |
| PASS_TO_PASS | preserved | 0 |

Harness added `_normalize_chained_division()` to rewrite `a/b/c/d` as
`a/(b.c.d)` before parsing. This made 2 of 3 hidden "should-parse"
tests pass but broke 1 hidden "should-fail" test (`km/s.Mpc-1` must
remain invalid). **Pattern**: over-permissive fix.

### `django__django-10097` (easy, FAILED)

| Test bucket | Pass | Fail |
|---|---|---|
| FAIL_TO_PASS | 431/438 = 98.4% | 7 |
| PASS_TO_PASS | preserved | 5 |

Harness tightened the URLValidator regex from `(?:\S+(?::\S*)?@)?` to
`(?:[^\s:@/]+(?::[^\s:@/]*)?@)?`. The new pattern rejected the bad
URLs from the issue (431/438 pass), but excluded valid characters like
`.`, `+`, `%` — breaking 7 hidden tests for legal URLs and 5
PASS_TO_PASS auth template tests. **Pattern**: over-restrictive fix.

### `matplotlib__matplotlib-20676` (easy, FAILED)

| Test bucket | Pass | Fail |
|---|---|---|
| FAIL_TO_PASS | 0/2 | 2 |
| PASS_TO_PASS | preserved | 0 |

Harness produced a 34-line patch that didn't address the documented
bug — 0/2 of the hidden tests pass. **Pattern**: misdiagnosed root
cause.

### Systematic insight

All three failures share a flavor: **harness's Evaluator is calibrated
for what the spec explicitly says to fix, and under-explores the
negative-case regression surface.** The next iteration of
`harness-evaluator.md` should add:

1. **Negative-case regression fuzz** — for any change to a parser,
   regex, validator, or any function whose contract includes "must
   reject input X", auto-generate adversarial inputs from both sides.
2. **Wrong-file probe** — re-read the spec, independently nominate
   2-3 plausible fix locations, require Generator to justify its
   chosen one against the alternatives.
3. **Cross-model peer review (which we DISABLED here)** — would the
   full harness's Codex review-loop catch these? Untested. A logical
   next experiment.

## Honest caveats

### "harness-lite" — what we disabled

| Feature | Default | What we ran | Why |
|---|:-:|:-:|---|
| `max_spec_rounds` | 3 | 1 | Spec generated offline from GitHub issue |
| Per-checkpoint Gen+Eval loop | ✓ | ✓ | Kept — load-bearing |
| `cross_model_review` (Codex peer) | ✓ | ✗ | Cost (~3× per instance) |
| `auto_retro` | ✓ | ✗ | Single-task eval, not multi-task |
| `full_verify` | ✓ | ✗ | No upstream PR target |
| `coverage_threshold` | 85 | 0 | Most repos lack conftest cov hookup |

**The full harness might recover 1-2 of our failed instances** — both
parser failures (astropy-14369, django-10097) are exactly the kind of
thing a cross-model peer review (a Codex session pushing back on
Generator's regex) would likely catch. This is a hypothesis we did not
test in this run.

### Sample-size caveat

10 instances. Enough for an **existence proof** ("harness can solve
instances no other agent can"), not enough for a **statistical claim**
about overall resolve-rate gap. A 500-instance run would establish
significance.

### Cost caveat

Even harness-lite costs ~2× per instance vs OpenHands ACP. The full
harness with cross-model review would cost ~5× per instance. Whether
the 2 hard breakthroughs justify the spend depends on use case — worth
it for high-stakes refactors, overkill for simple typos (see easy-tier
underperformance).

### Infrastructure caveats

- matplotlib instances required `--namespace swebench` (Docker Hub
  prebuilt images) instead of local build, due to conda network
  failures under Apple Silicon Docker amd64 emulation. Grader-level,
  not harness-level.
- Two graded failures (`django-10097`, `matplotlib-20676`) both
  produced patches that passed `git apply` cleanly; the issue was
  patch correctness, not patch generation.

## Methodology

| Constraint | Choice |
|---|---|
| Dataset | SWE-bench Verified (500 instances) |
| Sample | 10 stratified (3 easy + 4 medium + 3 hard) |
| Input | `problem_statement` only |
| Hidden tests | **Not exposed** to harness |
| Grader | Official `swebench.harness.run_evaluation` (Docker) |
| Host model | Claude Opus 4.7 |
| Harness config | **harness-lite** (see caveats above) |

## Reproduce

```bash
git clone <this-repo> && cd swe-bench-harness-eval
python3 -m venv .venv && .venv/bin/pip install swebench

.venv/bin/python scripts/fetch_baselines.py     # 5 historical baselines
# Manual: download OpenHands Opus 4.7/4.6 tarballs from
# https://github.com/OpenHands/benchmarks/issues/576
# Then merge into baselines/per_instance.json (see scripts/_merge_oh.py)

.venv/bin/python scripts/select_instances.py
.venv/bin/python scripts/build_spec.py
bash scripts/run_harness.sh                     # ~30-60 min, ~$50-150
bash scripts/grade.sh harness_v1                # Docker, ~30-90 min
.venv/bin/python scripts/compare.py --run-id '*'
```

All 10 prediction patches, all 10 grader reports, and per-instance
harness execution logs are committed for full reproducibility.

## What this work doesn't claim

- Does NOT claim harness > everything on overall SWE-bench Verified score
  (we only ran 10 instances; the full Anthropic-reported number for
  Opus 4.7 with Claude Code is 87.6%, far higher than our 70%).
- Does NOT claim full harness is better than harness-lite (we didn't test
  the full pipeline).
- Does NOT claim multi-agent is universally better than single-agent
  (we lost 1 easy instance to OpenHands).

What this work **does** claim, with evidence:
- On the hard tier of a stratified 10-instance slice, harness-lite +
  Opus 4.7 resolved 2 instances that 7 other agent setups (including
  OpenHands using the same Opus 4.7) failed.
- The two unique-solve patches involved multi-method, cross-file
  reasoning where the Generator/Evaluator loop demonstrably caught
  invariants that single-shot patches missed.
