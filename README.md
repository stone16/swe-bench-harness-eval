# SWE-bench Harness Evaluation

Measure whether the **harness-engineering-skills** multi-agent orchestration
delivers a real lift over single-agent baselines on SWE-bench Verified.

## What this repo answers

> "Does the harness skill (Planner → Generator → Evaluator → Cross-model
> review → Retro) resolve more real GitHub issues than running Claude /
> SWE-Agent / OpenHands by themselves — and is the gain worth the cost?"

## Evaluation contract

We follow the **standard SWE-bench Verified protocol** that every public
baseline on [swe-bench/experiments][1] uses. This is the only way to do an
apples-to-apples comparison.

| Constraint                  | Choice                                                 |
|-----------------------------|--------------------------------------------------------|
| Dataset                     | SWE-bench Verified (500 instances, OpenAI-annotated)   |
| Instance count              | 10 (stratified by difficulty, see below)               |
| Input given to the harness  | `problem_statement` only — the raw GitHub issue text   |
| Hidden test names           | **Not exposed** to the harness                         |
| Hidden test code            | **Not exposed** to the harness                         |
| Grading                     | Official `swebench.harness.run_evaluation` in Docker   |
| Pass criterion              | `FAIL_TO_PASS` tests pass AND `PASS_TO_PASS` still pass|
| Comparison method           | Per-instance verdict against 5 public baselines        |

This is the **fairest** setup. The harness sees exactly what a developer
opening a fresh GitHub issue would see — no privileged grading information.

## Stratified instance selection

We split SWE-bench Verified's `difficulty` field (annotator-estimated time
to fix) into three tiers, then mix instances by **baseline hardness** so a
single 10-instance run can tell us multiple things:

| Tier   | Difficulty label  | Picked | Why                                  |
|--------|-------------------|--------|--------------------------------------|
| Easy   | `<15 min fix`     | 3      | Sanity check + tail-of-easy stress   |
| Medium | `15 min - 1 hour` | 4      | The bulk of real-world bug-fix work  |
| Hard   | `1-4 hours` / `>4 hours` | 3 | Where multi-agent should excel |

Within each tier we mix `all-solved` / `majority` / `split` / `few-solved`
buckets so we can answer:

- **Match-the-pack**: does harness solve what everyone else solves?
- **Differentiation**: does harness solve cases only 1-2 baselines solved?
- **Breakthrough**: does harness solve cases NO baseline solved?
  (2 of our 10 instances are unresolved by all 5 public baselines.)

## Comparison baselines

Five public baselines fetched directly from `swe-bench/experiments`:

| Alias                 | Agent                  | Model              | Released   |
|-----------------------|------------------------|--------------------|------------|
| `sonar_opus_4_5`      | Sonar Foundation Agent | Claude Opus 4.5    | 2025-12-05 |
| `openhands_opus_4_5`  | OpenHands              | Claude Opus 4.5    | 2025-11-27 |
| `openhands_sonnet_4`  | OpenHands              | Claude Sonnet 4    | 2025-05-24 |
| `tools_opus_4`        | Bash-only Claude tools | Claude Opus 4      | 2025-05-22 |
| `sweagent_sonnet_4`   | SWE-Agent              | Claude Sonnet 4    | 2025-05-22 |

The two `*_opus_4_5` rows are the strongest reference points — they use the
same model class the harness is expected to run on, so the delta isolates
the **agent architecture's contribution**, not the model's.

## Repo layout

```
.
├── README.md                  # this file
├── baselines/
│   └── per_instance.json      # public results joined per-instance, by alias
├── instances/
│   └── candidates.json        # the 10 selected instances + metadata
├── specs/                     # generated harness spec.md per instance
│   └── <instance_id>.spec.md
├── predictions/
│   └── harness.jsonl          # final patches in SWE-bench prediction format
├── results/
│   └── eval.<run_id>.json     # official swebench grader output
├── scripts/
│   ├── fetch_baselines.py     # pull public results into per_instance.json
│   ├── select_instances.py    # stratified 10-instance picker
│   ├── build_spec.py          # problem_statement → harness spec.md adapter
│   ├── run_harness.sh         # per-instance driver (clone → harness → diff)
│   └── compare.py             # final report: harness vs public baselines
└── .venv/                     # isolated Python env (swebench + datasets)
```

## Reproduce

```bash
# 1. Bootstrap (one time)
python3 -m venv .venv && .venv/bin/pip install swebench

# 2. Pull baselines + select instances
.venv/bin/python scripts/fetch_baselines.py
.venv/bin/python scripts/select_instances.py

# 3. Generate one spec.md per instance
.venv/bin/python scripts/build_spec.py

# 4. Run harness on each instance (≈$10-25 per instance with default config)
scripts/run_harness.sh

# 5. Official grading
.venv/bin/python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Verified \
    --predictions_path predictions/harness.jsonl \
    --max_workers 4 \
    --run_id harness_v1

# 6. Compare against baselines
.venv/bin/python scripts/compare.py
```

## Harness configuration

Default full config (per the harness skill's recommended setup):

| Setting               | Value | Rationale                                  |
|-----------------------|-------|--------------------------------------------|
| `max_spec_rounds`     | 3     | Allow up to 3 spec-review iterations       |
| `max_eval_rounds`     | 3     | Allow up to 3 generator-fix iterations     |
| `cross_model_review`  | true  | Run review-loop with cross-vendor peer     |
| `auto_retro`          | true  | Persistent learning into `.harness/retro/` |
| `coverage_threshold`  | 85    | Hard minimum for backend checkpoints       |
| `autonomous_pr`       | false | We don't open real PRs against upstream    |

[1]: https://github.com/swe-bench/experiments
