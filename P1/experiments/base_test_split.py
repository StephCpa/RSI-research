"""Deterministic base-test split helper.

The benchmark-specific collector should supply stable test-case IDs. This helper
maps those IDs into disjoint A/B halves using a problem-specific SHA-256 seed.
"""
from __future__ import annotations
import hashlib
import numpy as np


def split_case_ids(case_ids, problem_id: str, split_seed: int):
    ids=list(case_ids)
    if len(ids)<2:
        raise ValueError("need at least two separable base test cases")
    h=hashlib.sha256(f"{split_seed}|{problem_id}".encode()).digest()
    seed=int.from_bytes(h[:8],"big")
    rng=np.random.default_rng(seed)
    order=rng.permutation(len(ids))
    k=(len(ids)+1)//2
    A=[ids[i] for i in order[:k]]
    B=[ids[i] for i in order[k:]]
    return A,B
