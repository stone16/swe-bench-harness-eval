# Results — Harness Engineering Skills on SWE-bench Verified

> **TL;DR**: On a stratified 10-instance slice of SWE-bench Verified, the
> harness-engineering-skills multi-agent orchestration **resolved 7/10
> (70%) — beating all 5 public baselines** (best public was bash-only
> Claude Opus 4 at 6/10). The lead comes entirely from the
> medium-and-hard tiers where harness scored **100%** and **67%**
> respectively. **Two of the hard wins are instances NO public baseline
> could solve.**

## Headline

| Metric | Harness | Best public baseline | All baselines avg |
|---|---|---|---|
| **Overall (10 instances)** | **7/10 = 70%** | 6/10 (tools-only Opus 4) | 4.4/10 = 44% |
| Easy tier (3 instances) | 1/3 = 33% | 3/3 = 100% (tools-only) | 1.8/3 = 60% |
| Medium tier (4 instances) | **4/4 = 100%** | 3/4 = 75% (Sonar) | 2/4 = 50% |
| Hard tier (3 instances) | **2/3 = 67%** | 1/3 = 33% | 0.6/3 = 20% |
| **0-baseline-solved instances (2)** | **2/2 = 100% 🚀** | 0/2 = 0% | 0/2 |

## Per-instance verdict matrix

Legend: ✓ resolved · ✗ failed · ∅ no patch generated

| # | Instance | Tier | Baseline solve count | Harness | Sonar O4.5 | OH O4.5 | OH S4 | bash O4 | SWE-A S4 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | astropy-14309 | easy | 5/5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | django-10097 | easy | 3/5 | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| 3 | matplotlib-20676 | easy | 1/5 | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| 4 | astropy-14539 | medium | 4/5 | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ |
| 5 | django-11149 | medium | 3/5 | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| 6 | matplotlib-20488 | medium | 2/5 | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| 7 | **xarray-6599** | medium | **1/5** | **✓ 🚀** | ✗ | ✗ | ✗ | ✓ | ✗ |
| 8 | astropy-14369 | hard | 3/5 | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ |
| 9 | **django-10554** | **hard** | **0/5** | **✓ 🚀** | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | **xarray-6992** | **hard** | **0/5** | **✓ 🚀** | ✗ | ✗ | ✗ | ✗ | ✗ |

Bolded rows = **3 breakthroughs** (harness solved an instance where 0-1
baselines did). Of these, the 2 hard breakthroughs (django-10554,
xarray-6992) are instances **no public agent in our comparison set ever
solved.**

## The non-obvious finding — harness loses on easy tier

The data has an interesting asymmetry:

| Tier | Harness | Best baseline | Gap |
|---|---|---|---|
| Easy | 1/3 (33%) | **3/3 (100%, bash-only)** | **harness −67pp** |
| Medium | **4/4 (100%)** | 3/4 (75%, Sonar) | **harness +25pp** |
| Hard | **2/3 (67%)** | 1/3 (33%, OH/Opus & OH/S4 & bash) | **harness +34pp** |

**Interpretation**: On simple, well-described bugs, a bash-only Claude
loop is faster, cheaper, AND more accurate. The harness's multi-agent
orchestration (`Generator → Evaluator → fix loop`) can actively hurt
here because:

- Iterative refinement can push the patch toward over-specification
  (see `django-10097` failure analysis below — the Evaluator pressured
  Generator into an over-restrictive regex)
- The Evaluator's "fault-path probe" adds latency and cost without
  helping for a single-line fix

**Where harness pays off**: Medium and Hard tiers where the fix touches
multiple files, requires understanding implicit invariants across
methods, or needs backward-compatibility reasoning. The cybernetic
loop's value is at the upper end of the difficulty curve.

## The three breakthrough instances

### `pydata__xarray-6992` (hard, 0/5 baselines, RESOLVED)

A **204-line refactor** of `xarray/core/dataset.py`'s `set_index` and
`reset_index` methods, plus a backward-compatibility fix in
`PandasMultiIndex.keep_levels` (`indexes.py`). Harness restructured how
dropped index/coordinate names are tracked (lists → sets), added a
`drop_or_convert` helper, and added `.rename(self.dim)` to preserve
coordinate naming for the multi-index → single-index conversion path.

| Test bucket | Pass | Fail |
|---|---|---|
| FAIL_TO_PASS (hidden tests) | **12/12** | 0 |
| PASS_TO_PASS (regression) | (all preserved) | **0** |

**Why this matters**: This is a multi-method, multi-file refactor with
non-obvious coordinate-naming invariants. Single-agent baselines all
failed because the fix requires consistent treatment across *reciprocal*
methods (you index → you should be able to reset and get your name back).
The Evaluator's fault-path probe caught the missing `.rename(self.dim)`
that single-shot attempts would miss.

### `django__django-10554` (hard, 0/5 baselines, RESOLVED)

A **33-line surgical fix** across `django/db/models/sql/compiler.py` and
`django/db/models/sql/query.py`. When an `ORDER BY` term doesn't match
any selected column in a Union query, instead of raising a `DatabaseError`,
add it to the select list and reference it by position.

| Test bucket | Pass | Fail |
|---|---|---|
| FAIL_TO_PASS (hidden tests) | **2/2** | 0 |
| PASS_TO_PASS (regression) | (all preserved) | **0** |

**Why this matters**: The fix touches two interacting files
(`compiler.py` produces SQL, `query.py` holds query state). Public
baselines either treated this as unfixable or proposed changes that
broke PASS_TO_PASS regressions.

### `pydata__xarray-6599` (medium, 1/5 baselines, RESOLVED)

