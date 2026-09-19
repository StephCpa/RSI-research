# Constructive inverse for the (4) single-block model:
# complement-pair deconvolution -> corner-free minors give z -> corners by linear minors
# -> rank-2 product decomposition -> atom masses by a 2x2 solve.
import itertools, numpy as np
CELLS=list(itertools.product([1,-1],repeat=4))
pair={(1,1):0,(1,-1):1,(-1,1):2,(-1,-1):3}
CORNERS=[(1,1,1,1),(-1,-1,-1,-1)]

def law4(c,q,eta,S):
    P={}
    for x in CELLS:
        v=0.0
        for h in range(2):
            pro=np.prod([q[h][i] if x[i]==1 else 1-q[h][i] for i in range(4)])
            proF=np.prod([1-q[h][i] if x[i]==1 else q[h][i] for i in range(4)])
            v+=c[h]*((1-eta)*pro+eta*proF)
        if x==CORNERS[0]: v+=S[0]*(1-eta)+S[1]*eta
        if x==CORNERS[1]: v+=S[0]*eta+S[1]*(1-eta)
        P[x]=v
    return P

def flat_index(x, rows_idx):
    cols_idx=[i for i in range(4) if i not in rows_idx]
    return pair[(x[rows_idx[0]],x[rows_idx[1]])], pair[(x[cols_idx[0]],x[cols_idx[1]])]

def recover(P, rows_idx):
    # linear-in-z entries for non-corner cells; corners unknown
    lin=np.zeros((4,4,2)); known=np.zeros((4,4),bool)
    for x in CELLS:
        if x in CORNERS: continue
        s=P[x]+P[tuple(-t for t in x)]; d=P[x]-P[tuple(-t for t in x)]
        r_,c_=flat_index(x,rows_idx); lin[r_,c_]=[s/2,d/2]; known[r_,c_]=True
    ci,cj=flat_index(CORNERS[0],rows_idx); di,dj=flat_index(CORNERS[1],rows_idx)
    # corner-free 3x3 minors as cubics in z
    def minor_poly(rows,cols):
        zs=np.linspace(0.5,4.0,6)
        vals=[np.linalg.det(np.array([[lin[i,j,0]+z*lin[i,j,1] for j in cols] for i in rows])) for z in zs]
        return np.polyfit(zs,vals,3)
    polys=[]
    for rows in itertools.combinations(range(4),3):
        for cols in itertools.combinations(range(4),3):
            if (ci in rows and cj in cols) or (di in rows and dj in cols): continue
            p=minor_poly(rows,cols)
            if np.max(np.abs(p))>1e-10: polys.append(p/np.max(np.abs(p)))
    if len(polys)<2: return None
    cands=[]
    for p in polys[:6]:
        for rt in np.roots(p):
            if abs(rt.imag)<1e-7 and rt.real>1.0001:
                if all(abs(np.polyval(q,rt.real))<1e-6 for q in polys): cands.append(rt.real)
    cands=[c for i,c in enumerate(cands) if not any(abs(c-cands[j])<1e-6 for j in range(i))]
    if len(cands)!=1: return ('nonunique', len(cands))
    z=cands[0]; r=1/z; eta=(1-r)/2
    Tm=np.array([[lin[i,j,0]+z*lin[i,j,1] for j in range(4)] for i in range(4)])
    # corners by a 3x3 minor that contains one corner entry and not the other
    def solve_corner(ci,cj,other):
        for rows in itertools.combinations(range(4),3):
            for cols in itertools.combinations(range(4),3):
                if ci not in rows or cj not in cols: continue
                if other[0] in rows and other[1] in cols: continue
                A=np.array([[Tm[i,j] for j in cols] for i in rows])
                ii=rows.index(ci); jj=cols.index(cj)
                A0=A.copy(); A0[ii,jj]=0.0
                A1=A.copy(); A1[ii,jj]=1.0
                d0=np.linalg.det(A0); slope=np.linalg.det(A1)-d0
                if abs(slope)>1e-9: return -d0/slope
        return None
    a=solve_corner(ci,cj,(di,dj)); b=solve_corner(di,dj,(ci,cj))
    if a is None or b is None: return None
    Tm[ci,cj]=a; Tm[di,dj]=b
    # rank-2 product decomposition of Tm (same quadric trick as the (2,2) case)
    U,sv,Vt=np.linalg.svd(Tm); B=U[:,:2]
    u,w=B[:,0],B[:,1]
    A2=w[0]*w[3]-w[1]*w[2]; B2=u[0]*w[3]+w[0]*u[3]-u[1]*w[2]-w[1]*u[2]; C2=u[0]*u[3]-u[1]*u[2]
    disc=B2*B2-4*A2*C2
    if disc<0: return None
    rts=[(-B2+np.sqrt(disc))/(2*A2), (-B2-np.sqrt(disc))/(2*A2)]
    comps=[]
    for s_ in rts:
        v=u+s_*w; v=v/v.sum(); comps.append(v)
    comps.sort(key=lambda v: -(v[0]+v[1]))              # orientation: DS+ has larger P(first=+1)
    Amat=np.column_stack(comps); C=np.linalg.pinv(Amat)@Tm
    c=C.sum(axis=1); bvecs=[C[h]/c[h] for h in range(2)]
    cols_idx=[i for i in range(4) if i not in rows_idx]
    q=[np.zeros(4),np.zeros(4)]
    for h in range(2):
        q[h][rows_idx[0]]=comps[h][0]+comps[h][1]; q[h][rows_idx[1]]=comps[h][0]+comps[h][2]
        q[h][cols_idx[0]]=bvecs[h][0]+bvecs[h][1];  q[h][cols_idx[1]]=bvecs[h][0]+bvecs[h][2]
    Qp=P[CORNERS[0]]-((1-eta)*a+eta*b); Qm=P[CORNERS[1]]-(eta*a+(1-eta)*b)
    S=np.linalg.solve(np.array([[1-eta,eta],[eta,1-eta]]), np.array([Qp,Qm]))
    return dict(eta=eta,a=a,b=b,c=c,q=q,S=S)

rng=np.random.default_rng(17); errs=[]; fails=0; used=[]
for _ in range(200):
    c=rng.dirichlet([3,3])*rng.uniform(0.4,0.7)
    q=[rng.uniform(0.6,0.95,4), rng.uniform(0.05,0.4,4)]
    eta=rng.uniform(0.05,0.3); Sp=rng.uniform(0.1,0.3); Sm=1-c.sum()-Sp
    if Sm<=0.05: continue
    P=law4(c,q,eta,[Sp,Sm])
    out=None
    for rows_idx in [(0,1),(0,2),(0,3)]:
        out=recover(P,rows_idx)
        if isinstance(out,dict): used.append(rows_idx); break
    if not isinstance(out,dict): fails+=1; continue
    e=max(abs(out['eta']-eta), abs(out['c'][0]-c[0]), abs(out['c'][1]-c[1]),
          np.max(np.abs(out['q'][0]-q[0])), np.max(np.abs(out['q'][1]-q[1])),
          abs(out['S'][0]-Sp), abs(out['S'][1]-Sm))
    errs.append(e)
errs=np.array(errs)
print(f"(4) constructive inverse: {len(errs)} instances recovered, {fails} failures")
print("   error: median %.2e  90th %.2e  max %.2e" % (np.median(errs), np.percentile(errs,90), errs.max()))