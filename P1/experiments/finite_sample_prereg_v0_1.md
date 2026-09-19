# Finite-sample study preregistration v0.1

**Purpose:** convert the population identifiability results for partitions
((2,2)) and ((4)) into an estimator/conditioning study suitable for the ICML
submission.

## 1. Core grid

Partitions:
[
(2,2),\quad (4).
]

Sample sizes:
[
N\in\{10^3,10^4,10^5,10^6\}.
]

Default development run: 20 random parameter draws/partition.  
Final paper run: 50 random parameter draws/partition with 20 multinomial
replicates per draw if runtime permits; otherwise freeze the reduced grid before
looking at comparative results.

## 2. Estimators

1. **Constructive inverse** applied to the smoothed empirical law.
2. **Constructive-initialized constrained MLE:** exactly one likelihood run from
   the constructive estimate.
3. **Random-start constrained MLE** with cumulative restart budgets
   [
   K\in\{1,2,4,8,16\}.
   ]

The random-start curve reuses the same ordered starts cumulatively, so the best
solution at (K=8) contains the first four starts used at (K=4).

The restart-equivalence summary is the smallest (K) whose median parameter
error is within 5% of the constructive-initialized MLE's median error at the same
partition and (N).

## 3. Primary metrics

For every dataset report:

- max natural-parameter error
  [
  E_\theta=\|\hat\theta-\theta\|_\infty;
  ]
- failure indicator;
- runtime;
- multinomial negative log likelihood;
- total-variation error between fitted and true reported laws.

The first implementation may emit the parameter-error/runtime columns before
the NLL/TV columns are added; the final paper run must include all five.

## 4. Conditioning / regularity

The normalization is frozen in `regularity_normalization.md` before the full
run. No post-hoc alternative normalization will replace it in the primary
figure.

Lead conditioning display:

[
\sqrt N E_\theta
\quad\text{vs}\quad
d_{reg}(\theta).
]

Auxiliary regression:

[
\log E_\theta
=
\beta_0+\beta_N\log N+\beta_{reg}\log d_{reg}+\epsilon,
]

with (\beta_N) estimated and a parameter-draw bootstrap CI. The reference
value (-1/2) is a comparison, not a constraint.

## 5. Controlled degeneracy paths

Random interior draws are supplemented with two deterministic paths.

### (2,2)

Move the DS components toward one another:

[
q_+=\tfrac12+\epsilon a,\qquad
q_-=\tfrac12-\epsilon b,
]

for
[
\epsilon\in\{0.30,0.20,0.10,0.05,0.02,0.01\}.
]

A second path moves the atom imbalance (S_+-S_-) toward zero.

### (4)

Approach the mirror/symmetric-accuracy locus:

[
q_-=1-q_++\epsilon v,
]

with the same decreasing epsilon grid. This directly targets the flattening
degeneracy described by the theorem.

## 6. Likelihood-initialization claim

Do not claim merely that constructive initialization "beats random starts."
Report performance as a function of (K) and the restart-equivalence point.
The intended interpretation is that the algebraic inverse supplies a globally
informed initializer; if sufficiently many random starts erase the difference,
that is reported rather than hidden.

## 7. Coverage study

A separate parametric-bootstrap study evaluates 95% interval coverage for the
constructive estimator.

Default coverage grid:

- (N\in\{10^3,10^4,10^5\});
- 10 parameter draws/partition during development;
- 200 bootstrap resamples/dataset in the final run.

Report per-coordinate and aggregate coverage, bootstrap failures, and interval
width. Coverage is descriptive evidence for the estimator; it is not used to
change the theorem.

## 8. Reproducibility

All seeds, parameter draws, restart budgets, normalization rules, and result CSVs
are retained. Exploratory changes require a new preregistration version before
the affected result is inspected.
