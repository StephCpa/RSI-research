# Finite-sample study preregistration v0.2

**Supersedes:** finite_sample_prereg_v0_1.md before the full paper run.

## 1. Core grid

Partitions:
\[
(2,2),\qquad (4).
\]

Sample sizes:
\[
N\in\{10^3,10^4,10^5,10^6\}.
\]

The main random-interior study uses the same parameter draw at all four \(N\) values so scaling with \(N\) is paired within draw.

## 2. Estimators

1. constructive inverse;
2. one constrained-MLE run initialized at the constructive estimate;
3. cumulative random-start constrained MLE with
   \[
   K\in\{1,2,4,8,16\}.
   \]

Report the smallest \(K\) whose median error is within 5% of the constructive-initialized MLE at the same partition and \(N\).

## 3. Metrics

For every dataset report:

- max natural-parameter error \(E_\theta\);
- \(|\hat S_+-S_+|\);
- total-variation error of the fitted reported law;
- multinomial negative log likelihood;
- failure indicator and runtime;
- error in a downstream accepted-set precision functional.

### 3.1 Downstream precision functional

Views alone do not identify the internal easy/blind split of \(S_\pm\), so the downstream precision functional fixes a synthetic external-audit split:

\[
\gamma_+=P(Y=-1\mid A^+)=0.30,
\qquad
\gamma_-=P(Y=+1\mid A^-)=0.30.
\]

The deployed synthetic gate accepts when at least 3 of 4 reported views are positive. Precision is computed from the DS truth classes and the fixed \(\gamma_\pm\). This is explicitly a **gold-anchored downstream functional**, not a claim that agreement identifies precision.

Report
\[
|\widehat{\mathrm{Prec}}-\mathrm{Prec}|.
\]

## 4. Frozen regularity normalization

All factor normalizations are frozen in regularity_normalization.md before the run. No post-hoc normalization replaces the primary one.

Lead display:
\[
\sqrt N\,E_\theta
\quad\text{vs}\quad
d_{\mathrm{reg}}.
\]

## 5. N-slope by regularity bin

Do not pool all regularity regimes for the main \(N\)-slope estimate.

For each partition, compute the quartiles of \(d_{\mathrm{reg}}\) across the **parameter draws only** (one margin per draw, before looking at recovery error). These define four bins Q1--Q4 from closest to farthest from degeneracy.

Within each bin fit
\[
\log E_\theta
=
\alpha_b+\beta_{N,b}\log N+\epsilon.
\]

Report \(\beta_{N,b}\) with a parameter-draw bootstrap 95% interval. The reference \(-1/2\) is not imposed.

The pooled
\[
\log E=\beta_0+\beta_N\log N+\beta_{\mathrm{reg}}\log d_{\mathrm{reg}}+\epsilon
\]
is retained only as an auxiliary summary.

## 6. Controlled degeneracy paths

Keep the frozen paths from v0.1:

- \((2,2)\) DS-component separation path;
- \((2,2)\) atom-imbalance path;
- \((4)\) mirror/symmetric-accuracy path.

Use
\[
\epsilon\in\{0.30,0.20,0.10,0.05,0.02,0.01\}.
\]

## 7. Coverage

Parametric-bootstrap 95% interval coverage is evaluated for the constructive estimator on
\[
N\in\{10^3,10^4,10^5\}.
\]

Report coordinatewise coverage, interval width, reconstruction failures, and aggregate coverage. Coverage is descriptive estimator evidence, not theorem evidence.

## 8. Reproducibility

Retain seeds, parameter draws, restart order, regularity-bin boundaries, result CSVs, and plot code. Any change to the above design after inspecting the affected result creates a new preregistration version.
