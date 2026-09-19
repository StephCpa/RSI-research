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
    ("benchmark", "visible_suite_definition"),
    ("benchmark", "gold_suite_definition"),
    ("candidate_generation", "model_ids"),
    ("candidate_generation", "samples_per_problem"),
    ("candidate_generation", "temperature"),
    ("candidate_generation", "top_p"),
    ("candidate_generation", "max_tokens"),
    ("prompts", "identity"),
    ("prompts", "order_swap"),
    ("prompts", "negation"),
    ("candidate_budget",),
    ("unanimous_target",),
    ("practical_blind_error_bar",),
    ("judge_quality_upper_bar",),
    ("fixed_pool_precision_halfwidth_target",),
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
    if missing:
        print("CONFIG NOT FROZEN; fix:")
        for x in missing:
            print("  -", x)
        raise SystemExit(2)

    file_keys = [
        ("benchmark", "problem_manifest"),
        ("benchmark", "base_test_split_manifest"),
        ("prompts", "identity"),
        ("prompts", "order_swap"),
        ("prompts", "negation"),
    ]
    if cfg.get("metamorphic_manifest"):
        file_keys.append(("metamorphic_manifest",))

    hashes = {}
    for path in file_keys:
        value = get(cfg, path)
        p = resolve_file(value)
        name = str(p.relative_to(HERE) if p.is_relative_to(HERE) else p)
        hashes[name] = sha256_bytes(p.read_bytes())

    # Freeze the analysis degrees of freedom too.
    analysis_files = [
        HERE / "audit_analysis.py",
        HERE / "audit_goldblind.py",
        HERE / "ds_excess.py",
        HERE / "audit_allocation.py",
        HERE / "audit_analysis_spec_v0_1.md",
        HERE / "audit_prereg_v0_3.md",
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
    print("analysis_spec_sha256:", hashes["audit_analysis_spec_v0_1.md"])
    print("ds_excess_sha256:", hashes["ds_excess.py"])
    print("allocation_sha256:", hashes["audit_allocation.py"])
    print("wrote:", out)


if __name__ == "__main__":
    main()
