# Preregistration v0.2 — Real-verifier audit pilot

**Project:** P1 — Self-Calibration of AI Verifiers  
**Status:** protocol draft to freeze before any hidden/gold outcome is inspected  
**Supersedes:** `audit_prereg_v0_1.md` (pre-freeze revision)  
**Purpose:** test the paper's actionable blind-set/audit claim on a real code-verification stack without using gold outcomes to tune the verifier scheme.

## 1. Primary question and estimands

The experiment asks whether a realistic verifier/check ensemble leaves a nonzero blind false-accept rate inside the unanimous-accept stratum, and how much an external gold audit shrinks the corresponding identified set.

Two nested schemes are frozen:

- **Baseline scheme** (mathcal V_0={V_{visible},V_A^{id},V_B^{id}}).
- **Transformation scheme** (mathcal V_1supsetmathcal V_0), adding the preregistered swap/negation views.

Define
[
U_m^+={W_v=+1 orall vinmathcal V_m},qquad
r_m=P(Y=-1mid U_m^+),qquad
b_m=P(Y=-1,U_m^+).
]

The **centerpiece empirical claim** is not (b_0-b_1): since (U_1^+subseteq U_0^+), blind mass can only decrease under any extra filter, including an uninformative one.

The primary transformation-informativeness estimand is therefore
[
oxed{r_0-r_1}.
]

A positive value means that the added checks preferentially remove false accepts rather than removing unanimous accepts at random.

Let
[
D=U_0^+setminus U_1^+.
]
Supporting quantities are

[
	ext{enrichment}
=
rac{P(Y=-1mid D)}{r_0},
]

[
P(Y=+1mid D)
quad	ext{and}quad
P(Dmid Y=+1,U_0^+).
]

The first describes how error-enriched the removed set is; the latter two describe the correctness cost of the stricter scheme.

The quantity
[
Delta b=b_0-b_1
]
is reported only as **magnitude of blind mass removed**, never as evidence that the added checks are informative.

## 2. Benchmark and frozen task structure

The pilot uses code-generation tasks with an automatic operational gold channel.

- **Candidate:** generated program for one benchmark problem.
- **Visible verifier:** the public/basic test suite.
- **Judge A / Judge B:** two frozen LLM judges from distinct model families.
- **Gold:** an extended hidden test suite never exposed to the candidate generator or judges.
- **Truth:** (Y=+1) iff the candidate passes the full gold suite; otherwise (Y=-1).

The preferred pilot benchmark is a frozen HumanEval+/EvalPlus-style split where the basic and extended suites are cleanly separated.

Before data collection, commit exact values for:

| Field | Frozen value |
|---|---|
| Benchmark + version/commit | **TO FILL** |
| Problem manifest/hash | **TO FILL** |
| Candidate generator model ID | **TO FILL** |
| Samples/problem by round | 10 initially; extensions of +5/problem |
| Generator decoding | **TO FILL** |
| Judge A exact provider/model ID | **TO FILL** |
| Judge B exact provider/model ID | **TO FILL** |
| Judge decoding | lowest supported temperature; **TO FILL** |
| Prompt templates/hashes | **TO FILL** |
| Visible-suite definition | **TO FILL** |
| Gold-suite definition | **TO FILL** |

The pilot cannot begin until the frozen configuration passes `freeze_audit_config.py`.

## 3. Verifiers and checks

### 3.1 Verifiers

1. (V_{visible}): basic/visible test suite.
2. (V_A): LLM judge A.
3. (V_B): LLM judge B.

A semantics-preserving refactor of the candidate is **not** a primary check, because a fixed test-coverage gap generally survives such a refactor.

### 3.2 Judge checks

For both LLM judges:

- identity correctness question;
- verdict-order swap;
- negation / bug-search question.

All outputs are normalized to (W=+1) meaning "supports correctness."

The negation view is **not** treated as an exchangeable replicate of the identity view. It intentionally primes defect search and may be systematically stricter. Its role is to define a transformed view, not to satisfy a Dawid--Skene replicate assumption. Any DS-style empirical appendix analysis must flag this mismatch.

Test-side metamorphic/property checks are secondary and only used on a preregistered eligible subset with known input/output relations.

## 4. Preflight — infrastructure only, gold blind

