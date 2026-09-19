# Preregistration v0.3 — Real-verifier audit pilot

**Project:** P1 — Self-Calibration of AI Verifiers  
**Status:** protocol draft to freeze before any hidden/gold outcome is inspected  
**Supersedes:** audit_prereg_v0_2.md (pre-freeze revision)  
**Primary benchmark:** HumanEval+/EvalPlus-style split  
**Preregistered robustness benchmark:** MBPP+  
**Purpose:** test whether a heterogeneous verifier/check ensemble has excess unanimous error beyond an independent-error null, and whether targeted gold auditing resolves the resulting blind-set uncertainty.

## 1. Split the base tests: screen A and view B

The benchmark's base tests are deterministically split within each problem into two disjoint halves before candidate generation.

- **Half A:** screening gate only. Candidates must pass all A tests to enter the audit population.
- **Half B:** a released non-LLM verifier view \(V_{\mathrm{testB}}\).

The split is determined by a frozen integer seed. For a problem with \(K\ge2\) separable base test cases, shuffle case IDs with a problem-specific RNG derived from (split_seed, problem_id), assign \(\lceil K/2\rceil\) to A and the remainder to B. Problems with fewer than two separable base cases are excluded from the primary analysis and listed.

The split manifest and seed are hashed in the lock file.

## 2. Verifier/check architecture

After A-screening, the released views are:

1. \(V_{\mathrm{testB}}\), held-out half of the base tests;
2. Judge A under identity, verdict-option-order swap, and negation/bug-search;
3. Judge B under the same three checks.

Thus the LLM subdesign has 3 checks × 2 judges:
\[
\pi_{\mathrm{LLM}}=(2,2,2).
\]

The test-B view is an additional non-LLM verifier with different failure modes; the complete empirical design is not claimed to be exactly the six-view theorem model.

The option-order manipulation is called **verdict-option order swap**. It tests option-label/order bias, not pairwise candidate-position bias. The negation view is intentionally stricter and is not treated as an exchangeable replicate of identity.

## 3. Baseline and transformation schemes

Define
\[
\mathcal V_0=\{V_{\mathrm{testB}},V_A^{\mathrm{id}},V_B^{\mathrm{id}}\}
\]
and
\[
\mathcal V_1=
\mathcal V_0\cup
\{V_A^{\mathrm{swap}},V_A^{\mathrm{neg}},V_B^{\mathrm{swap}},V_B^{\mathrm{neg}}\}.
\]

Let
\[
U_m^+=\{W_v=+1\ \forall v\in\mathcal V_m\},
\qquad
r_m=P(Y=-1\mid U_m^+),
\qquad
b_m=P(Y=-1,U_m^+).
\]

The primary transformation-informativeness estimand is
\[
r_0-r_1
\]
with a two-sided problem-cluster-bootstrap interval.

Let \(D=U_0^+\setminus U_1^+\). Supporting tradeoff quantities are
\[
\frac{P(Y=-1\mid D)}{r_0},
\qquad
P(Y=+1\mid D),
\qquad
P(D\mid Y=+1,U_0^+).
\]

The mechanical quantity \(\Delta b=b_0-b_1\) is reported only as the amount of blind mass removed. Its interval is paired: primary inference is a problem-cluster bootstrap of the paired candidate indicators; a fixed-pool McNemar-style paired table is supplementary.

## 4. Excess-unanimous-error analysis

A large \(r_1\) alone can mean that the judges are simply permissive. The stronger empirical signature is unanimous mass beyond what an independent-error model predicts.

Fit a two-class Dawid--Skene / product-Bernoulli null only to non-unanimous view patterns. With \(d\) released views,
\[
g_\theta(w)
=
\pi\prod_{v=1}^d q_{+,v}^{1(w_v=+1)}(1-q_{+,v})^{1(w_v=-1)}
+
(1-\pi)\prod_{v=1}^d q_{-,v}^{1(w_v=+1)}(1-q_{-,v})^{1(w_v=-1)},
\]
with orientation \(q_{+,v}>1/2>q_{-,v}\).

