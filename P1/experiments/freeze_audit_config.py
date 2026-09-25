"""Validate and freeze the real-verifier audit configuration.

This freeze is intentionally recompute-rather-than-trust:

1. hash the pinned EvalPlus dataset files and require exact full SHA-256 matches;
2. parse every task's base_input from those pinned files;
3. recompute the split-impossible set (K < 2) and require exact equality with
   the frozen split-exclusion manifests;
4. validate full canonical-harness result tables against every pinned task ID,
   derive canonical exclusions from those results, and require exact equality
   with the canonical-exclusion manifests;
5. derive the confirmatory frames from
      dataset - split exclusions - canonical exclusions - preflight union
   and require exact equality with the frozen frame manifests;
6. hash all manifests, prompts, preregistrations, and analysis code.

No gold/plus outcome is required by this script.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED_PROTOCOL = "audit_prereg_v0_3"

EXPECTED_DATASETS = {
    "MBPP+": {
        "version": "v0.2.0",
        "sha256_prefix": "b54e762755248ca4",
        "task_count": 378,
        "exactly_3_base_tests": 349,
        "one_test_B_view": 349,
        "split_impossible_count": 0,
        "B_ge3_count": 3,
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

REQUIRED_PATHS = [
    ("benchmark", "name"),
    ("benchmark", "version_or_commit"),
    ("benchmark", "dataset_file"),
    ("benchmark", "dataset_sha256"),
    ("benchmark", "expected_sha256_prefix"),
    ("benchmark", "problem_manifest"),
    ("benchmark", "base_test_split_seed"),
    ("benchmark", "base_test_split_manifest"),
    ("benchmark", "split_exclusion_manifest"),
    ("benchmark", "visible_suite_definition"),
    ("benchmark", "gold_suite_definition"),
    ("secondary_stratum", "name"),
    ("secondary_stratum", "version_or_commit"),
    ("secondary_stratum", "dataset_file"),
    ("secondary_stratum", "dataset_sha256"),
    ("secondary_stratum", "expected_sha256_prefix"),
    ("secondary_stratum", "problem_manifest"),
    ("secondary_stratum", "base_test_split_seed"),
    ("secondary_stratum", "base_test_split_manifest"),
    ("secondary_stratum", "split_exclusion_manifest"),
    ("secondary_stratum", "known_split_impossible_problem_ids"),
    ("secondary_stratum", "visible_suite_definition"),
    ("secondary_stratum", "gold_suite_definition"),
    ("preflight", "target_unique_mbpp_problems"),
    ("preflight", "candidates_per_problem"),
    ("preflight", "prior_mbpp_preflight_union_manifest"),
    ("preflight", "final_mbpp_preflight_union_manifest"),
    ("preflight", "problem_sample_seed"),
    ("candidate_generation", "model_ids"),
    ("candidate_generation", "samples_per_problem_main"),
    ("candidate_generation", "temperature"),
    ("candidate_generation", "top_p"),
    ("candidate_generation", "max_tokens"),
    ("prompts", "identity"),
    ("prompts", "order_swap"),
    ("prompts", "negation"),
    ("transport", "retry_backoff_seconds"),
    ("transport", "preflight_complete_row_min"),
    ("main_sampling", "terminal_rule"),
    ("main_sampling", "candidates_per_problem"),
    ("main_sampling", "clustered_halfwidth_aspirational"),
    ("main_sampling", "mbpp_preflight_union_manifest"),
    ("main_sampling", "humaneval_preflight_union_manifest"),
    ("main_sampling", "mbpp_canonical_harness_code"),
    ("main_sampling", "humaneval_canonical_harness_code"),
    ("main_sampling", "mbpp_canonical_harness_results"),
    ("main_sampling", "humaneval_canonical_harness_results"),
    ("main_sampling", "mbpp_canonical_exclusion_manifest"),
    ("main_sampling", "humaneval_canonical_exclusion_manifest"),
    ("main_sampling", "mbpp_main_frame_manifest"),
    ("main_sampling", "humaneval_main_frame_manifest"),
    ("practical_blind_error_bar",),
    ("judge_quality_upper_bar",),
    ("fixed_pool_precision_halfwidth_target",),
    ("judge_repeatability", "fraction"),
    ("judge_repeatability", "seed"),
]


def get(d, path):
    x = d
    for k in path:
        x = x[k]
    return x


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def resolve_file(value):
    p = Path(value)
    if not p.is_absolute():
        p = HERE / p
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def require_full_sha256(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError(f"{label} must be a full 64-hex SHA-256, got {value!r}")
    return value.lower()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl_dataset(path: Path):
    records = []
    seen = set()
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if "task_id" not in rec:
                raise ValueError(f"{path}:{line_no}: missing task_id")
            task_id = str(rec["task_id"])
            if task_id in seen:
                raise ValueError(f"{path}:{line_no}: duplicate task_id {task_id}")
            seen.add(task_id)
            base_input = rec.get("base_input")
            if not isinstance(base_input, list):
                raise ValueError(
                    f"{path}:{line_no} {task_id}: base_input must be a list"
                )
            records.append((task_id, len(base_input)))
    if not records:
        raise ValueError(f"{path}: empty dataset")
    return records


def dataset_facts(records):
    counts = {task_id: k for task_id, k in records}
    return {
        "task_count": len(records),
        "exactly_3_base_tests": sum(k == 3 for k in counts.values()),
        "one_test_B_view": sum(k >= 2 and (k // 2) == 1 for k in counts.values()),
        "split_impossible_ids": sorted(task_id for task_id, k in counts.items() if k < 2),
        "B_ge3_count": sum((k // 2) >= 3 for k in counts.values()),
        "base_count_by_task": counts,
    }


def load_problem_id_manifest(path: Path):
    data = load_json(path)
    ids = data.get("problem_ids")
    if not isinstance(ids, list):
        raise ValueError(f"{path}: expected a problem_ids list")
    ids = [str(x) for x in ids]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate problem_ids")
    return set(ids)


def load_exclusion_manifest(path: Path):
    data = load_json(path)
    excluded = data.get("excluded")
    if not isinstance(excluded, list):
        raise ValueError(f"{path}: expected an excluded list")
    out = {}
    for rec in excluded:
        pid = str(rec.get("problem_id", ""))
        if not pid:
            raise ValueError(f"{path}: exclusion record missing problem_id")
        if pid in out:
            raise ValueError(f"{path}: duplicate exclusion record for {pid}")
        out[pid] = rec
    return out


def expected_split_exclusions(facts):
    out = {}
    for pid in facts["split_impossible_ids"]:
        out[pid] = {
            "problem_id": pid,
            "base_test_count": facts["base_count_by_task"][pid],
            "exclusion_reason": "BASE_TEST_SPLIT_IMPOSSIBLE",
        }
    return out


def compare_split_manifest(path: Path, facts):
    actual = load_exclusion_manifest(path)
    expected = expected_split_exclusions(facts)
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise ValueError(
            f"{path}: split-exclusion set mismatch; missing={missing}, extra={extra}"
        )
    for pid, exp in expected.items():
        got = actual[pid]
        if int(got.get("base_test_count", -1)) != exp["base_test_count"]:
            raise ValueError(
                f"{path}: {pid} base_test_count mismatch: "
                f"{got.get('base_test_count')} != {exp['base_test_count']}"
            )
        if got.get("exclusion_reason") != exp["exclusion_reason"]:
            raise ValueError(
                f"{path}: {pid} exclusion_reason must be "
                f"{exp['exclusion_reason']}"
            )
    return set(expected)


def validate_dataset(section, label):
    name = section["name"]
    if name not in EXPECTED_DATASETS:
        raise ValueError(f"{label}.name unsupported by frozen protocol: {name!r}")
    expected = EXPECTED_DATASETS[name]

    if section["version_or_commit"] != expected["version"]:
        raise ValueError(
            f"{label}.version_or_commit must be {expected['version']!r}, "
            f"got {section['version_or_commit']!r}"
        )

    configured_sha = require_full_sha256(section["dataset_sha256"], f"{label}.dataset_sha256")
    dataset_path = resolve_file(section["dataset_file"])
    actual_sha = sha256_file(dataset_path)

    if actual_sha != configured_sha:
        raise ValueError(
            f"{label}: dataset SHA-256 mismatch; config={configured_sha}, file={actual_sha}"
        )
    if not actual_sha.startswith(expected["sha256_prefix"]):
        raise ValueError(
            f"{label}: dataset SHA-256 {actual_sha} does not match frozen prefix "
            f"{expected['sha256_prefix']}"
        )
    if section.get("expected_sha256_prefix") != expected["sha256_prefix"]:
        raise ValueError(
            f"{label}.expected_sha256_prefix must equal frozen prefix "
            f"{expected['sha256_prefix']}"
        )

    records = load_jsonl_dataset(dataset_path)
    facts = dataset_facts(records)

    checks = {
        "task_count": expected["task_count"],
        "exactly_3_base_tests": expected["exactly_3_base_tests"],
        "one_test_B_view": expected["one_test_B_view"],
        "split_impossible_count": expected["split_impossible_count"],
    }
    if "B_ge3_count" in expected:
        checks["B_ge3_count"] = expected["B_ge3_count"]

    observed = {
        "task_count": facts["task_count"],
        "exactly_3_base_tests": facts["exactly_3_base_tests"],
        "one_test_B_view": facts["one_test_B_view"],
        "split_impossible_count": len(facts["split_impossible_ids"]),
        "B_ge3_count": facts["B_ge3_count"],
    }
    for key, exp in checks.items():
        if observed[key] != exp:
            raise ValueError(
                f"{label}: pinned dataset fact mismatch for {key}: "
                f"observed={observed[key]}, expected={exp}"
            )

    return {
        "name": name,
        "path": dataset_path,
        "sha256": actual_sha,
        "records": records,
        "facts": facts,
        "task_ids": set(facts["base_count_by_task"]),
        "observed": observed,
    }


def validate_canonical_results(path: Path, dataset_info, harness_code_sha256):
    data = load_json(path)
    if data.get("benchmark") != dataset_info["name"]:
        raise ValueError(
            f"{path}: benchmark must be {dataset_info['name']!r}"
        )
    if data.get("dataset_sha256") != dataset_info["sha256"]:
        raise ValueError(
            f"{path}: dataset_sha256 does not match pinned dataset"
        )
    harness_sha = require_full_sha256(
        data.get("harness_code_sha256"), f"{path}.harness_code_sha256"
    )
    if harness_sha != harness_code_sha256:
        raise ValueError(
            f"{path}: harness_code_sha256 does not match the recomputed harness file hash"
        )

    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError(f"{path}: expected a results list")

    by_id = {}
    for rec in results:
        pid = str(rec.get("problem_id", ""))
        if not pid:
            raise ValueError(f"{path}: canonical result missing problem_id")
        if pid in by_id:
            raise ValueError(f"{path}: duplicate canonical result for {pid}")
        if not isinstance(rec.get("harness_ok"), bool):
            raise ValueError(f"{path}: {pid} harness_ok must be boolean")
        if not rec["harness_ok"] and not rec.get("exclusion_reason"):
            raise ValueError(
                f"{path}: {pid} failed harness but has no exclusion_reason"
            )
        by_id[pid] = rec

    if set(by_id) != dataset_info["task_ids"]:
        missing = sorted(dataset_info["task_ids"] - set(by_id))
        extra = sorted(set(by_id) - dataset_info["task_ids"])
        raise ValueError(
            f"{path}: canonical results must cover pinned frame exactly; "
            f"missing={missing[:20]}, extra={extra[:20]}"
        )

    exclusions = {
        pid: rec for pid, rec in by_id.items() if not rec["harness_ok"]
    }
    return exclusions


def compare_canonical_exclusion_manifest(path: Path, derived):
    actual = load_exclusion_manifest(path)
    if set(actual) != set(derived):
        missing = sorted(set(derived) - set(actual))
        extra = sorted(set(actual) - set(derived))
        raise ValueError(
            f"{path}: canonical-exclusion set mismatch; missing={missing}, extra={extra}"
        )
    for pid, rec in derived.items():
        if actual[pid].get("exclusion_reason") != rec.get("exclusion_reason"):
            raise ValueError(
                f"{path}: {pid} exclusion_reason mismatch: "
                f"{actual[pid].get('exclusion_reason')!r} != "
                f"{rec.get('exclusion_reason')!r}"
            )
    return set(actual)


def validate_main_frame(
    name,
    dataset_info,
    split_exclusions,
    canonical_exclusions,
    preflight_manifest_path: Path,
    main_frame_manifest_path: Path,
):
    preflight = load_problem_id_manifest(preflight_manifest_path)
    unknown_preflight = preflight - dataset_info["task_ids"]
    if unknown_preflight:
        raise ValueError(
            f"{preflight_manifest_path}: unknown {name} problem IDs "
            f"{sorted(unknown_preflight)[:20]}"
        )

    expected = (
        dataset_info["task_ids"]
        - split_exclusions
        - canonical_exclusions
        - preflight
    )
    actual = load_problem_id_manifest(main_frame_manifest_path)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{main_frame_manifest_path}: main frame mismatch; "
            f"missing={missing[:20]}, extra={extra[:20]}"
        )
    return {
        "preflight_count": len(preflight),
        "split_exclusion_count": len(split_exclusions),
        "canonical_exclusion_count": len(canonical_exclusions),
        "main_frame_count": len(actual),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python freeze_audit_config.py audit_config.json")

    cfg_path = Path(sys.argv[1]).resolve()
    cfg = json.loads(cfg_path.read_text())

    missing = []
    for path in REQUIRED_PATHS:
        try:
            v = get(cfg, path)
        except Exception:
            missing.append(".".join(path))
            continue
        if v is None or v == "" or v == []:
            missing.append(".".join(path))

    for j in cfg.get("judges", []):
        for k in ("model_id", "provider"):
            if not j.get(k):
                missing.append(f"judges[{j.get('label','?')}].{k}")
    if len(cfg.get("judges", [])) < 2:
        missing.append("judges (need >=2)")
    if cfg.get("protocol_version") != EXPECTED_PROTOCOL:
        missing.append(
            f"protocol_version must equal {EXPECTED_PROTOCOL!r}"
        )
    if "HumanEval/34" not in cfg.get("secondary_stratum", {}).get(
        "known_split_impossible_problem_ids", []
    ):
        missing.append(
            "secondary_stratum.known_split_impossible_problem_ids "
            "must include HumanEval/34"
        )

    if missing:
        print("CONFIG NOT FROZEN; fix:")
        for x in missing:
            print("  -", x)
        raise SystemExit(2)

    mbpp = validate_dataset(cfg["benchmark"], "benchmark")
    human = validate_dataset(cfg["secondary_stratum"], "secondary_stratum")

    # Problem manifests must exactly enumerate the pinned dataset frames.
    mbpp_problem_manifest = load_problem_id_manifest(
        resolve_file(cfg["benchmark"]["problem_manifest"])
    )
    human_problem_manifest = load_problem_id_manifest(
        resolve_file(cfg["secondary_stratum"]["problem_manifest"])
    )
    if mbpp_problem_manifest != mbpp["task_ids"]:
        raise ValueError(
            "MBPP+ problem_manifest does not exactly match the pinned dataset task IDs"
        )
    if human_problem_manifest != human["task_ids"]:
        raise ValueError(
            "HumanEval+ problem_manifest does not exactly match the pinned dataset task IDs"
        )

    mbpp_split = compare_split_manifest(
        resolve_file(cfg["benchmark"]["split_exclusion_manifest"]),
        mbpp["facts"],
    )
    human_split = compare_split_manifest(
        resolve_file(cfg["secondary_stratum"]["split_exclusion_manifest"]),
        human["facts"],
    )

    # HumanEval/34 is now a consequence of the pinned file, not the definition.
    if human["facts"]["split_impossible_ids"] != ["HumanEval/34"]:
        raise ValueError(
            "Pinned HumanEval+ file must recompute exactly one split-impossible "
            "task: HumanEval/34"
        )
    if mbpp["facts"]["split_impossible_ids"]:
        raise ValueError(
            "Pinned MBPP+ v0.2.0 file should have zero split-impossible tasks; "
            f"observed {mbpp['facts']['split_impossible_ids']}"
        )

    mbpp_harness_code = resolve_file(
        cfg["main_sampling"]["mbpp_canonical_harness_code"]
    )
    human_harness_code = resolve_file(
        cfg["main_sampling"]["humaneval_canonical_harness_code"]
    )
    mbpp_harness_sha = sha256_file(mbpp_harness_code)
    human_harness_sha = sha256_file(human_harness_code)

    mbpp_canon = validate_canonical_results(
        resolve_file(cfg["main_sampling"]["mbpp_canonical_harness_results"]),
        mbpp,
        mbpp_harness_sha,
    )
    human_canon = validate_canonical_results(
        resolve_file(cfg["main_sampling"]["humaneval_canonical_harness_results"]),
        human,
        human_harness_sha,
    )
    mbpp_canon_ex = compare_canonical_exclusion_manifest(
        resolve_file(cfg["main_sampling"]["mbpp_canonical_exclusion_manifest"]),
        mbpp_canon,
    )
    human_canon_ex = compare_canonical_exclusion_manifest(
        resolve_file(cfg["main_sampling"]["humaneval_canonical_exclusion_manifest"]),
        human_canon,
    )

    prior_mbpp = load_problem_id_manifest(
        resolve_file(cfg["preflight"]["prior_mbpp_preflight_union_manifest"])
    )
    final_mbpp = load_problem_id_manifest(
        resolve_file(cfg["preflight"]["final_mbpp_preflight_union_manifest"])
    )
    locked_mbpp = load_problem_id_manifest(
        resolve_file(cfg["main_sampling"]["mbpp_preflight_union_manifest"])
    )
    if not prior_mbpp <= final_mbpp:
        raise ValueError(
            "final MBPP+ preflight union must contain the prior v0.1/v0.2 union"
        )
    if final_mbpp != locked_mbpp:
        raise ValueError(
            "preflight.final_mbpp_preflight_union_manifest and "
            "main_sampling.mbpp_preflight_union_manifest must contain "
            "exactly the same problem IDs"
        )
    if len(final_mbpp) != int(cfg["preflight"]["target_unique_mbpp_problems"]):
        raise ValueError(
            "final MBPP+ preflight union size does not equal "
            "preflight.target_unique_mbpp_problems"
        )

    mbpp_frame = validate_main_frame(
        "MBPP+",
        mbpp,
        mbpp_split,
        mbpp_canon_ex,
        resolve_file(cfg["main_sampling"]["mbpp_preflight_union_manifest"]),
        resolve_file(cfg["main_sampling"]["mbpp_main_frame_manifest"]),
    )
    human_frame = validate_main_frame(
        "HumanEval+",
        human,
        human_split,
        human_canon_ex,
        resolve_file(cfg["main_sampling"]["humaneval_preflight_union_manifest"]),
        resolve_file(cfg["main_sampling"]["humaneval_main_frame_manifest"]),
    )

    file_keys = [
        ("benchmark", "dataset_file"),
        ("benchmark", "problem_manifest"),
        ("benchmark", "base_test_split_manifest"),
        ("benchmark", "split_exclusion_manifest"),
        ("secondary_stratum", "dataset_file"),
        ("secondary_stratum", "problem_manifest"),
        ("secondary_stratum", "base_test_split_manifest"),
        ("secondary_stratum", "split_exclusion_manifest"),
        ("preflight", "prior_mbpp_preflight_union_manifest"),
        ("preflight", "final_mbpp_preflight_union_manifest"),
        ("main_sampling", "mbpp_preflight_union_manifest"),
        ("main_sampling", "humaneval_preflight_union_manifest"),
        ("main_sampling", "mbpp_canonical_harness_code"),
        ("main_sampling", "humaneval_canonical_harness_code"),
        ("main_sampling", "mbpp_canonical_harness_results"),
        ("main_sampling", "humaneval_canonical_harness_results"),
        ("main_sampling", "mbpp_canonical_exclusion_manifest"),
        ("main_sampling", "humaneval_canonical_exclusion_manifest"),
        ("main_sampling", "mbpp_main_frame_manifest"),
        ("main_sampling", "humaneval_main_frame_manifest"),
        ("prompts", "identity"),
        ("prompts", "order_swap"),
        ("prompts", "negation"),
    ]

    hashes = {}
    for path in file_keys:
        p = resolve_file(get(cfg, path))
        name = str(p.relative_to(HERE) if p.is_relative_to(HERE) else p)
        hashes[name] = sha256_file(p)

    analysis_files = [
        HERE / "audit_analysis.py",
        HERE / "audit_goldblind.py",
        HERE / "ds_excess.py",
        HERE / "audit_allocation.py",
        HERE / "audit_analysis_spec_v0_1.md",
        HERE / "audit_prereg_v0_3.md",
        HERE / "preflight_prereg_v0_3.md",
        HERE / "preflight_duplication_check.py",
        HERE / "test_duplication_hashes.py",
        HERE / "judge_repeatability.py",
        HERE / "ast_hash.py",
        HERE / "base_test_split.py",
        HERE / "dataset_frame_audit.py",
        HERE / "freeze_audit_config.py",
    ]
    for p in analysis_files:
        if not p.exists():
            raise FileNotFoundError(p)
        hashes[str(p.relative_to(HERE))] = sha256_file(p)

    canonical = json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()
    lock = {
        "protocol_version": cfg["protocol_version"],
        "config_sha256": sha256_bytes(canonical),
        "file_sha256": hashes,
        "dataset_validation": {
            "MBPP+": {
                "version": cfg["benchmark"]["version_or_commit"],
                "sha256": mbpp["sha256"],
                **mbpp["observed"],
                **mbpp_frame,
            },
            "HumanEval+": {
                "version": cfg["secondary_stratum"]["version_or_commit"],
                "sha256": human["sha256"],
                **human["observed"],
                **human_frame,
            },
        },
        "config": cfg,
    }

    out = HERE / "audit_config.lock.json"
    out.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")

    print("AUDIT_CONFIG_FROZEN")
    print("config_sha256:", lock["config_sha256"])
    for name in ("MBPP+", "HumanEval+"):
        v = lock["dataset_validation"][name]
        print(
            f"{name}: sha256={v['sha256']} tasks={v['task_count']} "
            f"split_impossible={v['split_impossible_count']} "
            f"main_frame={v['main_frame_count']}"
        )
    print("analysis_sha256:", hashes["audit_analysis.py"])
    print("goldblind_sha256:", hashes["audit_goldblind.py"])
    print("prereg_sha256:", hashes["audit_prereg_v0_3.md"])
    print("preflight_prereg_sha256:", hashes["preflight_prereg_v0_3.md"])
    print("duplication_check_sha256:", hashes["preflight_duplication_check.py"])
    print("analysis_spec_sha256:", hashes["audit_analysis_spec_v0_1.md"])
    print("ds_excess_sha256:", hashes["ds_excess.py"])
    print("allocation_sha256:", hashes["audit_allocation.py"])
    print("repeatability_sha256:", hashes["judge_repeatability.py"])
    print("ast_hash_sha256:", hashes["ast_hash.py"])
    print("base_test_split_sha256:", hashes["base_test_split.py"])
    print("dataset_frame_audit_sha256:", hashes["dataset_frame_audit.py"])
    print("wrote:", out)


if __name__ == "__main__":
    main()
