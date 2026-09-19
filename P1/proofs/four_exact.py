# Corner-free 3x3 flattening minors as exact polynomials in z, at the running witness.
# NOTE: the choice of which two coordinates form the row factor matters (see below).
import itertools
from fractions import Fraction as Fr
import numpy as np
CELLS=list(itertools.product([1,-1],repeat=4))
cp,cm=Fr(1,5),Fr(1,4)
qp=[Fr(3,4),Fr(4,5),Fr(2,3),Fr(5,6)]; qm=[Fr(1,4),Fr(1,5),Fr(3,10),Fr(2,9)]
eta=Fr(1,10); z0=1/(1-2*eta)
def T(x):
    a,b=cp,cm
    for i in range(4):
        a*= qp[i] if x[i]==1 else 1-qp[i]
        b*= qm[i] if x[i]==1 else 1-qm[i]
    return a+b
def P(x): return (1-eta)*T(x)+eta*T(tuple(-t for t in x))
def Tz(x):
    s=P(x)+P(tuple(-t for t in x)); d=P(x)-P(tuple(-t for t in x))
    return (s/2, d/2)                                  # (const, z-coefficient)
pair={(1,1):0,(1,-1):1,(-1,1):2,(-1,-1):3}
def flatten(rows_idx):
    cols_idx=[i for i in range(4) if i not in rows_idx]
    Mz=[[None]*4 for _ in range(4)]
    for x in CELLS:
        r=pair[(x[rows_idx[0]],x[rows_idx[1]])]; c=pair[(x[cols_idx[0]],x[cols_idx[1]])]
        Mz[r][c]=Tz(x)
    return Mz
def polymul(a,b):
    out=[Fr(0)]*(len(a)+len(b)-1)
    for i,ai in enumerate(a):
        for j,bj in enumerate(b): out[i+j]+=ai*bj
    return out
def det3(Mz,rows,cols):
    A=[[list(Mz[i][j]) for j in cols] for i in rows]; tot=[Fr(0)]*4
    for perm,sgn in [((0,1,2),1),((1,2,0),1),((2,0,1),1),((0,2,1),-1),((2,1,0),-1),((1,0,2),-1)]:
        term=[Fr(1)]
        for i in range(3): term=polymul(term, A[i][perm[i]])
        for k,t in enumerate(term): tot[k]+=sgn*t
    return tot
def show(name, poly):
    f=[float(c) for c in poly]
    rts=np.roots(f[::-1]) if max(abs(np.array(f)))>0 else []
    exact=[]
    for r in rts:
        if abs(r.imag)<1e-9:
            cand=Fr(round(r.real*720),720)
            if sum(poly[k]*cand**k for k in range(len(poly)))==0: exact.append(cand)
    print(f"   {name}: coeffs {[str(c) for c in poly]}")
    print(f"        numeric roots {np.round(rts,6) if len(rts) else '(identically zero)'}  exact rational roots {exact}")
for rows_idx in [(0,1),(0,2)]:
    Mz=flatten(rows_idx)
    print(f"flattening with row coordinates {tuple(i+1 for i in rows_idx)}   (z0 = {z0}):")
    rows_a=[pair[(1,1)],pair[(1,-1)],pair[(-1,1)]]; cols_a=[pair[(1,-1)],pair[(-1,1)],pair[(-1,-1)]]
    rows_b=[pair[(1,-1)],pair[(-1,1)],pair[(-1,-1)]]; cols_b=[pair[(1,1)],pair[(1,-1)],pair[(-1,1)]]
    show("minor f1", det3(Mz,rows_a,cols_a)); show("minor f2", det3(Mz,rows_b,cols_b))
    A=np.array([[float(Mz[i][j][0]+2.0*Mz[i][j][1]) for j in range(4)] for i in range(4)])
    print("        rank of T_z at a generic z=2:", int(np.sum(np.linalg.svd(A,compute_uv=False)>1e-12)))