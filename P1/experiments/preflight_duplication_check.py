"""Gold-blind three-level duplication diagnostic for MBPP+ preflight v0.2.

Required input: CSV or JSONL with problem_id and candidate code.

Measures:
  raw    exact response text: sampler/cache-collapse diagnostic
  strict original AST identity: continuity with earlier reports
  loose  docstrings removed + function-local alpha-renaming: solution convergence

q_dup is computed over ALL unordered within-problem candidate pairs, so the
metric remains valid when later preflights use k=3.

Branching (frozen before this diagnostic):
  raw q_dup   >= 0.25 -> SAMPLER_COLLAPSE
  else loose q_dup >= 0.25 -> DUPLICATION_HIGH
  else -> PROBLEM_LEVEL_HETEROGENEITY

Only SAMPLER_COLLAPSE blocks the planned generator switch.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path

from ast_hash import raw_sha256, strict_ast_sha256, loose_ast_sha256

PLANNED_WEAKER_GENERATOR_MODEL_ID = "qwen3.6-flash-2026-04-16"
RAW_COLLAPSE_THRESHOLD = 0.25
LOOSE_DUPLICATION_THRESHOLD = 0.25


def load_rows(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _is_apass(row):
    return str(row.get("screen_tests_A", "")).strip() in {"1", "true", "True"}


def prepare(rows, only_apass=False):
    prepared = []
    syntax_errors = []
    missing_code = []

    for i, row in enumerate(rows):
        if only_apass and not _is_apass(row):
            continue
        problem = row.get("problem_id")
        code = row.get("code")
        candidate = row.get("candidate_id", f"row_{i}")
        if not problem:
            continue
        if code is None:
            missing_code.append(candidate)
            continue

        rec = {
            "problem_id": str(problem),
            "candidate_id": str(candidate),
            "raw": raw_sha256(str(code)),
            "strict": None,
            "loose": None,
        }
        try:
            rec["strict"] = strict_ast_sha256(str(code))
            rec["loose"] = loose_ast_sha256(str(code))
        except SyntaxError as e:
            syntax_errors.append({
                "candidate_id": str(candidate),
                "problem_id": str(problem),
                "lineno": e.lineno,
                "offset": e.offset,
                "msg": e.msg,
            })
        prepared.append(rec)

    return prepared, syntax_errors, missing_code


def pair_metric(prepared, key):
    by_problem = {}
    for r in prepared:
        if r[key] is not None:
            by_problem.setdefault(r["problem_id"], []).append(r[key])

    equal_pairs = 0
    total_pairs = 0
    per_problem = {}
    for problem, hashes in by_problem.items():
        eq = 0
        tot = 0
        for a, b in itertools.combinations(hashes, 2):
            tot += 1
            eq += int(a == b)
        if tot:
            equal_pairs += eq
            total_pairs += tot
            per_problem[problem] = {
                "n": len(hashes),
                "equal_pairs": eq,
                "total_pairs": tot,
                "q_dup": eq / tot,
                "distinct": len(set(hashes)),
            }

    return {
        "equal_pairs": equal_pairs,
        "total_pairs": total_pairs,
        "q_dup": None if total_pairs == 0 else equal_pairs / total_pairs,
        "problems_with_pairs": len(per_problem),
        "per_problem": per_problem,
    }


def summarize(rows, only_apass=False):
    prepared, syntax_errors, missing_code = prepare(rows, only_apass=only_apass)
    return {
        "candidate_rows_used_for_raw": len(prepared),
        "raw": pair_metric(prepared, "raw"),
        "strict": pair_metric(prepared, "strict"),
        "loose": pair_metric(prepared, "loose"),
        "syntax_error_count": len(syntax_errors),
        "syntax_errors": syntax_errors,
        "missing_code_count": len(missing_code),
        "missing_code_candidate_ids": missing_code,
    }


def optional_metadata(rows):
    out = {}
    fingerprint_keys = ["system_fingerprint", "model_fingerprint"]
    cache_keys = [
        "cached_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    ]
    for key in fingerprint_keys:
        vals = [r.get(key) for r in rows if r.get(key) not in (None, "")]
        if vals:
            out[key] = {
                "n": len(vals),
                "unique": sorted(set(map(str, vals))),
            }
    for key in cache_keys:
        vals = []
        for r in rows:
            value = r.get(key)
            if value in (None, ""):
                continue
            try:
                vals.append(float(value))
            except Exception:
                pass
        if vals:
            out[key] = {
                "n": len(vals),
                "min": min(vals),
                "max": max(vals),
                "mean": sum(vals) / len(vals),
            }
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_file")
    p.add_argument("--output", default="preflight_duplication_summary.json")
    a = p.parse_args()

    rows = load_rows(Path(a.input_file))
    all_summary = summarize(rows, only_apass=False)
    apass_summary = summarize(rows, only_apass=True)

    q_raw = all_summary["raw"]["q_dup"]
    q_loose = all_summary["loose"]["q_dup"]
    if q_raw is None or q_loose is None:
        branch = "INSUFFICIENT_DATA"
        switch_generator = False
    elif q_raw >= RAW_COLLAPSE_THRESHOLD:
        branch = "SAMPLER_COLLAPSE"
        switch_generator = False
    elif q_loose >= LOOSE_DUPLICATION_THRESHOLD:
        branch = "DUPLICATION_HIGH"
        switch_generator = True
    else:
        branch = "PROBLEM_LEVEL_HETEROGENEITY"
        switch_generator = True

    result = {
        "planned_weaker_generator_model_id_frozen_before_diagnostic":
            PLANNED_WEAKER_GENERATOR_MODEL_ID,
        "thresholds": {
            "raw_sampler_collapse": RAW_COLLAPSE_THRESHOLD,
            "loose_duplication_high": LOOSE_DUPLICATION_THRESHOLD,
        },
        "all_candidates": all_summary,
        "a_pass_only": apass_summary,
        "optional_provider_metadata": optional_metadata(rows),
        "branch": branch,
        "generator_switch_allowed": switch_generator,
        "interpretation": {
            "SAMPLER_COLLAPSE":
                "Exact-text repeats are too frequent; verify temperature/seed/cache propagation before changing generator.",
            "DUPLICATION_HIGH":
                "Sampler text varies, but solutions converge after alpha-normalization; proceed to weaker generator and keep many-problems/few-candidates sampling.",
            "PROBLEM_LEVEL_HETEROGENEITY":
                "Neither raw nor loose duplication is high; proceed to the preregistered weaker generator.",
            "INSUFFICIENT_DATA":
                "Not enough usable within-problem pairs to take the preregistered branch.",
        }[branch],
    }

    Path(a.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("wrote:", a.output)


if __name__ == "__main__":
    main()
