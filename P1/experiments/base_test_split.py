"""Deterministic base-test split helper.

The benchmark-specific collector supplies stable test-case IDs. This helper maps
those IDs into disjoint A/B halves using a problem-specific SHA-256 seed.

Tasks with fewer than two separable base-test cases are split-ineligible and must
be excluded before candidate generation with reason
BASE_TEST_SPLIT_IMPOSSIBLE. HumanEval/34 is preregistered as such a task.
"""
from __future__ import annotations

import hashlib
import numpy as np

SPLIT_IMPOSSIBLE_REASON = "BASE_TEST_SPLIT_IMPOSSIBLE"


class BaseTestSplitImpossible(ValueError):
    """Raised when a task cannot supply nonempty A and B halves."""


def split_case_ids(case_ids, problem_id: str, split_seed: int):
    ids = list(case_ids)
    if len(ids) < 2:
        raise BaseTestSplitImpossible(
            f"{problem_id}: {SPLIT_IMPOSSIBLE_REASON}; "
            f"need at least two separable base test cases, found {len(ids)}"
        )

    h = hashlib.sha256(f"{split_seed}|{problem_id}".encode()).digest()
    seed = int.from_bytes(h[:8], "big")
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(ids))

    # Frozen rule: A receives ceil(K/2), B receives floor(K/2).
    k = (len(ids) + 1) // 2
    A = [ids[i] for i in order[:k]]
    B = [ids[i] for i in order[k:]]

    if not A or not B:
        raise BaseTestSplitImpossible(
            f"{problem_id}: {SPLIT_IMPOSSIBLE_REASON}; "
            f"split produced |A|={len(A)}, |B|={len(B)}"
        )
    return A, B


def split_record(case_ids, problem_id: str, split_seed: int):
    """Return a manifest-ready split or exclusion record."""
    ids = list(case_ids)
    try:
        A, B = split_case_ids(ids, problem_id, split_seed)
        return {
            "problem_id": problem_id,
            "eligible": True,
            "base_test_count": len(ids),
            "A_count": len(A),
            "B_count": len(B),
            "A_case_ids": A,
            "B_case_ids": B,
            "exclusion_reason": None,
        }
    except BaseTestSplitImpossible:
        return {
            "problem_id": problem_id,
            "eligible": False,
            "base_test_count": len(ids),
            "A_count": 0,
            "B_count": 0,
            "A_case_ids": [],
            "B_case_ids": [],
            "exclusion_reason": SPLIT_IMPOSSIBLE_REASON,
        }
