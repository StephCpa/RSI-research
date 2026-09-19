"""
Standalone certificate: the corrupted-model map F at n = 4 is globally non-identifiable
on a nonempty open set.

This file is a PROOF ARTIFACT, not a discovery script.  It depends on no search, no
random seed, no saved .npy/.pkl file, and no SciPy.  Everything it needs is hardcoded:

    theta1   exact rational parameter point (an exact root of F(theta) = p by definition of p)
    p        the exact rational target, computed from theta1 with Fraction arithmetic
    y        an exact rational box center (a truncated 32-digit decimal).  y is NOT
             asserted to be a root: F(y) != p is expected and harmless.  The Krawczyk
             test certifies that a unique exact root theta2 of F(theta) = p lies in the
             box X = y +/- rad.
    rad      the exact rational box radius 10^-6

It checks, in this order:

    (C1) theta1 lies strictly inside the parameter domain            [exact rational]
    (C2) det J(theta1) != 0                                          [exact rational]
    (C3) every point of the box X = y +/- rad lies in the domain     [exact rational]
    (C4) ||theta1 - y||_inf > rad, so the box excludes theta1        [exact rational]
    (C5) Krawczyk: K(X) is contained in the interior of X            [interval]
         which gives a unique root of F(theta) = p inside X, and
         J nonsingular throughout X (since ||I - Y J(X)||_inf < 1).

(C5) is run twice.  The mpmath.iv pass is a numerical cross-check: it routes some exact
rationals through finite-precision mpf values before wrapping them as intervals.  The
Arb (python-flint) pass is the authoritative certificate: its comparisons are rigorous
ball comparisons.  Accordingly the script prints

    SANITY_CHECK:          C1..C4 and the mpmath.iv inclusion
    RIGOROUS_CERTIFICATE:  C1..C4, the Arb inclusion, and ||I - Y J(X)||_inf < 1 in Arb

and reports RIGOROUS_CERTIFICATE: NOT RUN when python-flint is unavailable.  No
certificate predicate is evaluated in floating point: all comparisons are between exact
rationals or interval/ball endpoints.

Conclusion.  theta1 and the root in X are distinct regular points of F with the same
image p.  By the inverse function theorem each has a neighbourhood mapped
diffeomorphically onto an open set containing p; the intersection of those two images
is a nonempty open set of laws each of which has at least two distinct feasible
preimages.
"""

import itertools
from fractions import Fraction as Fr

n = 4
PAT = list(itertools.product([1, -1], repeat=n))

# ----------------------------------------------------------------- hardcoded data
theta1 = [Fr(1, 20), Fr(3, 20), Fr(3, 10),                         # w1, w2, w3
          Fr(3, 4), Fr(17, 20), Fr(4, 5), Fr(17, 20),              # p1
          Fr(3, 10), Fr(3, 20), Fr(3, 20), Fr(2, 5),               # p2
          Fr(3, 20), Fr(1, 10), Fr(1, 20), Fr(1, 20)]              # eta

_y_decimal = [  # 32-digit truncation of the refined second root
    "0.10248059751283720015060206486886", "0.17816132396802456823541138450478",
    "0.24636204654457274433638246467336", "0.79995183322170808502159013270712",
    "0.87286369144594754297791458579402", "0.88146127058302182779800103278165",
    "0.87860979251466966310632742332651", "0.28539050186133588151160029753911",
    "0.15142110639058882558494816276127", "0.13975615566727892574205934749998",
    "0.37743509430118630153733425133683", "0.14698970184307544928098375432028",
    "0.09799490564223312435785064655798", "0.04812223557115030696686026912750",
    "0.03906369474287508076731801671833"]
y = [Fr(s) for s in _y_decimal]
rad = Fr(1, 10**6)

# ----------------------------------------------------------------- the model map
def components(th, one):
    w = [th[0], th[1], th[2], one - th[0] - th[1] - th[2]]
    P = [list(th[3:7]), list(th[7:11]), [one - e for e in th[11:15]], list(th[11:15])]
    return w, P

def F(th, one=1):
    w, P = components(th, one)
    out = []
    for pat in PAT:
        s = 0
        for k in range(4):
            t = w[k]
            for v in range(n):
                t = t * (P[k][v] if pat[v] == 1 else one - P[k][v])
            s = s + t
        out.append(s)
    return out[:-1]                       # 15 of the 16 cells; the last is redundant

