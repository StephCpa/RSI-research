# Exact-rational check of the cross-product system at the witness
# q+ = (3/4,4/5,2/3), q- = (1/4,1/5,3/10), eta_A = 1/10, rho0 = (4/5)^2 = 16/25.
import itertools
from fractions import Fraction as Fr
PATS3=[p for p in itertools.product([1,-1],repeat=3)]
N3=[p for p in PATS3 if abs(sum(p))!=3]
zk=[(-1,1,1),(1,-1,1),(1,1,-1)]

def blockA(q, eta, z):
    pro=Fr(1); proF=Fr(1)
    for i in range(3):
        pro  *= q[i] if z[i]==1 else 1-q[i]
        proF *= (1-q[i]) if z[i]==1 else q[i]
    return (1-eta)*pro + eta*proF

qp=[Fr(3,4),Fr(4,5),Fr(2,3)]; qm=[Fr(1,4),Fr(1,5),Fr(3,10)]; eta=Fr(1,10)
L=[[blockA(qp,eta,z), blockA(qm,eta,z)] for z in N3]        # 6x2, columns = the two true rays
idx={z:i for i,z in enumerate(N3)}
S=[[L[idx[z]][j]+L[idx[tuple(-t for t in z)]][j] for j in range(2)] for z in zk]
D=[[L[idx[z]][j]-L[idx[tuple(-t for t in z)]][j] for j in range(2)] for z in zk]
def quad(f,g): return [f[0]**2-g[0]**2, 2*(f[0]*f[1]-g[0]*g[1]), f[1]**2-g[1]**2]
A=quad(D[0],D[1]); B=quad(S[0],S[1]); C=quad(D[0],D[2]); Dd=quad(S[0],S[2])
polys=[]
for (i,j) in [(1,2),(2,0),(0,1)]:
    p2=B[i]*Dd[j]-B[j]*Dd[i]
    p1=-(A[i]*Dd[j]+B[i]*C[j])+(A[j]*Dd[i]+B[j]*C[i])
    p0=A[i]*C[j]-A[j]*C[i]
    polys.append([p2,p1,p0])
def roots_of(p):
    a,b,c=p
    if a==0: return ["linear root " + str(Fr(-c,b))] if b!=0 else ["identically zero" if c==0 else "no root"]
    disc=b*b-4*a*c
    # exact square root test
    if disc<0: return ["complex"]
    r=Fr(int(round(float(disc)**0.5)))
    # refine integer sqrt on numerator/denominator
    from math import isqrt
    num, den = disc.numerator, disc.denominator
    sn, sd = isqrt(num), isqrt(den)
    if sn*sn==num and sd*sd==den:
        s=Fr(sn,sd)
        return [Fr(-b+s,2*a), Fr(-b-s,2*a)]
    return ["irrational disc"]
print("rho0 = 16/25 =", Fr(16,25))
for k,p in enumerate(polys):
    print(f"poly {k+1}: coefficients {p}")
    print(f"          value at rho=16/25: {p[0]*Fr(16,25)**2 + p[1]*Fr(16,25) + p[2]}")
    print(f"          exact roots: {roots_of(p)}")