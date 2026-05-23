# SWE-bench Harness Evaluation

> Does multi-agent orchestration actually beat single-agent approaches **when
> controlled for model**? We took the [harness-engineering-skills][hes] plugin
> (running in a stripped-down "harness-lite" config — see caveats) and ran it
> on Claude Opus 4.7 against the **same model** in OpenHands' SWE-bench
> Verified evaluation. Then we widened the comparison to include 5 older
> public baselines.

[hes]: https://github.com/stone16/harness-engineering-skills

## Headline numbers — same model (Opus 4.7) comparison

| Tier | Harness-lite + Opus 4.7 (this repo) | OpenHands + Opus 4.7 | Δ |
|---|:-:|:-:|:-:|
| **Overall (10 instances)** | **7/10 = 70%** | 6/10 = 60% | **+10pp** |
| Easy (3 instances) | 1/3 = 33% | 2/3 = 67% | −34pp |
| Medium (4 instances) | **4/4 = 100%** | 4/4 = 100% | tie |
| **Hard (3 instances)** | **2/3 = 67%** | **0/3 = 0%** | **+67pp** 🚀 |

The lead comes **entirely from the hard tier**. On easy bugs, harness's
multi-agent overhead actually hurts. On medium bugs, modern OpenHands +
Opus 4.7 already saturates. On **hard bugs, OpenHands + Opus 4.7 went
0/3 — harness solved 2 of those 3**.

📄 **[Full per-instance verdict matrix and failure analysis →
RESULTS.md][RESULTS.md]**

## The two instances that prove the architecture lift

Both are SWE-bench Verified hard-tier instances. Both were failed by
OpenHands with Opus 4.7 AND Opus 4.6 AND every older-model baseline we
checked (Sonar, OpenHands/Sonnet 4, bash-only Claude, SWE-Agent). Both
were resolved by harness-lite with Opus 4.7:

| Instance | OpenHands o4.7 | OpenHands o4.6 | Sonar o4.5 | SWE-Agent s4 | bash o4 | **Harness-lite o4.7** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `django__django-10554` (hard, ORDER BY in Union) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| `pydata__xarray-6992` (hard, set_index/reset_index refactor) | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |

This is the result we set out to find: instances where **no public
agent — even using the same Opus 4.7 model — could resolve, but
multi-agent orchestration with a Generator/Evaluator/fault-path loop
could**.

## What's "harness-lite"?

The harness skill ships with a default pipeline that's heavier than what
we ran. We stripped several features to make the per-instance evaluation
affordable on our budget. **Be honest about this when reading the
numbers** — what we tested is one slice of the full design:

| Harness feature | Default | What we ran | Why |
|---|:-:|:-:|---|
| `max_spec_rounds` | 3 | **1** | Spec was pre-generated offline from the GitHub issue; no Spec Evaluator loop needed |
| Per-checkpoint Generator + Evaluator loop | ✓ | **✓** | This IS the load-bearing anti-drift mechanism — kept |
| `cross_model_review` (Codex/Gemini peer) | ✓ | **✗** | Disabled to save cost (~3× per instance) |
| `auto_retro` (post-PR retro) | ✓ | **✗** | Disabled — single-task eval, not multi-task learning |
| `skip_full_verify` | false | **true** | No upstream PR to verify against |
| `coverage_threshold` | 85 | 0 | Most repos don't expose conftest-compatible coverage |

**Update — we ran the harness-full A/B experiment**: we re-ran all 3
failed instances (`astropy-14369`, `django-10097`, `matplotlib-20676`)
with `cross_model_review=true` (Codex peer review enabled). **Result:
0/3 resolved.** Cross-model peer review changed the patch strategy on
2/3 instances (one going from hacky string preprocessor to proper LALR
grammar rewrite, one moving from wrong layer to right layer) — but
**did not flip any failure to a pass**. Both Claude and Codex share
the same bias toward "make positive cases pass" and miss negative-case
regression risk. Full A/B writeup: **[EXPERIMENT_AB.md][AB]**.

[AB]: ./EXPERIMENT_AB.md

## Per-instance matrix (8-system comparison)

Legend: ✓ resolved · ✗ failed

