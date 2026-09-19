# (3,1) without the quartic: recover rho = (1-2 eta_A)^2 directly from the cross-product
# system (a - rho b) x (c - rho d) = 0, then the two component rays as roots of A - rho B.
# Also: do the spurious quartic roots survive positivity + orientation?
import itertools, numpy as np
exec(open('threeone.py').read().split("ok=0; trials=50")[0])   # PATS3, N3, blockA, full_law, sk_dk, H, invert3

def lin_funcs(L):
    """s_k, d_k as linear forms on (lambda, mu); returns 3x2 arrays."""
    zk = [(-1,1,1),(1,-1,1),(1,1,-1)]
    idx = {z:i for i,z in enumerate(N3)}
    S = np.zeros((3,2)); D = np.zeros((3,2))
    for k,z in enumerate(zk):
        zp, zm = idx[z], idx[tuple(-t for t in z)]
        for j in range(2):
            S[k,j] = L[zp,j] + L[zm,j]
            D[k,j] = L[zp,j] - L[zm,j]
    return S, D

def quad_coef(f, g):
    """coefficients (lam^2, lam*mu, mu^2) of f^2 - g^2 where f,g are linear forms."""
    return np.array([f[0]**2-g[0]**2, 2*(f[0]*f[1]-g[0]*g[1]), f[1]**2-g[1]**2])

def rho_candidates(L):
    S, D = lin_funcs(L)
    A = quad_coef(D[0], D[1]); B = quad_coef(S[0], S[1])
    C = quad_coef(D[0], D[2]); Dd = quad_coef(S[0], S[2])
    # cross product of (A - rho B) and (C - rho Dd): three quadratics in rho
    polys = []
    for (i,j) in [(1,2),(2,0),(0,1)]:
        # (A_i - rho B_i)(C_j - rho D_j) - (A_j - rho B_j)(C_i - rho D_i)
        p2 = B[i]*Dd[j] - B[j]*Dd[i]
        p1 = -(A[i]*Dd[j] + B[i]*C[j]) + (A[j]*Dd[i] + B[j]*C[i])
        p0 = A[i]*C[j] - A[j]*C[i]
        polys.append(np.array([p2,p1,p0]))
    # common roots
    cands = []
    for p in polys:
        if np.max(np.abs(p)) < 1e-14: continue
        for r in np.roots(p/np.max(np.abs(p))):
            if abs(r.imag) < 1e-8: cands.append(r.real)
    keep = []
    for r in cands:
        if 0 < r < 1 and all(abs(np.polyval(p, r)) < 1e-9*max(1,np.max(np.abs(p))) for p in polys):
            if not any(abs(r-k) < 1e-6 for k in keep): keep.append(r)
    return keep, (A,B,C,Dd)

def rays(L, rho, A, B):
    p = A - rho*B                     # binary quadratic in (lambda, mu)
    rts = np.roots(p) if abs(p[0])>1e-14 else [np.inf]
    out = []
    for t in rts:
        vec = L[:,0]*t + L[:,1] if np.isfinite(t) else L[:,0]
        out.append(vec.real)
    return out

rng = np.random.default_rng(21)
errs=[]; nrho=[]; spurious_pass=0; spurious_tot=0
for _ in range(300):
    c = rng.dirichlet([3,3])*rng.uniform(0.4,0.7)
    qA = [rng.uniform(0.6,0.95,3), rng.uniform(0.05,0.4,3)]
    etaA = rng.uniform(0.05,0.3); etaB = rng.uniform(0.05,0.3)
    qB = [rng.uniform(0.6,0.95), rng.uniform(0.05,0.4)]
    pB = [etaB+(1-2*etaB)*qB[0], etaB+(1-2*etaB)*qB[1]]
    Sp = rng.uniform(0.1,0.3); Sm = 1-c.sum()-Sp
    if Sm <= 0.05: continue
    P = full_law(c, qA, etaA, pB, (Sp,Sm), etaB)
    M = np.array([[P[(z,x)] for x in (1,-1)] for z in N3])
    L = np.linalg.svd(M)[0][:,:2]
    keep, (A,B,C,Dd) = rho_candidates(L)
    nrho.append(len(keep))
    if len(keep)==1:
        eta_hat = (1-np.sqrt(keep[0]))/2
        errs.append(abs(eta_hat-etaA))
    # do the spurious quartic roots survive positivity + orientation?
    ts = np.linspace(-3,3,9); vals=[H(L[:,0]+t*L[:,1]) for t in ts]
    for t in np.roots(np.polyfit(ts, vals, 4)):
        if abs(t.imag) > 1e-7: continue
        vec = L[:,0]+t.real*L[:,1]
        for sgn in (1,-1):
            w = sgn*vec
            if np.all(w > 0):
                out = invert3(w/w.sum())
                if out is None: continue
                q, e = out
                oriented = np.all(q>0.5) or np.all(q<0.5)
                true_dir = min(np.max(np.abs(w/w.sum() - np.array([c[h]*blockA(qA[h],etaA,z) for z in N3])/
                                             sum(c[h]*blockA(qA[h],etaA,z) for z in N3))) for h in range(2))
                if true_dir > 1e-6:                      # a spurious root
                    spurious_tot += 1
                    if oriented: spurious_pass += 1
print("rho route: number of common rho in (0,1) per instance:",
      dict(zip(*np.unique(nrho, return_counts=True))))
print("           |eta_A_hat - eta_A| : median %.2e, max %.2e" % (np.median(errs), np.max(errs)))
print(f"spurious quartic roots that are positive: {spurious_tot}; "
      f"of these, passing the all-q-one-side orientation test: {spurious_pass}")