The conditional likelihood is
\[
P_\theta(w\mid w\notin\{+\mathbf1,-\mathbf1\})
=
\frac{g_\theta(w)}
{\sum_{u\notin\{+\mathbf1,-\mathbf1\}}g_\theta(u)}.
\]

The fit never uses the two unanimous cells. Let \(\hat m_{\mathrm{off}}\) be the observed total non-unanimous mass and \(G_{\mathrm{off}}(\hat\theta)\) the fitted null's non-unanimous probability. Recover the null DS mass by
\[
\hat c_{\mathrm{DS}}
=
\hat m_{\mathrm{off}}/G_{\mathrm{off}}(\hat\theta).
\]

The predicted unanimous-accept mass is
\[
\hat p^{\mathrm{DS}}_+
=
\hat c_{\mathrm{DS}}g_{\hat\theta}(+\mathbf1).
\]

Define
\[
\boxed{
E_+
=
\hat p_{\mathrm{obs}}(+\mathbf1)-\hat p^{\mathrm{DS}}_+
}
\]
as the excess unanimous-accept mass under the independent-error null. Define \(E_-\) analogously.

Primary uncertainty for \(E_+\) is a problem-cluster bootstrap that refits the null inside each replicate. The main text states explicitly that this panel is model-based. The model-free identified-set panel remains the centerpiece.

A positive \(E_+\), together with gold-measured \(r_1>0\), is the empirical signature that wrong candidates accumulate in unanimity more strongly than the independent-error null explains.

## 5. Gold-blind preflight and fixed diagnostic cohort

Before any hidden/gold suite is run:

1. run an infrastructure preflight of about 50 candidates;
2. freeze config/prompts/models;
3. generate a fixed first cohort of 10 candidates/problem;
4. deduplicate within problem by AST-normalized code;
5. compute all W-only diagnostics.

Report on the deduplicated fixed cohort:

- \(\hat u_0,\hat u_1\);
- 6×6 LLM-view disagreement matrix;
- 6×6 LLM-view phi-correlation matrix;
- within-judge/across-check versus across-judge/within-check summaries;
- marginal acceptance of every view;
- test-B agreement with the six LLM views;
- AST duplicate rate.

The matrices are direct evidence about whether the empirical 3-check × 2-judge subdesign resembles the intended block structure or instead contains strong judge-level dependence.

## 6. Judge repeatability / R&R

Exactly 5% of judge calls are selected for repeat execution using a deterministic hash of (repeat_seed, candidate_id, judge_id, check_id).

The repeated call uses the exact same model ID, prompt bytes, API parameters, and parser. No retry is triggered by the verdict.

Report flip rate overall, by judge, by check, and by judge × check.

## 7. Deduplication and effective sample size

Primary generalization analyses deduplicate within problem by the SHA-256 hash of
\[
\texttt{ast.dump(ast.parse(code), annotate_fields=True, include_attributes=False)}.
\]

The first occurrence is retained. Raw-pool results are reported as a sensitivity analysis.

## 8. W-only stopping and fixed-pool precision target

Generation proceeds in uniform rounds of
\[
10,\ 15,\ 20,\ 25,\ 30
\]
candidates/problem and uses only W and AST hashes.

The stopping target is
\[
n^{\mathrm{dedup}}_{U_1^+}\ge2500,
\]
or the maximum 30 candidates/problem.

The target 2500 is chosen before gold because it gives approximately 0.02 worst-case half-width for a 95% binomial proportion interval in a fixed pool. If the target is not reached, the run stops at the maximum round and is labeled a fixed-pool precision shortfall; generation is not extended after inspecting Y.

After gold is revealed, report the realized CP half-width. The desired fixed-pool precision criterion is
\[
\text{CP half-width}(r_1)\le0.02.
\]

## 9. Practical interpretation bars

Statistical precision and practical relevance are separate.

- Practical blind-error bar: \(r_{\mathrm{practical}}=0.02\).
- Judge-quality upper bar: \(r_{\mathrm{bad}}=0.40\).

Interpretation uses the problem-cluster 95% interval:

