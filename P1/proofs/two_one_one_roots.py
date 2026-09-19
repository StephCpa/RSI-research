"""Which candidate eta_B roots lift to a genuine feasible solution?
(numeric lift, with the basis determinant checked — that is where the extraneous roots live)"""
import sympy as sp, numpy as np
from sympy import Rational as R
from two_one_one_model import build

d = build(); eB, eC = d['eB'], d['eC']; F = d['F']; P = d['P']; G = d['G']
Gn = [np.array(sp.Matrix(G[h]).evalf(), dtype=float) for h in range(2)]
Kn = [float(k) for k in d['K']]; Yn = [float(y) for y in d['Y']]
ZA = [(1,1),(1,-1),(-1,1),(-1,-1)]
Pn = {(za,xb,xc): float(P(za,xb,xc)) for za in ZA for xb in (1,-1) for xc in (1,-1)}

def analyse(eb, ec):
    Hp = np.outer([1-eb,eb],[1-ec,ec]); Hm = Hp[::-1,::-1]
    Bm = np.column_stack([Gn[0].reshape(4), Gn[1].reshape(4), Hp.reshape(4), Hm.reshape(4)])
    det = np.linalg.det(Bm)
    if abs(det) < 1e-10: return dict(det=det, feasible=False, note="basis degenerate")
    ap = np.linalg.solve(Bm, np.array([Pn[((1,1),xb,xc)] for xb in (1,-1) for xc in (1,-1)]))
    am = np.linalg.solve(Bm, np.array([Pn[((-1,-1),xb,xc)] for xb in (1,-1) for xc in (1,-1)]))
    Sp, Sm = ap[2]+am[2], ap[3]+am[3]
    if min(abs(Sp), abs(Sm)) < 1e-12: return dict(det=det, feasible=False, note="zero atom mass")
    etaA = am[2]/Sp; rA = 1-2*etaA; ok = 0 < etaA < 0.5 and Sp > 0 and Sm > 0
    for h in range(2):
        ch = Kn[h] + ap[h] + am[h]; X = ap[h] - am[h]
        if ch <= 0: ok = False; continue
        q1 = 0.5*(1+(X+Yn[h])/(ch*rA)); q2 = 0.5*(1+(X-Yn[h])/(ch*rA))
        if not (0 < q1 < 1 and 0 < q2 < 1): ok = False
    return dict(det=det, etaA=etaA, S=(Sp,Sm), feasible=ok)

if __name__ == "__main__":
    for cand in [R(1,8), R(7,24), sp.Rational(1,2) - 3*sp.sqrt(551203)/11288]:
        cf = float(cand); print(f"\ncandidate eta_B = {sp.nsimplify(cand)} (~{cf:.5f})")
        f0 = sp.Poly(sp.expand(F[0].subs(eB, cand)), eC)
        for s in sp.solve(sp.Eq(f0.as_expr(), 0), eC):
            if not sp.im(s).is_zero: continue
            sv = float(s)
            if not (0 < sv < 0.5): print(f"   eta_C = {sv:.5f}: outside (0,1/2)"); continue
            info = analyse(cf, sv)
            print(f"   eta_C = {sv:.5f}: det(basis) = {info['det']:.2e} -> "
                  f"{info.get('note','')} feasible={info['feasible']}")