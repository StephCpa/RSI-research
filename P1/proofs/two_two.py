# Constructive recovery for the (2,2) block-corrupted model:
# structural zeros -> rank-2 completion -> atom-channel moments -> deconvolution -> Kruskal.
import itertools, numpy as np
rng = np.random.default_rng(3)
S = [(1,1),(1,-1),(-1,1),(-1,-1)]          # block states, index 0..3
M = [1,2]                                   # mixed states (+-, -+)
U = [0,3]                                   # unanimous states (++, --)

def block_law(q, eta, comp):
    """P(block state | component): comp='ds' uses q=(q_a,q_b); 'A+'/'A-' are atoms."""
    v = np.zeros(4)
    for i,(x,y) in enumerate(S):
        if comp == 'ds':
            pro  = (q[0] if x==1 else 1-q[0])*(q[1] if y==1 else 1-q[1])
            proF = (1-q[0] if x==1 else q[0])*(1-q[1] if y==1 else q[1])
            v[i] = (1-eta)*pro + eta*proF
        elif comp == 'A+':
            v[i] = (1-eta) if (x,y)==(1,1) else (eta if (x,y)==(-1,-1) else 0.0)
        else:
            v[i] = (1-eta) if (x,y)==(-1,-1) else (eta if (x,y)==(1,1) else 0.0)
    return v

def make_law(w, qA, qB, eta):
    """w = (w_DS+, w_DS-, S+, S-); qA/qB are 2x2: rows = DS+/DS-, cols = the two views."""
    P = np.zeros((4,4))
    P += w[0]*np.outer(block_law(qA[0], eta[0],'ds'), block_law(qB[0], eta[1],'ds'))
    P += w[1]*np.outer(block_law(qA[1], eta[0],'ds'), block_law(qB[1], eta[1],'ds'))
    P += w[2]*np.outer(block_law(None, eta[0],'A+'), block_law(None, eta[1],'A+'))
    P += w[3]*np.outer(block_law(None, eta[0],'A-'), block_law(None, eta[1],'A-'))
    return P

def recover(P):
    # step 1: structural zeros + rank-2 completion
    R = np.zeros((4,4))
    R[np.ix_(M,M)] = P[np.ix_(M,M)]; R[np.ix_(M,U)] = P[np.ix_(M,U)]; R[np.ix_(U,M)] = P[np.ix_(U,M)]
    R[np.ix_(U,U)] = R[np.ix_(U,M)] @ np.linalg.inv(R[np.ix_(M,M)]) @ R[np.ix_(M,U)]
    # step 2: atom residual moments
    Q = P - R
    a = Q[np.ix_(U,U)].sum(); Qn = Q[np.ix_(U,U)]/a
    xs = np.array([1.0,-1.0])                       # U = [++, --] -> X = +1,-1
    mA = (Qn.sum(axis=1)*xs).sum(); mB = (Qn.sum(axis=0)*xs).sum()
    c  = sum(Qn[i,j]*xs[i]*xs[j] for i in range(2) for j in range(2))
    mu = np.sign(mA)*np.sqrt(mA*mB/c)
    rA, rB = mA/mu, mB/mu
    etaA, etaB = (1-rA)/2, (1-rB)/2
    Sp, Sm = a*(1+mu)/2, a*(1-mu)/2
    # step 3: deconvolve, then Kruskal on 2 x 2 x (2x2)
    F = np.zeros((4,4))
    for i,s in enumerate(S): F[i, S.index((-s[0],-s[1]))] = 1
    LA = (1-etaA)*np.eye(4) + etaA*F
    LB = (1-etaB)*np.eye(4) + etaB*F
    Rstar = np.linalg.inv(LA) @ R @ np.linalg.inv(LB).T
    # Rstar = sum_h w_h  a_h  b_h^T with a_h, b_h product distributions over two binary views
    Uu, sv, Vt = np.linalg.svd(Rstar)
    # rank-2: recover the two rank-1 terms by solving for the mixture (2 components, product form)
    # use the four-view product structure: marginal of view1 given component etc. via CP on 2x2x4
    # simple route: Rstar has rank 2; its column space is spanned by a_+, a_-.  Use the
    # product constraint a(x,y) = f(x)g(y) to pin the two directions.
    Bs = Uu[:, :2]                                   # column space of Rstar
    u, wv = Bs[:,0], Bs[:,1]
    # a vector v = u + s*wv is a product distribution iff v0*v3 - v1*v2 = 0 (homogeneous)
    A2 = wv[0]*wv[3] - wv[1]*wv[2]
    B2 = u[0]*wv[3] + wv[0]*u[3] - u[1]*wv[2] - wv[1]*u[2]
    C2 = u[0]*u[3] - u[1]*u[2]
    disc = B2*B2 - 4*A2*C2
    roots = [(-B2+np.sqrt(disc))/(2*A2), (-B2-np.sqrt(disc))/(2*A2)]
    qA_rec = []
    for s_ in roots:
        v = u + s_*wv
        v = v/v.sum()
        qA_rec.append((v[0]+v[1], v[0]+v[2]))       # marginals P(view = +1)
    # orientation on side A fixes the +/- labels
    order = sorted(range(2), key=lambda i: -(qA_rec[i][0]+qA_rec[i][1]))
    aplus  = (u + roots[order[0]]*wv); aplus  = aplus/aplus.sum()
    aminus = (u + roots[order[1]]*wv); aminus = aminus/aminus.sum()
    qA_ord = [qA_rec[order[0]], qA_rec[order[1]]]
    # left inverse pairs side B automatically:  Rstar = A diag(c) B^T
    Amat = np.column_stack([aplus, aminus])
    C = np.linalg.pinv(Amat) @ Rstar                 # rows = c_h * b_h^T
    c = C.sum(axis=1)
    b = [C[h]/c[h] for h in range(2)]
    qB_ord = [(bh[0]+bh[1], bh[0]+bh[2]) for bh in b]
    return dict(etaA=etaA, etaB=etaB, Sp=Sp, Sm=Sm, qA=qA_ord, qB=qB_ord, c=c)

# ---- test on random interior parameters
errs = []
for _ in range(500):
    w = rng.dirichlet([3,3,3,3])
    qA = [rng.uniform(0.6,0.95,2), rng.uniform(0.05,0.4,2)]
    qB = [rng.uniform(0.6,0.95,2), rng.uniform(0.05,0.4,2)]
    eta = rng.uniform(0.03,0.3,2)
    P = make_law(w,qA,qB,eta)
    r = recover(P)
    e = max(abs(r['etaA']-eta[0]), abs(r['etaB']-eta[1]), abs(r['Sp']-w[2]), abs(r['Sm']-w[3]),
            abs(r['c'][0]-w[0]), abs(r['c'][1]-w[1]),
            max(abs(r['qA'][h][k]-qA[h][k]) for h in range(2) for k in range(2)),
            max(abs(r['qB'][h][k]-qB[h][k]) for h in range(2) for k in range(2)))
    errs.append(e)
errs=np.array(errs)
print("(2,2) full constructive inverse (eta, S+-, c+-, qA, qB), 500 random interior points:")
print("   median error %.2e   90th pct %.2e   max %.2e" % (np.median(errs), np.percentile(errs,90), errs.max()))