Run approximately 50 candidates (e.g. 10 problems × 5 samples) before the main generation.

Allowed diagnostics:

- code extraction / compilation / runtime-failure rates;
- visible-test pass rate;
- judge API success and parse rate;
- each judge/check marginal (+1) rate;
- unanimous rates (hat u_0,hat u_1);
- pairwise raw-agreement and phi-correlation matrices among judge views, both overall and conditional on (V_{visible}=+1);
- latency and cost.

No hidden/extended test is run during preflight.

Preflight passes only if judge parsing is at least 99.5% and the view system is not degenerate (e.g. a parser bug making all views constant). Any model/prompt change after preflight creates a new preregistration version.

## 5. Fixed diagnostic cohort and gold-blind figure-risk gate

After config freeze, generate a **fixed first cohort of 10 candidates per problem**. This cohort is used to estimate (hat u_0,hat u_1) and view dependence without optional-stopping bias.

Before any gold suite is run, record:

[
hat u_m=P(U_m^+),quad min{0,1},
]

the full pairwise-agreement matrix, and the conditional matrix given (V_{visible}=+1).

For audit-budget intuition, targeted sampling puts approximately (B) draws in (U_1^+), while uniform sampling puts approximately (u_1B). Thus the standard-error ratio is approximately (1/sqrt{u_1}).

A preregistered **gold-blind prominence rule** is:

- if (hat u_1le0.60), keep the targeted-vs-uniform budget curve as a candidate main-text panel;
- if (hat u_1>0.60), demote that curve to secondary/appendix status because the efficiency difference is predictably weak.

This rule changes only figure prominence. It does **not** add, remove, or tune checks after seeing (hat u_1).

## 6. Candidate extension and stopping

After the fixed first cohort, candidate generation may continue in uniform rounds of +5 candidates/problem:

[
10, 15, 20, 25, 30 	ext{ candidates/problem}.
]

Stopping uses only reported views (W), never gold (Y):

- stop once (n_{U_1^+}ge1000), or
- stop at 30 candidates/problem.

The final (hat u_1) from the adaptively stopped pool is reported descriptively and noted as slightly affected by optional stopping. The fixed first cohort supplies the preregistered gold-blind estimate of (u_1). The blind-rate estimate (r_1) is not selected on (Y), so the stopping rule is gold blind.

Only after the candidate manifest and view table are frozen and hashed may the hidden/gold suite run.

## 7. Gold labels and primary inference

For every frozen candidate:

[
Y=+1 iff 	ext{passes all extended/gold tests}.
]

Store the binary truth plus diagnostic failure metadata (first failing test ID, number of failed tests, timeout/exception), but the primary analysis uses only binary (Y).

Candidates are clustered within benchmark problem. Therefore the primary population-level uncertainty interval is a **problem-level cluster bootstrap**, not a binomial Clopper--Pearson interval.

### 7.1 Primary cluster interval

Resample benchmark problems with replacement. For each selected problem, carry all of its frozen candidates (a hierarchical within-problem resample is a sensitivity analysis). Recompute (r_0,r_1,r_0-r_1), enrichment, and cost metrics.

Use 10,000 bootstrap replicates for final results and percentile 95% intervals. The main transformation statistic (r_0-r_1) uses a **two-sided** interval.

Report:

- realized problem-level ICC for the blind-error indicator inside (U_1^+);
- empirical design effect
  [
  DEFF=widehat{mathrm{Var}}_{cluster}(hat r_1)Big/{ hat r_1(1-hat r_1)/n_{U_1^+}};
  ]
- the corresponding (n_{eff}=n_{U_1^+}/DEFF).

If fewer than 5 blind errors or fewer than 3 problems containing a blind error are observed, label the cluster interval **sparse-event unstable** and do not claim a GREEN result from it.

### 7.2 Fixed-pool certification interval

Clopper--Pearson remains a supplementary interval **conditional on this exact frozen candidate pool**. It is not the primary population-generalization interval.

This distinction is explicit in every figure/table.

## 8. Practical relevance threshold

The preregistered threshold remains

[
r_{min}=0.005.
]

