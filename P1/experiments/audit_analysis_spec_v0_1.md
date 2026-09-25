# Frozen audit analysis specification v0.1

This document is hashed by freeze_audit_config.py and is part of the preregistration lock.

Revision (pre-v0.3-API, gold-blind, before any confirmatory W statistic): the
primary pool changed from the strict-AST-deduplicated pool to the raw candidate
pool with problem-clustered inference. Loose and strict deduplication are
demoted to preregistered sensitivity tiers (Section A.2). The completed MBPP+
v0.2 duplication diagnostic and its `DUPLICATION_HIGH` branch are unchanged.

## A. Primary population

Primary rows are drawn from two frozen benchmark strata, MBPP+ and HumanEval+.

Within each benchmark, primary rows are:

1. passed base-test screen A;
2. valid frozen candidate/view joins;
3. **all candidate draws** (no deduplication; the raw candidate pool).

The primary estimand is the candidate-draw-level false-accept rate under the
frozen generator proposal distribution. Within-problem dependence is addressed
by problem-level cluster bootstrap, not by candidate removal. No
design-informing preflight problem appears in the confirmatory frame.

### A.2 Deduplication sensitivity tiers

Deduplicated pools are reported as sensitivity analyses with distinct estimands:

- **loose dedup (main sensitivity):** first occurrence per
  `(benchmark, problem_id, loose_ast_sha256)`, where the loose hash strips
  docstrings and alpha-renames function-local identifiers (`ast_hash.py`);
  approximates the structural-solution-level false-accept rate. Computable
  from a `code` or `loose_ast_sha256` column.
- **strict dedup (continuity / legacy sensitivity):** first occurrence per
  `(benchmark, problem_id, ast_hash)`; preserves comparability with v0.1/v0.2
  reports and does not determine the primary r_1.

### A.1 Test-B strength asymmetry

The common A/B split is intentionally kept across both benchmarks, even though
the resulting non-LLM view has different strength:

- MBPP+ v0.2.0: 349/378 tasks have exactly three base tests, hence a one-test B
  view under the frozen ceil/floor split;
- HumanEval+: 20/164 tasks have a one-test B view, while 98/164 have at least
  three tests in B;
- HumanEval/34 is excluded before generation as
  `BASE_TEST_SPLIT_IMPOSSIBLE` because it has one base test.

Before gold, report by benchmark:

[
P(V_{testB}=-1mid A	ext{-pass},	ext{complete}),
]

both candidate-weighted and problem-weighted, the problem distribution of
(|B|), and dissent stratified by (|B|).

Cross-benchmark differences in (r_1) are interpreted as joint benchmark/view
heterogeneity, not as a pure benchmark effect.

## B. Primary schemes

\[
\mathcal V_0=\{testB,A^{id},B^{id}\},
\qquad
\mathcal V_1=\mathcal V_0\cup\{A^{swap},A^{neg},B^{swap},B^{neg}\}.
\]

Compute \(u_m,r_m,b_m\), \(D=U_0^+\setminus U_1^+\), \(r_0-r_1\), enrichment, and rejection-cost quantities exactly as in preregistration v0.3.

## C. Stratified cluster bootstrap

Use 10,000 replicates and percentile two-sided 95% intervals.

Within each replicate:

1. resample MBPP+ problems with replacement, preserving the frozen MBPP+ frame size;
2. independently resample HumanEval+ problems with replacement, preserving the frozen HumanEval+ frame size;
3. carry all candidate draws for each selected problem (raw pool; sensitivity
   replicates instead carry the loose- or strict-deduplicated first
   occurrences per Section A.2);
4. recompute benchmark-specific statistics;
5. form the pooled standardized summary using frozen task-frame weights
   [
   omega_M=|F_M|/(|F_M|+|F_H|),qquad omega_H=1-omega_M.
   ]

