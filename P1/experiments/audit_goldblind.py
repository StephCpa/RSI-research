"""Gold-blind diagnostics for the real-verifier audit pilot.

Input CSV requires:
  problem_id, candidate_id, view_<...>

No hidden/gold truth column is used or allowed for the preregistered diagnostic
cohort. This script estimates u0/u1, pairwise agreement and phi correlation,
and the preregistered figure-C prominence gate.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

DEFAULT_BASELINE = [
    "view_visible_tests",
    "view_judgeA_identity",
    "view_judgeB_identity",
]


def load(path: Path):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("empty input")
    if "truth" in rows[0]:
        raise ValueError(
            "goldblind input must not contain a truth column; use a W-only table"
        )
    required = {"problem_id", "candidate_id"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    views = [c for c in rows[0] if c.startswith("view_")]
    if not views:
        raise ValueError("need at least one view_* column")
    W = np.array([[int(r[c]) for c in views] for r in rows], dtype=int)
    if not np.all(np.isin(W, [-1, 1])):
        raise ValueError("all view columns must be +/-1")
    return rows, views, W


def pairwise_agreement(W):
    k = W.shape[1]
    A = np.eye(k)
    for i in range(k):
        for j in range(i + 1, k):
            A[i, j] = A[j, i] = np.mean(W[:, i] == W[:, j])
    return A


def phi_matrix(W):
    # Pearson correlation of +/-1 binary views equals the phi coefficient.
    if W.shape[0] < 2:
        return np.full((W.shape[1], W.shape[1]), np.nan)
    return np.corrcoef(W, rowvar=False)


def write_matrix(path, names, A):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["view"] + names)
        for name, row in zip(names, A):
            w.writerow([name] + [f"{x:.8g}" for x in row])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--baseline-views", nargs="+", default=DEFAULT_BASELINE)
    p.add_argument("--full-views", nargs="+", default=None)
    p.add_argument("--visible-col", default="view_visible_tests")
    p.add_argument("--output", default=None)
    a = p.parse_args()

    path = Path(a.input_csv)
    rows, names, W = load(path)
    col = {name: i for i, name in enumerate(names)}
    full = a.full_views or names
    for c in a.baseline_views + full + [a.visible_col]:
        if c not in col:
            raise ValueError(f"missing view column: {c}")

    u0 = np.logical_and.reduce([W[:, col[c]] == 1 for c in a.baseline_views])
    u1 = np.logical_and.reduce([W[:, col[c]] == 1 for c in full])
    visible = W[:, col[a.visible_col]] == 1

    A_all = pairwise_agreement(W)
    P_all = phi_matrix(W)
    A_vis = pairwise_agreement(W[visible])
    P_vis = phi_matrix(W[visible])

    u0hat = float(np.mean(u0))
    u1hat = float(np.mean(u1))
    ratio = float(1 / np.sqrt(u1hat)) if u1hat > 0 else np.inf
    prominence = "candidate-main" if u1hat <= .60 else "secondary"

    summary = {
        "n_candidates": len(W),
        "n_visible_positive": int(visible.sum()),
        "u0": u0hat,
        "u1": u1hat,
        "n_u0": int(u0.sum()),
        "n_u1": int(u1.sum()),
        "targeted_vs_uniform_se_ratio_approx": ratio,
        "budget_panel_status": prominence,
        "marginal_acceptance": {
            name: float(np.mean(W[:, j] == 1)) for j, name in enumerate(names)
        },
    }

    outdir = Path(a.output) if a.output else path.parent / "goldblind_results"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "goldblind_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    write_matrix(outdir / "agreement_all.csv", names, A_all)
    write_matrix(outdir / "phi_all.csv", names, P_all)
    write_matrix(outdir / "agreement_visible_positive.csv", names, A_vis)
    write_matrix(outdir / "phi_visible_positive.csv", names, P_vis)

    print(f"candidates={len(W)} visible_positive={visible.sum()}")
    print(f"u0={u0hat:.6f} u1={u1hat:.6f}")
    print(f"approx targeted/uniform SE advantage = {ratio:.3f}x")
    print("budget panel preregistered status:", prominence)
    print("wrote:", outdir)


if __name__ == "__main__":
    main()
