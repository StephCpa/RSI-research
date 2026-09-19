"""Judge repeatability helper for audit preregistration v0.3.

Two modes:

select:
  input one row per original judge call with
  call_id,candidate_id,judge_id,check_id,...
  deterministically selects approximately 5% using SHA-256.

analyze:
  input repeated-call table with
  call_id,candidate_id,judge_id,check_id,view_original,view_repeat
  and reports flip rates overall and by judge/check.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def selected(seed: int, candidate_id: str, judge_id: str, check_id: str, fraction: float) -> bool:
    key=f"{seed}|{candidate_id}|{judge_id}|{check_id}".encode()
    x=int.from_bytes(hashlib.sha256(key).digest()[:8],"big")/2**64
    return x < fraction


def select_mode(a):
    with Path(a.input_csv).open(newline="") as f:
        rows=list(csv.DictReader(f))
    req={"call_id","candidate_id","judge_id","check_id"}
    miss=req-set(rows[0])
    if miss:
        raise ValueError(f"missing columns: {sorted(miss)}")
    keep=[r for r in rows if selected(a.seed,r["candidate_id"],r["judge_id"],r["check_id"],a.fraction)]
    out=Path(a.output)
    with out.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(keep)
    print(f"selected {len(keep)}/{len(rows)} = {len(keep)/len(rows):.4f}")
    print("wrote:",out)


def analyze_mode(a):
    with Path(a.input_csv).open(newline="") as f:
        rows=list(csv.DictReader(f))
    req={"candidate_id","judge_id","check_id","view_original","view_repeat"}
    miss=req-set(rows[0])
    if miss:
        raise ValueError(f"missing columns: {sorted(miss)}")

    def rate(rr):
        if not rr:
            return None
        return sum(int(r["view_original"])!=int(r["view_repeat"]) for r in rr)/len(rr)

    by_j=defaultdict(list); by_c=defaultdict(list); by_jc=defaultdict(list)
    for r in rows:
        by_j[r["judge_id"]].append(r)
        by_c[r["check_id"]].append(r)
        by_jc[(r["judge_id"],r["check_id"])].append(r)

    out={
        "n_repeat_calls":len(rows),
        "flip_rate_overall":rate(rows),
        "by_judge":{k:rate(v) for k,v in sorted(by_j.items())},
        "by_check":{k:rate(v) for k,v in sorted(by_c.items())},
        "by_judge_check":{f"{j}|{c}":rate(v) for (j,c),v in sorted(by_jc.items())},
    }
    Path(a.output).write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(out,indent=2))


def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="mode",required=True)

    s=sub.add_parser("select")
    s.add_argument("input_csv")
    s.add_argument("--seed",type=int,default=20260920)
    s.add_argument("--fraction",type=float,default=.05)
    s.add_argument("--output",default="judge_repeat_selection.csv")

    q=sub.add_parser("analyze")
    q.add_argument("input_csv")
    q.add_argument("--output",default="judge_repeatability.json")

    a=p.parse_args()
    if a.mode=="select":
        select_mode(a)
    else:
        analyze_mode(a)


if __name__=="__main__":
    main()
