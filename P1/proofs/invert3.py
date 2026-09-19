# Check the closed-form inverse for a size-3 relation-error block.
# Given a_h(z) = w * P(Z=z | DS component h) on the six non-unanimous patterns,
# recover (w, q1, q2, q3, eta).
import numpy as np
rng = np.random.default_rng(5)

def a_of(w, q, eta, z):
    pro  = np.prod([q[i] if z[i]==1 else 1-q[i] for i in range(3)])
    proF = np.prod([1-q[i] if z[i]==1 else q[i] for i in range(3)])
    return w*((1-eta)*pro + eta*proF)

def recover(a):                      # a: dict pattern -> value, six non-unanimous patterns
    zk = [(-1,1,1),(1,-1,1),(1,1,-1)]
    s = [a[z]+a[tuple(-x for x in z)] for z in zk]
    d = [a[z]-a[tuple(-x for x in z)] for z in zk]
    # r^2 = (d_k^2 - d_l^2)/(s_k^2 - s_l^2), pick the best-conditioned pair
    best=None
    for k in range(3):
        for l in range(k+1,3):
            den = s[k]**2-s[l]**2
            if abs(den) > 1e-12:
                val = (d[k]**2-d[l]**2)/den
                if best is None or abs(den) > best[1]: best = (val, abs(den))
    r = np.sqrt(best[0])
    u = [s[k]-d[k]/r for k in range(3)]
    v = [s[k]+d[k]/r for k in range(3)]
    C = u[0]*v[0]
    A = u[0]*u[1]*u[2]/(2*C)
    o = [u[k]/(2*A) for k in range(3)]
    q = [ok/(1+ok) for ok in o]
    w = A*np.prod([1+ok for ok in o])
    return w, q, (1-r)/2, [u[k]*v[k] for k in range(3)]

err_max=0
for trial in range(2000):
    w = rng.uniform(0.05,0.5); q = rng.uniform(0.55,0.95,3); eta = rng.uniform(0.02,0.45)
    pats=[p for p in [(x,y,z) for x in (1,-1) for y in (1,-1) for z in (1,-1)]
          if abs(sum(p))!=3]
    a={p: a_of(w,q,eta,p) for p in pats}
    W,Q,E,Cs = recover(a)
    err = max(abs(W-w), max(abs(Q[i]-q[i]) for i in range(3)), abs(E-eta))
    err_max=max(err_max, err)
print("max recovery error over 2000 random interior points: %.2e" % err_max)

# where the formula degrades: s_k^2 = s_l^2 for all pairs
w,q,eta = 0.3, np.array([0.8,0.8,0.8]), 0.2
pats=[p for p in [(x,y,z) for x in (1,-1) for y in (1,-1) for z in (1,-1)] if abs(sum(p))!=3]
a={p: a_of(w,q,eta,p) for p in pats}
zk=[(-1,1,1),(1,-1,1),(1,1,-1)]
s=[a[z]+a[tuple(-x for x in z)] for z in zk]
print("exchangeable q (all equal): s_k values =", np.round(s,8), "-> all pairwise denominators vanish")