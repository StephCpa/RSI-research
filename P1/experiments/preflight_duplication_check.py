"""Gold-blind AST-duplication diagnostic for MBPP+ preflight v0.2.

Accepted input formats:
  * CSV
  * JSONL

Required fields:
  problem_id
and either:
  ast_hash
or:
  code

Optional fields:
  candidate_id
  screen_tests_A   (used for the A-pass restricted summary)

The script never reads truth/gold fields. If such fields are present, they are ignored.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ast_hash import ast_sha256


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


def summarize(rows, only_apass=False):
    work = []
    for r in rows:
        if only_apass and str(r.get("screen_tests_A", "")) not in {"1", "true", "True"}:
            continue
        if not r.get("problem_id"):
            continue
        h = r.get("ast_hash")
        if not h:
            code = r.get("code")
            if not code:
                continue
            try:
                h = ast_sha256(code)
            except Exception:
                continue
        work.append((str(r["problem_id"]), str(h)))

    by_problem = {}
    for p, h in work:
        by_problem.setdefault(p, []).append(h)

    eligible = {p: hs for p, hs in by_problem.items() if len(hs) >= 2}
    pair_problems = {p: hs[:2] for p, hs in eligible.items()}
    same_pairs = sum(1 for hs in pair_problems.values() if len(set(hs)) == 1)
    total_pairs = len(pair_problems)

    total_candidates = sum(len(hs) for hs in by_problem.values())
    distinct_candidates = sum(len(set(hs)) for hs in by_problem.values())

    return {
        "problems_with_candidates": len(by_problem),
        "problems_with_at_least_2_candidates": len(eligible),
        "two_candidate_problem_pairs": total_pairs,
        "same_ast_pairs": same_pairs,
        "q_dup": None if total_pairs == 0 else same_pairs / total_pairs,
        "candidate_rows_used": total_candidates,
        "distinct_ast_count_sum": distinct_candidates,
        "duplicate_candidate_fraction": None if total_candidates == 0 else 1 - distinct_candidates / total_candidates,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_file")
    p.add_argument("--output", default="preflight_duplication_summary.json")
    a = p.parse_args()

    rows = load_rows(Path(a.input_file))
    result = {
        "all_usable_rows": summarize(rows, only_apass=False),
        "a_pass_only": summarize(rows, only_apass=True),
        "decision_threshold_q_dup": 0.25,
    }
    q = result["all_usable_rows"]["q_dup"]
    if q is None:
        branch = "INSUFFICIENT_DATA"
    elif q >= 0.25:
        branch = "DUPLICATION_HIGH"
    else:
        branch = "PROBLEM_LEVEL_HETEROGENEITY"
    result["branch"] = branch

    Path(a.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("wrote:", a.output)


if __name__ == "__main__":
    main()
