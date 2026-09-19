# Preregistration v0.1 — Real-verifier audit pilot

**Project:** P1 — Self-Calibration of AI Verifiers  
**Status:** protocol draft to freeze before any pilot labels are inspected  
**Purpose:** determine early whether the real-task audit claim is empirically resolvable, and, if so, produce the ICML-facing verifier experiment.

## 1. Primary question

Does the unanimous-accept stratum contain a non-negligible blind false-accept mass under a realistic verifier ensemble, and does allocating gold labels to that stratum tighten certified error bounds faster than uniform or disagreement-only auditing?

This experiment is deliberately not a test of the population identifiability theorems. It tests the actionable consequence: internal agreement can leave blind error mass that a targeted external audit resolves.

## 2. Frozen task structure

The pilot uses code-generation tasks with an automatic operational gold channel.

- **Candidate:** a generated program for one benchmark problem.
- **Visible test verifier:** the public/basic test suite available to the candidate-generation loop.
- **Judge A / Judge B:** two LLM judges from distinct model families, frozen before the first pilot run.
- **Gold:** an extended hidden test suite that is never shown to the candidate generator or to the LLM judges.
- **Truth label (Y):** (Y=+1) iff the candidate passes the full gold suite; otherwise (Y=-1).

The preferred pilot benchmark is a frozen HumanEval+/MBPP+-style split in which the basic suite and extended suite are cleanly separated. The exact benchmark version, task list, candidate-generator model IDs, and judge model IDs must be recorded below before data collection.

### 2.1 To freeze before data

| Field | Frozen value |
|---|---|
| Benchmark + version/commit | **TO FILL** |
| Problems included | **TO FILL** |
| Candidate generator model(s) + exact IDs | **TO FILL** |
| Samples per problem | **TO FILL** |
| Sampling temperature / decoding | **TO FILL** |
| Judge A exact model ID | **TO FILL** |
| Judge B exact model ID | **TO FILL** |
| Judge prompt templates / hashes | **TO FILL** |
| Visible-suite definition | **TO FILL** |
| Gold-suite definition | **TO FILL** |

**Lock rule.** The pilot does not begin until every field above is filled and committed. Any later change creates a new preregistration version.

## 3. Verifiers and checks

The experiment separates *verifier diversity* from *check diversity*.

### 3.1 Verifiers

1. (V_{mathrm{test}}): visible/basic test suite.
2. (V_A): LLM judge A.
3. (V_B): LLM judge B.

The visible test suite is intentionally not treated as a transformed copy of itself; a semantics-preserving refactor of the candidate is not expected to expose a fixed coverage gap and is not a primary check.

### 3.2 Checks

For the LLM judges:

- **identity:** standard correctness judgment;
- **verdict-order swap:** reverse the presentation order of the explicit verdict options while preserving semantics;
- **negation:** ask the complementary question (e.g. whether the program is incorrect / whether a counterexample exists) and normalize by the known sign relation.

For tests:

- **identity:** the visible suite;
- **metamorphic/property checks:** used only on a preregistered eligible subset of tasks for which the input/output relation is known independently of the candidate. These checks are secondary unless the eligible subset is large enough to support a separate analysis.

No claim will be made that refactoring the candidate itself should reveal a fixed test-suite coverage gap.

## 4. Normalized views and strata

Every verifier–check output is normalized to the same sign convention (W_vin\{-1,+1\}), where (+1) means the view supports correctness.

Define

[
U^+ = \{W_v=+1 \text{ for every released view } v\}.
]

The primary blind event is

[
B^+ = \{Y=-1,\; W_v=+1 \text{ for every released view } v\}.
]

Primary estimands:

[
r_U = P(Y=-1\mid U^+), \qquad
b = P(B^+), \qquad
u = P(U^+).
]

The concentration ratio

[
\Gamma = \frac{P(Y=-1\mid U^+)}{P(Y=-1)}
]

is secondary and describes how strongly false accepts concentrate in the unanimous stratum.

## 5. Hypotheses

### H1 — resolvable blind mass

The unanimous-accept stratum contains a practically non-negligible blind false-accept rate:

[
r_U > r_{\min}.
]

For the pilot, (r_{\min}=0.005) (0.5%). This is an effect-size threshold, not a null of exact zero.

### H2 — targeted audit efficiency

At equal gold budget (B), unanimous-stratified allocation yields a narrower 95% interval for the blind contribution to false-accept mass than uniform allocation.

Primary comparison:

[
\operatorname{width}_{U^+}(B)
<
\operatorname{width}_{\mathrm{uniform}}(B)
]

for the preregistered budget grid.

### H3 — disagreement-only cannot resolve blind mass

