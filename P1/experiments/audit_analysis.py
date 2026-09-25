"""Primary gold analysis for audit preregistration v0.3.

Primary population:
  - passed screen A,
  - raw candidate pool (no deduplication),
  - clustered inference by problem.

Deduplication is a sensitivity tier: --dedup loose (structural-solution
estimand; requires a code or loose_ast_sha256 column) or --dedup strict
(continuity with v0.1/v0.2 reports).

Model-based excess unanimity and audit-allocation efficiency are implemented in
separate frozen scripts (ds_excess.py and audit_allocation.py).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta, binomtest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_BASELINE = [
    "view_tests_B",
    "view_judgeA_identity",
    "view_judgeB_identity",
]


def cp_interval(k,n,alpha=.05):
    if n==0:
        return 0.0,1.0
    lo=0.0 if k==0 else float(beta.ppf(alpha/2,k,n-k+1))
    hi=1.0 if k==n else float(beta.ppf(1-alpha/2,k+1,n-k))
    return lo,hi


def _loose_hash_column(rows):
    """Loose AST hash per row: prefer a precomputed loose_ast_sha256 column,
    else compute from code. Unparseable rows are kept unique and counted."""
    have_pre = "loose_ast_sha256" in rows[0]
    have_code = "code" in rows[0]
    if not have_pre and not have_code:
        raise ValueError(
            "--dedup loose requires a 'code' or 'loose_ast_sha256' column"
        )
    from ast_hash import loose_ast_sha256

    keys = []
    unparsed = 0
    for r in rows:
        pre = r.get("loose_ast_sha256", "") if have_pre else ""
        if pre:
            keys.append(pre)
            continue
        code = r.get("code")
        if code is None:
            raise ValueError(
                f"row {r.get('candidate_id', '?')} has neither loose hash nor code"
            )
        try:
            keys.append(loose_ast_sha256(code))
        except SyntaxError:
            unparsed += 1
            keys.append("__unparsed__" + str(r.get("candidate_id", "")))
    return keys, unparsed


def load(path,no_dedup=False,dedup="none"):
    with Path(path).open(newline="") as f:
        rows=list(csv.DictReader(f))
    if not rows:
        raise ValueError("empty input")
    required={"problem_id","candidate_id","ast_hash","screen_tests_A","truth","view_tests_B"}
    missing=required-set(rows[0])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if any(int(r["screen_tests_A"])!=1 for r in rows):
        raise ValueError("table contains candidates that failed screen A")

    raw_n=len(rows)
    loose_unparsed=0
    if dedup=="none":
        keep=rows
    elif dedup=="strict":
        seen=set(); keep=[]
        for r in rows:
            key=(r["problem_id"],r["ast_hash"])
            if key in seen:
                continue
            seen.add(key); keep.append(r)
    elif dedup=="loose":
        hashes,loose_unparsed=_loose_hash_column(rows)
        seen=set(); keep=[]
        for r,h in zip(rows,hashes):
            key=(r["problem_id"],h)
            if key in seen:
                continue
            seen.add(key); keep.append(r)
    else:
        raise ValueError(f"unknown dedup mode: {dedup!r}")

    truth=np.array([int(r["truth"]) for r in keep],dtype=int)
    if not np.all(np.isin(truth,[-1,1])):
        raise ValueError("truth must be +/-1")
    view_cols=[c for c in keep[0] if c.startswith("view_")]
    W={c:np.array([int(r[c]) for r in keep],dtype=int) for c in view_cols}
    for c,v in W.items():
        if not np.all(np.isin(v,[-1,1])):
            raise ValueError(f"{c} must be +/-1")
    problem=np.array([r["problem_id"] for r in keep],dtype=object)
    return rows,keep,problem,truth,W,raw_n,dedup,loose_unparsed


def scheme(W,cols):
    for c in cols:
        if c not in W:
            raise ValueError(f"missing scheme view {c}")
    return np.logical_and.reduce([W[c]==1 for c in cols])


def safe(a,b):
    return np.nan if b==0 else a/b


def cluster_table(problem,truth,u0,u1):
    d=u0 & ~u1
    out=[]
    for p in np.unique(problem):
        z=problem==p
        n=int(z.sum())
        u0n=int((z&u0).sum()); u1n=int((z&u1).sum())
        e0=int((z&u0&(truth==-1)).sum()); e1=int((z&u1&(truth==-1)).sum())
        dn=int((z&d).sum())
        de=int((z&d&(truth==-1)).sum())
        dc=int((z&d&(truth==1)).sum())
        c0=int((z&u0&(truth==1)).sum())
        out.append((p,n,u0n,e0,u1n,e1,dn,de,dc,c0))
    return out


def metrics(t):
    n,u0n,e0,u1n,e1,dn,de,dc,c0=t
    r0=safe(e0,u0n); r1=safe(e1,u1n); rd=safe(de,dn)
    return {
        "u0":safe(u0n,n),
        "u1":safe(u1n,n),
        "r0":r0,
        "r1":r1,
        "r0_minus_r1":r0-r1 if np.isfinite(r0) and np.isfinite(r1) else np.nan,
        "b0":safe(e0,n),
        "b1":safe(e1,n),
        "delta_b":safe(e0-e1,n),
        "removed_error_rate":rd,
        "enrichment":safe(rd,r0) if np.isfinite(rd) and np.isfinite(r0) else np.nan,
        "correct_given_removed":safe(dc,dn),
        "correct_yield_loss":safe(dc,c0),
    }


def totals_from_clusters(ct):
    a=np.asarray([[x[i] for i in range(1,10)] for x in ct],dtype=float)
    return a.sum(axis=0)


def bootstrap(ct,reps,seed):
    rng=np.random.default_rng(seed)
    a=np.asarray([[x[i] for i in range(1,10)] for x in ct],dtype=float)
    m=len(a)
    names=["u0","u1","r0","r1","r0_minus_r1","b0","b1","delta_b",
           "enrichment","correct_given_removed","correct_yield_loss"]
    out={k:np.full(reps,np.nan) for k in names}
    for b in range(reps):
        t=a[rng.integers(0,m,size=m)].sum(axis=0)
        d=metrics(t)
        for k in names:
            out[k][b]=d[k]
    return out


def ci(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    return (np.nan,np.nan) if len(x)==0 else tuple(np.quantile(x,[.025,.975]))


def icc_binary(ct):
    ns=[]; ks=[]
    for x in ct:
        n=int(x[4]); k=int(x[5])
        if n>0:
            ns.append(n); ks.append(k)
    ns=np.asarray(ns,float); ks=np.asarray(ks,float)
    if len(ns)<2 or ns.sum()<=len(ns):
        return np.nan
    ps=ks/ns; p=ks.sum()/ns.sum()
    B=np.sum(ns*(ps-p)**2)
    W=np.sum(ks*(1-ps)**2+(ns-ks)*ps**2)
    msb=B/(len(ns)-1); msw=W/(ns.sum()-len(ns))
    n0=(ns.sum()-np.sum(ns**2)/ns.sum())/(len(ns)-1)
    den=msb+(n0-1)*msw
    return np.nan if abs(den)<1e-15 else float((msb-msw)/den)


def make_figure(point,boot,cp,outpath):
    u1=point["u1"]; b1=point["b1"]
    r1lo,r1hi=ci(boot["r1"])
    b_lo,b_hi=u1*r1lo,u1*r1hi
    cp_lo,cp_hi=cp

    fig,ax=plt.subplots(1,3,figsize=(10.6,3.0))

    ax[0].plot([0,0],[0,u1],lw=9,alpha=.22,label="agreement-only set")
    ax[0].errorbar([1],[b1],yerr=[[b1-b_lo],[b_hi-b1]],fmt="o",capsize=4,
                   label="problem-cluster audit")
    ax[0].errorbar([1.08],[b1],
                   yerr=[[b1-u1*cp_lo],[u1*cp_hi-b1]],fmt=".",capsize=3,
                   alpha=.55,label="fixed-pool CP")
    ax[0].set_xticks([0,1],["agreement","gold audit"])
    ax[0].set_ylabel("blind false-accept mass")
    ax[0].set_title("(A) identified set shrinks")
    ax[0].legend(fontsize=6.3)

    r0lo,r0hi=ci(boot["r0"]); r1lo,r1hi=ci(boot["r1"])
    vals=[point["r0"],point["r1"]]
    ax[1].errorbar([0,1],vals,
                   yerr=[[vals[0]-r0lo,vals[1]-r1lo],
                         [r0hi-vals[0],r1hi-vals[1]]],fmt="o",capsize=4)
    ax[1].set_xticks([0,1],[r"$r_0$",r"$r_1$"])
    ax[1].set_ylabel("false-accept rate in unanimous set")
    ax[1].set_title("(B) added-check informativeness")

    elo,ehi=ci(boot["enrichment"])
    clo,chi=ci(boot["correct_given_removed"])
    ax[2].bar([0,1],[point["enrichment"],point["correct_given_removed"]])
    ax[2].errorbar([0,1],[point["enrichment"],point["correct_given_removed"]],
                   yerr=[[point["enrichment"]-elo,point["correct_given_removed"]-clo],
                         [ehi-point["enrichment"],chi-point["correct_given_removed"]]],
                   fmt="none",capsize=4)
    ax[2].set_xticks([0,1],["error enrichment","correct | removed"],rotation=10)
    ax[2].set_title("(C) removal tradeoff")

    fig.tight_layout()
    fig.savefig(outpath)
    fig.savefig(outpath.with_suffix(".png"),dpi=180)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--baseline-views",nargs="+",default=DEFAULT_BASELINE)
    p.add_argument("--full-views",nargs="+",default=None)
    p.add_argument("--cluster-reps",type=int,default=10000)
    p.add_argument("--seed",type=int,default=20260919)
    p.add_argument("--practical-bar",type=float,default=.02)
    p.add_argument("--judge-bad-bar",type=float,default=.40)
    p.add_argument("--precision-halfwidth",type=float,default=.02)
    p.add_argument("--dedup",choices=["none","loose","strict"],default="none",
                   help="primary pool is 'none' (raw candidate draws); "
                        "'loose' and 'strict' are sensitivity tiers")
    p.add_argument("--output",default=None)
    a=p.parse_args()

    path=Path(a.input_csv)
    raw,rows,problem,truth,W,raw_n,dedup,loose_unparsed=load(path,dedup=a.dedup)
    full=a.full_views or list(W.keys())
    u0=scheme(W,a.baseline_views); u1=scheme(W,full)

    # A-screen null-calibration check.
    if any(int(r["screen_tests_A"])!=1 for r in rows):
        raise RuntimeError("NULL_CALIBRATION_FAIL: non-screened row in analysis population")
    print("NULL_CALIBRATION: PASS")

    ct=cluster_table(problem,truth,u0,u1)
    point=metrics(totals_from_clusters(ct))
    boot=bootstrap(ct,a.cluster_reps,a.seed)
    r1_ci=ci(boot["r1"]); diff_ci=ci(boot["r0_minus_r1"])
    db_ci=ci(boot["delta_b"])

    n_u1=int(u1.sum()); k_u1=int((u1&(truth==-1)).sum())
    cp=cp_interval(k_u1,n_u1)
    cp_half=(cp[1]-cp[0])/2
    blind_problem_count=len(set(problem[u1&(truth==-1)]))

    icc=icc_binary(ct)
    naive_var=point["r1"]*(1-point["r1"])/n_u1 if n_u1 and np.isfinite(point["r1"]) else np.nan
    cluster_var=float(np.nanvar(boot["r1"],ddof=1))
    deff=cluster_var/naive_var if np.isfinite(naive_var) and naive_var>0 else np.nan
    neff=n_u1/deff if np.isfinite(deff) and deff>0 else np.nan

    if np.isfinite(r1_ci[0]) and r1_ci[0] > a.judge_bad_bar:
        category="JUDGE_QUALITY_FAIL"
    elif np.isfinite(r1_ci[1]) and r1_ci[1] < a.practical_bar:
        category="LOW_BLIND"
    elif (np.isfinite(r1_ci[0]) and r1_ci[0] > a.practical_bar
          and np.isfinite(r1_ci[1]) and r1_ci[1] < a.judge_bad_bar
          and cp_half <= a.precision_halfwidth and blind_problem_count >= 3):
        category="HEADLINE_BLIND"
    else:
        category="INCONCLUSIVE"

    # Fixed-pool paired blind-indicator table.
    B0=u0&(truth==-1); B1=u1&(truth==-1)
    n00=int((~B0&~B1).sum()); n01=int((~B0&B1).sum())
    n10=int((B0&~B1).sum()); n11=int((B0&B1).sum())
    discord=n01+n10
    mcnemar_p=float(binomtest(min(n01,n10),discord,.5).pvalue) if discord else 1.0

    summary={
        "n_raw":raw_n,
        "dedup_mode":dedup,
        "n_primary":len(rows),
        "duplicate_fraction":1-len(rows)/raw_n,
        "loose_unparsed_rows":loose_unparsed,
        "point":point,
        "cluster95":{
            "r0":ci(boot["r0"]),
            "r1":r1_ci,
            "r0_minus_r1":diff_ci,
            "delta_b_paired":db_ci,
            "enrichment":ci(boot["enrichment"]),
            "correct_given_removed":ci(boot["correct_given_removed"]),
            "correct_yield_loss":ci(boot["correct_yield_loss"]),
        },
        "fixed_pool_cp95_r1":cp,
        "fixed_pool_cp_halfwidth_r1":cp_half,
        "paired_blind_table":{"00":n00,"01":n01,"10":n10,"11":n11,
                              "mcnemar_exact_p":mcnemar_p},
        "icc_u1_blind":icc,
        "empirical_deff":deff,
        "n_eff":neff,
        "n_u1":n_u1,
        "k_u1":k_u1,
        "blind_problem_count":blind_problem_count,
        "interpretation":category,
    }

    outdir=Path(a.output) if a.output else path.parent/"audit_results"
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/"audit_summary.json").write_text(json.dumps(summary,indent=2,default=float)+"\n")
    make_figure(point,boot,cp,outdir/"audit_primary.pdf")

    print(json.dumps(summary,indent=2,default=float))
    print("wrote:",outdir)


if __name__=="__main__":
    main()
