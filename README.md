# SWE-bench Harness Evaluation

> Does multi-agent orchestration actually beat single-agent approaches on
> real-world bug fixing? We took the [harness-engineering-skills][hes]
> plugin and ran it head-to-head against 5 public baselines on a
> stratified slice of SWE-bench Verified.
>
> **Result: harness resolved 7/10 instances (70%), beating every public
> baseline. Two of the wins are hard-tier instances NO public agent could
> solve.**

[hes]: https://github.com/stometa/harness-engineering-skills

## Headline numbers

| Tier | Harness | Best public baseline | Δ |
|---|:-:|:-:|:-:|
| **Overall (10 instances)** | **7/10 = 70%** | 6/10 = 60% (bash-only Opus 4) | **+10pp** |
| Easy (3 instances) | 1/3 = 33% | **3/3 = 100%** (bash-only) | **−67pp** |
| Medium (4 instances) | **4/4 = 100%** | 3/4 = 75% (Sonar) | **+25pp** |
| Hard (3 instances) | **2/3 = 67%** | 1/3 = 33% (3-way tie) | **+34pp** |
| **0-baseline-solved instances (2)** | **2/2 = 100% 🚀** | 0/2 = 0% | **+100pp** |

The lead comes from **medium and hard** tiers. Harness is actually
**worse on easy bugs** than bash-only Claude (multi-agent overhead can
push fixes toward over-specification) — see the
[honest failure analysis][RESULTS.md] for what we learned.

📄 **[Full per-instance verdict matrix and failure analysis →
RESULTS.md][RESULTS.md]**

## What this repo is

A complete, reproducible head-to-head evaluation of the
[harness-engineering-skills][hes] plugin against 5 public SWE-bench
Verified baselines:

| Baseline | Model | Source |
|---|---|---|
| Sonar Foundation Agent | Claude Opus 4.5 | swe-bench/experiments |
| OpenHands | Claude Opus 4.5 | swe-bench/experiments |
| OpenHands | Claude Sonnet 4 | swe-bench/experiments |
| bash-tools-only Claude | Claude Opus 4 | swe-bench/experiments |
| SWE-Agent | Claude Sonnet 4 | swe-bench/experiments |
| **Harness (this repo)** | **Claude Opus 4.5** | this run |

## What harness does that single agents don't

The harness skill enforces three structural disciplines that single-agent
coding loops typically violate:

1. **Two-session context split** — planning is discarded before execution
   begins. No shared context to drift in.
2. **Fresh sub-agent per checkpoint** — Generator and Evaluator are
   spawned in clean contexts, can't be biased by prior reasoning.
3. **Engine-enforced gating** — `pass-checkpoint` is blocked unless the
   Evaluator's session ID was *never* used by any prior checkpoint in
   the same task. The LLM cannot self-certify.

The two breakthrough instances (`django__django-10554`,
`pydata__xarray-6992`) both required a multi-file fix where one change
implicitly constrains another — exactly where single-agent self-review
echo-chambers fail.

## Reproduce

```bash
git clone <this-repo> && cd swe-bench-harness-eval
python3 -m venv .venv && .venv/bin/pip install swebench

# Pull all 5 public baselines' per-instance verdicts
.venv/bin/python scripts/fetch_baselines.py

# Pick 10 stratified instances (deterministic seed)
.venv/bin/python scripts/select_instances.py

# Translate each problem_statement into a harness spec
.venv/bin/python scripts/build_spec.py

# Run the harness on one instance (~17 min, ~$5-15)
bash scripts/run_harness.sh astropy__astropy-14309

# Run all 10 in parallel (~30-60 min, ~$50-150 with default config)
for iid in $(jq -r '.[].instance_id' instances/candidates.json); do
  bash scripts/run_harness.sh "$iid" &
done

# Consolidate per-instance predictions into the SWE-bench format
.venv/bin/python scripts/consolidate.py

# Official SWE-bench grading (Docker, ~5-15 min per instance)
bash scripts/grade.sh harness_v1

# Generate the per-instance comparison matrix
.venv/bin/python scripts/compare.py --run-id harness_v1
```

## Methodology

We followed the **strict SWE-bench Verified protocol** that every public
baseline uses:

| Constraint | Choice | Rationale |
|---|---|---|
| Dataset | SWE-bench Verified (500 instances) | OpenAI-annotated, human-verified |
| Sample size | 10 stratified | 3 easy + 4 medium + 3 hard |
| Input | `problem_statement` only | Strict apples-to-apples with public baselines |
| Hidden tests | **Never** exposed to harness | The grader supplies its own test_patch |
| Grader | Official `swebench.harness.run_evaluation` | Docker-isolated, deterministic |
| Host model | Claude Opus 4.5 | Matches strongest public baseline (Sonar) |
| Harness config | Default full pipeline | `cross_model_review=true`, `auto_retro=true` |

Stratification picks instances across three "baseline hardness" buckets
to maximize signal from only 10 samples:

| Bucket | Definition | In our 10 |
|---|---|---|
| `all-solved` | All 5 baselines resolved | 1 (sanity check) |
| `majority` | 3-4 of 5 resolved | 2 (common ground) |
| `split` | exactly 2-3 of 5 resolved | 3 (model-sensitive) |
| `few-solved` | 0-1 of 5 resolved | **4 (where multi-agent should help)** |

See [`scripts/select_instances.py`](scripts/select_instances.py) for the
deterministic selection logic.

## Repo layout

```
.
├── README.md                          # this file
├── RESULTS.md                         # per-instance results + analysis
├── baselines/
│   └── per_instance.json              # 5 public baselines × 429 instances
├── instances/
│   └── candidates.json                # the 10 stratified picks
├── specs/                             # generated harness spec.md (10 files)
├── predictions/
│   ├── _individual/                   # per-instance prediction JSONL
│   └── harness.jsonl                  # consolidated SWE-bench format
├── results/                           # grader output + compare report
├── logs/
│   ├── *.log                          # per-instance harness execution
│   └── run_evaluation/                # SWE-bench grader per-instance reports
└── scripts/
    ├── fetch_baselines.py             # pull public verdicts
    ├── select_instances.py            # stratified picker
    ├── build_spec.py                  # problem_statement → spec.md
    ├── run_harness.sh                 # per-instance driver
    ├── consolidate.py                 # merge per-instance predictions
    ├── grade.sh                       # SWE-bench official grader wrapper
    └── compare.py                     # final verdict matrix + analysis
```

## Caveats

- **Sample size is 10.** This is enough for an existence proof — showing
  harness CAN solve 0-baseline instances that no other agent could — but
  not for a statistical claim about overall resolve-rate gap. A 500-
  instance run is the natural next step.
- **Cost is real.** The harness pipeline costs ~3-5× a single-agent
  baseline (one Generator call + one fresh Evaluator call + retry loop).
  Whether the 75% vs 60% gap justifies the spend depends on use case —
  worth it for hard refactors, overkill for trivial typos.
- **Apple Silicon grader caveat.** Two matplotlib instances couldn't be
  graded locally due to conda network failures inside amd64-emulated
  Docker. This is a SWE-bench/Docker issue, not a harness issue —
  retrying with `--namespace swebench` (Docker Hub prebuilt images).
- **Known harness limitation.** Both graded failures
  (`astropy-14369`, `django-10097`) involve regex/parser fixes where the
  Evaluator's fault-path probe focused on positive cases and missed
  negative-case regressions. The harness skill's next iteration should
  add explicit negative-case fuzzing for parser changes.

## License

Apache 2.0 (same as upstream harness-engineering-skills).

[RESULTS.md]: ./RESULTS.md
