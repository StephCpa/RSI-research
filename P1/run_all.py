"""Run the deterministic/reproducibility checks shipped with P1.

This is intentionally conservative: exploratory scans are not part of the verification target.
Each script is run in its own directory context and timed. A nonzero exit status fails the run.
"""
from __future__ import annotations
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROOFS = ROOT / "proofs"

SCRIPTS = [
    "gauge.py",
    "exact_blocks.py",
    "invert3.py",
    "two_two.py",
    "rho_exact.py",
    "four_exact.py",
    "four_inverse.py",
    "two_one_one_gb.py",
    "two_one_one_roots.py",
    "certify_singleton_n4.py",
]

def run(name: str) -> tuple[bool, float]:
    path = PROOFS / name
    t0 = time.perf_counter()
    p = subprocess.run([sys.executable, path.name], cwd=PROOFS, text=True)
    dt = time.perf_counter() - t0
    return p.returncode == 0, dt

if __name__ == "__main__":
    ok = True
    print("P1 deterministic verification")
    print("=" * 72)
    for name in SCRIPTS:
        passed, dt = run(name)
        ok &= passed
        print(f"{name:<30} {'PASS' if passed else 'FAIL':<5}  {dt:8.2f}s")
    print("=" * 72)
    print("VERIFY:", "PASS" if ok else "FAIL")
    raise SystemExit(0 if ok else 1)
