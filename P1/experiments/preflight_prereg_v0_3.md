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

Run an AST-normalized duplication audit on the existing v0.2 candidates.

For each problem, compute:

\[
d_p =
\frac{\#\{\text{distinct normalized AST hashes}\}}
     {\#\{\text{successfully extracted candidates}\}}.
\]

For the current 2-candidate-per-problem v0.2 sample, additionally report:

- number and fraction of problems with 1 distinct AST out of 2;
- number and fraction with 2 distinct ASTs out of 2;
- overall duplicate-candidate fraction;
- the same quantities restricted to A-pass problems.

### 1.1 Decision branch

Let \(q_{dup}\) be the fraction of eligible 2-candidate problems whose two
candidates have the same normalized AST hash.

- If \(q_{dup}\ge 0.25\), classify the proposal sampler as **duplication-high**.
  Before changing model capability, verify that the requested temperature /
  sampling parameters actually reach the provider and that no fixed seed or
  response cache is collapsing the two draws. Re-run a gold-blind preflight
  after fixing sampling.
- If \(q_{dup}<0.25\), classify the observed 0/2-vs-2/2 behavior as primarily
  **problem-level heterogeneity** and proceed to the one-step-weaker generator
  branch below.

The 0.25 threshold is a pre-data operational trigger for this diagnostic only;
it is not a paper result.

This duplication check is the only open design item in v0.3.

---

## 2. Generator change

If the duplication diagnostic does not reveal a collapsed sampler:

- keep MBPP+ as the benchmark population;
- do **not** select a hard tail;
- switch the generator down exactly one declared capability step;
- prefer staying in the same model family when a clearly ordered smaller model
  is locally available;
- freeze the exact provider/model ID and decoding parameters before the new
  preflight.

The purpose is to move the proposal distribution away from near-universal
A-pass without flooding the pool with blatantly wrong code.

No second capability downgrade is allowed inside v0.3. A further downgrade
requires v0.4.

---

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
| Generator | qwen3.7-flash | one declared step weaker if duplication-low |
| Hard-tail selection | forbidden | still forbidden |
| Primary freeze gate | strict A-pass band | \(U_1^+\) share + view heterogeneity |
| A-pass band | hard \(0.10<p<0.90\) | secondary warning \(0.05<p<0.98\) |
| Completeness | ≥0.995 six-view | ≥0.98 complete rows after frozen retries |
| Retry policy | transport-only, not fully frozen | initial + 3 retries at 2/8/32 s |
| Missing views | freeze failure | row exclusion + two extreme imputations |
| Main sampling shape | candidate-heavy | up to 400 problems ×3 |
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

- v0.2 eligible problems: **TO FILL**
- same-AST 2/2 problem pairs: **TO FILL**
- \(q_{dup}\): **TO FILL**
- branch: **TO FILL — duplication-high / problem-level heterogeneity**
- action taken before v0.3 API calls: **TO FILL**
