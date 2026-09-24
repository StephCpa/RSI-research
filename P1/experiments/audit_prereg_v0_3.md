# Preregistration v0.3 — Real-verifier audit pilot

**Project:** P1 — Self-Calibration of AI Verifiers  
**Status:** protocol draft to freeze before any hidden/gold outcome is inspected  
**Supersedes:** audit_prereg_v0_2.md (pre-freeze revision)  
**Confirmatory strata:** MBPP+ (v0.2.0 task frame) + HumanEval+  
**Preflight design:** see `preflight_prereg_v0_3.md`  
**Purpose:** test whether a heterogeneous verifier/check ensemble has excess unanimous error beyond an independent-error null, and whether targeted gold auditing resolves the resulting blind-set uncertainty.

## 1. Split the base tests: screen A and view B

The benchmark's base tests are deterministically split within each problem into
two disjoint halves before candidate generation.

- **Half A:** screening gate only. Candidates must pass all A tests to enter the
  audit population.
- **Half B:** a released non-LLM verifier view (V_{mathrm{testB}}).

The split is determined by a frozen integer seed. For a problem with (Kge2)
separable base test cases, shuffle case IDs with a problem-specific RNG derived
from ((	ext{split seed},	ext{problem id})), assign
(lceil K/2ceil) to A and the remainder to B.

### 1.1 Known cross-benchmark asymmetry in test-B strength

The two confirmatory strata have very different base-test cardinalities under
this common split rule.

The dataset audit performed before freeze found:

| stratum | tasks | tasks with exactly 3 base tests | tasks with a 1-test B view | split-impossible |
|---|---:|---:|---:|---:|
| MBPP+ v0.2.0 | 378 | 349 | 349 | 0 |
| HumanEval+ | 164 | 18 | 20 | 1 |

Therefore, for about 92% of MBPP+ tasks, the common split rule produces

[
|A|=2,qquad |B|=1.
]

By contrast, HumanEval+ typically has a stronger B view; 98 of its 164 tasks
have at least 3 tests in B under the frozen split rule.

This asymmetry is preregistered as a known source of cross-benchmark
heterogeneity. A difference between (r_{1,M}) and (r_{1,H}) cannot be
interpreted as a pure "benchmark effect"; part of it may reflect the different
strength of (V_{mathrm{testB}}).

The scheme is nevertheless kept identical across strata because retaining a
non-LLM view in both benchmarks is preferable to making MBPP+ judges-only.

### 1.2 Screened population is intentionally weaker than standard MBPP base-pass

For the dominant 3-base-test MBPP+ tasks, screening uses only the two A tests
and the third test is withheld as (V_{mathrm{testB}}).

Thus the MBPP+ analysis population is explicitly

[
{	ext{passes frozen half-A screen}},
]

not the usual population that passes all three EvalPlus base tests.

This changes the screened population by design and must be stated whenever
MBPP+ results are described.

### 1.3 Gold-blind diagnostics for test-B strength

Before any gold result is opened, report separately by benchmark stratum:

[
d_B
=
P(V_{mathrm{testB}}=-1mid A	ext{-pass},	ext{required views complete}),
]

together with:

- the distribution of (|B|) across eligible problems;
- candidate-weighted test-B dissent rate;
- problem-weighted test-B dissent rate;
- test-B dissent rate stratified by (|B|).

These W-only quantities are descriptive diagnostics of non-LLM view strength
and are used to interpret cross-benchmark heterogeneity; they do not alter the
frozen verifier scheme.

### 1.4 Split-impossible exclusion

A task with fewer than two separable base test cases is excluded **before
candidate generation** with exclusion reason

[
	exttt{BASE_TEST_SPLIT_IMPOSSIBLE}.
]

HumanEval/34 is preregistered here as a known split-impossible task because it
has exactly one base test.

The exclusion decision uses base-test structure only, never plus/gold outcomes.
Every split-impossible problem is written to a frozen split-exclusion manifest.

The split manifest, split-exclusion manifest, and seed for each benchmark are
hashed in the lock file.

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

## 5. Gold-blind preflight

The active preflight protocol is `preflight_prereg_v0_3.md`.

Key frozen points are:

- v0.3 MBPP+ preflight = 100 problems × 2 candidates;
- already-burned v0.1/v0.2 MBPP+ problems are reused first to conserve fresh
  confirmatory frame;
- no plus/gold labels are executed during preflight;
- the primary freeze gates are unanimity-stratum nondegeneracy and view
  heterogeneity, not the old strict A-pass proxy;
