"""Gold-blind diagnostics for audit preregistration v0.3.

Input CSV must NOT contain truth. Required columns:
  problem_id, candidate_id, ast_hash, screen_tests_A,
  view_tests_B, and six view_judge* columns.

Primary diagnostics deduplicate within problem by ast_hash, compute u0/u1, the
6x6 LLM-view disagreement and phi matrices, test-B agreement, marginal
acceptance, and duplicate rate.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import numpy as np

DEFAULT_BASELINE = [
    "view_tests_B",
    "view_judgeA_identity",
    "view_judgeB_identity",
]


def load(path: Path, no_dedup=False):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("empty input")
    if "truth" in rows[0]:
        raise ValueError("gold-blind input must not contain truth")

    required = {"problem_id","candidate_id","ast_hash","screen_tests_A","view_tests_B"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if any(int(r["screen_tests_A"]) != 1 for r in rows):
        raise ValueError("gold-blind table contains candidates that failed screen A")

    raw_n = len(rows)
    if no_dedup:
        keep = rows
    else:
        seen=set(); keep=[]
        for r in rows:
            key=(r["problem_id"],r["ast_hash"])
            if key in seen:
                continue
            seen.add(key); keep.append(r)

    view_cols=[c for c in keep[0] if c.startswith("view_")]
    judge_cols=[c for c in view_cols if c.startswith("view_judge")]
    if len(judge_cols) != 6:
        raise ValueError(f"expected six LLM judge views, found {len(judge_cols)}")
    W={c:np.array([int(r[c]) for r in keep],dtype=int) for c in view_cols}
    for c,v in W.items():
        if not np.all(np.isin(v,[-1,1])):
            raise ValueError(f"{c} must be +/-1")
    return rows,keep,W,judge_cols,raw_n


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
    p.add_argument("--no-dedup",action="store_true")
    p.add_argument("--output",default=None)
    a=p.parse_args()

    path=Path(a.input_csv)
    raw,rows,W,judge_cols,raw_n=load(path,no_dedup=a.no_dedup)
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

    summary={
        "n_raw":raw_n,
        "n_ast_dedup":len(rows),
        "duplicate_fraction":1-len(rows)/raw_n,
        "u0":float(np.mean(u0)),
        "u1":float(np.mean(u1)),
        "n_u0":int(u0.sum()),
        "n_u1":int(u1.sum()),
        "marginal_acceptance":{c:float(np.mean(W[c]==1)) for c in full},
        "testB_agreement_with_llm":tb_agree,
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
