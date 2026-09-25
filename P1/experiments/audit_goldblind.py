"""Gold-blind diagnostics for audit preregistration v0.3.

Input CSV must NOT contain truth. Required columns:
  benchmark, problem_id, candidate_id, ast_hash, screen_tests_A, test_B_size,
  view_tests_B, and six view_judge* columns.

Primary diagnostics analyze the raw candidate pool (no deduplication), compute
u0/u1, the 6x6 LLM-view disagreement and phi matrices, test-B agreement,
marginal acceptance, and duplicate rate. Deduplication is a sensitivity tier:
--dedup loose (structural-solution estimand; requires a code or
loose_ast_sha256 column) or --dedup strict (continuity with v0.1/v0.2).
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

from ast_hash import apply_dedup

DEFAULT_BASELINE = [
    "view_tests_B",
    "view_judgeA_identity",
    "view_judgeB_identity",
]


def load(path: Path, dedup="none"):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("empty input")
    if "truth" in rows[0]:
        raise ValueError("gold-blind input must not contain truth")

    required = {"benchmark","problem_id","candidate_id","ast_hash","screen_tests_A","test_B_size","view_tests_B"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if any(int(r["screen_tests_A"]) != 1 for r in rows):
        raise ValueError("gold-blind table contains candidates that failed screen A")

    keep, pool = apply_dedup(rows, dedup)

    view_cols=[c for c in keep[0] if c.startswith("view_")]
    judge_cols=[c for c in view_cols if c.startswith("view_judge")]
    if len(judge_cols) != 6:
        raise ValueError(f"expected six LLM judge views, found {len(judge_cols)}")
    W={c:np.array([int(r[c]) for r in keep],dtype=int) for c in view_cols}
    for c,v in W.items():
        if not np.all(np.isin(v,[-1,1])):
            raise ValueError(f"{c} must be +/-1")
    return rows,keep,W,judge_cols,pool


def matrix(cols,W,kind="agreement"):
    X=np.column_stack([W[c] for c in cols])
    k=len(cols)
    if kind=="phi":
        return np.corrcoef(X,rowvar=False)
    A=np.eye(k)
    for i in range(k):
        for j in range(i+1,k):
            val=np.mean(X[:,i]==X[:,j])
            A[i,j]=A[j,i]=val
    return A


def write_matrix(path,names,A):
    with path.open("w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["view"]+names)
        for name,row in zip(names,A):
            w.writerow([name]+[f"{x:.8g}" for x in row])


def main():
    p=argparse.ArgumentParser()
    p.add_argument("input_csv")
    p.add_argument("--baseline-views",nargs="+",default=DEFAULT_BASELINE)
    p.add_argument("--full-views",nargs="+",default=None)
    p.add_argument("--dedup",choices=["none","loose","strict"],default="none",
                   help="primary pool is 'none' (raw candidate draws); "
                        "'loose' and 'strict' are sensitivity tiers")
    p.add_argument("--output",default=None)
    a=p.parse_args()

    path=Path(a.input_csv)
    raw,rows,W,judge_cols,pool=load(path,dedup=a.dedup)
    full=a.full_views or list(W.keys())
    for c in a.baseline_views+full:
        if c not in W:
            raise ValueError(f"missing view column {c}")

    u0=np.logical_and.reduce([W[c]==1 for c in a.baseline_views])
    u1=np.logical_and.reduce([W[c]==1 for c in full])

    Jagr=matrix(judge_cols,W,"agreement")
    Jdis=1-Jagr
    np.fill_diagonal(Jdis,0)
    Jphi=matrix(judge_cols,W,"phi")

    # Test-B agreement with each LLM view.
    tb=W["view_tests_B"]
    tb_agree={c:float(np.mean(tb==W[c])) for c in judge_cols}

    # Preregistered per-stratum test-B strength diagnostics.
    benchmarks=np.array([r["benchmark"] for r in rows],dtype=object)
    problems=np.array([r["problem_id"] for r in rows],dtype=object)
    bsize=np.array([int(r["test_B_size"]) for r in rows],dtype=int)

    def testb_strength(mask):
        idx=np.flatnonzero(mask)
        if len(idx)==0:
            return {}
        # Candidate-weighted dissent.
        cand=float(np.mean(tb[idx]==-1))

        # Problem-weighted dissent: equal weight per benchmark-local problem.
        pvals=[]
        for p in sorted(set(problems[idx])):
            z=idx[problems[idx]==p]
            pvals.append(float(np.mean(tb[z]==-1)))
        prob=float(np.mean(pvals)) if pvals else float("nan")

        # Problem-level distribution of |B| (one frozen size per task).
        bdist={}
        for p in sorted(set(problems[idx])):
            z=idx[problems[idx]==p]
            vals=set(map(int,bsize[z]))
            if len(vals)!=1:
                raise ValueError(f"inconsistent test_B_size within problem {p}: {sorted(vals)}")
            k=next(iter(vals))
            bdist[str(k)]=bdist.get(str(k),0)+1

        by_size={}
        for k in sorted(set(map(int,bsize[idx]))):
            zk=idx[bsize[idx]==k]
            pv=[]
            for p in sorted(set(problems[zk])):
                zp=zk[problems[zk]==p]
                pv.append(float(np.mean(tb[zp]==-1)))
            by_size[str(k)]={
                "candidate_rows":int(len(zk)),
                "candidate_weighted_dissent":float(np.mean(tb[zk]==-1)),
                "problem_count":int(len(set(problems[zk]))),
                "problem_weighted_dissent":float(np.mean(pv)) if pv else float("nan"),
            }

        return {
            "candidate_weighted_testB_dissent":cand,
            "problem_weighted_testB_dissent":prob,
            "B_size_problem_distribution":bdist,
            "testB_dissent_by_B_size":by_size,
        }

    by_stratum={}
    for b in sorted(set(benchmarks)):
        by_stratum[str(b)]=testb_strength(benchmarks==b)

    summary={
        "n_raw":pool["n_raw"],
        "dedup_mode":pool["dedup_mode"],
        "n_analyzed":pool["n_analyzed"],
        "duplicate_fraction":pool["duplicate_fraction"],
        "loose_unparsed_rows":pool["loose_unparsed_rows"],
        "blank_hash_rows":pool["blank_hash_rows"],
        "u0":float(np.mean(u0)),
        "u1":float(np.mean(u1)),
        "n_u0":int(u0.sum()),
        "n_u1":int(u1.sum()),
        "marginal_acceptance":{c:float(np.mean(W[c]==1)) for c in full},
        "testB_agreement_with_llm":tb_agree,
        "testB_strength_by_stratum":by_stratum,
        "llm_view_order":judge_cols,
    }

    outdir=Path(a.output) if a.output else path.parent/"goldblind_results"
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/"goldblind_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    write_matrix(outdir/"llm_agreement_6x6.csv",judge_cols,Jagr)
    write_matrix(outdir/"llm_disagreement_6x6.csv",judge_cols,Jdis)
    write_matrix(outdir/"llm_phi_6x6.csv",judge_cols,Jphi)

    print(json.dumps(summary,indent=2))
    print("wrote:",outdir)


if __name__=="__main__":
    main()
