"""Parametric-bootstrap coverage study for the constructive estimators.

Imports the frozen finite-sample parameter generators and reconstruction
functions.  For each simulated dataset, fit the constructive estimator,
generate parametric-bootstrap samples from that fitted model, and form
coordinatewise percentile intervals.

This is a descriptive finite-sample inference study, not theorem evidence.
"""
from __future__ import annotations

import argparse, csv, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import finite_sample as fs


def vec22(t):
    return np.r_[
        np.asarray(t["w"], float),
        np.asarray(t["qA"][0], float),
        np.asarray(t["qA"][1], float),
        np.asarray(t["qB"][0], float),
        np.asarray(t["qB"][1], float),
        np.asarray(t["eta"], float),
    ]


def names22():
    return [
        "w_ds_plus","w_ds_minus","S_plus","S_minus",
        "qA_plus_1","qA_plus_2","qA_minus_1","qA_minus_2",
        "qB_plus_1","qB_plus_2","qB_minus_1","qB_minus_2",
        "etaA","etaB",
    ]


def vec4(t):
    return np.r_[
        np.asarray(t["c"], float),
        np.asarray(t["S"], float),
        np.asarray(t["q"][0], float),
        np.asarray(t["q"][1], float),
        [float(t["eta"])],
    ]


def names4():
    return [
        "c_plus","c_minus","S_plus","S_minus",
        "q_plus_1","q_plus_2","q_plus_3","q_plus_4",
        "q_minus_1","q_minus_2","q_minus_3","q_minus_4",
        "eta",
    ]


def reconstruct(part, p):
    return fs.recover22_emp(p) if part == "22" else fs.recover4_emp(p)


def law(part, t):
    return fs.law22_vec(t) if part == "22" else fs.law4_vec(t)


def vectorize(part, t):
    return vec22(t) if part == "22" else vec4(t)


def param_names(part):
    return names22() if part == "22" else names4()


def run(args):
    rng = np.random.default_rng(args.seed)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []

    for part in ["22","4"]:
        for N in args.ns:
            for draw in range(args.draws):
                truth = fs.random_theta22(rng) if part == "22" else fs.random_theta4(rng)
                p = law(part, truth)
                counts = fs.multinomial_sample(p, N, rng)
                phat = fs.smoothed_empirical(counts, args.pseudocount)
                est = reconstruct(part, phat)

                names = param_names(part)
                tv = vectorize(part, truth)

                if est is None:
                    for j, name in enumerate(names):
                        rows.append(dict(
                            partition=part, N=N, draw=draw, parameter=name,
                            truth=tv[j], estimate=np.nan, lo=np.nan, hi=np.nan,
                            covered=0, width=np.nan, bootstrap_success=0,
                            estimator_failed=1,
                        ))
                    print(f"part={part} N={N} draw={draw}: estimator failed")
                    continue

                ev = vectorize(part, est)
                pest = law(part, est)
                boot = []
                failures = 0
                for _ in range(args.boot):
                    cb = fs.multinomial_sample(pest, N, rng)
                    pb = fs.smoothed_empirical(cb, args.pseudocount)
                    eb = reconstruct(part, pb)
                    if eb is None:
                        failures += 1
                        continue
                    boot.append(vectorize(part, eb))

                boot = np.asarray(boot, dtype=float)
                success = len(boot)
                if success:
                    lo = np.quantile(boot, .025, axis=0)
                    hi = np.quantile(boot, .975, axis=0)
                else:
                    lo = hi = np.full_like(tv, np.nan)

                for j, name in enumerate(names):
                    covered = int(np.isfinite(lo[j]) and lo[j] <= tv[j] <= hi[j])
                    rows.append(dict(
                        partition=part, N=N, draw=draw, parameter=name,
                        truth=tv[j], estimate=ev[j], lo=lo[j], hi=hi[j],
                        covered=covered,
                        width=(hi[j]-lo[j]) if np.isfinite(lo[j]) else np.nan,
                        bootstrap_success=success,
                        estimator_failed=0,
                    ))
                print(
                    f"part={part} N={N} draw={draw}: "
                    f"bootstrap_success={success}/{args.boot}"
                )

    path = outdir / "coverage.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    summary = []
    for part in ["22","4"]:
        for N in args.ns:
            rr = [r for r in rows if r["partition"] == part and int(r["N"]) == N
                  and not int(r["estimator_failed"])]
            if not rr:
                continue
            summary.append(dict(
                partition=part,
                N=N,
                mean_coordinate_coverage=float(np.mean([int(r["covered"]) for r in rr])),
                median_interval_width=float(np.nanmedian([float(r["width"]) for r in rr])),
                estimator_failure_rate=float(np.mean([
                    int(r["estimator_failed"]) for r in rows
                    if r["partition"] == part and int(r["N"]) == N
                ])),
                mean_bootstrap_success=float(np.mean([int(r["bootstrap_success"]) for r in rr])),
            ))
    with (outdir / "coverage_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader(); w.writerows(summary)

    print("wrote", path)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ns", type=int, nargs="+", default=[1000,10000,100000])
    p.add_argument("--draws", type=int, default=10)
    p.add_argument("--boot", type=int, default=200)
    p.add_argument("--pseudocount", type=float, default=.5)
    p.add_argument("--seed", type=int, default=20260920)
    p.add_argument("--output", default=str(HERE / "results" / "coverage"))
    p.add_argument("--quick", action="store_true")
    a = p.parse_args()
    if a.quick:
        a.ns = [1000]
        a.draws = 2
        a.boot = 20
    return a


if __name__ == "__main__":
    run(parse_args())