It is **not** a deployment safety tolerance. It is the minimum effect size chosen for ICML main-text relevance at the planned audit scale: with (n_{U_1^+}=1000), it corresponds to 5 expected blind false accepts, and the two-sided 95% fixed-pool Clopper--Pearson upper bound after observing zero errors is about 0.37%, below the 0.5% threshold. Thus 0.5% is deliberately set just above the smallest rate that the planned fixed-pool audit can resolve. Clustered inference may still classify the same result as unresolved, which is intentionally conservative.

## 9. Red / yellow / green interpretation

Use the **clustered** interval for main-text relevance.

- **GREEN:** cluster-bootstrap 95% lower bound for (r_1) exceeds 0.005, with at least 5 blind errors in at least 3 distinct problems.
- **YELLOW:** the clustered interval includes 0.005, or sparse-event stability criteria fail.
- **RED:** (n_{U_1^+}<500), or both the clustered 95% upper bound and the fixed-pool CP upper bound are below 0.005.

A GREEN under CP but YELLOW under clustering is reported as YELLOW.

The centerpiece Figure B below is still produced for any nonempty (U_1^+); the tier controls framing, not whether results are hidden.

## 10. Null-calibration / harness check

Before any substantive gold analysis, run a mechanical pseudo-gold check using the visible-test verdict as the "truth" label.

Because (U_1^+) includes (V_{visible}=+1), the pseudo false-accept rate inside (U_1^+) must be exactly zero. Any nonzero value indicates a candidate/view/label join or normalization bug and invalidates the run until fixed.

This check uses no hidden-test information.

## 11. Primary figures

### Figure B — centerpiece: agreement-only identified set versus audit

For blind false-accept mass
[
b_1=P(Y=-1,U_1^+)=u_1r_1,
]
agreement alone implies only
[
b_1in[0,u_1].
]

After a gold audit,
[
b_1in[u_1r_L,u_1r_U],
]
where ([r_L,r_U]) is the primary cluster interval; the fixed-pool CP interval is shown as a lighter sensitivity marker.

This panel requires no latent-model fitting.

### Figure A — supporting: blind error in unanimous accepts

Report (hat r_1), its cluster interval, the supplementary CP interval, (hat u_1), and (hat b_1).

### Transformation informativeness panel/table

Primary:
[
r_0-r_1
]
with a two-sided problem-cluster-bootstrap interval.

Supporting 2×2 within (U_0^+):

| | (Y=-1) | (Y=+1) |
|---|---:|---:|
| removed (D) | | |
| retained (U_1^+) | | |

Also report the enrichment ratio (P(Y=-1mid D)/r_0), (P(Y=+1mid D)), and (P(Dmid Y=+1,U_0^+)).

Report (Delta b=b_0-b_1) only as magnitude removed.

### Budget panel — secondary unless (hat u_1le0.60)

Compare **unanimous-stratified versus uniform** allocation over
[
Bin{25,50,100,200,500,1000}.
]

The disagreement-only allocation is relegated to an appendix structural control: because it has zero inclusion probability in (U_1^+), the blind identified set does not shrink.

## 12. Judge/check dependence outputs

Before gold:

- 6×6 judge-view raw-agreement matrix;
- 6×6 phi-correlation matrix;
- same matrices conditional on (V_{visible}=+1);
- (hat u_0,hat u_1);
- marginal acceptance rate of every view.

These are reported even if inconvenient. Very high identity/swap agreement is itself evidence that the nominal number of views overstates effective diversity.

## 13. Analysis locking

The local side must commit, **before candidate generation**:

1. `audit_config.lock.json`;
2. SHA-256 of the frozen analysis script;
3. hashes of all prompts and problem/manifests;
4. this preregistration version.

`freeze_audit_config.py` generates these hashes automatically. Any later change to analysis code, prompts, model IDs, or manifests requires a new lock and preregistration version.

## 14. Secondary analyses

Clearly labeled secondary analyses may include:

- generator-family strata;
- same-family vs cross-family judge subsets;
- identity-only versus identity+transformed views;
- eligible metamorphic-test subset;
- model-based latent identified intervals;
- hierarchical within-problem bootstrap sensitivity;
- finite-population/hypergeometric certification intervals.

None may replace the preregistered primary quantities above.

## 15. Decision log

| Date | Change | Reason | Made before looking at affected gold outcome? |
|---|---|---|---|
| | | | |
