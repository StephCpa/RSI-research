# MBPP+ preflight preregistration v0.3 — diff from v0.2

**Status:** DRAFT / GOLD-BLIND / NOT LOCKED  
**Supersedes:** the v0.2 preflight design after two correctly refused freezes.  
**Gold status:** must remain unexecuted until this protocol passes and the audit config is locked.

## 0. Why v0.3 exists

v0.2 completed 80 candidates over 40 MBPP+ problems with the same generator,
judges, prompts, and decoding as v0.1. The freeze was correctly refused because:

- six-view completeness on A-pass rows was 0.972 after transport-only retries;
- candidate A-pass was exactly 0.90, failing the preregistered strict upper bound;
- problem outcomes were 4 problems at 0/2, 0 at 1/2, and 36 at 2/2;
- one 0/2 problem was a canonical-harness failure rather than generator failure.

The absence of any 1/2 problems makes the next diagnostic **proposal duplication /
intra-problem dependence**, not another immediate change in task difficulty.

No plus/gold result may be inspected while executing this document.

---

## 1. One open diagnostic before changing the generator

Run a **three-level duplication audit** on the existing v0.2 candidate text.
The three measures answer different questions and must not be conflated.

### 1.1 Raw-text duplication — sampler/cache diagnostic

For each candidate, hash the exact UTF-8 response text:

[
h_{raw}(x)=operatorname{SHA256}(x).
]

This measure is sensitive to byte-identical outputs. At the requested stochastic
sampling settings, a high exact-text repeat rate is evidence to check whether
temperature/top-p/seed parameters are reaching the API or whether responses are
being cached/replayed.

### 1.2 Strict AST duplication — continuity metric

Retain the previous metric:

[
h_{strict}(x)=
operatorname{SHA256}{	exttt{ast.dump(ast.parse(x), include_attributes=False)}}.
]

Comments disappear, but docstrings and identifier spellings remain. This metric
is reported only for continuity with v0.1/v0.2; it does **not** drive the branch.

### 1.3 Loose AST duplication — solution-convergence diagnostic

Construct a conservative loose AST by:

- removing module/function/class docstrings;
- alpha-renaming function-local arguments and local identifiers by binding
  order;
- leaving global/builtin names, attributes, literals, operators, and control
  structure intact.

Then hash the resulting AST dump.

This treats simple local-variable renames and docstring additions as the same
solution without attempting general semantic equivalence.

### 1.4 Pair definition

For every metric, compute duplication over **all unordered within-problem
candidate pairs**, not just the first two:

[
q_{dup}^{(m)}
=
rac{#{(i,j):i<j, h_m(x_i)=h_m(x_j)}}
     {#{(i,j):i<j}}.
]

This definition remains valid when the main design uses three candidates per
problem.

Syntax errors must be counted and listed; they are not silently skipped.
Raw-text hashes remain available for syntax-error rows, while strict/loose AST
pair denominators use only syntax-valid pairs.

### 1.5 Frozen decision branch

Use operational threshold 0.25 for the two branching metrics:

- If
  [
  q_{dup}^{raw}ge0.25,
  ]
  classify **SAMPLER_COLLAPSE**. Do **not** change generator capability. First
  verify temperature/top-p propagation, fixed seeds, response caching, and any
  provider cache/fingerprint metadata that is available.

- Else if
  [
  q_{dup}^{loose}ge0.25,
  ]
  classify **DUPLICATION_HIGH**. The sampler is producing different text, but
  the solutions converge structurally. Proceed to the preregistered weaker
  generator; this branch is also evidence for keeping the many-problems /
  few-candidates sampling shape.

- Else classify **PROBLEM_LEVEL_HETEROGENEITY** and proceed to the
  preregistered weaker generator.

Only **SAMPLER_COLLAPSE** blocks the generator switch.

The strict AST rate is reported but does not choose the branch.

This duplication check is the only open empirical diagnostic before the v0.3
API run.

## 2. Generator change

The weaker generator is frozen **before** running the duplication diagnostic:

[
oxed{	exttt{qwen3.6-flash-2026-04-16}}
]

This is the dated Qwen3.6-Flash snapshot used as the one-generation-lower
replacement for the current (	exttt{qwen3.7-flash}) proposal model.

Rules:

- keep MBPP+ as the benchmark population;
- do **not** select a hard tail;
- keep the v0.2 candidate-generation prompt and decoding policy unchanged
  unless the duplication branch is **SAMPLER_COLLAPSE**, in which case only
  sampler/transport plumbing is repaired and the generator model is not changed;
- if the exact snapshot ID above is unavailable on the local endpoint, do not
  silently substitute an alias or another model. Record the availability
  failure and create a new preregistration version before choosing a substitute;
- no second capability downgrade is allowed inside v0.3.

Under **DUPLICATION_HIGH** or **PROBLEM_LEVEL_HETEROGENEITY**, the next
preflight uses exactly (	exttt{qwen3.6-flash-2026-04-16}).

## 3. Judge B transport blocker

The judge-B model stack is unchanged unless explicitly versioned.

A billing/capacity repair or a different endpoint serving the **same exact model
ID** is a transport fix and does not change the verifier definition.

Switching judge-B model ID or family changes the verifier stack and requires a
new preregistration version before use.

### 3.1 Frozen retry policy

For transport-only failures (network error, HTTP 429/5xx, provider capacity /
BalanceError):

1. initial request;
2. retry after 2 s;
3. retry after 8 s;
4. retry after 32 s.

Prompts, model IDs, decoding parameters, and parsing rules remain byte-for-byte
unchanged.

No retry is triggered by the semantic verdict.

### 3.2 Missing-view policy

After the retry budget is exhausted:

- mark the required view as missing;
- exclude that candidate row from the primary complete-case \(U_0/U_1\)
  analysis;
- retain the row in the raw artifact;
- report row-level and cell-level missingness by judge/check and provider error
  class.

For the preflight freeze gate, required-view row completeness after retries must
satisfy

\[
\boxed{\text{complete-row rate} \ge 0.98}.
\]

For the post-lock main collection, the analysis proceeds even if missingness is
nonzero. In addition to complete-case results, report two adversarial
sensitivities:

1. set every missing required view to \(+1\);
2. set every missing required view to \(-1\).

If the qualitative conclusion changes across the two extremes, label the
result **missingness-sensitive**.

---

## 4. Canonical-harness exclusion rule

Before candidate sampling, run each benchmark problem's frozen canonical /
reference solution through the **base-test harness only** (A∪B).

Exclude a problem before candidate generation if the canonical solution:

- crashes;
- times out;
- cannot be executed by the frozen harness; or
- fails the base-test harness for infrastructure reasons.

Do not use plus/gold tests to make this decision.

Record:

- excluded problem IDs;
- exclusion reason;
- total exclusion count.

The MBPP/580 failure from v0.2 is an example of this rule.

---

## 5. v0.3 preflight sampling shape

The preflight itself must emphasize independent problem coverage.

Use:

\[
\boxed{100\ \text{problems} \times 2\ \text{candidates/problem}}
\]

uniformly sampled without replacement from the canonical-harness-valid MBPP+
population using a frozen problem-sample seed.

This preflight is gold blind.

The full post-lock W-only collection, if the preflight passes, uses the broader
shape in Section 8.

---

## 6. Primary preflight freeze gates

The old strict \(0.10<P(A\text{-pass})<0.90\) gate is retired in v0.3 because it
was only a proxy for whether the actual unanimity experiment was degenerate.

### 6.1 Infrastructure gates

The preflight may freeze only if:

- requested candidate count completes;
- extraction success is reported;
- successful-HTTP judge parse rate is at least 0.995;
- complete required-view row rate after the frozen retry budget is at least 0.98.

### 6.2 Unanimity-stratum gate

Among A-pass, required-view-complete rows define the full transformed unanimous
stratum \(U_1^+\). Require

\[
\boxed{
0.20
<
P(U_1^+\mid A\text{-pass},\ \text{complete})
<
0.90
}.
\]

This is the primary non-degeneracy gate.

### 6.3 View-heterogeneity gate

Among the same A-pass complete rows, let \(H\) be the event that the six LLM
views are not all identical. Require

\[
\boxed{P(H)\ge 0.05}.
\]

Also emit the 6×6 disagreement matrix and the six marginal positive rates.

This gate prevents freezing a nominally six-view design that is effectively
constant.

### 6.4 A-pass sanity statistic

Continue to report \(P(A\text{-pass})\), but it is no longer the primary
freeze criterion.

Use the wider preregistered sanity band

\[
0.05<P(A\text{-pass})<0.98.
\]

A value outside this band is a **sanity warning** that must be written into the
freeze artifact. It does not by itself override otherwise-passing primary
unanimity/heterogeneity gates unless fewer than 50 A-pass complete rows remain,
in which case the preflight is underpowered and freeze is refused.

---

## 7. Gold-blind diagnostics emitted by v0.3 preflight

Before freeze, write:

- candidate A-pass rate;
- problem-wise A-pass histogram;
- AST distinct-solution statistics;
- \(P(U_1^+\mid A\text{-pass},complete)\);
- six-view non-unanimous-row share;
- 6×6 LLM disagreement matrix;
- six marginal LLM positive rates;
- test-B vs LLM-view agreement;
- required-view row completeness;
- missing cells by judge/check/error type;
- judge-repeatability flip rate if the 5% repeatability sample is already run.

No plus/gold label may appear in these artifacts.

---

## 8. Post-lock main W-only sampling shape

If v0.3 preflight passes and the config is locked, the main W-only collection
uses many problems and few candidates per problem.

Sample in problem batches up to:

\[
\boxed{400\ \text{problems} \times 3\ \text{candidates/problem}}.
\]

Problem IDs are sampled without replacement from the canonical-harness-valid
population using the frozen main-sample seed.

### 8.0 Preflight/main separation

The main sampling frame **excludes every problem used in any gold-blind
preflight that informed the final design**, including the v0.1, v0.2, and v0.3
preflight problem IDs.

In particular, none of the 100 v0.3 preflight problems may appear in the
400-problem main draw.

The excluded-preflight problem manifest is frozen and hashed before the main
draw. This prevents W-level statistics used to choose or validate the gates
from re-entering the confirmatory main sample.

Do not extend candidate depth within a problem beyond 3 in v0.3.

### 8.1 W-only stopping rule

After each completed 100-problem batch, count

\[
M_{U_1}
=
\#\{\text{problems with at least one AST-distinct }U_1^+\text{ candidate}\}.
\]

Stop early only if

\[
\boxed{M_{U_1}\ge 250}
\]

and all data-quality requirements remain satisfied.

Otherwise continue to the next problem batch, up to 400 problems.

The stopping rule uses only W, AST hashes, transport status, and problem IDs.
It never uses Y / plus / gold.

The primary cluster bootstrap therefore has a problem-level support target,
rather than a nominal candidate-count target.

---

## 9. Gold remains sealed through W-only collection

The order is mandatory:

1. pass v0.3 preflight;
2. write and commit the lock;
3. collect W-only main sample under Section 8;
4. freeze candidate manifest, AST hashes, view table, transport exclusions, and
   repeatability artifacts;
5. only then execute plus/gold;
6. run the preregistered clustered analyses.

No outcome-dependent hard-tail selection is permitted.

Adopting an entirely different harder benchmark is allowed only in a future
preregistration version declared before drawing from it.

---

## 10. Changes from v0.2

| Item | v0.2 | v0.3 |
|---|---|---|
| Main diagnostic problem | A-pass rate | proposal duplication + unanimity degeneracy |
| Preflight sampling | 40×2 | 100×2 |
| Generator | qwen3.7-flash | `qwen3.6-flash-2026-04-16` unless SAMPLER_COLLAPSE |
| Hard-tail selection | forbidden | still forbidden |
| Primary freeze gate | strict A-pass band | \(U_1^+\) share + view heterogeneity |
| A-pass band | hard \(0.10<p<0.90\) | secondary warning \(0.05<p<0.98\) |
| Completeness | ≥0.995 six-view | ≥0.98 complete rows after frozen retries |
| Retry policy | transport-only, not fully frozen | initial + 3 retries at 2/8/32 s |
| Missing views | freeze failure | row exclusion + two extreme imputations |
| Main sampling shape | candidate-heavy | up to 400 problems ×3 |
| Preflight/main overlap | unspecified | main excludes all v0.1–v0.3 preflight problems |
| Main stopping | candidate count | problems contributing to \(U_1^+\) |
| Canonical harness failure | observed ad hoc | preregistered base-harness exclusion |

---

## 11. Decision log entry carried forward

v0.1 and v0.2 freezes were refused and gold was never executed. v0.2 showed
persistent all-or-none problem clustering under broader problem coverage.
Therefore v0.3 first diagnoses AST duplication, then — only if the sampler is
not collapsed — changes generator capability by one step and changes the
freeze gates to measure the actual unanimity experiment rather than the proxy
A-pass rate.

**Do not freeze v0.3 until Section 1's duplication diagnostic has been run and
its result appended below.**

### Duplication diagnostic result

- planned weaker generator fixed before diagnostic: `qwen3.6-flash-2026-04-16`
- v0.2 usable within-problem pairs: **TO FILL**
- raw equal-pair fraction (q_{dup}^{raw}): **TO FILL**
- strict AST equal-pair fraction (q_{dup}^{strict}): **TO FILL**
- loose AST equal-pair fraction (q_{dup}^{loose}): **TO FILL**
- syntax-error rows: **TO FILL**
- branch: **TO FILL — SAMPLER_COLLAPSE / DUPLICATION_HIGH / PROBLEM_LEVEL_HETEROGENEITY**
- generator switch allowed by branch: **TO FILL**
- optional cache/fingerprint metadata finding: **TO FILL / unavailable**
- action taken before v0.3 API calls: **TO FILL**
