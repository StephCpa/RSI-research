# Exact-rational check of (a) full column rank of the block-model Jacobian at the
# rational witness, for every partition of n=4, and (b) the closed-form inverse for a
# size-3 block.
import itertools
from fractions import Fraction as Fr

def cells(n): return list(itertools.product([1,-1], repeat=n))

def law(theta, part):
    n=sum(part); T=len(part); idx=[]; s=0
    for m in part: idx.append(list(range(s,s+m))); s+=m
    w=[theta[0],theta[1],theta[2],1-theta[0]-theta[1]-theta[2]]
    q1=theta[3:3+n]; q2=theta[3+n:3+2*n]; eta=theta[3+2*n:3+2*n+T]
    out=[]
    for pat in cells(n):
        tot=0
        for h in range(4):
            comp=1
            for b,cols in enumerate(idx):
                e=eta[b]
                if h==0: pv=[q1[v] for v in cols]
                elif h==1: pv=[q2[v] for v in cols]
                elif h==2: pv=[1]*len(cols)
                else: pv=[0]*len(cols)
                pro=1; proF=1
                for a,v in enumerate(cols):
                    pro  *= pv[a] if pat[v]==1 else 1-pv[a]
                    proF *= (1-pv[a]) if pat[v]==1 else pv[a]
                comp *= (1-e)*pro + e*proF
            tot += w[h]*comp
        out.append(tot)
    return out[:-1]

def jac(theta, part):
    h=Fr(1,10**6); J=[]
    for i in range(len(theta)):
        tp=list(theta); tm=list(theta); tp[i]+=h; tm[i]-=h
        J.append([(a-b)/(2*h) for a,b in zip(law(tp,part), law(tm,part))])
    return [[J[i][r] for i in range(len(theta))] for r in range(len(J[0]))]   # rows=cells

def rank_and_minor(M, d):
    rows=[r[:] for r in M]
    A=[r[:] for r in rows]; m=len(A); rank=0; sign=1
    for c in range(d):
        piv=None
        for r in range(rank, m):
            if A[r][c]!=0: piv=r; break
        if piv is None: continue
        if piv!=rank:
            A[rank],A[piv]=A[piv],A[rank]; sign=-sign
        for r in range(rank+1,m):
            f=A[r][c]/A[rank][c]
            A[r]=[A[r][k]-f*A[rank][k] for k in range(d)]
        rank+=1
        if rank==d: break
    if rank<d: return rank, None
    det=Fr(sign)
    for i in range(d): det*= A[i][i]
    return rank, det   # signed determinant of the d pivot rows, in the order they were used

theta_full = ([Fr(1,5),Fr(1,4),Fr(1,6)] +
              [Fr(3,4),Fr(4,5),Fr(2,3),Fr(5,6)] +
              [Fr(1,4),Fr(1,5),Fr(3,10),Fr(2,9)])
ETA = [Fr(1,10),Fr(1,8),Fr(1,12),Fr(1,9)]
print("partition        d   rank   nonzero minor (exact)")
for part in [(1,1,1,1),(2,1,1),(2,2),(3,1),(4,)]:
    T=len(part); th = theta_full + ETA[:T]; d=3+2*4+T
    M=jac(th, part); rk,det=rank_and_minor(M,d)
    print(f"{str(part):<14} {d:>3}   {rk:>3}    {det}")

# exact rank at an exchangeable point of (3,1,1): equal accuracies inside the size-3 block
theta_exch = ([Fr(1,5),Fr(1,4),Fr(1,6)] +
              [Fr(4,5),Fr(4,5),Fr(4,5),Fr(3,4),Fr(5,6)] +      # q1: exchangeable in block 1
              [Fr(1,4),Fr(1,4),Fr(1,4),Fr(1,5),Fr(3,10)] +     # q2: exchangeable in block 1
              [Fr(1,10),Fr(1,8),Fr(1,9)])
M = jac(theta_exch, (3,1,1)); rk, det = rank_and_minor(M, 16)
print()
print("exchangeable (3,1,1): exact rank", rk, "of 16; nonzero pivot minor:", det != 0)