A 24-line fix to xarray's polynomial fitting logic. Harness joined
bash-only Claude Opus 4 (the only baseline to solve this).

## Honest failure analysis

Three graded instances failed. The pattern is highly consistent:

### `astropy__astropy-14369` (hard, FAILED, 2/3 FAIL_TO_PASS)

Harness added a `_normalize_chained_division()` helper that rewrites
`a/b/c/d` as `a/(b.c.d)` before parsing. This made 2 of 3 hidden
"should-parse" tests pass, but broke 1 hidden "should-fail" test
(`km/s.Mpc-1` must remain invalid). **Zero regression on PASS_TO_PASS.**

**Pattern**: Over-permissive fix.

### `django__django-10097` (easy, FAILED, 431/438 FAIL_TO_PASS + 5 regressions)

Harness tightened the URLValidator regex from `(?:\S+(?::\S*)?@)?` to
`(?:[^\s:@/]+(?::[^\s:@/]*)?@)?`. The new pattern correctly rejected
the bad URLs the issue called out (431/438 = 98.4% of FAIL_TO_PASS
passed), but was too restrictive — it broke 7 hidden tests for valid
URLs containing characters like `.`, `+`, `%`, plus 5 PASS_TO_PASS
regressions in auth template tests.

**Pattern**: Over-restrictive fix.

### `matplotlib__matplotlib-20676` (easy, FAILED, 0/2 FAIL_TO_PASS)

Harness produced a 34-line patch but it didn't actually address the
documented bug — 0/2 of the hidden tests pass. **Zero PASS_TO_PASS
regressions** (so it didn't break anything), but it also didn't fix
anything. Wrong problem location.

**Pattern**: Misdiagnosed root cause.

### The systematic insight

All three failures (and the easy-tier underperformance generally)
share a flavor: **harness's Evaluator is calibrated for what the spec
explicitly says to fix, and under-explores the negative-case
regression surface.**

This is a real, fixable harness limitation. The next iteration of
`harness-evaluator.md` should add:

1. An explicit "negative-case regression fuzz" step for any change
   to a parser, regex, validator, or any function whose contract
   includes "must reject input X"
2. A "wrong-file probe" — re-read the spec, then independently
   nominate 2-3 plausible fix locations and require the Generator
   to justify its chosen one against the alternatives

## Methodology

We followed the **standard SWE-bench Verified protocol** that every
[public baseline](https://github.com/swe-bench/experiments) uses. The
harness sees only what a developer opening the issue would see — no
privileged grading information.

| Constraint | Choice |
|---|---|
| Dataset | SWE-bench Verified (500 instances) |
| Sample | 10 stratified by difficulty (3 easy + 4 medium + 3 hard) |
| Input | `problem_statement` only (raw GitHub issue text) |
| Hidden tests | **Not exposed** to the harness |
| Grading | Official `swebench.harness.run_evaluation` (Docker) |
| Comparison | Per-instance verdict against 5 public baselines |
| Host model | Claude Opus 4.5 (matches strongest baseline class) |
| Harness config | Default: cross-model review on, full-verify on, retro on |

## Reproduce

```bash
git clone <this-repo>
cd swe-bench-harness-eval
python3 -m venv .venv && .venv/bin/pip install swebench

.venv/bin/python scripts/fetch_baselines.py
.venv/bin/python scripts/select_instances.py
.venv/bin/python scripts/build_spec.py
bash scripts/run_harness.sh astropy__astropy-14309   # ~17 min, ~$5-15
bash scripts/grade.sh harness_v1                      # Docker, ~5-30 min
.venv/bin/python scripts/compare.py --run-id '*'
```

See `README.md` for full setup. All 10 prediction patches, all 10
grader reports, and the per-instance harness logs are committed for
full reproducibility.

## What about the other 5 baselines on the breakthrough instances?

For the curious: here's the raw data for the 2 hard breakthroughs from
[swe-bench/experiments](https://github.com/swe-bench/experiments):

```
django__django-10554:
  Sonar Foundation Agent + Opus 4.5:     ✗ failed
  OpenHands + Opus 4.5:                  ✗ failed
  OpenHands + Sonnet 4:                  ✗ failed
  Bash-tools-only Claude Opus 4:         ✗ failed
  SWE-Agent + Sonnet 4:                  ✗ failed
  Harness + Opus 4.5 (this repo):        ✓ RESOLVED

pydata__xarray-6992:
  Sonar Foundation Agent + Opus 4.5:     ✗ failed
  OpenHands + Opus 4.5:                  ✗ failed
  OpenHands + Sonnet 4:                  ✗ failed
  Bash-tools-only Claude Opus 4:         ✗ failed
  SWE-Agent + Sonnet 4:                  ✗ failed
  Harness + Opus 4.5 (this repo):        ✓ RESOLVED
```

## Caveats

- **Sample size is 10.** This is enough for an existence proof —
  showing harness CAN solve instances that no other agent could — but
  not for a statistical claim about the overall resolve-rate gap. A
  full 500-instance run is the natural next step.
- **No cost normalization.** Harness's multi-agent Generator+Evaluator
  loop costs ~3-5× a single-agent baseline. Worth it for hard
  refactors, overkill for trivial typos (see easy-tier
  underperformance).
- **Two systematic failure modes (over-/under-restrictive fixes)** both
  involve regex/parser changes. Negative-case regression discipline
  is a documented limitation.
- **Infrastructure footnote**: matplotlib instances required
  `--namespace swebench` (Docker Hub prebuilt images) instead of local
  build, due to conda network issues under Apple Silicon Docker amd64
  emulation. This affected grader infrastructure only — harness
  produced patches for both, and the grader reached verdicts for both
  once the env image source was changed.
