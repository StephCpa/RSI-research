"""Analyze the preregistered real-verifier audit experiment.

Input CSV schema:
  candidate_id, truth, view_<name1>, view_<name2>, ...

truth and every view column must be encoded as +1/-1.  The script is deliberately
provider-agnostic: candidate generation, judge calls, and hidden-test execution
are separate collection steps.  This file consumes only the frozen result table.

Primary outputs implement the preregistration:
  A. false-accept rate in the unanimous-accept stratum;
  B. agreement-only blind-mass identified set [0, P(U+)] versus the audited interval;
  C. interval width versus gold budget for unanimous-stratified, uniform, and
     disagreement-only allocation.
"""
from __future__ import annotations

import argparse, csv
from pathlib import Path

import numpy as np
from scipy.stats import beta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def cp_interval(k: int, n: int, alpha: float = 0.05):
    if n == 0:
        return 0.0, 1.0
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def load_csv(path: Path):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("empty input")
    view_cols = [c for c in rows[0] if c.startswith("view_")]
    if not view_cols:
        raise ValueError("need at least one view_* column")
    truth = np.array([int(r["truth"]) for r in rows], dtype=int)
    W = np.array([[int(r[c]) for c in view_cols] for r in rows], dtype=int)
    if not np.all(np.isin(truth, [-1, 1])) or not np.all(np.isin(W, [-1, 1])):
        raise ValueError("truth and view columns must be +/-1")
    return rows, view_cols, truth, W


def audit_interval(indices, truth, up, u_mass):
    idx = np.asarray(indices, dtype=int)
    in_u = up[idx]
    n_u = int(in_u.sum())
    k_u = int(((truth[idx] == -1) & in_u).sum())
    lo, hi = cp_interval(k_u, n_u)
    # blind mass b = P(U+) * P(Y=-1 | U+)
    return dict(n_u=n_u, k_u=k_u, r_lo=lo, r_hi=hi,
                b_lo=u_mass * lo, b_hi=u_mass * hi,
                width=u_mass * (hi - lo))


def simulate(truth, up, budgets, reps, seed):
    rng = np.random.default_rng(seed)
    n = len(truth)
    iu = np.flatnonzero(up)
    idis = np.flatnonzero(~up)
    u_mass = len(iu) / n
    out = []

    for B in budgets:
        for rep in range(reps):
            # unanimous-stratified
            take = min(B, len(iu))
            idx = rng.choice(iu, size=take, replace=False) if take else np.array([], dtype=int)
            d = audit_interval(idx, truth, up, u_mass)
            out.append(dict(policy="unanimous", budget=B, replicate=rep, **d))

            # uniform
            take = min(B, n)
            idx = rng.choice(n, size=take, replace=False)
            d = audit_interval(idx, truth, up, u_mass)
            out.append(dict(policy="uniform", budget=B, replicate=rep, **d))

            # disagreement-only: zero inclusion probability in U+.
            take = min(B, len(idis))
            idx = rng.choice(idis, size=take, replace=False) if take else np.array([], dtype=int)
            d = audit_interval(idx, truth, up, u_mass)
            out.append(dict(policy="disagreement", budget=B, replicate=rep, **d))
    return out


def write_csv(rows, path):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def make_figure(truth, up, sim, outpath):
    n = len(truth)
    iu = np.flatnonzero(up)
    u = len(iu) / n
    k = int((truth[iu] == -1).sum())
    r = k / len(iu) if len(iu) else np.nan
    rlo, rhi = cp_interval(k, len(iu))

    fig, ax = plt.subplots(1, 3, figsize=(10.8, 3.0))

    # A
    ax[0].errorbar([0], [r], yerr=[[r-rlo], [rhi-r]], fmt="o", capsize=4)
    ax[0].set_xlim(-0.7, 0.7)
    ax[0].set_xticks([0], ["unanimous accepts"])
    ax[0].set_ylabel("false-accept rate")
    ax[0].set_ylim(bottom=0)
    ax[0].set_title("(A) blind error in $U^+$")

    # B: blind-mass identified set
    b_true = u * r
    ax[1].plot([0, 0], [0, u], lw=8, alpha=0.25, label="agreement-only set")
    ax[1].errorbar([1], [b_true], yerr=[[b_true-u*rlo], [u*rhi-b_true]],
                   fmt="o", capsize=4, label="gold-audited interval")
    ax[1].set_xticks([0, 1], ["agreement", "audit"])
    ax[1].set_ylabel("blind false-accept mass")
    ax[1].set_title("(B) identified set vs audit")
    ax[1].legend(fontsize=7)

    # C
    for policy in ["unanimous", "uniform", "disagreement"]:
        budgets = sorted({int(r["budget"]) for r in sim if r["policy"] == policy})
        med, lo, hi = [], [], []
        for B in budgets:
            vals = np.array([float(r["width"]) for r in sim
                             if r["policy"] == policy and int(r["budget"]) == B])
            med.append(np.median(vals)); lo.append(np.quantile(vals, .1)); hi.append(np.quantile(vals, .9))
        ax[2].plot(budgets, med, marker="o", label=policy)
        ax[2].fill_between(budgets, lo, hi, alpha=.15)
    ax[2].set_xscale("log")
    ax[2].set_xlabel("gold budget")
    ax[2].set_ylabel("95% interval width for blind mass")
    ax[2].set_title("(C) allocation efficiency")
    ax[2].legend(fontsize=7)

    fig.tight_layout()
    fig.savefig(outpath)
    fig.savefig(outpath.with_suffix(".png"), dpi=180)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--budgets", type=int, nargs="+", default=[25, 50, 100, 200, 500, 1000])
    p.add_argument("--reps", type=int, default=1000)
    p.add_argument("--seed", type=int, default=20260919)
    p.add_argument("--output", default=None)
    a = p.parse_args()

    path = Path(a.input_csv)
    rows, view_cols, truth, W = load_csv(path)
    up = np.all(W == 1, axis=1)
    n_u = int(up.sum())
    k_u = int(((truth == -1) & up).sum())
    r = k_u / n_u if n_u else np.nan
    rlo, rhi = cp_interval(k_u, n_u)
    u = n_u / len(truth)
    b = k_u / len(truth)

    print("views:", ", ".join(view_cols))
    print("candidates:", len(truth))
    print(f"U+ count: {n_u} ({u:.4f})")
    print(f"false accepts in U+: {k_u}")
    print(f"r_U = P(Y=-1|U+): {r:.6f}  95% CP [{rlo:.6f}, {rhi:.6f}]")
    print(f"blind mass P(B+): {b:.6f}")
    print(f"kill criterion CP upper < 0.005: {bool(rhi < 0.005)}")
    print(f"count criterion n_U+ < 500: {bool(n_u < 500)}")

    sim = simulate(truth, up, a.budgets, a.reps, a.seed)
    outdir = Path(a.output) if a.output else path.parent / "audit_results"
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(sim, outdir / "audit_budget_simulation.csv")
    make_figure(truth, up, sim, outdir / "audit_primary.pdf")
    print("wrote:", outdir)


if __name__ == "__main__":
    main()