An allocation with zero inclusion probability in (U^+) does not update the identified interval for (r_U); its blind-mass bound is therefore flat as a function of budget.

This is a structural control, not a statistical hypothesis test.

## 6. Audit strategies

Gold labels are known automatically for the full dataset, but the analysis hides them and reveals them according to a simulated audit policy.

For each budget

[
B\in\{25,50,100,200,500,1000\},
]

compare:

1. **Unanimous-stratified:** sample from (U^+) only for the primary blind-mass target.
2. **Uniform:** sample uniformly from all candidates.
3. **Disagreement-only:** sample only from (\{W\neq+\mathbf 1\}).

For any policy with unequal inclusion probabilities and any estimand outside (r_U), use the known design weights / Horvitz–Thompson estimator. The primary (r_U) interval under unanimous-stratified sampling is the exact Clopper–Pearson interval.

Each budget/policy pair is resampled 1000 times from the fixed finite dataset to estimate the distribution of interval width.

## 7. Primary figures

The main experiment produces exactly three panels.

### Panel A — blind error inside unanimous accepts

Report

[
\widehat r_U = \frac{\#\{Y=-1,U^+\}}{\#\{U^+\}}
]

with a 95% Clopper–Pearson interval, plus (u=P(U^+)) and the absolute blind mass (b=P(B^+)).

### Panel B — agreement-only identified set versus audit interval

Fit the preregistered latent model to the observed view law and report its agreement-only identified interval for accepted-set precision. Overlay the gold-audited interval obtained from the sampled (U^+) labels.

This panel must be labeled **model-based** if the latent model is used; the empirical gold rate is shown separately.

### Panel C — interval width versus gold budget

Plot median and 10th–90th percentile interval width over the 1000 audit resamples for unanimous-stratified, uniform, and disagreement-only allocation.

The disagreement-only curve should remain flat for the blind component by construction.

## 8. Pilot size and stopping rule

The two-day pilot proceeds until either:

- at least **1000 unanimous-accept candidates** have gold labels, or
- the candidate budget specified in the frozen config is exhausted.

Because gold is automatic, all generated candidates may be evaluated by the hidden suite; the “audit budget” is simulated after the fact.

### 8.1 Kill condition

The real-task audit result is **not** promoted to the ICML main paper if, at the end of the pilot,

[
\operatorname{CP}^{95\%}_{\mathrm{upper}}(r_U) < 0.005,
]

or if fewer than 500 unanimous-accept candidates are obtained.

Interpretation: the chosen benchmark/verifier stack either has blind mass below the preregistered practically resolvable threshold or does not generate enough unanimous accepts to support the intended audit demonstration.

If the kill condition fires, the theory paper continues unchanged; the real-task framing is weakened and a second benchmark may be tried only under a new preregistration version.

### 8.2 Go condition

Proceed to the full experiment if:

- (n_{U^+}\ge1000), and
- the 95% upper bound on (r_U) is at least 0.5%.

A stronger “headline” condition is a 95% lower bound above 0.5%; failure of that stronger condition does not itself kill the experiment.

## 9. Exclusions and leakage controls

- Any candidate whose visible-test execution is nondeterministic or crashes the harness is retained as a visible-test failure unless the harness itself is at fault.
- Gold tests are never included in judge prompts or candidate-generation prompts.
- Judge prompts do not include hidden-test outcomes.
- If a benchmark problem leaks its extended tests through the model context or tooling, that task is excluded by a predeclared mechanical rule and listed.
- Judge API retries are allowed only for transport failures, not for unfavorable verdicts.
- Model/version changes after the first data are prohibited within a preregistration version.

## 10. Secondary analyses

Secondary, clearly labeled analyses may include:

- separate blind rates by candidate generator;
- same-family versus cross-family judge subsets;
- identity-only views versus identity + transformed judge checks;
- tasks with preregistered metamorphic checks versus tasks without them;
- calibration of model-based identified intervals under observed misspecification.

These analyses cannot replace the three primary panels.

## 11. Relation to the finite-sample simulation

The simulation and this pilot run in parallel.

The finite-sample study will additionally:

1. plot reconstruction error versus sample size (N);
2. plot reconstruction error versus a normalized distance-to-degeneracy statistic derived from (|\Delta_\pi(\theta)|) / the relevant condition numbers;
3. compare the constructive inverse, random-start EM/MLE, and EM/MLE initialized at the constructive estimate.

The expected role of the constructive inverse is initialization-free consistent recovery; the likelihood refinement tests whether one EM/Newton stage improves statistical efficiency.

## 12. Decision log

Any deviation from this protocol is appended here before the affected result is inspected.

| Date | Change | Reason | Made before looking at affected outcome? |
|---|---|---|---|
| | | | |
