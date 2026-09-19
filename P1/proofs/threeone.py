# (3,1): quartic selection of the two size-3 DS directions on the atom-free stratum,
# then the closed-form atom-residual closure of the singleton confounding direction.
import itertools, numpy as np
rng = np.random.default_rng(12)
PATS3 = [p for p in itertools.product([1,-1],repeat=3)]
N3 = [p for p in PATS3 if abs(sum(p))!=3]                 # 6 non-unanimous patterns
U3 = [(1,1,1),(-1,-1,-1)]

def blockA(q, eta, z):
    pro  = np.prod([q[i] if z[i]==1 else 1-q[i] for i in range(3)])
    proF = np.prod([1-q[i] if z[i]==1 else q[i] for i in range(3)])
    return (1-eta)*pro + eta*proF

def atomA(eta, z, sign):                                   # sign=+1 -> A+, -1 -> A-
    if z == (1,1,1):   return (1-eta) if sign>0 else eta
    if z == (-1,-1,-1):return eta if sign>0 else (1-eta)
    return 0.0

def full_law(c, qA, etaA, pB, S, etaB):
    """c=(c+,c-), qA=[q+ (3), q- (3)], pB=(p+,p-), S=(S+,S-)."""
    P = {}
    for z in PATS3:
        for x in (1,-1):
            v = 0.0
            for h in range(2):
                v += c[h]*blockA(qA[h], etaA, z)*(pB[h] if x==1 else 1-pB[h])
            for si,sign in enumerate([1,-1]):
                pb = (1-etaB) if (x==1)==(sign>0) else etaB
                v += S[si]*atomA(etaA, z, sign)*pb
            P[(z,x)] = v
    return P

def sk_dk(a):                                              # a: dict over N3
    zk = [(-1,1,1),(1,-1,1),(1,1,-1)]
    s = np.array([a[z]+a[tuple(-t for t in z)] for z in zk])
    d = np.array([a[z]-a[tuple(-t for t in z)] for z in zk])
    return s, d

def H(vec):                                                # quartic invariant
    a = {z: vec[i] for i,z in enumerate(N3)}
    s,d = sk_dk(a)
    return (d[0]**2-d[1]**2)*(s[0]**2-s[2]**2) - (d[0]**2-d[2]**2)*(s[0]**2-s[1]**2)

def invert3(vec):                                          # scale-invariant (q, eta)
    a = {z: vec[i] for i,z in enumerate(N3)}
    s,d = sk_dk(a)
    best=None
    for k in range(3):
        for l in range(k+1,3):
            den=s[k]**2-s[l]**2
            if abs(den)>1e-14 and (best is None or abs(den)>best[1]):
                best=((d[k]**2-d[l]**2)/den, abs(den))
    if best is None or best[0]<=0: return None
    r=np.sqrt(best[0])
    if not (0<r<1): return None
    u=s-d/r; v=s+d/r
    if np.any(u==0): return None
    C=u[0]*v[0]
    if abs(C)<1e-18: return None
    A=u[0]*u[1]*u[2]/(2*C)
    o=u/(2*A)
    if np.any(o<=0): return None
    q=o/(1+o)
    return q, (1-r)/2

