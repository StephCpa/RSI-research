# Canonical-harness result schema

The freeze does not trust a hand-written exclusion list. For each benchmark it
requires a **full per-task canonical-harness result table** covering every task
in the pinned dataset exactly once, and derives the canonical-exclusion set from
that table.

Example:

```json
{
  "benchmark": "MBPP+",
  "dataset_sha256": "<full 64-hex SHA-256 of the pinned JSONL>",
  "harness_code_sha256": "<full 64-hex SHA-256 identifying the frozen harness>",
  "results": [
    {
      "problem_id": "Mbpp/2",
      "harness_ok": true,
      "exclusion_reason": null
    },
    {
      "problem_id": "Mbpp/580",
      "harness_ok": false,
      "exclusion_reason": "CANONICAL_HARNESS_FAILURE"
    }
  ]
}
```

Rules enforced by `freeze_audit_config.py`:

1. `benchmark` must match the configured stratum;
2. `dataset_sha256` must equal the recomputed hash of the pinned dataset file;
3. `harness_code_sha256` must equal the SHA-256 recomputed from the frozen canonical-harness code file configured for that benchmark;
4. `results` must cover **every pinned task ID exactly once**;
5. failed rows must have an exclusion reason;
6. the canonical-exclusion manifest must equal the set of failed rows exactly;
7. the final confirmatory frame is recomputed as

[
F
=
	ext{dataset task IDs}
-
	ext{split-impossible IDs}
-
	ext{canonical-harness exclusions}
-
	ext{preflight-union IDs}.
]

The frozen main-frame manifest must equal this derived set exactly.
