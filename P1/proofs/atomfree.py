# Rank of the DS-only map restricted to atom-free cells, for n=4 partitions,
# and the null direction when it is deficient.
import itertools, numpy as np
np.set_printoptions(precision=4, suppress=True)

def setup(part):
    n=sum(part); T=len(part); idx=[]; s=0
    for m in part: idx.append(list(range(s,s+m))); s+=m
    PAT=[p for p in itertools.product([1,-1],repeat=n)]
    atomfree=[p for p in PAT if any(len(set(p[v] for v in cols))>1 for cols in idx)]
    def law(t):                     # t = [w1,w2, q+_1..n, q-_1..n, eta_1..T]
        w=t[:2]; qp=t[2:2+n]; qm=t[2+n:2+2*n]; eta=t[2+2*n:2+2*n+T]
        out=[]
        for pat in atomfree:
            tot=0
            for h,q in enumerate([qp,qm]):
                comp=1
                for b,cols in enumerate(idx):
                    e=eta[b]
                    pro=np.prod([q[v] if pat[v]==1 else 1-q[v] for v in cols])
                    proF=np.prod([1-q[v] if pat[v]==1 else q[v] for v in cols])
                    comp*= (1-e)*pro + e*proF
                tot += w[h]*comp
            out.append(tot)
        return np.array(out)
    return law, len(atomfree), 2+2*n+T, n, T

def jac(law, t):
    eps=1e-6; J=[]
    for i in range(len(t)):
        e=np.zeros(len(t)); e[i]=eps
        J.append((law(t+e)-law(t-e))/(2*eps))
    return np.array(J).T

rng=np.random.default_rng(4)
print("partition   atom-free cells   DS params   rank")
nulls={}
for part in [(2,2),(3,1),(4,),(2,1,1)]:
    law,cells,d,n,T = setup(part)
    t=np.concatenate([rng.uniform(0.15,0.35,2), rng.uniform(0.6,0.95,n),
                      rng.uniform(0.05,0.4,n), rng.uniform(0.05,0.25,T)])
    J=jac(law,t); s=np.linalg.svd(J,compute_uv=False)
    rk=int(np.sum(s>1e-9*s[0]))
    print(f"{str(part):<12} {cells:>10} {d:>13} {rk:>7}")
    if rk<d:
        _,_,Vt=np.linalg.svd(J)
        nulls[part]=(t,Vt[rk:], n, T)

# interpret the (3,1) null direction
t,Nv,n,T = nulls[(3,1)]
v = Nv[0]/np.max(np.abs(Nv[0]))
names = ["w+","w-"]+[f"q+_{i+1}" for i in range(n)]+[f"q-_{i+1}" for i in range(n)]+[f"eta_{b+1}" for b in range(T)]
print("\n(3,1) null direction (normalized):")
for nm,val in zip(names,v):
    if abs(val)>1e-8: print(f"   {nm:<7} {val: .4f}")
# predicted: d eta_2 = e, d q_h,4 = -e(1-2 q_h,4)/(1-2 eta_2) keeps p_h,4 = eta+(1-2eta)q fixed
eta2 = t[2+2*n+1]; qp4=t[2+3]; qm4=t[2+n+3]
pred = np.zeros_like(v)
pred[2+2*n+1] = 1.0
pred[2+3]     = -(1-2*qp4)/(1-2*eta2)
pred[2+n+3]   = -(1-2*qm4)/(1-2*eta2)
pred = pred/np.max(np.abs(pred))
print("cosine between observed null vector and the predicted (eta_singleton vs q) direction:",
      round(float(abs(v@pred)/(np.linalg.norm(v)*np.linalg.norm(pred))),12))