ok=0; trials=50; roots_real=[]; feas_pairs=[]; errs=[]
for _ in range(trials):
    c = rng.dirichlet([3,3])*rng.uniform(0.4,0.7)
    qA = [rng.uniform(0.6,0.95,3), rng.uniform(0.05,0.4,3)]
    etaA = rng.uniform(0.05,0.3); etaB = rng.uniform(0.05,0.3)
    qB = [rng.uniform(0.6,0.95), rng.uniform(0.05,0.4)]
    pB = [etaB+(1-2*etaB)*qB[0], etaB+(1-2*etaB)*qB[1]]
    Sp = rng.uniform(0.1,0.3); Sm = 1-c.sum()-Sp
    if Sm<=0.05: continue
    P = full_law(c, qA, etaA, pB, (Sp,Sm), etaB)
    # atom-free 6x2 matrix
    M = np.array([[P[(z,x)] for x in (1,-1)] for z in N3])
    Uu,sv,Vt = np.linalg.svd(M); L = Uu[:,:2]
    # quartic in t along a(t) = L0 + t L1  (plus the point at infinity)
    ts = np.linspace(-3,3,9); vals=[H(L[:,0]+t*L[:,1]) for t in ts]
    coef = np.polyfit(ts, vals, 4); rts = np.roots(coef)
    real = [t.real for t in rts if abs(t.imag)<1e-7*max(1,abs(t.real))]
    roots_real.append(len(real))
    cands=[]
    for t in real:
        vec = L[:,0]+t*L[:,1]
        for sgn in (1,-1):                                  # fix overall sign to positive
            w = sgn*vec
            if np.all(w>0):
                out = invert3(w/np.sum(w))
                if out is not None: cands.append((w/np.sum(w), out))
    pairs=[]
    for i in range(len(cands)):
        for j in range(len(cands)):
            if i==j: continue
            (a1,(q1,e1)),(a2,(q2,e2)) = cands[i],cands[j]
            if np.all(q1>0.5) and np.all(q2<0.5) and abs(e1-e2)<1e-6:
                pairs.append((i,j,e1))
    feas_pairs.append(len(pairs))
    if len(pairs)!=1: continue
    i,j,etaA_hat = pairs[0]
    aP, aM = cands[i][0], cands[j][0]
    qA_hat = [cands[i][1][0], cands[j][1][0]]
    # scale/pair with side B by least squares on the atom-free matrix
    B = np.linalg.pinv(np.column_stack([aP,aM])) @ M           # rows: kappa_h*(p_h, 1-p_h)
    kappa = B.sum(axis=1); p_hat = B[:,0]/kappa
    # aP, aM were normalised to sum 1 on N3, so kappa_h = c_h * (DS_h mass on N3)
    massN = [sum(blockA(qA_hat[h], etaA_hat, z) for z in N3) for h in range(2)]
    c_hat = np.array([kappa[h]/massN[h] for h in range(2)])
    # subtract the DS part from the full law -> atom residual
    res = {}
    for z in PATS3:
        for x in (1,-1):
            ds = sum(c_hat[h]*blockA(qA_hat[h], etaA_hat, z)*(p_hat[h] if x==1 else 1-p_hat[h])
                     for h in range(2))
            res[(z,x)] = P[(z,x)] - ds
    tot = sum(res[(z,x)] for z in U3 for x in (1,-1))
    EA  = sum(res[(z,x)]*(1 if z==(1,1,1) else -1) for z in U3 for x in (1,-1))/tot
    EB  = sum(res[(z,x)]*x for z in U3 for x in (1,-1))/tot
    EAB = sum(res[(z,x)]*(1 if z==(1,1,1) else -1)*x for z in U3 for x in (1,-1))/tot
    rA = 1-2*etaA_hat; rB = EAB/rA; etaB_hat = (1-rB)/2
    mu = EA/rA; Sp_hat, Sm_hat = tot*(1+mu)/2, tot*(1-mu)/2
    qB_hat = [(p_hat[h]-etaB_hat)/(1-2*etaB_hat) for h in range(2)]
    err = max(abs(etaA_hat-etaA), abs(etaB_hat-etaB), abs(Sp_hat-Sp), abs(Sm_hat-Sm),
              abs(c_hat[0]-c[0]), abs(c_hat[1]-c[1]),
              np.max(np.abs(qA_hat[0]-qA[0])), np.max(np.abs(qA_hat[1]-qA[1])),
              abs(qB_hat[0]-qB[0]), abs(qB_hat[1]-qB[1]))
    errs.append(err); ok+=1
errs=np.array(errs)
print(f"(3,1): {ok}/{trials} instances fully recovered")
print("   real quartic roots per instance:", dict(zip(*np.unique(roots_real, return_counts=True))))
print("   feasible oriented pairs sharing eta_A:", dict(zip(*np.unique(feas_pairs, return_counts=True))))
print("   full-parameter error: median %.2e  90th %.2e  max %.2e" %
      (np.median(errs), np.percentile(errs,90), errs.max()))