- **HEADLINE-BLIND:** lower bound \(>0.02\), upper bound \(<0.40\), fixed-pool CP half-width \(\le0.02\), and blind errors occur in at least 3 problems.
- **LOW-BLIND:** cluster upper bound \(<0.02\).
- **JUDGE-QUALITY-FAIL:** cluster lower bound \(>0.40\). Report it, but frame it as inadequate judge quality rather than a useful blind-set gate.
- **INCONCLUSIVE:** everything else.

A candidate-level CP result never overrides the clustered category.

## 10. Primary inference

Primary population inference is a problem-level cluster bootstrap with 10,000 replicates. Resample problems with replacement and carry all retained AST-deduplicated candidates for each selected problem.

Report the approximate problem-level ICC, empirical design effect, and effective candidate count for the blind-error indicator within \(U_1^+\).

Clopper--Pearson remains supplementary, explicitly labeled fixed-pool certification.

## 11. Centerpiece model-free identified-set panel

For blind mass
\[
b_1=P(Y=-1,U_1^+)=u_1r_1,
\]
agreement alone gives
\[
b_1\in[0,u_1].
\]

After gold auditing,
\[
b_1\in[u_1r_L,u_1r_U],
\]
where \([r_L,r_U]\) is the clustered interval. The fixed-pool CP interval is a sensitivity marker.

## 12. Real allocation problem for a deployed gate

The budget experiment estimates the total false-accept mass of a deployed gate, not \(r_1\) alone.

Among A-screened candidates, define
\[
G=1
\iff
V_{\mathrm{testB}}=+1
\quad\text{and}\quad
\#\{\text{positive LLM views among the six}\}\ge4.
\]

Accepted candidates are stratified by positive LLM-view count \(h\in\{6,5,4\}\).

The estimand is
\[
F_G=P(Y=-1,G=1)
=
\sum_h P(H=h)\,P(Y=-1\mid H=h).
\]

At each gold budget compare:

1. **uniform-screened:** simple random sampling from the entire A-screened population;
2. **proportional-accepted:** allocate among accepted strata proportional to stratum size;
3. **oracle Neyman:** retrospective efficiency benchmark
   \[
   n_h\propto N_h\sqrt{p_h(1-p_h)};
   \]
4. **unanimity-weighted:** frozen weights \(w_6:w_5:w_4=3:1:1\), with \(n_h\propto w_hN_h\);
5. **model-assisted:** allocate 50% of the accepted-stratum budget to \(h=6\), allocate the remainder proportionally over \(h=5,4\), and use the fitted DS posterior as a control variate on non-unanimous strata with a within-stratum Hájek residual correction.

Compare strategies over 2,000 repeated audit samples per budget by RMSE, median absolute error, and 95th-percentile absolute error for \(F_G\). Label oracle Neyman as unattainable.

## 13. Null-calibration check

Before substantive gold analysis, treat the A-screen verdict as pseudo truth. Every included candidate passed A by construction, so the pseudo false-accept rate inside \(U_1^+\) must be exactly zero. Any nonzero value indicates a join/normalization bug and invalidates the run until fixed.

## 14. MBPP+ robustness run

HumanEval contamination limits external validity. MBPP+ is preregistered now as an appendix robustness benchmark rather than chosen after seeing HumanEval+.

Use the same frozen generator, judges, prompts, parsing, test-split algorithm, repeatability fraction, dedup rule, and analysis code. Run a fixed 5 candidates/problem with no outcome-dependent extension. Report \(r_1\), \(E_+\), and the centerpiece identified-set shrinkage with problem-cluster intervals.

## 15. Freeze

Before candidate generation, commit:

- audit_config.lock.json;
- hashes of all prompt/manifests;
- hash of audit_analysis.py;
- hash of audit_goldblind.py;
- hash of ds_excess.py;
- hash of audit_allocation.py;
- hash of audit_analysis_spec_v0_1.md;
- hash of this v0.3 preregistration;
- exact model/provider identifiers;
- base-test split seed and repeatability seed.

Any later change requires a new protocol version before inspecting the affected gold result.

## 16. Decision log

| Date | Change | Reason | Made before affected gold outcome? |
|---|---|---|---|
| | | | |
