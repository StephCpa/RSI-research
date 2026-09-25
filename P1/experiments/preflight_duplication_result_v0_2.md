# MBPP+ v0.2 duplication diagnostic result

**Status:** GOLD-BLIND diagnostic complete  
**Protocol:** `preflight_prereg_v0_3.md`  
**Gold accessed:** NO  
**External API calls during diagnostic:** NO  
**Protocol modified by diagnostic:** NO

## Source artifact

The completed MBPP+ v0.2 preflight artifact was located in the local source
worktree:

```
/Volumes/Elements SE/Frontier/RSI-Research/experiments/E05/results/preflight_mbpp_v0.2/
```

Key inputs:

- `preflight_table.csv`: 80 rows, 40 problems, no gold/plus columns;
- `code/*.py`: 80 candidate files;
- `raw_responses/gen_*.json`: generator metadata.

All 80 code files matched the frozen `code_sha256` values in the preflight
table exactly: zero missing and zero mismatches.

A temporary candidate-only input table was built at:

```
/tmp/dupdiag/preflight_v02_candidates_wonly.csv
```

with only:

- `problem_id`
- `candidate_id`
- `code`
- `screen_tests_A`
- optional provider metadata

The diagnostic summary was written to:

```
/tmp/dupdiag/preflight_duplication_summary.json
```

## Regression self-test

```
DUPLICATION_HASH_SELFTEST: PASS
```

## All candidates

80 usable rows, 40 problems with within-problem pairs, 40 unordered pairs.

| metric | equal pairs | total pairs | q_dup |
|---|---:|---:|---:|
| raw | 4 | 40 | 0.1000 |
| strict | 5 | 40 | 0.1250 |
| loose | 17 | 40 | 0.4250 |

Syntax errors: **0**  
Missing code rows: **0**

Raw-identical problems:

- Mbpp/250
- Mbpp/404
- Mbpp/741
- Mbpp/777

Strict-AST-identical problems additionally include:

- Mbpp/6

Loose-AST-identical problems:

- Mbpp/6
- Mbpp/56
- Mbpp/70
- Mbpp/89
- Mbpp/222
- Mbpp/233
- Mbpp/250
- Mbpp/262
- Mbpp/404
- Mbpp/406
- Mbpp/424
- Mbpp/425
- Mbpp/596
- Mbpp/637
- Mbpp/741
- Mbpp/777
- Mbpp/804

## A-pass subset

72 rows, 36 problems with pairs, 36 unordered pairs.

| metric | equal pairs | total pairs | q_dup |
|---|---:|---:|---:|
| raw | 3 | 36 | 0.0833333 |
| strict | 4 | 36 | 0.1111111 |
| loose | 16 | 36 | 0.4444444 |

## Provider metadata

All 80 generator responses reported:

```
cached_tokens = 0
```

so:

- n = 80
- min = 0
- max = 0
- mean = 0.0

No `system_fingerprint` or `model_fingerprint` field was present.

The returned model was consistently:

```
qwen3.7-flash
```

## Frozen branch decision

The preregistered thresholds are:

[
q_{mathrm{dup}}^{raw}ge0.25
Rightarrow
	exttt{SAMPLER_COLLAPSE},
]

otherwise

[
q_{mathrm{dup}}^{loose}ge0.25
Rightarrow
	exttt{DUPLICATION_HIGH}.
]

Observed:

[
q_{mathrm{dup}}^{raw}=0.100<0.25,
]

[
q_{mathrm{dup}}^{loose}=0.425ge0.25.
]

Therefore:

[
oxed{	exttt{DUPLICATION_HIGH}}
]

and the preregistered generator switch is **allowed**.

The next generator remains the one frozen before this diagnostic:

```
qwen3.6-flash-2026-04-16
```

## Interpretation

The proposal sampler is not classified as collapsed: exact-text duplication is
only 4/40 pairs, and provider metadata shows no cached-token hits.

However, structurally equivalent solutions are common: 17/40 pairs become
identical after docstring removal and local alpha-renaming. Thus extra draws
within the same short MBPP problem frequently reproduce the same underlying
solution form.

This supports the preregistered many-problems / few-candidates design and
triggers the already-frozen weaker-generator branch.

## Next preregistered action

Do not run gold.

Before the v0.3 API preflight:

1. resolve the Judge-B DashScope transport/BalanceError issue without changing
   judge prompt semantics;
2. verify availability of exact generator ID
   `qwen3.6-flash-2026-04-16`;
3. construct the v0.3 100-problem preflight set by reusing already-burned
   MBPP+ preflight problems first and adding only enough fresh problems to reach
   100 unique preflight problems;
4. run the frozen v0.3 gold-blind preflight;
5. freeze only if all v0.3 gates pass.

No hard-tail selection and no model substitution are permitted.
