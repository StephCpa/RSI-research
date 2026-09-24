# P1 experiments

## 1. Finite-sample recovery

The ICML-facing finite-sample study is implemented in `finite_sample.py`.

It evaluates the two constructive models used in the paper, partitions `(2,2)` and `(4)`, at

[
N \in \{10^3,10^4,10^5,10^6\}.
]

Three estimators are compared:

1. the constructive inverse applied to the empirical law;
2. constrained multinomial MLE from random starts;
3. the same MLE initialized at the constructive estimate.

The script also reports a numerical **regularity margin** assembled from the critical determinants, singular values, inversion denominators, and discriminants used by the reconstruction. This is a conditioning diagnostic, not a replacement for the symbolic `Delta_pi` in the theorem.

Quick smoke run:

```bash
python P1/experiments/finite_sample.py --quick
```

Full default run:

```bash
python P1/experiments/finite_sample.py
```

Outputs are written to `P1/experiments/results/`:

- `finite_sample.csv`
- `finite_sample_vs_N.pdf/png`
- `finite_sample_vs_regularity.pdf/png`

The random-start MLE is intentionally disadvantaged only by initialization; it optimizes the same constrained likelihood as the constructive-initialized MLE.

## 2. Real-verifier audit pilot

See `audit_prereg_v0_1.md`.

The protocol must be filled and frozen before any pilot gold outcomes are inspected. In particular, benchmark version, exact candidate-generator and judge model IDs, prompt hashes, and visible/gold suite definitions remain to be committed before launch.


## 3. Freeze the audit configuration

Copy and fill the template:

```bash
cp P1/experiments/audit_config.example.json P1/experiments/audit_config.json
# add frozen prompt files and problem/metamorphic manifests
make audit-freeze
```

The freeze command writes `audit_config.lock.json` with SHA-256 hashes of the
configuration and referenced prompt/manifest files. Commit that lock file
before generating candidates or inspecting hidden-suite outcomes.


## 4. Analyze a frozen audit table

The analysis stage is provider-agnostic. Prepare a CSV following
`audit_schema_example.csv` and run:

```bash
python P1/experiments/audit_analysis.py path/to/audit_table.csv
```

This produces the three preregistered panels: blind error in the unanimous
stratum, agreement-only blind-mass identified set versus the audited interval,
and interval width versus gold budget for unanimous, uniform, and
disagreement-only allocation.


## 5. Gold-blind diagnostics

Before any hidden/gold suite is run, analyze the fixed first cohort:

```bash
python P1/experiments/audit_goldblind.py path/to/views_only.csv
```

The input must not contain a `truth` column. The script writes `u0/u1`, the
preregistered budget-panel prominence gate, marginal acceptance rates, and
pairwise agreement/phi matrices overall and conditional on visible-test pass.

## 6. Revised audit inference

The current preregistration is `audit_prereg_v0_2.md`. It supersedes v0.1
before freeze. Population uncertainty is problem-cluster bootstrap; the
Clopper-Pearson interval is retained only as a fixed-pool certification
sensitivity. The primary transformation statistic is `r0-r1`, not
`delta_b`.

## 7. Coverage and controlled degeneracy

```bash
make coverage-quick
make degeneracy-quick
```

The final versions are:

```bash
make coverage
make degeneracy
```

`regularity_normalization.md` freezes every normalization used in the
conditioning plots. `finite_sample_prereg_v0_1.md` freezes the restart grid,
the free `beta_N` scaling regression, the coverage design, and the controlled
paths toward the algebraic degeneracy sets.


## 8. Current frozen protocols

Before the real audit pilot, use:

- `audit_prereg_v0_3.md`
- `audit_analysis_spec_v0_1.md`

These supersede the earlier pre-freeze audit versions.

The v0.3 design splits base tests into screen-A and verifier-view-B, uses AST
deduplication, includes a 5% judge-repeatability sample, preregisters MBPP+ as a
robustness benchmark, and adds an independent-error excess-unanimity analysis.

## 9. Excess unanimity and allocation analyses

After the gold-blind view table is frozen, the independent-error null can be
checked without gold:

```bash
python P1/experiments/ds_excess.py path/to/views_only.csv
```

After gold is available:

```bash
python P1/experiments/audit_analysis.py path/to/audit_table.csv
python P1/experiments/audit_allocation.py path/to/audit_table.csv
```

The allocation study targets the total false-accept mass of the preregistered
deployed gate rather than the unanimous-stratum rate alone.

