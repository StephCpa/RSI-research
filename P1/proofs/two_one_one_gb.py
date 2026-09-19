"""Literal saturation certificate for (2,1,1):  <F0,F+,F-> : (det B)^inf
via the Rabinowitsch trick  w*det(B) = 1, with a lex Groebner basis."""
import sympy as sp
from two_one_one_model import build

d = build(); eB, eC = d['eB'], d['eC']; w = sp.symbols('w')
gens = d['F'] + [w*d['detB'] - 1]
G = sp.groebner(gens, w, eC, eB, order='lex')
print("saturated ideal, lex Groebner basis in (w, eC, eB):")
for g in G.exprs:
    print("   ", sp.factor(sp.simplify(g)))
elim = [g for g in G.exprs if not g.free_symbols & {w, eC}]
print("\neliminant in eB:", [sp.factor(e) for e in elim])
for e in elim:
    rts = sp.roots(sp.Poly(e, eB))
    print("   roots:", {sp.nsimplify(k): v for k, v in rts.items()},
          "   feasible in (0,1/2):", [r for r in rts if r.is_real and 0 < r < sp.Rational(1,2)])
print("\ntrue (eta_B, eta_C) =", d['truth'])