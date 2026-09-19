"""Analyze the preregistered real-verifier audit experiment (v0.2).

Input CSV requires:
  problem_id, candidate_id, truth, view_<...>

truth and every view column are encoded as +1/-1.

Primary population uncertainty uses a problem-level cluster bootstrap. A
Clopper-Pearson interval is also reported, but only as a fixed-pool
certification interval conditional on the realized candidate set.

Default schemes:
  V0 = visible tests + Judge A identity + Judge B identity
  V1 = all view_* columns
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


DEFAULT_BASELINE = [
    "view_visible_tests",
    "view_judgeA_identity",
    "view_judgeB_identity",
]


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
    required = {"problem_id", "candidate_id", "truth"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    view_cols = [c for c in rows[0] if c.startswith("view_")]
    if not view_cols:
        raise ValueError("need at least one view_* column")
    problem = np.array([r["problem_id"] for r in rows], dtype=object)
    truth = np.array([int(r["truth"]) for r in rows], dtype=int)
    W = {c: np.array([int(r[c]) for r in rows], dtype=int) for c in view_cols}
    if not np.all(np.isin(truth, [-1, 1])):
        raise ValueError("truth must be +/-1")
    for c, v in W.items():
        if not np.all(np.isin(v, [-1, 1])):
            raise ValueError(f"{c} must be +/-1")
    return rows, problem, truth, W


def scheme_mask(W, cols):
    bad = [c for c in cols if c not in W]
    if bad:
        raise ValueError(f"scheme columns absent from CSV: {bad}")
    return np.logical_and.reduce([W[c] == 1 for c in cols])


def safe_div(a, b):
    return np.nan if b == 0 else a / b


def counts_from_masks(problem, truth, u0, u1):
    uniq = np.unique(problem)
    out = []
    d = u0 & ~u1
    for p in uniq:
        z = problem == p
        n = int(z.sum())
        u0n = int((z & u0).sum())
        u1n = int((z & u1).sum())
        e0 = int((z & u0 & (truth == -1)).sum())
        e1 = int((z & u1 & (truth == -1)).sum())
        dn = int((z & d).sum())
        de = int((z & d & (truth == -1)).sum())
        dc = int((z & d & (truth == 1)).sum())
        out.append((p, n, u0n, e0, u1n, e1, dn, de, dc))
    return out


def metrics_from_totals(n, u0n, e0, u1n, e1, dn, de, dc):
    r0 = safe_div(e0, u0n)
    r1 = safe_div(e1, u1n)
    rd = safe_div(de, dn)
    return {
        "u0": safe_div(u0n, n),
        "u1": safe_div(u1n, n),
        "r0": r0,
        "r1": r1,
        "r0_minus_r1": r0 - r1 if np.isfinite(r0) and np.isfinite(r1) else np.nan,
        "b0": safe_div(e0, n),
        "b1": safe_div(e1, n),
        "delta_b": safe_div(e0 - e1, n),
        "removed_n": dn,
        "removed_error_n": de,
        "removed_correct_n": dc,
        "removed_error_rate": rd,
        "enrichment": safe_div(rd, r0) if np.isfinite(rd) and np.isfinite(r0) else np.nan,
        "correct_given_removed": safe_div(dc, dn),
        "correct_yield_loss": safe_div(dc, u0n - e0),
    }


def point_metrics(problem, truth, u0, u1):
    cc = counts_from_masks(problem, truth, u0, u1)
    a = np.asarray([[x[i] for i in range(1, 9)] for x in cc], dtype=float)
    totals = a.sum(axis=0)
    return metrics_from_totals(*totals), cc


def cluster_bootstrap(cluster_counts, reps=10000, seed=20260919):
    """Resample problems and carry all candidates from each selected problem."""
    rng = np.random.default_rng(seed)
    a = np.asarray([[x[i] for i in range(1, 9)] for x in cluster_counts], dtype=float)
    m = len(a)
    idx = rng.integers(0, m, size=(reps, m))
    totals = a[idx].sum(axis=1)
    names = [
        "u0", "u1", "r0", "r1", "r0_minus_r1", "b0", "b1", "delta_b",
        "enrichment", "correct_given_removed", "correct_yield_loss"
    ]
    vals = {k: np.full(reps, np.nan) for k in names}
    for i, t in enumerate(totals):
        d = metrics_from_totals(*t)
        for k in names:
            vals[k][i] = d[k]
    return vals


def ci(x, alpha=.05):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return np.nan, np.nan
    return float(np.quantile(x, alpha / 2)), float(np.quantile(x, 1 - alpha / 2))


def icc_oneway_binary(cluster_counts):
    """Approximate one-way random-effects ICC for Y=-1 inside U1+."""
    ns, ks = [], []
    for x in cluster_counts:
        u1n, e1 = int(x[4]), int(x[5])
        if u1n > 0:
            ns.append(u1n); ks.append(e1)
    ns = np.asarray(ns, dtype=float)
    ks = np.asarray(ks, dtype=float)
    if len(ns) < 2 or ns.sum() <= len(ns):
        return np.nan
    ps = ks / ns
    p = ks.sum() / ns.sum()
    B = np.sum(ns * (ps - p) ** 2)
    W = np.sum(ks * (1 - ps) ** 2 + (ns - ks) * ps ** 2)
    msb = B / (len(ns) - 1)
    msw = W / (ns.sum() - len(ns))
    n0 = (ns.sum() - np.sum(ns ** 2) / ns.sum()) / (len(ns) - 1)
    den = msb + (n0 - 1) * msw
    return np.nan if abs(den) < 1e-15 else float((msb - msw) / den)


def audit_interval(indices, truth, up, u_mass):
    idx = np.asarray(indices, dtype=int)
    in_u = up[idx]
    n_u = int(in_u.sum())
    k_u = int(((truth[idx] == -1) & in_u).sum())
    lo, hi = cp_interval(k_u, n_u)
    return dict(
        n_u=n_u, k_u=k_u, r_lo=lo, r_hi=hi,
        b_lo=u_mass * lo, b_hi=u_mass * hi,
        width=u_mass * (hi - lo),
    )


def simulate_fixed_pool_allocations(truth, up, budgets, reps, seed):
    """Secondary fixed-pool comparison; CP intervals are conditional on this pool."""
    rng = np.random.default_rng(seed)
    n = len(truth)
    iu = np.flatnonzero(up)
    idis = np.flatnonzero(~up)
    u_mass = len(iu) / n
    out = []
    for B in budgets:
        for rep in range(reps):
            take = min(B, len(iu))
            idx = rng.choice(iu, size=take, replace=False) if take else np.array([], dtype=int)
            out.append(dict(policy="unanimous", budget=B, replicate=rep,
                            **audit_interval(idx, truth, up, u_mass)))

            take = min(B, n)
            idx = rng.choice(n, size=take, replace=False)
            out.append(dict(policy="uniform", budget=B, replicate=rep,
                            **audit_interval(idx, truth, up, u_mass)))

            # Structural control only; this arm is not a headline comparator.
            take = min(B, len(idis))
            idx = rng.choice(idis, size=take, replace=False) if take else np.array([], dtype=int)
            out.append(dict(policy="disagreement", budget=B, replicate=rep,
                            **audit_interval(idx, truth, up, u_mass)))
    return out


def write_csv(rows, path):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def make_primary_figure(point, boot, cp, sim, outpath, show_budget=True):
    u1, r1, b1 = point["u1"], point["r1"], point["b1"]
    r1_lo, r1_hi = ci(boot["r1"])
    diff_lo, diff_hi = ci(boot["r0_minus_r1"])
    b_lo, b_hi = u1 * r1_lo, u1 * r1_hi
    cp_lo, cp_hi = cp

    fig, ax = plt.subplots(1, 3, figsize=(10.8, 3.0))

    # Centerpiece: agreement-only identified set -> clustered audit interval.
    ax[0].plot([0, 0], [0, u1], lw=9, alpha=.22, label="agreement-only set")
    ax[0].errorbar([1], [b1], yerr=[[b1 - b_lo], [b_hi - b1]],
                   fmt="o", capsize=4, label="problem-cluster audit")
    ax[0].errorbar([1.08], [b1],
                   yerr=[[b1 - u1 * cp_lo], [u1 * cp_hi - b1]],
                   fmt=".", capsize=3, alpha=.55, label="fixed-pool CP")
    ax[0].set_xticks([0, 1], ["agreement", "gold audit"])
    ax[0].set_ylabel("blind false-accept mass")
    ax[0].set_title("(A) identified set shrinks")
    ax[0].legend(fontsize=6.5)

    # Informativeness: r0 vs r1.
    r0_lo, r0_hi = ci(boot["r0"])
    vals = [point["r0"], point["r1"]]
    los = [r0_lo, r1_lo]; his = [r0_hi, r1_hi]
    ax[1].errorbar([0, 1], vals,
                   yerr=[[vals[i] - los[i] for i in range(2)],
                         [his[i] - vals[i] for i in range(2)]],
                   fmt="o", capsize=4)
    ax[1].set_xticks([0, 1], [r"$r_0$", r"$r_1$"])
    ax[1].set_ylabel("false-accept rate within unanimous set")
    ax[1].set_title("(B) transformation enrichment")
    ax[1].text(.5, max(vals) if np.all(np.isfinite(vals)) else .5,
               rf"$r_0-r_1={point['r0_minus_r1']:.3g}$\n95% CI [{diff_lo:.3g},{diff_hi:.3g}]",
               ha="center", va="bottom", fontsize=7)

    # Secondary fixed-pool allocation comparison.
    if show_budget:
        for policy in ["unanimous", "uniform"]:
            budgets = sorted({int(r["budget"]) for r in sim if r["policy"] == policy})
            med, lo, hi = [], [], []
            for B in budgets:
                x = np.array([float(r["width"]) for r in sim
                              if r["policy"] == policy and int(r["budget"]) == B])
                med.append(np.median(x)); lo.append(np.quantile(x, .1)); hi.append(np.quantile(x, .9))
            ax[2].plot(budgets, med, marker="o", label=policy)
            ax[2].fill_between(budgets, lo, hi, alpha=.15)
        ax[2].set_xscale("log")
        ax[2].set_xlabel("gold budget")
        ax[2].set_ylabel("fixed-pool 95% interval width")
        ax[2].set_title("(C) targeted vs uniform")
        ax[2].legend(fontsize=7)
    else:
        ax[2].axis("off")
        ax[2].text(.5, .5, r"$\hat u_1>0.60$\nBudget panel preregistered as secondary",
                   ha="center", va="center", transform=ax[2].transAxes)

    fig.tight_layout()
    fig.savefig(outpath)
    fig.savefig(outpath.with_suffix(".png"), dpi=180)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--baseline-views", nargs="+", default=DEFAULT_BASELINE)
    p.add_argument("--full-views", nargs="+", default=None,
                   help="default: all view_* columns")
    p.add_argument("--visible-col", default="view_visible_tests")
    p.add_argument("--cluster-reps", type=int, default=10000)
    p.add_argument("--budget-reps", type=int, default=1000)
    p.add_argument("--budgets", type=int, nargs="+", default=[25, 50, 100, 200, 500, 1000])
    p.add_argument("--seed", type=int, default=20260919)
    p.add_argument("--threshold", type=float, default=.005)
    p.add_argument("--output", default=None)
    a = p.parse_args()

    path = Path(a.input_csv)
    rows, problem, truth, W = load_csv(path)
    full = a.full_views or list(W.keys())
    u0 = scheme_mask(W, a.baseline_views)
    u1 = scheme_mask(W, full)

    # Mechanical no-gold label-join check.
    if a.visible_col not in W:
        raise ValueError(f"visible column {a.visible_col} missing")
    pseudo_false = int((u1 & (W[a.visible_col] == -1)).sum())
    if pseudo_false != 0:
        raise RuntimeError(
            f"NULL_CALIBRATION_FAIL: {pseudo_false} U1+ rows have visible pseudo-truth=-1"
        )
    print("NULL_CALIBRATION: PASS")

    point, clusters = point_metrics(problem, truth, u0, u1)
    boot = cluster_bootstrap(clusters, a.cluster_reps, a.seed)
    r1_cluster = ci(boot["r1"])
    diff_cluster = ci(boot["r0_minus_r1"])

    n_u1 = int(u1.sum())
    k_u1 = int((u1 & (truth == -1)).sum())
    cp = cp_interval(k_u1, n_u1)
    blind_problem_count = len(set(problem[u1 & (truth == -1)]))

    icc = icc_oneway_binary(clusters)
    p1 = point["r1"]
    naive_var = p1 * (1 - p1) / n_u1 if n_u1 and np.isfinite(p1) else np.nan
    cluster_var = float(np.nanvar(boot["r1"], ddof=1))
    deff = cluster_var / naive_var if np.isfinite(naive_var) and naive_var > 0 else np.nan
    neff = n_u1 / deff if np.isfinite(deff) and deff > 0 else np.nan

    if n_u1 < 500:
        tier = "RED"
    elif np.isfinite(r1_cluster[1]) and r1_cluster[1] < a.threshold and cp[1] < a.threshold:
        tier = "RED"
    elif (np.isfinite(r1_cluster[0]) and r1_cluster[0] > a.threshold
          and k_u1 >= 5 and blind_problem_count >= 3):
        tier = "GREEN"
    else:
        tier = "YELLOW"

    print("baseline views:", ", ".join(a.baseline_views))
    print("full views:", ", ".join(full))
    print(f"candidates={len(truth)} problems={len(np.unique(problem))}")
    print(f"u0={point['u0']:.6f} u1={point['u1']:.6f}")
    print(f"r0={point['r0']:.6f} r1={point['r1']:.6f}")
    print(f"r0-r1={point['r0_minus_r1']:.6f} cluster95={diff_cluster}")
    print(f"cluster95(r1)={r1_cluster}; fixed-pool CP95(r1)={cp}")
    print(f"blind errors in U1+={k_u1}, across {blind_problem_count} problems")
    print(f"ICC≈{icc:.4f} empirical_DEFF≈{deff:.3f} n_eff≈{neff:.1f}")
    print(f"removed enrichment={point['enrichment']:.4f}")
    print(f"P(Y=+1|D)={point['correct_given_removed']:.4f}")
    print(f"P(D|Y=+1,U0+)={point['correct_yield_loss']:.4f}")
    print(f"delta_b (magnitude only)={point['delta_b']:.6f}")
    print("PREREG_TIER:", tier)

    sim = simulate_fixed_pool_allocations(truth, u1, a.budgets, a.budget_reps, a.seed + 1)
    outdir = Path(a.output) if a.output else path.parent / "audit_results"
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(sim, outdir / "audit_budget_fixed_pool.csv")

    summary = {
        "point": point,
        "cluster95": {
            "r0": ci(boot["r0"]),
            "r1": r1_cluster,
            "r0_minus_r1": diff_cluster,
            "enrichment": ci(boot["enrichment"]),
            "correct_given_removed": ci(boot["correct_given_removed"]),
            "correct_yield_loss": ci(boot["correct_yield_loss"]),
        },
        "fixed_pool_cp95_r1": cp,
        "icc_u1_blind": icc,
        "empirical_deff": deff,
        "n_eff": neff,
        "n_u1": n_u1,
        "k_u1": k_u1,
        "blind_problem_count": blind_problem_count,
        "tier": tier,
    }
    (outdir / "audit_summary.json").write_text(json.dumps(summary, indent=2, default=float) + "\n")

    # Supporting 2x2 table.
    d = u0 & ~u1
    table = [
        {"stratum": "removed_D", "Y_minus": int((d & (truth == -1)).sum()),
         "Y_plus": int((d & (truth == 1)).sum())},
        {"stratum": "retained_U1", "Y_minus": int((u1 & (truth == -1)).sum()),
         "Y_plus": int((u1 & (truth == 1)).sum())},
    ]
    write_csv(table, outdir / "transformation_2x2.csv")

    make_primary_figure(point, boot, cp, sim, outdir / "audit_primary.pdf",
                        show_budget=point["u1"] <= .60)
    print("wrote:", outdir)


if __name__ == "__main__":
    main()
