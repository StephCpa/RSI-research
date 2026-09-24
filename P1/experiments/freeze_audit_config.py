"""Validate and freeze the real-verifier audit configuration.

Usage:
  cp audit_config.example.json audit_config.json
  # fill every required field and add prompt/manifest files
  python freeze_audit_config.py audit_config.json

The command refuses null/empty required fields, hashes the config plus every
referenced prompt/manifest file AND the preregistered analysis code, then writes
audit_config.lock.json. Commit the lock before candidate generation or any gold
inspection.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED_PROTOCOL = "audit_prereg_v0_3"

REQUIRED_PATHS = [
    ("benchmark", "name"),
    ("benchmark", "version_or_commit"),
    ("benchmark", "problem_manifest"),
    ("benchmark", "base_test_split_seed"),
    ("benchmark", "base_test_split_manifest"),
    ("benchmark", "split_exclusion_manifest"),
    ("benchmark", "visible_suite_definition"),
    ("benchmark", "gold_suite_definition"),
    ("secondary_stratum", "name"),
    ("secondary_stratum", "version_or_commit"),
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


def resolve_file(value):
    p = Path(value)
    if not p.is_absolute():
        p = HERE / p
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def load_split_exclusion_manifest(path: Path):
    """Load the frozen JSON split-exclusion manifest.

    Expected shape:
      {
        "benchmark": "...",
        "excluded": [
          {
            "problem_id": "...",
            "base_test_count": 1,
            "exclusion_reason": "BASE_TEST_SPLIT_IMPOSSIBLE"
          }
        ]
      }
    """
    data = json.loads(path.read_text())
    excluded = data.get("excluded")
    if not isinstance(excluded, list):
        raise ValueError(
            f"{path}: split-exclusion manifest must contain an 'excluded' list"
        )
    return data


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
            missing.append(".".join(path)); continue
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

    # HumanEval/34 is preregistered as split-impossible before generation.
    expected_split_impossible = cfg.get("secondary_stratum", {}).get(
        "known_split_impossible_problem_ids", []
    )
    if "HumanEval/34" not in expected_split_impossible:
        missing.append(
            "secondary_stratum.known_split_impossible_problem_ids must include HumanEval/34"
        )

    if missing:
        print("CONFIG NOT FROZEN; fix:")
        for x in missing:
            print("  -", x)
        raise SystemExit(2)

    file_keys = [
        ("benchmark", "problem_manifest"),
        ("benchmark", "base_test_split_manifest"),
        ("benchmark", "split_exclusion_manifest"),
        ("secondary_stratum", "problem_manifest"),
        ("secondary_stratum", "base_test_split_manifest"),
        ("secondary_stratum", "split_exclusion_manifest"),
        ("preflight", "prior_mbpp_preflight_union_manifest"),
        ("preflight", "final_mbpp_preflight_union_manifest"),
        ("main_sampling", "mbpp_preflight_union_manifest"),
        ("main_sampling", "humaneval_preflight_union_manifest"),
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
        value = get(cfg, path)
        p = resolve_file(value)
        name = str(p.relative_to(HERE) if p.is_relative_to(HERE) else p)
        hashes[name] = sha256_bytes(p.read_bytes())

    # Validate the split-exclusion manifests before freezing their hashes.
    mbpp_split_path = resolve_file(get(cfg, ("benchmark", "split_exclusion_manifest")))
    human_split_path = resolve_file(get(cfg, ("secondary_stratum", "split_exclusion_manifest")))
    load_split_exclusion_manifest(mbpp_split_path)
    human_manifest = load_split_exclusion_manifest(human_split_path)
    human34 = [
        r for r in human_manifest["excluded"]
        if r.get("problem_id") == "HumanEval/34"
    ]
    if len(human34) != 1:
        raise ValueError(
            "HumanEval split-exclusion manifest must contain exactly one HumanEval/34 record"
        )
    rec = human34[0]
    if rec.get("exclusion_reason") != "BASE_TEST_SPLIT_IMPOSSIBLE":
        raise ValueError(
            "HumanEval/34 exclusion_reason must be BASE_TEST_SPLIT_IMPOSSIBLE"
        )
    if int(rec.get("base_test_count", -1)) != 1:
        raise ValueError(
            "HumanEval/34 split-exclusion record must have base_test_count=1"
        )

    # Freeze the analysis degrees of freedom too.
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
        HERE / "freeze_audit_config.py",
    ]
    for p in analysis_files:
        if not p.exists():
            raise FileNotFoundError(p)
        hashes[str(p.relative_to(HERE))] = sha256_bytes(p.read_bytes())

    canonical = json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()
    lock = {
        "protocol_version": cfg["protocol_version"],
        "config_sha256": sha256_bytes(canonical),
        "file_sha256": hashes,
        "config": cfg,
    }
    out = HERE / "audit_config.lock.json"
    out.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print("AUDIT_CONFIG_FROZEN")
    print("config_sha256:", lock["config_sha256"])
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
    print("wrote:", out)


if __name__ == "__main__":
    main()
