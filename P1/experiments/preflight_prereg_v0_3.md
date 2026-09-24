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

## 5. v0.3 preflight sampling shape and frame conservation

The v0.3 preflight uses

[
oxed{100 	ext{MBPP+ problems}	imes2 	ext{candidates/problem}}
]

but it must **reuse already-burned preflight problems first**.

Let

[
B_{12}=B_{v0.1}cup B_{v0.2}
]

be the union of MBPP+ problem IDs already used by the two earlier gold-blind
preflights. Construct the v0.3 preflight problem set as follows:

1. include every canonical-harness-valid problem in (B_{12});
2. if fewer than 100 unique problems are available, fill the remainder by
   uniform sampling without replacement from previously unused,
   canonical-harness-valid MBPP+ problems using the frozen v0.3 preflight seed;
3. never discard an already-burned problem merely to create a fresh 100-problem
   sample.

Thus the union of all MBPP+ preflight problems after v0.3 is targeted to be
**100 unique problems total**, not 10+40+100 fresh problems.

This preserves fresh MBPP+ tasks for the confirmatory frame while keeping the
v0.3 gate evaluation gold blind.

The full post-lock design uses the two-stratum frame in Section 8.

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

## 8. Post-lock confirmatory frame: two preregistered benchmark strata

The earlier (M_{U_1}ge250) stopping target is removed. With MBPP+ v0.2.0
containing 378 tasks, a strict no-overlap rule plus preflight/canonical
exclusions can make 250 contributing MBPP+ problems impossible. A nominal
"up to 400 MBPP+ problems" cap is likewise not a valid stopping rule when the
eligible frame can be smaller.

### 8.1 Stratum A — MBPP+

MBPP+ v0.2.0 contains 378 tasks. The main MBPP+ frame is

[
F_M
=
{	ext{canonical-harness-valid MBPP+ tasks}}
setminus
{	ext{all MBPP+ preflight tasks}}.
]

Because v0.3 reuses v0.1/v0.2 tasks first, the union of preflight tasks is
targeted to be 100 unique MBPP+ problems. Subject to canonical-harness
exclusions, the main MBPP+ frame is therefore expected to be at most roughly
278 problems, not 400.

Every task in (F_M) receives exactly **3 candidate-generation attempts**.
There is no candidate-depth extension beyond 3.

### 8.2 Stratum B — HumanEval+

HumanEval+ is preregistered **now**, before the duplication diagnostic and
before any W-only confirmatory statistic, as a second confirmatory stratum.

Let

[
F_H
=
{	ext{canonical-harness-valid HumanEval+ tasks}}
setminus
{	ext{any HumanEval+ problems previously used in design-informing preflights}}.
]

HumanEval has 164 tasks before any such exclusions.

Use the same frozen:

- generator model and decoding policy;
- Judge A / Judge B model IDs;
- identity / verdict-option-order / negation prompts;
- A/B base-test split algorithm;
- retry/missingness policy;
- AST hashing/deduplication;
- 5% repeatability rule;
- gold definition and analysis scripts.

Every task in (F_H) also receives exactly **3 candidate-generation attempts**.

HumanEval+ is not a post-result rescue benchmark. It is part of the
preregistered two-stratum confirmatory design.

### 8.3 No preflight/main overlap

No problem used in any design-informing preflight may enter its benchmark's
confirmatory frame. The frozen lock contains:

- MBPP+ preflight-union manifest;
- HumanEval+ preflight-union manifest (possibly empty);
- canonical-harness exclusion manifests;
- final (F_M) and (F_H) manifests.

### 8.4 Main-sample terminal rule: frame exhaustion

The confirmatory W-only collection samples the **entire frozen eligible frame**
(F_Mcup F_H), subject only to transport completion/exclusion rules already
preregistered.

There is no early stop based on (M_{U_1}), candidate count, or a W-derived
proxy once the confirmatory run begins.

The terminal state is explicit:

[
oxed{	ext{FRAME EXHAUSTED}}
]

when every eligible problem in both frozen strata has received its three
candidate attempts and the frozen transport policy has terminated.

If a stratum has fewer eligible problems than anticipated, no replacement is
drawn from a new benchmark and candidate depth is not increased.

### 8.5 Precision target is an analysis adequacy criterion, not a gold-dependent stopping rule

The desired clustered 95% half-width

[
h_{mathrm{cluster}}(r_1)le0.02
]

is retained as an **aspirational precision bar**, but it is **not** used to stop
sampling because (r_1) requires gold (Y). Using the realized clustered
half-width as a stopping rule would break the gold-sealed W-only design and
would require sequential-inference corrections not otherwise part of this
protocol.

After the full frozen frame is exhausted and gold is opened, report the
achieved clustered half-width for each benchmark and for the stratified pooled
estimand. If it exceeds 0.02, label the result **precision-limited** and report
the achieved interval. Do not rescue precision by:

- generating more candidates per sampled problem;
- reusing preflight problems;
- selecting a hard tail;
- adding a third benchmark after seeing results.

### 8.6 Stratified pooled analysis

Report benchmark-specific estimates (r_{1,M}) and (r_{1,H}) first.

For a pooled summary, use frozen task-frame weights

[
omega_M
=
rac{|F_M|}{|F_M|+|F_H|},
qquad
omega_H=1-omega_M.
]

The pooled estimand is the corresponding task-frame-standardized quantity, and
the cluster bootstrap resamples problems **within each benchmark stratum**
while preserving the frozen stratum sizes and weights.

Also report an equal-stratum-weight sensitivity
(omega_M=omega_H=1/2) so that the larger MBPP+ frame cannot hide
cross-benchmark heterogeneity.

## 9. Gold remains sealed through W-only collection

The order is mandatory:

1. pass v0.3 preflight;
2. write and commit the lock;
3. collect the full frozen two-stratum W-only frame under Section 8 until
   FRAME EXHAUSTED;
4. freeze candidate manifests, AST hashes, view tables, transport exclusions,
   repeatability artifacts, and final stratum sizes;
5. only then execute plus/gold for both strata;
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
| Main sampling shape | candidate-heavy | census of frozen MBPP+ + HumanEval+ frames, 3 candidates/problem |
| Preflight reuse | unspecified | v0.3 reuses v0.1/v0.2 MBPP+ problems first |
| Preflight/main overlap | unspecified | confirmatory frames exclude all design-informing preflight problems |
| Main stopping | candidate count | no early stop; terminal state is FRAME EXHAUSTED |
| Precision rule | nominal candidate target | report achieved clustered half-width; >0.02 = precision-limited |
| Canonical harness failure | observed ad hoc | preregistered base-harness exclusion |

---

## 11. Decision log entry carried forward

v0.1 and v0.2 freezes were refused and gold was never executed. v0.2 showed
persistent all-or-none problem clustering under broader problem coverage.
Therefore v0.3 first diagnoses AST duplication, then — only if the sampler is
not collapsed — changes generator capability by one step and changes the
freeze gates to measure the actual unanimity experiment rather than the proxy
A-pass rate.

Before the duplication diagnostic is run, the sampling-frame arithmetic is
also frozen: v0.3 reuses already-burned MBPP+ preflight tasks, HumanEval+ is a
predeclared second confirmatory stratum, and the main run ends by frame
exhaustion rather than an infeasible contributing-problem target.

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