def J(th, one=1):
    """Exact Jacobian; works for Fraction, mpmath.iv and Arb inputs alike."""
    w, P = components(th, one)
    rows = []
    for pat in PAT[:-1]:
        prod = []
        for k in range(4):
            t = one
            for v in range(n):
                t = t * (P[k][v] if pat[v] == 1 else one - P[k][v])
            prod.append(t)
        row = [prod[0] - prod[3], prod[1] - prod[3], prod[2] - prod[3]]
        for k in (0, 1):                                  # d/dp1_v , d/dp2_v
            for v in range(n):
                rest = one
                for u in range(n):
                    if u != v:
                        rest = rest * (P[k][u] if pat[u] == 1 else one - P[k][u])
                row.append(w[k] * rest if pat[v] == 1 else -(w[k] * rest))
        for v in range(n):                                # d/deta_v
            r3 = r4 = one
            for u in range(n):
                if u != v:
                    r3 = r3 * (P[2][u] if pat[u] == 1 else one - P[2][u])
                    r4 = r4 * (P[3][u] if pat[u] == 1 else one - P[3][u])
            term = w[3] * r4 - w[2] * r3
            row.append(term if pat[v] == 1 else -term)
        rows.append(row)
    return rows

p = F(theta1)                                             # exact rational target

# ----------------------------------------------------------------- exact checks
def domain_ok(th):
    w4 = 1 - th[0] - th[1] - th[2]
    if min(th[0], th[1], th[2], w4) <= 0:
        return False
    return all(th[11 + v] < th[7 + v] < Fr(1, 2) < th[3 + v] < 1 - th[11 + v] for v in range(n))

def det_exact(rows):
    A = [r[:] for r in rows]; d = Fr(1); m = len(A)
    for c in range(m):
        piv = next((r for r in range(c, m) if A[r][c] != 0), None)
        if piv is None:
            return Fr(0)
        if piv != c:
            A[c], A[piv] = A[piv], A[c]; d = -d
        d *= A[c][c]
        for r in range(c + 1, m):
            f = A[r][c] / A[c][c]
            A[r] = [A[r][k] - f * A[c][k] for k in range(m)]
    return d

C1 = domain_ok(theta1)
detJ1 = det_exact(J(theta1))
C2 = detJ1 != 0
lo_box = [c - rad for c in y]; hi_box = [c + rad for c in y]
C3 = (min(lo_box[0], lo_box[1], lo_box[2]) > 0
      and 1 - hi_box[0] - hi_box[1] - hi_box[2] > 0
      and all(hi_box[11 + v] < lo_box[7 + v] and hi_box[7 + v] < Fr(1, 2)
              and lo_box[3 + v] > Fr(1, 2) and hi_box[3 + v] < 1 - hi_box[11 + v]
              for v in range(n)))
sep = max(abs(theta1[i] - y[i]) for i in range(15))
C4 = sep > rad

print("(C1) theta1 strictly inside the domain            :", C1)
print("(C2) det J(theta1) != 0                           :", C2)
print("      det J(theta1) =", detJ1)
print("(C3) whole box y +/- 1e-6 inside the domain       :", C3)
print("(C4) |theta1 - y|_inf > box radius                :", C4, " (separation =", sep, ")")

# ----------------------------------------------------------------- approximate inverse
# Y is an arbitrary fixed matrix; only ||I - Y J(X)|| < 1 matters, so a rationalized
# approximate inverse computed deterministically from y is enough.
import mpmath as mp
mp.mp.dps = 40
Jy = mp.matrix([[mp.mpf(x.numerator) / mp.mpf(x.denominator) for x in row] for row in J(y)])
Yf = Jy**-1
SCALE = 10**25
Y = [[Fr(int(mp.floor(Yf[i, j] * SCALE)), SCALE) for j in range(15)] for i in range(15)]

Fy = [a - b for a, b in zip(F(y), p)]                     # exact rational residual at y
YFy = [sum(Y[i][j] * Fy[j] for j in range(15)) for i in range(15)]
center = [y[i] - YFy[i] for i in range(15)]               # exact rational