For (r_1), pool through the weighted numerator/denominator:
[
r_{1,mathrm{pool}}
=
rac{omega_M b_{1,M}+omega_H b_{1,H}}
     {omega_M u_{1,M}+omega_H u_{1,H}}.
]

Report benchmark-specific estimates first, then the task-frame-weighted pooled
estimate, then an equal-stratum-weight sensitivity (omega_M=omega_H=1/2).

The achieved clustered half-width is reported for every estimate. A half-width
above 0.02 is labeled **precision-limited**; it does not trigger additional
sampling after frame exhaustion.

## D. Paired delta-b inference

For each candidate define
\[
B_{0i}=1\{Y_i=-1,U_{0i}^+\},
\qquad
B_{1i}=1\{Y_i=-1,U_{1i}^+\}.
\]

Report the fixed-pool paired 2×2 table. The population interval for \(\Delta b=E[B_0-B_1]\) is the problem-cluster bootstrap interval; do not form two independent binomial intervals.

## E. Independent-error excess-unanimity estimator

Fit the oriented two-class product-Bernoulli null only on patterns that are neither all-plus nor all-minus. Maximize
\[
\sum_{w\notin\{+\mathbf1,-\mathbf1\}}n_w
\log\frac{g_\theta(w)}{G_{\mathrm{off}}(\theta)}.
\]

Recover null DS scale with
\[
\hat c=\hat m_{\mathrm{off}}/G_{\mathrm{off}}(\hat\theta)
\]
and report
\[
\hat E_+
=
\hat p_{\mathrm{obs}}(+\mathbf1)
-
\hat c\,g_{\hat\theta}(+\mathbf1).
\]

Use 12 deterministic random starts plus one warm start where available. Record if \(\hat c>1\). Primary uncertainty is a problem-cluster bootstrap with the model refit inside each replicate.

## F. Judge repeatability

Repeat exactly the preregistered 5% hash-selected judge calls. Report flip rate overall and by judge/check. The first verdict remains the primary-analysis verdict.

## G. Deployed-gate allocation estimator

Gate:
\[
G=1
\iff
testB=+1
\text{ and at least 4 of 6 LLM views are +1}.
\]

Accepted strata are positive-LLM-count 6, 5, 4. For design-based stratum means \(\hat p_h\),
\[
\hat F_G=\sum_h(N_h/N)\hat p_h.
\]

Uniform-screened is estimated by the sample mean of \(1\{G=1,Y=-1\}\) over the screened sample. Unanimity-weighted allocation uses weights \(3:1:1\) times stratum size. Oracle Neyman uses gold-known \(p_h\) only as a retrospective lower bound.

For model-assisted estimation let \(m_i\) be the DS posterior false-class probability. Audit half the accepted budget in \(h=6\), distribute the remainder proportionally over \(h=5,4\), and use
\[
\hat p_h^{MA}
=
\bar m_h
+
\frac1{n_h}\sum_{i\in s_h}(1\{Y_i=-1\}-m_i)
\]
on non-unanimous strata.

Compare 2,000 repeated audit samples per budget by RMSE, median absolute error, and 95th-percentile absolute error for \(F_G\).

## H. Main figures

1. model-free identified-set shrinkage \([0,u_1]\to[u_1r_L,u_1r_U]\);
2. transformation informativeness \(r_0\) vs \(r_1\), with \(r_0-r_1\) CI;
3. independent-error predicted unanimous mass vs observed unanimous mass, showing \(E_+\);
4. allocation RMSE versus gold budget, secondary if space constrained.

## I. Robustness

- loose-deduplicated analysis (main sensitivity; structural-solution estimand);
- strict-deduplicated analysis (continuity with v0.1/v0.2 reports);
- fixed-pool Clopper--Pearson;
- benchmark-specific MBPP+ and HumanEval+ results plus cross-benchmark heterogeneity;
- identity-only judge scheme;
- judge-repeatability sensitivity;
- DS-null diagnostics including conditional-likelihood value and \(\hat c\).
