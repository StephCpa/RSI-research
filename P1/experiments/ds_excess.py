"""Independent-error excess-unanimity analysis.

Fits an oriented two-class product-Bernoulli (Dawid--Skene-style) null only to
non-unanimous view patterns, then predicts the unanimous mass that conditional
independence would imply.  The unanimous cells are excluded from fitting.

This module is import-safe; audit_allocation.py also reuses fit_ds() and
posterior_minus().
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def sigmoid(x):
    x = np.asarray(x, dtype=float)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -35, 35)))


def decode(x, d):
    x = np.asarray(x, dtype=float)
    pi = float(sigmoid(x[0]))
    qp = 0.5 + 0.49 * sigmoid(x[1:1+d])
    qm = 0.5 - 0.49 * sigmoid(x[1+d:1+2*d])
    return pi, qp, qm


def component_prob(W, q):
    W = np.asarray(W, dtype=int)
    q = np.asarray(q, dtype=float)
    return np.prod(np.where(W == 1, q, 1 - q), axis=1)


def mixture_prob(W, pi, qp, qm):
    return pi * component_prob(W, qp) + (1 - pi) * component_prob(W, qm)


def all_patterns(d):
    return np.array(list(itertools.product([1, -1], repeat=d)), dtype=int)


def fit_ds(W, starts=12, seed=20260919, warm=None, maxiter=2000):
    """Fit conditional DS null using only non-unanimous rows.

    Returns dict with pi, q_plus, q_minus, conditional_nll, G_off, and x.
    """
    W = np.asarray(W, dtype=int)
    if W.ndim != 2 or W.shape[1] < 3:
        raise ValueError("need a 2D view matrix with at least three views")
    d = W.shape[1]
    unanimous = np.all(W == 1, axis=1) | np.all(W == -1, axis=1)
    X = W[~unanimous]
    if len(X) == 0:
        raise ValueError("no non-unanimous rows for DS fit")

    pats = all_patterns(d)
    off = ~(np.all(pats == 1, axis=1) | np.all(pats == -1, axis=1))

    def objective(x):
        pi, qp, qm = decode(x, d)
        gx = np.clip(mixture_prob(X, pi, qp, qm), 1e-300, None)
        gp = mixture_prob(pats, pi, qp, qm)
        goff = float(gp[off].sum())
        if goff <= 0 or not np.isfinite(goff):
            return 1e100
        return float(-np.log(gx).sum() + len(X) * np.log(goff))

    rng = np.random.default_rng(seed)
    x0s = []
    if warm is not None:
        x0s.append(np.asarray(warm, dtype=float))
    # Deterministic center start plus preregistered seeded starts.
    x0s.append(np.zeros(1 + 2*d))
    while len(x0s) < starts + (1 if warm is not None else 0):
        x0s.append(rng.normal(0, 1.3, 1 + 2*d))

    best = None
    for x0 in x0s:
        opt = minimize(
            objective, x0, method="L-BFGS-B",
            options={"maxiter": maxiter, "ftol": 1e-12, "gtol": 1e-8},
        )
        if np.isfinite(opt.fun) and (best is None or opt.fun < best.fun):
            best = opt
    if best is None:
        raise RuntimeError("DS conditional fit failed")

    pi, qp, qm = decode(best.x, d)
    gp = mixture_prob(pats, pi, qp, qm)
    goff = float(gp[off].sum())
    return {
        "pi": pi,
        "q_plus": qp,
        "q_minus": qm,
        "conditional_nll": float(best.fun),
        "G_off": goff,
        "x": np.asarray(best.x, dtype=float),
    }


def posterior_minus(W, fit):
    W = np.asarray(W, dtype=int)
    pi = float(fit["pi"])
    qp = np.asarray(fit["q_plus"], float)
    qm = np.asarray(fit["q_minus"], float)
    fp = component_prob(W, qp)
    fm = component_prob(W, qm)
    den = pi * fp + (1 - pi) * fm
    return np.divide((1 - pi) * fm, den, out=np.full(len(W), .5), where=den > 0)


def excess_stats(W, fit):
    W = np.asarray(W, dtype=int)
    n = len(W)
    plus = np.all(W == 1, axis=1)
    minus = np.all(W == -1, axis=1)
    off_mass = 1 - plus.mean() - minus.mean()

    d = W.shape[1]
    pp = np.ones((1, d), dtype=int)
    pm = -np.ones((1, d), dtype=int)
    gplus = float(mixture_prob(pp, fit["pi"], fit["q_plus"], fit["q_minus"])[0])
    gminus = float(mixture_prob(pm, fit["pi"], fit["q_plus"], fit["q_minus"])[0])
    c_ds = off_mass / fit["G_off"]

    pred_plus = c_ds * gplus
    pred_minus = c_ds * gminus
    obs_plus = float(plus.mean())
    obs_minus = float(minus.mean())
    return {
        "n": n,
        "obs_plus": obs_plus,
        "obs_minus": obs_minus,
        "off_mass": float(off_mass),
        "c_ds": float(c_ds),
        "pred_plus": float(pred_plus),
        "pred_minus": float(pred_minus),
        "excess_plus": float(obs_plus - pred_plus),
        "excess_minus": float(obs_minus - pred_minus),
        "conditional_nll": float(fit["conditional_nll"]),
        "null_scale_incompatible": bool(c_ds > 1.0 + 1e-8),
    }


def deduplicate_rows(rows, view_cols, require_ast=True):
    if require_ast and "ast_hash" not in rows[0]:
        raise ValueError("primary analysis requires ast_hash; use --no-dedup only for sensitivity")
    seen = set()
    keep = []
    for r in rows:
        key = (r["problem_id"], r.get("ast_hash", r["candidate_id"]))
        if key in seen:
            continue
        seen.add(key)
        keep.append(r)
    W = np.array([[int(r[c]) for c in view_cols] for r in keep], dtype=int)
    problems = np.array([r["problem_id"] for r in keep], dtype=object)
    return keep, problems, W


def load_views(path, no_dedup=False):
    with Path(path).open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("empty input")
    for c in ("problem_id", "candidate_id"):
        if c not in rows[0]:
            raise ValueError(f"missing {c}")
    view_cols = [c for c in rows[0] if c.startswith("view_")]
    if len(view_cols) < 3:
        raise ValueError("need at least three view_* columns")
    if no_dedup:
        keep = rows
        W = np.array([[int(r[c]) for c in view_cols] for r in keep], dtype=int)
        problems = np.array([r["problem_id"] for r in keep], dtype=object)
    else:
        keep, problems, W = deduplicate_rows(rows, view_cols, require_ast=True)
    return keep, problems, view_cols, W


def cluster_bootstrap(rows, view_cols, problems, reps=1000, starts=12, seed=20260920):
    rng = np.random.default_rng(seed)
    uniq = np.unique(problems)
    by_problem = {
        p: np.array([[int(r[c]) for c in view_cols] for r in rows if r["problem_id"] == p], dtype=int)
        for p in uniq
    }
    vals = []
    warm = None
    for b in range(reps):
        chosen = rng.choice(uniq, size=len(uniq), replace=True)
        Wb = np.vstack([by_problem[p] for p in chosen])
        try:
            fb = fit_ds(Wb, starts=starts, seed=seed + b + 1, warm=warm)
            warm = fb["x"]
            sb = excess_stats(Wb, fb)
            vals.append((sb["excess_plus"], sb["excess_minus"], sb["c_ds"]))
        except Exception:
            vals.append((np.nan, np.nan, np.nan))
    return np.asarray(vals, dtype=float)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--starts", type=int, default=12)
    p.add_argument("--cluster-reps", type=int, default=1000)
    p.add_argument("--seed", type=int, default=20260919)
    p.add_argument("--no-dedup", action="store_true")
    p.add_argument("--output", default=None)
    a = p.parse_args()

    rows, problems, view_cols, W = load_views(a.input_csv, no_dedup=a.no_dedup)
    fit = fit_ds(W, starts=a.starts, seed=a.seed)
    stat = excess_stats(W, fit)

    boot = cluster_bootstrap(
        rows, view_cols, problems, reps=a.cluster_reps,
        starts=a.starts, seed=a.seed + 1000,
    )
    good = np.isfinite(boot[:, 0])
    ci_plus = np.quantile(boot[good, 0], [.025, .975]) if good.any() else [np.nan, np.nan]
    ci_minus = np.quantile(boot[good, 1], [.025, .975]) if good.any() else [np.nan, np.nan]

    summary = {
        **stat,
        "view_cols": view_cols,
        "pi": fit["pi"],
        "q_plus": fit["q_plus"].tolist(),
        "q_minus": fit["q_minus"].tolist(),
        "excess_plus_cluster95": [float(ci_plus[0]), float(ci_plus[1])],
        "excess_minus_cluster95": [float(ci_minus[0]), float(ci_minus[1])],
        "cluster_bootstrap_success": int(good.sum()),
        "cluster_bootstrap_reps": int(a.cluster_reps),
    }

    outdir = Path(a.output) if a.output else Path(a.input_csv).parent / "ds_excess_results"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "ds_excess_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(4.8,3.2))
    obs=[stat["obs_plus"],stat["obs_minus"]]
    pred=[stat["pred_plus"],stat["pred_minus"]]
    x=np.arange(2)
    width=.34
    ax.bar(x-width/2,obs,width,label="observed")
    ax.bar(x+width/2,pred,width,label="independent-error null")
    ax.set_xticks(x,["all +","all -"])
    ax.set_ylabel("reported-pattern mass")
    ax.set_title(f"excess + = {stat['excess_plus']:.3g}")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(outdir/"ds_excess.pdf")
    fig.savefig(outdir/"ds_excess.png",dpi=180)
    plt.close(fig)

    with (outdir / "ds_excess_bootstrap.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["excess_plus", "excess_minus", "c_ds"])
        w.writerows(boot)

    print(json.dumps(summary, indent=2))
    print("wrote:", outdir)


if __name__ == "__main__":
    main()
