"""Audit-budget allocation study for the deployed gate in preregistration v0.3.

The input is the gold-labeled, A-screened candidate table. The primary pool is
the raw candidate draws (no deduplication); loose/strict deduplication are
sensitivity tiers via --dedup.

Strategies:
  uniform_screened
  proportional_accepted
  unanimity_weighted (3:1:1 over LLM-positive strata 6,5,4)
  oracle_neyman
  model_assisted

The target is total false-accept mass F_G = P(Y=-1, G=1) in the A-screened
population.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ds_excess
from ast_hash import apply_dedup


def load(path, dedup="none"):
    with Path(path).open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("empty input")
    for c in ("problem_id", "candidate_id", "truth"):
        if c not in rows[0]:
            raise ValueError(f"missing {c}")
    if "screen_tests_A" in rows[0]:
        bad = [r["candidate_id"] for r in rows if int(r["screen_tests_A"]) != 1]
        if bad:
            raise ValueError("input contains candidates that failed screen A")

    view_cols = [c for c in rows[0] if c.startswith("view_")]
    if "view_tests_B" not in view_cols:
        raise ValueError("need view_tests_B")
    judge_cols = [c for c in view_cols if c.startswith("view_judge")]
    if len(judge_cols) != 6:
        raise ValueError(f"expected six LLM judge views, found {len(judge_cols)}")

    keep, pool = apply_dedup(rows, dedup)

    truth = np.array([int(r["truth"]) for r in keep], dtype=int)
    W = np.array([[int(r[c]) for c in view_cols] for r in keep], dtype=int)
    testB = np.array([int(r["view_tests_B"]) for r in keep], dtype=int)
    J = np.array([[int(r[c]) for c in judge_cols] for r in keep], dtype=int)
    return keep, truth, view_cols, W, judge_cols, testB, J, pool


def largest_remainder_allocation(B, sizes, weights):
    """Integer allocation with caps; redistributes unused budget."""
    sizes = np.asarray(sizes, dtype=int)
    weights = np.asarray(weights, dtype=float)
    out = np.zeros(len(sizes), dtype=int)
    remaining = min(int(B), int(sizes.sum()))
    active = sizes > 0
    while remaining > 0 and active.any():
        ww = weights.copy()
        ww[~active] = 0
        if ww.sum() <= 0:
            ww = active.astype(float)
        target = remaining * ww / ww.sum()
        add = np.floor(target).astype(int)
        add = np.minimum(add, sizes - out)
        if add.sum() == 0:
            frac = target - np.floor(target)
            order = np.argsort(-frac)
            placed = False
            for j in order:
                if active[j] and out[j] < sizes[j]:
                    out[j] += 1
                    remaining -= 1
                    placed = True
                    break
            if not placed:
                break
        else:
            out += add
            remaining -= int(add.sum())
        active = out < sizes
    return out


def stratified_estimate(indices_by_h, alloc, y, rng, model_score=None, model_assisted=False):
    N = len(y)
    est = 0.0
    sampled = {}
    for h_i, idx in enumerate(indices_by_h):
        nh = int(alloc[h_i])
        if nh > len(idx):
            nh = len(idx)
        samp = rng.choice(idx, size=nh, replace=False) if nh > 0 else np.array([], dtype=int)
        sampled[h_i] = samp

        Nh = len(idx)
        if Nh == 0:
            continue

        if model_assisted and h_i > 0:
            # h_i=0 is unanimous stratum (h=6): use direct audit there.
            mh = float(np.mean(model_score[idx]))
            if nh > 0:
                residual = float(np.mean((y[samp] - model_score[samp])))
            else:
                residual = 0.0
            ph = mh + residual
        else:
            if nh == 0:
                return np.nan, sampled
            ph = float(np.mean(y[samp]))
        est += (Nh / N) * ph
    return est, sampled


def one_replicate(B, y, gate, strata_idx, stratum_p, ds_score, rng):
    N = len(y)
    accepted = np.flatnonzero(gate)
    sizes = np.array([len(x) for x in strata_idx], dtype=int)
    out = {}

    # Uniform over the entire screened population.
    n = min(B, N)
    samp = rng.choice(N, size=n, replace=False)
    out["uniform_screened"] = float(np.mean(y[samp] * gate[samp]))

    # Proportional over accepted strata.
    alloc = largest_remainder_allocation(B, sizes, sizes.astype(float))
    out["proportional_accepted"], _ = stratified_estimate(
        strata_idx, alloc, y, rng
    )

    # Theory-motivated unanimity oversampling: h=6 gets 3x weight.
    alloc = largest_remainder_allocation(B, sizes, sizes * np.array([3.0, 1.0, 1.0]))
    out["unanimity_weighted"], _ = stratified_estimate(
        strata_idx, alloc, y, rng
    )

    # Oracle Neyman benchmark.
    sd = np.sqrt(np.clip(stratum_p * (1 - stratum_p), 0, None))
    alloc = largest_remainder_allocation(B, sizes, sizes * sd)
    out["oracle_neyman"], _ = stratified_estimate(
        strata_idx, alloc, y, rng
    )

    # Model-assisted: 50% to unanimous, rest proportional to h=5,4.
    if B <= 0:
        out["model_assisted"] = np.nan
    else:
        alloc = np.zeros(3, dtype=int)
        b_u = min((B + 1) // 2, sizes[0])
        alloc[0] = b_u
        rem = B - b_u
        tail = largest_remainder_allocation(rem, sizes[1:], sizes[1:].astype(float))
        alloc[1:] = tail
        # If unanimous stratum was capped, redistribute spare budget.
        spare = B - int(alloc.sum())
        if spare > 0:
            extra = largest_remainder_allocation(
                spare, sizes - alloc, (sizes - alloc).astype(float)
            )
            alloc += extra
        out["model_assisted"], _ = stratified_estimate(
            strata_idx, alloc, y, rng, model_score=ds_score, model_assisted=True
        )

    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--budgets", type=int, nargs="+", default=[25,50,100,200,500,1000])
    p.add_argument("--reps", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20260922)
    p.add_argument("--ds-starts", type=int, default=12)
    p.add_argument("--dedup",choices=["none","loose","strict"],default="none",
                   help="primary pool is 'none' (raw candidate draws); "
                        "'loose' and 'strict' are sensitivity tiers")
    p.add_argument("--output", default=None)
    a = p.parse_args()

    rows, truth, view_cols, W, judge_cols, testB, J, pool = load(
        a.input_csv, dedup=a.dedup
    )
    y = (truth == -1).astype(float)
    pos = (J == 1).sum(axis=1)
    gate = (testB == 1) & (pos >= 4)

    # Accepted strata in preregistered order h=6,5,4.
    strata_idx = [np.flatnonzero((testB == 1) & (pos == h)) for h in (6,5,4)]
    stratum_p = np.array([
        np.mean(y[idx]) if len(idx) else 0.0 for idx in strata_idx
    ])
    F_true = float(np.mean(y * gate))

    fit = ds_excess.fit_ds(W, starts=a.ds_starts, seed=a.seed)
    ds_score = ds_excess.posterior_minus(W, fit)

    rng = np.random.default_rng(a.seed + 1)
    raw = []
    for B in a.budgets:
        for rep in range(a.reps):
            ests = one_replicate(B, y, gate, strata_idx, stratum_p, ds_score, rng)
            for method, est in ests.items():
                raw.append({
                    "budget": B,
                    "replicate": rep,
                    "method": method,
                    "estimate": est,
                    "truth": F_true,
                    "error": est - F_true if np.isfinite(est) else np.nan,
                    "abs_error": abs(est - F_true) if np.isfinite(est) else np.nan,
                })

    methods = sorted({r["method"] for r in raw})
    summary = []
    for B in a.budgets:
        for method in methods:
            e = np.array([
                float(r["error"]) for r in raw
                if int(r["budget"]) == B and r["method"] == method
                and np.isfinite(float(r["error"]))
            ])
            if len(e) == 0:
                continue
            summary.append({
                "budget": B,
                "method": method,
                "rmse": float(np.sqrt(np.mean(e**2))),
                "median_abs_error": float(np.median(np.abs(e))),
                "q95_abs_error": float(np.quantile(np.abs(e), .95)),
                "bias": float(np.mean(e)),
            })

    outdir = Path(a.output) if a.output else Path(a.input_csv).parent / "allocation_results"
    outdir.mkdir(parents=True, exist_ok=True)

    with (outdir / "allocation_raw.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(raw[0].keys()))
        w.writeheader(); w.writerows(raw)
    with (outdir / "allocation_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)

    meta = {
        "F_true": F_true,
        "N_screened": len(y),
        "n_raw": pool["n_raw"],
        "dedup_mode": pool["dedup_mode"],
        "n_analyzed": pool["n_analyzed"],
        "duplicate_fraction": pool["duplicate_fraction"],
        "loose_unparsed_rows": pool["loose_unparsed_rows"],
        "blank_hash_rows": pool["blank_hash_rows"],
        "N_accepted": int(gate.sum()),
        "strata_h_6_5_4_sizes": [len(x) for x in strata_idx],
        "strata_h_6_5_4_false_rates": stratum_p.tolist(),
        "judge_cols": judge_cols,
        "view_cols": view_cols,
    }
    (outdir / "allocation_meta.json").write_text(json.dumps(meta, indent=2) + "\n")

    # Figure.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.2,3.4))
    for method in methods:
        rr = [r for r in summary if r["method"] == method]
        ax.plot([r["budget"] for r in rr], [r["rmse"] for r in rr],
                marker="o", label=method)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("gold budget")
    ax.set_ylabel("RMSE for total false-accept mass")
    ax.legend(fontsize=6.5)
    fig.tight_layout()
    fig.savefig(outdir / "allocation_rmse.pdf")
    fig.savefig(outdir / "allocation_rmse.png", dpi=180)
    plt.close(fig)

    print(json.dumps(meta, indent=2))
    print("wrote:", outdir)


if __name__ == "__main__":
    main()
