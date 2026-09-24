"""Gold-blind pinned-dataset frame audit for EvalPlus JSONL files.

This helper does not read plus/gold outcomes. It computes:

- full SHA-256 of the dataset file;
- exact problem manifest;
- base_input-count summary;
- deterministic split-impossible exclusion manifest (K < 2).

It also checks the preregistered version-specific SHA-256 prefix and frame
counts before writing artifacts.

Example:
  python dataset_frame_audit.py \
      --benchmark MBPP+ \
      --version v0.2.0 \
      --dataset /path/to/MbppPlus-v0.2.0.jsonl \
      --outdir P1/experiments/local_mbpp_frame
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "MBPP+": {
        "version": "v0.2.0",
        "sha256_prefix": "b54e762755248ca4",
        "task_count": 378,
        "exactly_3_base_tests": 349,
        "one_test_B_view": 349,
        "split_impossible_count": 0,
    },
    "HumanEval+": {
        "version": "v0.1.10",
        "sha256_prefix": "42526ec0e7d5f3ee",
        "task_count": 164,
        "exactly_3_base_tests": 18,
        "one_test_B_view": 20,
        "split_impossible_count": 1,
        "B_ge3_count": 98,
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_dataset(path: Path):
    rows = []
    seen = set()
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            task_id = str(rec.get("task_id", ""))
            if not task_id:
                raise ValueError(f"{path}:{line_no}: missing task_id")
            if task_id in seen:
                raise ValueError(f"{path}:{line_no}: duplicate task_id {task_id}")
            seen.add(task_id)
            base_input = rec.get("base_input")
            if not isinstance(base_input, list):
                raise ValueError(
                    f"{path}:{line_no} {task_id}: base_input must be a list"
                )
            rows.append((task_id, len(base_input)))
    return rows


def summarize(rows):
    counts = {task_id: k for task_id, k in rows}
    split_ids = sorted(task_id for task_id, k in counts.items() if k < 2)
    return {
        "task_count": len(rows),
        "exactly_3_base_tests": sum(k == 3 for k in counts.values()),
        "one_test_B_view": sum(k >= 2 and k // 2 == 1 for k in counts.values()),
        "split_impossible_count": len(split_ids),
        "split_impossible_ids": split_ids,
        "B_ge3_count": sum(k // 2 >= 3 for k in counts.values()),
        "base_count_by_task": counts,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--benchmark", choices=sorted(EXPECTED), required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--outdir", required=True)
    a = p.parse_args()

    exp = EXPECTED[a.benchmark]
    if a.version != exp["version"]:
        raise SystemExit(
            f"VERSION_MISMATCH: expected {exp['version']}, got {a.version}"
        )

    path = Path(a.dataset).resolve()
    digest = sha256_file(path)
    if not digest.startswith(exp["sha256_prefix"]):
        raise SystemExit(
            f"SHA_PREFIX_MISMATCH: {digest} does not start with "
            f"{exp['sha256_prefix']}"
        )

    rows = load_dataset(path)
    facts = summarize(rows)

    for key in (
        "task_count",
        "exactly_3_base_tests",
        "one_test_B_view",
        "split_impossible_count",
    ):
        if facts[key] != exp[key]:
            raise SystemExit(
                f"FRAME_FACT_MISMATCH {key}: observed={facts[key]} expected={exp[key]}"
            )
    if "B_ge3_count" in exp and facts["B_ge3_count"] != exp["B_ge3_count"]:
        raise SystemExit(
            "FRAME_FACT_MISMATCH B_ge3_count: "
            f"observed={facts['B_ge3_count']} expected={exp['B_ge3_count']}"
        )

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    problem_manifest = {
        "benchmark": a.benchmark,
        "version": a.version,
        "dataset_sha256": digest,
        "problem_ids": sorted(task_id for task_id, _ in rows),
    }
    split_manifest = {
        "benchmark": a.benchmark,
        "version": a.version,
        "dataset_sha256": digest,
        "excluded": [
            {
                "problem_id": pid,
                "base_test_count": facts["base_count_by_task"][pid],
                "exclusion_reason": "BASE_TEST_SPLIT_IMPOSSIBLE",
            }
            for pid in facts["split_impossible_ids"]
        ],
    }
    summary = {
        "benchmark": a.benchmark,
        "version": a.version,
        "dataset_file": str(path),
        "dataset_sha256": digest,
        "expected_sha256_prefix": exp["sha256_prefix"],
        "task_count": facts["task_count"],
        "exactly_3_base_tests": facts["exactly_3_base_tests"],
        "one_test_B_view": facts["one_test_B_view"],
        "split_impossible_count": facts["split_impossible_count"],
        "split_impossible_ids": facts["split_impossible_ids"],
        "B_ge3_count": facts["B_ge3_count"],
    }

    (outdir / "problem_manifest.json").write_text(
        json.dumps(problem_manifest, indent=2) + "\n", encoding="utf-8"
    )
    (outdir / "split_exclusion_manifest.json").write_text(
        json.dumps(split_manifest, indent=2) + "\n", encoding="utf-8"
    )
    (outdir / "dataset_frame_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    print("DATASET_FRAME_AUDIT: PASS")
    print("benchmark:", a.benchmark)
    print("version:", a.version)
    print("sha256:", digest)
    print("tasks:", facts["task_count"])
    print("split-impossible:", facts["split_impossible_ids"])
    print("wrote:", outdir)


if __name__ == "__main__":
    main()
