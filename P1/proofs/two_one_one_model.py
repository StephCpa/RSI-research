"""Exact (2,1,1) witness model and the three reduction equations F0, F+, F-.

Importable: `from two_one_one_model import build` returns everything the
elimination scripts need, with no exec() and no dependence on the working directory.
"""
import sympy as sp
from sympy import Rational as R

ZA = [(1,1),(1,-1),(-1,1),(-1,-1)]

def build(c=(R(1,5), R(1,4)),
          qp=(R(3,4), R(4,5), R(5,6), R(7,10)),
          qm=(R(1,5), R(3,10), R(2,9), R(1,4)),
          etaA=R(1,10), etaB0=R(1,8), etaC0=R(1,6), Sp=R(1,5)):
    q = [list(qp), list(qm)]; Sm = 1 - c[0] - c[1] - Sp
    def PA(h, za):
        pro  = (q[h][0] if za[0]==1 else 1-q[h][0])*(q[h][1] if za[1]==1 else 1-q[h][1])
        proF = (1-q[h][0] if za[0]==1 else q[h][0])*(1-q[h][1] if za[1]==1 else q[h][1])
        return (1-etaA)*pro + etaA*proF
    pB = [etaB0 + (1-2*etaB0)*q[h][2] for h in range(2)]
    pC = [etaC0 + (1-2*etaC0)*q[h][3] for h in range(2)]
    def P(za, xb, xc):
        v = 0
        for h in range(2):
            v += c[h]*PA(h,za)*(pB[h] if xb==1 else 1-pB[h])*(pC[h] if xc==1 else 1-pC[h])
        for si, sg in enumerate([1,-1]):
            pa = ((1-etaA) if za==(1,1) else etaA if za==(-1,-1) else 0) if sg>0 else \
                 ((1-etaA) if za==(-1,-1) else etaA if za==(1,1) else 0)
            bB = (1-etaB0) if (xb==1)==(sg>0) else etaB0
            bC = (1-etaC0) if (xc==1)==(sg>0) else etaC0
            v += [Sp, Sm][si]*pa*bB*bC
        return v
    # identified from the mixed-block stratum (the Kruskal step)
    G = [sp.Matrix([[pB[h]*pC[h], pB[h]*(1-pC[h])],
                    [(1-pB[h])*pC[h], (1-pB[h])*(1-pC[h])]]) for h in range(2)]
    t = [[c[h]*PA(h,(1,-1)), c[h]*PA(h,(-1,1))] for h in range(2)]
    K = [t[h][0]+t[h][1] for h in range(2)]; Y = [t[h][0]-t[h][1] for h in range(2)]
    eB, eC = sp.symbols('eB eC')
    Hp = sp.Matrix([[(1-eB)*(1-eC), (1-eB)*eC], [eB*(1-eC), eB*eC]])
    Hm = sp.Matrix([[eB*eC, eB*(1-eC)], [(1-eB)*eC, (1-eB)*(1-eC)]])
    B  = sp.Matrix.hstack(*[sp.Matrix(4,1,list(M)) for M in [G[0], G[1], Hp, Hm]])
    def coeffs(za):
        rhs = sp.Matrix(4,1,[P(za,xb,xc) for xb in (1,-1) for xc in (1,-1)])
        return sp.simplify(B.solve(rhs))
    ap, am = coeffs((1,1)), coeffs((-1,-1))
    lpp, lmp, lpm, lmm = ap[2], ap[3], am[2], am[3]
    E0 = sp.together(lpm/(lpp+lpm) - lmp/(lmp+lmm))
    rA = 1 - 2*lpm/(lpp+lpm)
    eqs = [sp.numer(sp.cancel(E0))]
    for h in range(2):
        ch = K[h] + ap[h] + am[h]; X = ap[h] - am[h]
        eqs.append(sp.numer(sp.cancel(sp.together(X**2 - Y[h]**2 - rA**2*ch*(ch - 2*K[h])))))
    return dict(eB=eB, eC=eC, F=[sp.expand(e) for e in eqs], detB=sp.expand(B.det()),
                truth=(etaB0, etaC0), P=P, G=G, K=K, Y=Y)