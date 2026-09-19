# Identification phase diagram over relation-error block structures.
# Blocks tau = 1..T with sizes m_tau (sum = n); one relation bit E_tau flips every view
# in its block.  Parameters: 3 free weights, per-view q1_v, q2_v (underlying P(W*=+1)
# for the two DS components), and one eta_tau per block:  d = 3 + 2n + T.
import itertools, numpy as np
from scipy.optimize import least_squares

def make(part):
    n = sum(part); T = len(part)
    idx = []; s = 0
    for m in part: idx.append(list(range(s, s+m))); s += m
    PAT = np.array(list(itertools.product([1,-1], repeat=n)))
    def law(t):
        z = np.concatenate([t[:3],[0.0]]); w = np.exp(z-z.max()); w = w/w.sum()
        q1, q2, eta = t[3:3+n], t[3+n:3+2*n], t[3+2*n:3+2*n+T]
        out = np.zeros(len(PAT))
        for h in range(4):
            comp = np.ones(len(PAT))
            for b, cols in enumerate(idx):
                e = eta[b]
                if h == 0:   pv = q1[cols]
                elif h == 1: pv = q2[cols]
                elif h == 2: pv = np.ones(len(cols))      # atom+: W* = +1
                else:        pv = np.zeros(len(cols))     # atom-: W* = -1
                Z = PAT[:, cols]
                pro  = np.prod(np.where(Z==1, pv, 1-pv), axis=1)      # E_tau = 0
                proF = np.prod(np.where(Z==-1, pv, 1-pv), axis=1)     # E_tau = 1 (all flipped)
                comp *= (1-e)*pro + e*proF
            out += w[h]*comp
        return out[:-1]
    d = 3+2*n+T
    return law, d, n, T

def rank_check(part, rng, trials):
    law, d, n, T = make(part)
    rk = []
    for _ in range(trials):
        t = np.concatenate([rng.uniform(-1,1,3), rng.uniform(0.6,0.95,n),
                            rng.uniform(0.05,0.4,n), rng.uniform(0.03,0.25,T)])
        eps=1e-6; J=[]
        for i in range(len(t)):
            e=np.zeros(len(t)); e[i]=eps
            J.append((law(t+e)-law(t-e))/(2*eps))
        s=np.linalg.svd(np.array(J).T, compute_uv=False)
        rk.append(int(np.sum(s > 1e-9*s[0])))
    return d, 2**n-1, min(rk), max(rk)

def global_scan(part, rng, truths, starts):
    law, d, n, T = make(part)
    lo = np.concatenate([[-6.]*3, [0.5001]*n, [1e-4]*n, [1e-4]*T])
    hi = np.concatenate([[ 6.]*3, [0.9999]*n, [0.4999]*n, [0.4999]*T])
    rand = lambda: np.concatenate([rng.uniform(-1,1,3), rng.uniform(0.6,0.95,n),
                                   rng.uniform(0.05,0.4,n), rng.uniform(0.03,0.25,T)])
    def canon(t):
        z=np.concatenate([t[:3],[0.0]]); w=np.exp(z-z.max()); w=w/w.sum()
        return np.concatenate([w, t[3:]])
    multi=0; counts=[]
    for _ in range(truths):
        truth=rand(); target=law(truth); reps=[]
        for _ in range(starts):
            t0=np.clip(rand(),lo,hi)
            r=least_squares(lambda t: law(t)-target, t0, bounds=(lo,hi),
                            xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=6000)
            if np.max(np.abs(r.fun))<1e-12 and np.all(r.x[3:]>lo[3:]+1e-5) and np.all(r.x[3:]<hi[3:]-1e-5):
                c=canon(r.x)
                if c.min()>1e-3 and not any(np.max(np.abs(c-y))<1e-4 for y in reps): reps.append(c)
        counts.append(len(reps));  multi += (len(reps)>1)
    return multi, counts


if __name__ == "__main__":
    import sys
    rng = np.random.default_rng(42)
    print("demo: singleton partition at n=4, small budget")
    print(rank_check((1,1,1,1), rng, trials=3), global_scan((1,1,1,1), rng, truths=2, starts=20))