# ----------------------------------------------------------------- Krawczyk, mpmath.iv
def krawczyk_mpmath():
    mp.iv.dps = 40
    X = [mp.iv.mpf([mp.mpf(lo_box[i].numerator) / mp.mpf(lo_box[i].denominator),
                    mp.mpf(hi_box[i].numerator) / mp.mpf(hi_box[i].denominator)]) for i in range(15)]
    JX = J(X, one=mp.iv.mpf(1))
    Yiv = [[mp.iv.mpf(mp.mpf(Y[i][j].numerator) / mp.mpf(Y[i][j].denominator)) for j in range(15)]
           for i in range(15)]
    M = [[(mp.iv.mpf(1) if i == j else mp.iv.mpf(0))
          - sum(Yiv[i][k] * JX[k][j] for k in range(15)) for j in range(15)] for i in range(15)]
    d = [mp.iv.mpf([mp.mpf(-rad.numerator) / mp.mpf(rad.denominator),
                    mp.mpf(rad.numerator) / mp.mpf(rad.denominator)]) for _ in range(15)]
    inside = True
    for i in range(15):
        Ki = mp.iv.mpf(mp.mpf(center[i].numerator) / mp.mpf(center[i].denominator)) \
             + sum(M[i][j] * d[j] for j in range(15))
        loi = mp.iv.mpf(mp.mpf(lo_box[i].numerator) / mp.mpf(lo_box[i].denominator))
        hii = mp.iv.mpf(mp.mpf(hi_box[i].numerator) / mp.mpf(hi_box[i].denominator))
        if not (Ki.a > loi.b and Ki.b < hii.a):           # endpoint comparisons, no floats
            inside = False
    rowsum = max(sum(abs(M[i][j]).b for j in range(15)) for i in range(15))
    return inside, rowsum

ok_mp, rs_mp = krawczyk_mpmath()
print("(C5a) cross-check, mpmath.iv: K(X) inside X       :", ok_mp,
      " ||I-YJ(X)||_inf <", mp.nstr(rs_mp, 6))

# ----------------------------------------------------------------- Krawczyk, Arb balls
arb_inside = arb_strict = False
arb_available = True
try:
    from flint import arb, ctx
    ctx.prec = 200
    def ball(a, b):
        mid = (a + b) / 2; r = (b - a) / 2
        return arb(arb(mid.numerator) / arb(mid.denominator), arb(r.numerator) / arb(r.denominator))
    X = [ball(lo_box[i], hi_box[i]) for i in range(15)]
    JX = J(X, one=arb(1))
    Yb = [[arb(Y[i][j].numerator) / arb(Y[i][j].denominator) for j in range(15)] for i in range(15)]
    M = [[(arb(1) if i == j else arb(0)) - sum(Yb[i][k] * JX[k][j] for k in range(15))
          for j in range(15)] for i in range(15)]
    dball = ball(-rad, rad)
    inside = True
    for i in range(15):
        Ki = arb(center[i].numerator) / arb(center[i].denominator) \
             + sum(M[i][j] * dball for j in range(15))
        lo_i = arb(lo_box[i].numerator) / arb(lo_box[i].denominator)
        hi_i = arb(hi_box[i].numerator) / arb(hi_box[i].denominator)
        if not (Ki > lo_i and Ki < hi_i):                 # Arb comparisons are rigorous
            inside = False
    rowsum = max(sum(abs(M[i][j]) for j in range(15)) for i in range(15))
    arb_inside = inside
    arb_strict = bool(rowsum < arb(1))
    print("(C5b) certificate, Arb balls: K(X) inside X       :", arb_inside,
          " ||I-YJ(X)||_inf <=", rowsum.upper())
    print("      ||I-YJ(X)||_inf < 1 (rigorous)              :", arb_strict)
except ImportError:
    arb_available = False
    print("(C5b) python-flint not installed; Arb certificate not run")

exact_ok = C1 and C2 and C3 and C4
print("\nSANITY_CHECK:", "PASS" if (exact_ok and ok_mp) else "FAIL")
if not arb_available:
    print("RIGOROUS_CERTIFICATE: NOT RUN")
else:
    print("RIGOROUS_CERTIFICATE:",
          "PASS" if (exact_ok and arb_inside and arb_strict) else "FAIL")