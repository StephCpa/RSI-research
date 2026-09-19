"""Rank and conditioning of the (3,1,1) model at generic vs exchangeable within-block accuracies."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
from blocks import make

law, d, n, T = make((3,1,1))
def rank_at(q1_block, q2_block, seed=0):
    r = np.random.default_rng(seed)
    t = np.concatenate([r.uniform(-1,1,3),
                        np.array(list(q1_block)+[0.8,0.75]),
                        np.array(list(q2_block)+[0.25,0.3]),
                        r.uniform(0.05,0.25,T)])
    eps = 1e-6; J = []
    for i in range(len(t)):
        e = np.zeros(len(t)); e[i] = eps
        J.append((law(t+e) - law(t-e))/(2*eps))
    s = np.linalg.svd(np.array(J).T, compute_uv=False)
    return int(np.sum(s > 1e-9*s[0])), s[len(t)-1]/s[0]

if __name__ == "__main__":
    print("d =", d)
    print("generic q inside the 3-block:      rank %d, smin/smax %.2e" % rank_at((0.9,0.75,0.65),(0.2,0.35,0.28), 1))
    print("exchangeable q inside the 3-block: rank %d, smin/smax %.2e" % rank_at((0.8,0.8,0.8),(0.25,0.25,0.25), 2))
    print("exchangeable in DS+ only:          rank %d, smin/smax %.2e" % rank_at((0.8,0.8,0.8),(0.2,0.35,0.28), 3))