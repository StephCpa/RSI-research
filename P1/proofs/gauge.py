"""REGRESSION TEST for the Z2 gauge lemma (the lemma itself is proved analytically:
K_{1-eta}(1-q; x) = K_eta(q; x) because P_{1-q}(x) = P_q(-x), and complementing eta swaps
the two atom components, which swapping S+ and S- undoes).

Checks that eta_tau -> 1 - eta_tau, c_+ <-> c_-, q_{+,v} -> 1 - q_{-,v}, S_+ <-> S_-
leaves the reported law unchanged, and that the map preserves the orientation condition
q_+ > 1/2 > q_- -- so orientation cannot fix the gauge; only the chamber r_tau > 0 does."""
import itertools, numpy as np

def law(part, c, q, eta, S):
    n = sum(part); idx = []; s = 0
    for m in part: idx.append(list(range(s, s+m))); s += m
    P = {}
    for x in itertools.product([1,-1], repeat=n):
        v = 0.0
        for h in range(2):                                    # DS components
            comp = c[h]
            for b, cols in enumerate(idx):
                pro  = np.prod([q[h][i] if x[i]==1 else 1-q[h][i] for i in cols])
                proF = np.prod([1-q[h][i] if x[i]==1 else q[h][i] for i in cols])
                comp *= (1-eta[b])*pro + eta[b]*proF
            v += comp
        for si, sg in enumerate([1,-1]):                      # atom components
            comp = S[si]
            for b, cols in enumerate(idx):
                allp = all(x[i]==1 for i in cols); alln = all(x[i]==-1 for i in cols)
                if sg > 0: f = (1-eta[b]) if allp else (eta[b] if alln else 0.0)
                else:      f = (1-eta[b]) if alln else (eta[b] if allp else 0.0)
                comp *= f
            v += comp
        P[x] = v
    return P

rng = np.random.default_rng(3)
print("partition   max |P - P_dagger|   orientation preserved?   eta_dagger < 1/2 ?")
for part in [(1,1,1,1),(2,1,1),(2,2),(3,1),(4,),(3,1,1),(1,1,1,1,1)]:
    n = sum(part); T = len(part)
    c = rng.dirichlet([3,3])*0.6
    q = [rng.uniform(0.55,0.95,n), rng.uniform(0.05,0.45,n)]
    eta = rng.uniform(0.05,0.45,T); S = [0.2, 1-c.sum()-0.2]
    P = law(part, c, q, eta, S)
    cd = [c[1], c[0]]; qd = [1-q[1], 1-q[0]]; ed = 1-eta; Sd = [S[1], S[0]]
    Pd = law(part, cd, qd, ed, Sd)
    err = max(abs(P[x]-Pd[x]) for x in P)
    orient = bool(np.all(qd[0] > 0.5) and np.all(qd[1] < 0.5))
    print(f"{str(part):<12} {err:.2e}              {orient!s:<20}   {bool(np.all(ed<0.5))}")

# --- is the Z2 global, i.e. do per-block flips fail to be symmetries? -----------
print("\nper-block flip (flip eta on ONE check, complement that block's q, swap components):")
for part in [(2,1,1),(2,2),(3,1)]:
    n=sum(part); T=len(part); idx=[]; s=0
    for m in part: idx.append(list(range(s,s+m))); s+=m
    c=rng.dirichlet([3,3])*0.6
    q=[rng.uniform(0.55,0.95,n), rng.uniform(0.05,0.45,n)]
    eta=rng.uniform(0.05,0.45,T); S=[0.2, 1-c.sum()-0.2]
    P=law(part,c,q,eta,S)
    worst=0
    for b in range(T):
        ed=eta.copy(); ed[b]=1-eta[b]
        qd=[q[1].copy(), q[0].copy()]
        for i in idx[b]:
            qd[0][i]=1-q[1][i]; qd[1][i]=1-q[0][i]     # complement only inside block b
        Pd=law(part,[c[1],c[0]],qd,ed,[S[1],S[0]])
        worst=max(worst, max(abs(P[x]-Pd[x]) for x in P))
    print(f"   {str(part):<10} max |P - P_flip| over single-block flips: {worst:.3e}")