| # | Instance | Tier | Harness-lite | OH o4.7 | OH o4.6 | OH o4.5 | Sonar o4.5 | OH s4 | bash o4 | SWE-A s4 |
|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | astropy-14309 | easy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | django-10097 | easy | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |
| 3 | matplotlib-20676 | easy | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| 4 | astropy-14539 | medium | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✓ |
| 5 | django-11149 | medium | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| 6 | matplotlib-20488 | medium | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| 7 | xarray-6599 | medium | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| 8 | astropy-14369 | hard | ✗ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ |
| 9 | **django-10554** | **hard** | **✓ 🚀** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | **xarray-6992** | **hard** | **✓ 🚀** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

## Methodology

Strict adherence to the [public SWE-bench Verified protocol][swebench]:

| Constraint | Choice | Rationale |
|---|---|---|
| Dataset | SWE-bench Verified (500 instances) | OpenAI-annotated, human-verified |
| Sample | 10 stratified | 3 easy + 4 medium + 3 hard |
| Input | `problem_statement` only | Strict apples-to-apples |
| Hidden tests | **Never** exposed to harness | Grader supplies its own |
| Grader | Official `swebench.harness.run_evaluation` | Docker-isolated, deterministic |
| Host model | **Claude Opus 4.7** | Same as OpenHands primary baseline |
| Harness config | **harness-lite** (see above) | Cost-pruned, evaluator loop preserved |

## Baselines

| Alias | Agent | Model | Source | Per-instance data |
|---|---|---|---|---|
| **oh/o47** | OpenHands ACP | Claude Opus 4.7 | [OpenHands/benchmarks #576][oh] | ✓ tarball |
| oh/o46 | OpenHands ACP | Claude Opus 4.6 | OpenHands/benchmarks #576 | ✓ tarball |
| sonar/o45 | Sonar Foundation Agent | Claude Opus 4.5 | [swe-bench/experiments][exp] | ✓ JSON |
| oh/o45 | OpenHands | Claude Opus 4.5 | swe-bench/experiments | ✓ JSON |
| oh/s4 | OpenHands | Claude Sonnet 4 | swe-bench/experiments | ✓ JSON |
| tools/o4 | bash-tools-only Claude | Claude Opus 4 | swe-bench/experiments | ✓ JSON |
| swea/s4 | SWE-Agent | Claude Sonnet 4 | swe-bench/experiments | ✓ JSON |

The first two (OH o4.7 and OH o4.6) are the **load-bearing same-model
comparison points**. The other five give historical context but used
older model classes (Opus 4.5 era and below).

## Reproduce

```bash
git clone <this-repo> && cd swe-bench-harness-eval
python3 -m venv .venv && .venv/bin/pip install swebench

.venv/bin/python scripts/fetch_baselines.py     # 5 swe-bench/experiments baselines
# OpenHands Opus 4.7/4.6 tarballs: download from OpenHands/benchmarks #576

.venv/bin/python scripts/select_instances.py
.venv/bin/python scripts/build_spec.py

bash scripts/run_harness.sh astropy__astropy-14309  # ~17 min, ~$5-15
bash scripts/grade.sh harness_v1                    # Docker, ~5-30 min
.venv/bin/python scripts/compare.py --run-id '*'
```

## Caveats

- **Sample size is 10.** This is enough for an existence proof — showing
  harness-lite CAN solve instances no agent (including OpenHands+Opus
  4.7) could — but not for a statistical claim about overall
  resolve-rate gap. A full 500-instance run is the natural next step.
- **harness-lite ≠ full harness.** We disabled cross-model peer review,
  full-verify, retro, and reduced spec rounds. The full harness might
  resolve more instances at higher cost.
- **Cost asymmetry.** Even harness-lite's two-agent loop is roughly 2×
  the cost per instance of OpenHands' single-agent loop. Whether the
  +1 instance (70% vs 60%) and +2 hard breakthroughs justify the spend
  depends on use case.
- **Easy-tier underperformance is real.** Harness lost on `django-10097`
  (over-restrictive regex) where OpenHands won. Multi-agent overhead
  can push fixes toward over-specification on simple bugs.
- **Apple Silicon grader caveat.** matplotlib instances required
  `--namespace swebench` (Docker Hub prebuilt images) due to conda
  network failures under amd64 emulation. Infrastructure, not harness.

## License

Apache 2.0 (same as upstream harness-engineering-skills).

[RESULTS.md]: ./RESULTS.md
[swebench]: https://github.com/swe-bench/SWE-bench
[exp]: https://github.com/swe-bench/experiments
[oh]: https://github.com/OpenHands/benchmarks/issues/576
