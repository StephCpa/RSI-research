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