## 10. Local collector requirements

The local collector should use:

- `base_test_split.py` for deterministic A/B splitting;
- `ast_hash.py` for within-problem AST deduplication;
- `judge_repeatability.py select` before repeat calls and
  `judge_repeatability.py analyze` after them.

The primary CSV schemas are in `audit_views_schema_example.csv` (gold blind)
and `audit_schema_example.csv` (after gold).


## 11. MBPP+ preflight v0.3 draft

After the two gold-blind freeze refusals, the next preflight design is in
`preflight_prereg_v0_3.md`. It changes the primary freeze gates from the old
strict A-pass proxy to the actual unanimity-stratum and view-heterogeneity
quantities, broadens the problem-level sampling shape, freezes transport
retries/missing-view sensitivity, and stops on the number of problems
contributing to `U1+`.

Before any new API run, execute the one remaining diagnostic on the existing
v0.2 candidate artifact:

```bash
python P1/experiments/preflight_duplication_check.py path/to/v0_2_candidates.csv
```

The diagnostic accepts CSV or JSONL with `problem_id` plus either `ast_hash`
or `code`. Do not freeze v0.3 until its duplication branch has been recorded
in the preregistration.


## 12. v0.3 duplication branch (current)

Before the next API preflight, run the hash self-test and then the v0.2
duplication diagnostic:

```bash
python P1/experiments/test_duplication_hashes.py
python P1/experiments/preflight_duplication_check.py path/to/v0_2_candidates.csv
```

The diagnostic now reports three measures over **all unordered within-problem
pairs**:

- `raw`: exact response text, used to detect sampler/cache collapse;
- `strict`: the original AST identity metric, retained for continuity;
- `loose`: docstrings removed and function-local identifiers alpha-renamed,
  used to measure genuine solution convergence.

Branches are frozen in `preflight_prereg_v0_3.md`:

- raw duplicate-pair fraction >= 0.25 -> `SAMPLER_COLLAPSE`, do not switch models;
- otherwise loose duplicate-pair fraction >= 0.25 -> `DUPLICATION_HIGH`;
- otherwise -> `PROBLEM_LEVEL_HETEROGENEITY`.

Both latter branches proceed to the already frozen generator
`qwen3.6-flash-2026-04-16`. The main confirmatory problem draw excludes all
problems used in the v0.1-v0.3 preflights.


## 13. Frame arithmetic frozen before the duplication diagnostic

The v0.3 frame design now conserves fresh MBPP+ tasks and removes the infeasible
`M_U1 >= 250` stop:

- the v0.3 MBPP+ preflight reuses the union of v0.1/v0.2 preflight problems
  first, then draws only enough fresh problems to reach 100 unique preflight
  tasks;
- MBPP+ and HumanEval+ are preregistered confirmatory strata;
- all design-informing preflight problems are excluded from their benchmark's
  confirmatory frame;
- each eligible main-frame problem receives exactly three candidate attempts;
- the main W-only run ends at `FRAME EXHAUSTED`, not at a candidate/problem
  count target;
- clustered 95% half-width <= 0.02 is an aspirational post-gold precision bar,
  not a gold-dependent stopping rule;
- if the achieved clustered half-width exceeds 0.02, report the estimate as
  `precision-limited`; do not add candidates, a hard tail, or a third
  benchmark after seeing gold.

The lock now requires frozen MBPP+/HumanEval+ frame manifests and hashes both
the audit and preflight preregistrations.


## 14. Test-B strength asymmetry and split-impossible tasks

The common A/B split is retained across MBPP+ and HumanEval+, but its strength
is explicitly treated as heterogeneous:

- MBPP+ v0.2.0: most tasks yield a one-test B verifier;
- HumanEval+: B is typically stronger;
- report test-B dissent by benchmark and by `test_B_size` before opening gold.

The screened MBPP+ population is therefore "passes half-A", not the standard
"passes all base tests" population.

Tasks with fewer than two separable base tests are excluded before generation
with reason `BASE_TEST_SPLIT_IMPOSSIBLE`. `HumanEval/34` is preregistered as
a known exclusion. Templates:

```
P1/experiments/mbpp_split_exclusions.example.json
P1/experiments/humaneval_split_exclusions.example.json
```

`freeze_audit_config.py` hashes both manifests and validates that the
HumanEval manifest contains exactly one `HumanEval/34` record with
`base_test_count=1` and the frozen exclusion reason.
