"""Controlled approaches to algebraic degeneracy for (2,2) and (4).

The goal is to show that finite-sample error grows as the frozen regularity
margin shrinks.  These paths are prespecified in finite_sample_prereg_v0_1.md.
"""
from __future__ import annotations

import argparse, csv, sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import finite_sample as fs


EPS_GRID = [0.30,0.20,0.10,0.05,0.02,0.01]


def theta22_sep(eps):
    w = np.array([.30,.30,.22,.18])
    a = np.array([.80,.60]); b = np.array([.70,.50])
    qAp = .5 + eps*a; qAm = .5 - eps*b
    qBp = .5 + eps*np.array([.65,.75]); qBm = .5 - eps*np.array([.55,.60])
    return dict(w=w, qA=[qAp,qAm], qB=[qBp,qBm], eta=np.array([.10,.15]))


def theta22_atom(delta):
    atom=.40
    Sp=atom*(1+delta)/2; Sm=atom*(1-delta)/2
    w=np.array([.32,.28,Sp,Sm])
    return dict(
        w=w,
        qA=[np.array([.80,.74]),np.array([.22,.28])],
        qB=[np.array([.77,.82]),np.array([.25,.18])],
        eta=np.array([.10,.15]),
    )


def theta4_mirror(eps):
    qp=np.array([.80,.75,.70,.85])
    v=np.array([.40,-.30,.20,-.10])
    qm=1-qp+eps*v
    return dict(
        c=np.array([.30,.25]),
        S=np.array([.25,.20]),
        q=[qp,qm],
        eta=.10,
    )


def run(args):
    rng=np.random.default_rng(args.seed)
    outdir=Path(args.output); outdir.mkdir(parents=True,exist_ok=True)
    rows=[]
    paths=[
        ("22_component_separation","22",theta22_sep),
        ("22_atom_imbalance","22",theta22_atom),
        ("4_mirror","4",theta4_mirror),
    ]
    for label,part,fn in paths:
        for eps in EPS_GRID:
            truth=fn(eps)
            p=fs.law22_vec(truth) if part=="22" else fs.law4_vec(truth)
            reg=fs.regularity22(truth) if part=="22" else fs.regularity4(truth)
            errfun=fs.error22 if part=="22" else fs.error4
            for rep in range(args.replicates):
                counts=fs.multinomial_sample(p,args.N,rng)
                phat=fs.smoothed_empirical(counts,args.pseudocount)
                est=fs.recover22_emp(phat) if part=="22" else fs.recover4_emp(phat)
                rows.append(dict(
                    path=label, partition=part, epsilon=eps, N=args.N,
                    replicate=rep, regularity_margin=reg,
                    error=errfun(est,truth), failed=int(est is None),
                ))
            print(label, eps, "margin", f"{reg:.3e}")

    with (outdir/"degeneracy_paths.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    fig,ax=plt.subplots(1,3,figsize=(10.2,3.0),sharey=True)
    for a,(label,part,_) in zip(ax,paths):
        rr=[r for r in rows if r["path"]==label and np.isfinite(float(r["error"]))]
        for eps in EPS_GRID:
            x=[r for r in rr if float(r["epsilon"])==eps]
            if not x: continue
            margin=float(x[0]["regularity_margin"])
            vals=np.array([float(r["error"]) for r in x])
            a.errorbar([margin],[np.median(vals)],
                       yerr=[[np.median(vals)-np.quantile(vals,.1)],
                             [np.quantile(vals,.9)-np.median(vals)]],
                       fmt="o",capsize=3)
            a.annotate(f"{eps:g}",(margin,np.median(vals)),fontsize=6)
        a.set_xscale("log"); a.set_yscale("log")
        a.set_xlabel("frozen regularity margin")
        a.set_title(label.replace("_"," "))
    ax[0].set_ylabel("constructive max parameter error")
    fig.tight_layout()
    fig.savefig(outdir/"degeneracy_paths.pdf")
    fig.savefig(outdir/"degeneracy_paths.png",dpi=180)
    plt.close(fig)


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--N",type=int,default=10000)
    p.add_argument("--replicates",type=int,default=100)
    p.add_argument("--pseudocount",type=float,default=.5)
    p.add_argument("--seed",type=int,default=20260921)
    p.add_argument("--output",default=str(HERE/"results"/"degeneracy"))
    p.add_argument("--quick",action="store_true")
    a=p.parse_args()
    if a.quick:
        a.replicates=5
    return a


if __name__=="__main__":
    run(parse_args())