- the three-level raw/strict/loose duplication diagnostic is run before the new
  preflight;
- the weaker generator is already frozen before that diagnostic;
- all design-informing preflight problems are excluded from their benchmark's
  confirmatory frame.

The preflight artifacts and their problem manifests are hashed into the lock.

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

## 8. Confirmatory sampling frame and precision

The confirmatory main run is a **two-stratum census of the frozen eligible
problem frames**, not a candidate-count stopping design.

### 8.1 MBPP+ stratum

MBPP+ v0.2.0 contains 378 tasks before protocol exclusions. Define

[
F_M
=
{	ext{canonical-harness-valid MBPP+ tasks}}
setminus
{	ext{all MBPP+ design-informing preflight tasks}}.
]

The v0.3 preflight reuses already-burned v0.1/v0.2 tasks first, so the union of
MBPP+ preflight problems is targeted to be 100 unique tasks rather than 150
fresh tasks.

### 8.2 HumanEval+ stratum

Define

[
F_H
=
{	ext{canonical-harness-valid HumanEval+ tasks}}
setminus
{	ext{all HumanEval+ design-informing preflight tasks}}.
]

HumanEval contains 164 tasks before exclusions.

HumanEval+ is declared before any confirmatory W statistic exists; it is not a
post-result rescue benchmark.

### 8.3 Candidate depth

Every problem in (F_Mcup F_H) receives exactly 3 generation attempts under
the same frozen generator and verifier stack. Candidate depth is never increased
to rescue precision.

### 8.4 Terminal state

The W-only main run ends only at

[
oxed{	ext{FRAME EXHAUSTED}}
]

when every eligible problem in both frozen strata has received its 3 attempts
and the frozen transport/missingness policy has terminated.

There is no early stop based on (M_{U_1}), candidate count, or observed W
rates once the confirmatory run starts.

Only after the W-only frame is exhausted are the candidate/view manifests
frozen and gold opened.

### 8.5 Precision

The desired clustered 95% half-width

[
h_{mathrm{cluster}}(r_1)le0.02
]

is an aspirational **analysis-adequacy bar**, not a sampling stop, because it
depends on gold (Y).

After gold, report the achieved clustered half-width separately for MBPP+,
HumanEval+, and the stratified pooled estimand. If a half-width exceeds 0.02,
mark that estimate **precision-limited** and report it as such. No additional
benchmark, hard tail, preflight reuse, or within-problem depth is added after
seeing this result.

The fixed-pool Clopper--Pearson half-width is still reported, but it does not
substitute for the clustered interval.

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

Primary population inference is **benchmark-stratified problem-level cluster
bootstrap** with 10,000 replicates.

Within each bootstrap replicate:

1. resample MBPP+ problem IDs with replacement from (F_M), preserving
   (|F_M|);
2. independently resample HumanEval+ problem IDs with replacement from (F_H),
   preserving (|F_H|);
3. carry all retained AST-deduplicated candidates for each selected problem;
4. recompute benchmark-specific and pooled statistics.

Report benchmark-specific (r_{1,M}) and (r_{1,H}) first.

The primary pooled task-frame weights are frozen as

[
omega_M=rac{|F_M|}{|F_M|+|F_H|},
qquad
omega_H=1-omega_M.
]

Also report an equal-stratum-weight sensitivity
(omega_M=omega_H=1/2).

Report problem-level ICC, empirical design effect, and effective candidate count
within each benchmark stratum. A candidate-level Clopper--Pearson interval is
supplementary fixed-pool certification only.

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

## 14. Cross-benchmark heterogeneity

MBPP+ and HumanEval+ are both confirmatory strata.

For every main statistic report:

- MBPP+ estimate and cluster interval;
- HumanEval+ estimate and cluster interval;
- task-frame-weighted pooled estimate;
- equal-stratum-weight sensitivity.

A pooled headline is not used to hide qualitative disagreement between the two
benchmarks. If the benchmark-specific effects have opposite signs or materially
different interpretation categories, report the heterogeneity directly.

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
- base-test split seed and repeatability seed;
- MBPP+ and HumanEval+ preflight-union manifests;
- canonical-harness exclusion manifests for both benchmarks;
- base-test split-exclusion manifests for both benchmarks, including the preregistered `HumanEval/34` exclusion;
- frozen confirmatory frame manifests `F_M` and `F_H`;
- frozen stratum-weight rule.

Any later change requires a new protocol version before inspecting the affected gold result.

## 16. Decision log

| Date | Change | Reason | Made before affected gold outcome? |
|---|---|---|---|
| | | | |
