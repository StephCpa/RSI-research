"""Finite-sample recovery study for the (2,2) and (4) block models.

Outputs:
  - CSV with one row per (partition, N, replicate, method)
  - recovery-error-vs-N figure
  - recovery-error-vs-regularity-margin figure

Methods:
  constructive         population inverse applied to the empirical law
  mle_constructive     one constrained-MLE run initialized at the constructive estimate
  mle_random_k<K>      best constrained MLE after K random starts; K is preregistered

The regularity_margin column is a normalized numerical proxy built from the
same determinants/discriminants/denominators that define the algebraic regular
set.  It is intentionally reported separately from the symbolic Delta_pi used
in the theorem.
"""
from __future__ import annotations

import argparse, csv, math, sys, time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
PROOFS = ROOT / "proofs"
if str(PROOFS) not in sys.path:
    sys.path.insert(0, str(PROOFS))

import two_two as tt
import four_inverse as fi

EPS = 1e-9


def sigmoid(x):
    x = np.asarray(x, dtype=float)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -35, 35)))


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-8, 1 - 1e-8)
    return np.log(p / (1 - p))


def softmax4(a3):
    z = np.r_[np.asarray(a3, dtype=float), 0.0]
    z -= z.max()
    e = np.exp(z)
    return e / e.sum()


def encode_weights(w):
    w = np.clip(np.asarray(w, dtype=float), 1e-10, None)
    w = w / w.sum()
    return np.log(w[:3] / w[3])


def qplus_from_x(x):
    return 0.5 + 0.49 * sigmoid(x)


def qminus_from_x(x):
    return 0.5 - 0.49 * sigmoid(x)


def eta_from_x(x):
    return 0.49 * sigmoid(x)


def x_from_qplus(q):
    return logit((np.asarray(q) - 0.5) / 0.49)


def x_from_qminus(q):
    return logit((0.5 - np.asarray(q)) / 0.49)


def x_from_eta(e):
    return logit(np.asarray(e) / 0.49)


def multinomial_sample(p, n, rng):
    p = np.asarray(p, dtype=float)
    p = np.clip(p, 0, None)
    p /= p.sum()
    return rng.multinomial(int(n), p)


def smoothed_empirical(counts, alpha=0.5):
    counts = np.asarray(counts, dtype=float)
    return (counts + alpha) / (counts.sum() + alpha * counts.size)


# ---------------------------------------------------------------------------
# (2,2)
# ---------------------------------------------------------------------------

def random_theta22(rng):
    w = rng.dirichlet([3, 3, 2, 2])
    qA = [rng.uniform(0.58, 0.95, 2), rng.uniform(0.05, 0.42, 2)]
    qB = [rng.uniform(0.58, 0.95, 2), rng.uniform(0.05, 0.42, 2)]
    eta = rng.uniform(0.03, 0.30, 2)
    return dict(w=w, qA=qA, qB=qB, eta=eta)


def decode22(x):
    x = np.asarray(x, dtype=float)
    w = softmax4(x[:3])
    qA = [qplus_from_x(x[3:5]), qminus_from_x(x[5:7])]
    qB = [qplus_from_x(x[7:9]), qminus_from_x(x[9:11])]
    eta = eta_from_x(x[11:13])
    return dict(w=w, qA=qA, qB=qB, eta=eta)


def encode22(t):
    return np.r_[
        encode_weights(t["w"]),
        x_from_qplus(t["qA"][0]),
        x_from_qminus(t["qA"][1]),
        x_from_qplus(t["qB"][0]),
        x_from_qminus(t["qB"][1]),
        x_from_eta(t["eta"]),
    ]


def law22_vec(t):
    return tt.make_law(t["w"], t["qA"], t["qB"], t["eta"]).reshape(-1)


def recover22_emp(p):
    try:
        out = tt.recover(np.asarray(p).reshape(4, 4))
        t = dict(
            w=np.array([out["c"][0], out["c"][1], out["Sp"], out["Sm"]], dtype=float),
            qA=[np.asarray(out["qA"][0]), np.asarray(out["qA"][1])],
            qB=[np.asarray(out["qB"][0]), np.asarray(out["qB"][1])],
            eta=np.array([out["etaA"], out["etaB"]], dtype=float),
        )
        if np.any(t["w"] <= 0) or abs(t["w"].sum() - 1) > 0.15:
            return None
        if np.any(t["eta"] <= 0) or np.any(t["eta"] >= 0.49):
            return None
        for arr in t["qA"] + t["qB"]:
            if np.any(arr <= 0.01) or np.any(arr >= 0.99):
                return None
        return t
    except Exception:
        return None


def error22(est, truth):
    if est is None:
        return np.nan
    vals = [
        np.max(np.abs(np.asarray(est["w"]) - truth["w"])),
        np.max(np.abs(np.asarray(est["eta"]) - truth["eta"])),
    ]
    for a, b in zip(est["qA"], truth["qA"]):
        vals.append(np.max(np.abs(np.asarray(a) - np.asarray(b))))
    for a, b in zip(est["qB"], truth["qB"]):
        vals.append(np.max(np.abs(np.asarray(a) - np.asarray(b))))
    return float(max(vals))


def regularity22(t):
    """Normalized numerical margin built from the critical factors."""
    w, qA, qB, eta = t["w"], t["qA"], t["qB"], t["eta"]
    # DS part R.
    RA = [tt.block_law(qA[h], eta[0], "ds") for h in range(2)]
    RB = [tt.block_law(qB[h], eta[1], "ds") for h in range(2)]
    R = w[0] * np.outer(RA[0], RB[0]) + w[1] * np.outer(RA[1], RB[1])
    s_mm = np.linalg.svd(R[np.ix_(tt.M, tt.M)], compute_uv=False)
    mm_margin = s_mm[-1] / max(s_mm[0], EPS)

    # Atom inversion margins.
    atom_mass = w[2] + w[3]
    mu = abs(w[2] - w[3]) / max(atom_mass, EPS)
    rA, rB = 1 - 2 * eta[0], 1 - 2 * eta[1]

    # Product-component separation after deconvolution: smallest singular value
    # of the two component vectors on each side.
    avec = np.column_stack([
        np.array([
            qA[h][0] * qA[h][1],
            qA[h][0] * (1 - qA[h][1]),
            (1 - qA[h][0]) * qA[h][1],
            (1 - qA[h][0]) * (1 - qA[h][1]),
        ]) for h in range(2)
    ])
    bvec = np.column_stack([
        np.array([
            qB[h][0] * qB[h][1],
            qB[h][0] * (1 - qB[h][1]),
            (1 - qB[h][0]) * qB[h][1],
            (1 - qB[h][0]) * (1 - qB[h][1]),
        ]) for h in range(2)
    ])
    sa = np.linalg.svd(avec, compute_uv=False)
    sb = np.linalg.svd(bvec, compute_uv=False)
    sep = min(sa[-1] / sa[0], sb[-1] / sb[0])

    factors = np.array([
        mm_margin,
        mu,
        abs(rA),
        abs(rB),
        sep,
        atom_mass,
        min(w[0], w[1]),
        min(w[2], w[3]),
    ], dtype=float)
    return float(max(np.min(factors), 1e-14))


# ---------------------------------------------------------------------------
# (4): finite-sample version of the constructive inverse.
# ---------------------------------------------------------------------------

def random_theta4(rng):
    w = rng.dirichlet([3, 3, 2, 2])
    return dict(
        c=np.array(w[:2]),
        S=np.array(w[2:]),
        q=[rng.uniform(0.58, 0.95, 4), rng.uniform(0.05, 0.42, 4)],
        eta=float(rng.uniform(0.03, 0.30)),
    )


def decode4(x):
    x = np.asarray(x, dtype=float)
    w = softmax4(x[:3])
    return dict(
        c=w[:2],
        S=w[2:],
        q=[qplus_from_x(x[3:7]), qminus_from_x(x[7:11])],
        eta=float(eta_from_x(x[11])),
    )


def encode4(t):
    w = np.r_[t["c"], t["S"]]
    return np.r_[
        encode_weights(w),
        x_from_qplus(t["q"][0]),
        x_from_qminus(t["q"][1]),
        x_from_eta(t["eta"]),
    ]


def law4_vec(t):
    P = fi.law4(t["c"], t["q"], t["eta"], t["S"])
    return np.array([P[x] for x in fi.CELLS], dtype=float)


def _lin4(P, rows_idx):
    lin = np.zeros((4, 4, 2))
    for x in fi.CELLS:
        if x in fi.CORNERS:
            continue
        xn = tuple(-a for a in x)
        s, d = P[x] + P[xn], P[x] - P[xn]
        i, j = fi.flat_index(x, rows_idx)
        lin[i, j] = [s / 2, d / 2]
    return lin


def _corner_positions(rows_idx):
    a = fi.flat_index(fi.CORNERS[0], rows_idx)
    b = fi.flat_index(fi.CORNERS[1], rows_idx)
    return a, b


def _corner_free_minors(lin, rows_idx):
    import itertools
    ca, cb = _corner_positions(rows_idx)
    minors = []
    for rows in itertools.combinations(range(4), 3):
        for cols in itertools.combinations(range(4), 3):
            if (ca[0] in rows and ca[1] in cols) or (cb[0] in rows and cb[1] in cols):
                continue

            def f(z, rows=rows, cols=cols):
                A = np.array([[lin[i, j, 0] + z * lin[i, j, 1] for j in cols] for i in rows])
                return np.linalg.det(A)

            grid = np.linspace(1.01, 4.0, 9)
            scale = max(max(abs(f(z)) for z in grid), 1e-12)
            minors.append((f, scale))
    return minors


def _solve_corner_ls(Tm, pos, other):
    import itertools
    values, weights = [], []
    for rows in itertools.combinations(range(4), 3):
        for cols in itertools.combinations(range(4), 3):
            if pos[0] not in rows or pos[1] not in cols:
                continue
            if other[0] in rows and other[1] in cols:
                continue
            A = np.array([[Tm[i, j] for j in cols] for i in rows])
            ii, jj = rows.index(pos[0]), cols.index(pos[1])
            A0 = A.copy(); A0[ii, jj] = 0.0
            A1 = A.copy(); A1[ii, jj] = 1.0
            d0 = np.linalg.det(A0)
            slope = np.linalg.det(A1) - d0
            if abs(slope) > 1e-10:
                values.append(-d0 / slope)
                weights.append(slope * slope)
    if not values:
        return None, 0.0
    values, weights = np.asarray(values), np.asarray(weights)
    return float(np.sum(values * weights) / np.sum(weights)), float(np.max(np.sqrt(weights)))


def recover4_emp(pvec):
    P = {x: float(pvec[i]) for i, x in enumerate(fi.CELLS)}
    best = None
    for rows_idx in [(0, 1), (0, 2), (0, 3)]:
        try:
            lin = _lin4(P, rows_idx)
            minors = _corner_free_minors(lin, rows_idx)
            if len(minors) < 2:
                continue

            def obj(z):
                return sum((f(z) / sc) ** 2 for f, sc in minors)

            opt = minimize_scalar(obj, bounds=(1.001, 5.0), method="bounded",
                                  options={"xatol": 1e-10, "maxiter": 400})
            z = float(opt.x)
            if not np.isfinite(z) or z <= 1:
                continue
            eta = (1 - 1 / z) / 2
            if not (0 < eta < 0.49):
                continue

            Tm = np.array([[lin[i, j, 0] + z * lin[i, j, 1] for j in range(4)] for i in range(4)])
            ca, cb = _corner_positions(rows_idx)
            a, slope_a = _solve_corner_ls(Tm, ca, cb)
            b, slope_b = _solve_corner_ls(Tm, cb, ca)
            if a is None or b is None:
                continue
            Tm[ca] = a
            Tm[cb] = b

            U, sv, Vt = np.linalg.svd(Tm)
            B = U[:, :2]
            u, wv = B[:, 0], B[:, 1]
            A2 = wv[0] * wv[3] - wv[1] * wv[2]
            B2 = u[0] * wv[3] + wv[0] * u[3] - u[1] * wv[2] - wv[1] * u[2]
            C2 = u[0] * u[3] - u[1] * u[2]
            disc = B2 * B2 - 4 * A2 * C2
            if disc <= 0 or abs(A2) < 1e-12:
                continue
            roots = [(-B2 + np.sqrt(disc)) / (2 * A2), (-B2 - np.sqrt(disc)) / (2 * A2)]
            comps = []
            for r in roots:
                v = u + r * wv
                if abs(v.sum()) < 1e-12:
                    raise FloatingPointError
                v = v / v.sum()
                comps.append(v)
            comps.sort(key=lambda v: -(v[0] + v[1]))
            Amat = np.column_stack(comps)
            C = np.linalg.pinv(Amat) @ Tm
            c = C.sum(axis=1)
            if np.any(c <= 0):
                continue
            bvecs = [C[h] / c[h] for h in range(2)]
            cols_idx = [i for i in range(4) if i not in rows_idx]
            q = [np.zeros(4), np.zeros(4)]
            for h in range(2):
                q[h][rows_idx[0]] = comps[h][0] + comps[h][1]
                q[h][rows_idx[1]] = comps[h][0] + comps[h][2]
                q[h][cols_idx[0]] = bvecs[h][0] + bvecs[h][1]
                q[h][cols_idx[1]] = bvecs[h][0] + bvecs[h][2]
            if np.any(q[0] <= 0.5) or np.any(q[1] >= 0.5):
                continue
            if np.any(q[0] >= 1) or np.any(q[1] <= 0):
                continue

            Qp = P[fi.CORNERS[0]] - ((1 - eta) * a + eta * b)
            Qm = P[fi.CORNERS[1]] - (eta * a + (1 - eta) * b)
            Sat = np.linalg.solve(np.array([[1 - eta, eta], [eta, 1 - eta]]), np.array([Qp, Qm]))
            if np.any(Sat <= 0):
                continue
            total = c.sum() + Sat.sum()
            c, Sat = c / total, Sat / total
            est = dict(c=c, S=Sat, q=q, eta=eta)
            cand = (float(opt.fun), est, min(slope_a, slope_b), float(disc))
            if best is None or cand[0] < best[0]:
                best = cand
        except Exception:
            continue
    return None if best is None else best[1]


def error4(est, truth):
    if est is None:
        return np.nan
    return float(max(
        np.max(np.abs(np.asarray(est["c"]) - truth["c"])),
        np.max(np.abs(np.asarray(est["S"]) - truth["S"])),
        np.max(np.abs(np.asarray(est["q"][0]) - truth["q"][0])),
        np.max(np.abs(np.asarray(est["q"][1]) - truth["q"][1])),
        abs(float(est["eta"]) - truth["eta"]),
    ))


def _normalized_minor_signal(lin, rows_idx):
    """Scale-free coefficient norm for corner-free 3x3 determinant polynomials.

    A determinant coefficient is cubic in the affine entry coefficients.  We
    divide its coefficient l2 norm by the cube of the selected-entry l2 scale.
    """
    import itertools
    ca, cb = _corner_positions(rows_idx)
    best = 0.0
    zs = np.array([-1.5, -0.5, 0.5, 1.5])
    V = np.vander(zs, 4, increasing=True)
    for rows in itertools.combinations(range(4), 3):
        for cols in itertools.combinations(range(4), 3):
            if (ca[0] in rows and ca[1] in cols) or (cb[0] in rows and cb[1] in cols):
                continue
            vals = []
            coeff_scale = 0.0
            for z in zs:
                A = np.array([[lin[i, j, 0] + z * lin[i, j, 1] for j in cols] for i in rows])
                vals.append(np.linalg.det(A))
            for i in rows:
                for j in cols:
                    coeff_scale += lin[i, j, 0] ** 2 + lin[i, j, 1] ** 2
            coeff = np.linalg.solve(V, np.asarray(vals))
            denom = max(coeff_scale ** 1.5, 1e-15)
            best = max(best, float(np.linalg.norm(coeff) / denom))
    return best


def _normalized_corner_slope(Tm, pos, other):
    """Maximum scale-free cofactor used for linear corner recovery."""
    import itertools
    best = 0.0
    for rows in itertools.combinations(range(4), 3):
        for cols in itertools.combinations(range(4), 3):
            if pos[0] not in rows or pos[1] not in cols:
                continue
            if other[0] in rows and other[1] in cols:
                continue
            A = np.array([[Tm[i, j] for j in cols] for i in rows], dtype=float)
            ii, jj = rows.index(pos[0]), cols.index(pos[1])
            C = np.delete(np.delete(A, ii, axis=0), jj, axis=1)
            denom = max(np.linalg.norm(C[0]) * np.linalg.norm(C[1]), 1e-15)
            best = max(best, abs(np.linalg.det(C)) / denom)
    return float(best)


def regularity4(t):
    """Frozen scale-free regularity margin, maximized over the three flattenings."""
    p = law4_vec(t)
    P = {x: float(p[i]) for i, x in enumerate(fi.CELLS)}
    z0 = 1 / (1 - 2 * t["eta"])
    best = 0.0
    for rows_idx in [(0, 1), (0, 2), (0, 3)]:
        lin = _lin4(P, rows_idx)
        minors = _corner_free_minors(lin, rows_idx)
        signal = _normalized_minor_signal(lin, rows_idx)
        Tm = np.array([[lin[i, j, 0] + z0 * lin[i, j, 1] for j in range(4)] for i in range(4)])
        ca, cb = _corner_positions(rows_idx)
        a, _ = _solve_corner_ls(Tm, ca, cb)
        b, _ = _solve_corner_ls(Tm, cb, ca)
        if a is None or b is None:
            continue
        Tm[ca], Tm[cb] = a, b
        U = np.linalg.svd(Tm)[0][:, :2]
        u, wv = U[:, 0], U[:, 1]
        A2 = wv[0] * wv[3] - wv[1] * wv[2]
        B2 = u[0] * wv[3] + wv[0] * u[3] - u[1] * wv[2] - wv[1] * u[2]
        C2 = u[0] * u[3] - u[1] * u[2]
        disc = max(B2 * B2 - 4 * A2 * C2, 0.0)
        coeff_norm2 = A2 * A2 + B2 * B2 + C2 * C2
        disc_margin = disc / max(coeff_norm2, 1e-15)
        slope_a = _normalized_corner_slope(Tm, ca, cb)
        slope_b = _normalized_corner_slope(Tm, cb, ca)
        factors = [
            signal,
            slope_a,
            slope_b,
            disc_margin,
            abs(1 - 2 * t["eta"]),
            min(t["c"]),
            min(t["S"]),
        ]
        best = max(best, min(factors))
    return float(max(best, 1e-14))


# ---------------------------------------------------------------------------
# Likelihood fitting
# ---------------------------------------------------------------------------

def fit_mle(counts, partition, starts, rng, init=None, maxiter=1200):
    counts = np.asarray(counts, dtype=float)

    if partition == "22":
        decode, law, dim = decode22, law22_vec, 13
    else:
        decode, law, dim = decode4, law4_vec, 12

    def nll(x):
        p = np.clip(law(decode(x)), 1e-14, 1)
        return float(-np.dot(counts, np.log(p)))

    x0s = []
    if init is not None:
        try:
            x0s.append(encode22(init) if partition == "22" else encode4(init))
        except Exception:
            pass
    while len(x0s) < starts:
        x0s.append(rng.normal(0, 1.2, dim))

    best = None
    for x0 in x0s:
        opt = minimize(nll, x0, method="L-BFGS-B",
                       options={"maxiter": maxiter, "ftol": 1e-10, "gtol": 1e-7})
        if np.isfinite(opt.fun) and (best is None or opt.fun < best.fun):
            best = opt
    return None if best is None else decode(best.x)


def fit_mle_restart_curve(counts, partition, restart_grid, rng, maxiter=1200):
    """Return cumulative-best random-start MLE at each K in restart_grid."""
    counts = np.asarray(counts, dtype=float)
    restart_grid = sorted(set(int(k) for k in restart_grid))
    if not restart_grid or restart_grid[0] < 1:
        raise ValueError("restart_grid must contain positive integers")

    if partition == "22":
        decode, law, dim = decode22, law22_vec, 13
    else:
        decode, law, dim = decode4, law4_vec, 12

    def nll(x):
        p = np.clip(law(decode(x)), 1e-14, 1)
        return float(-np.dot(counts, np.log(p)))

    best = None
    out = {}
    for k in range(1, max(restart_grid) + 1):
        x0 = rng.normal(0, 1.2, dim)
        opt = minimize(nll, x0, method="L-BFGS-B",
                       options={"maxiter": maxiter, "ftol": 1e-10, "gtol": 1e-7})
        if np.isfinite(opt.fun) and (best is None or opt.fun < best.fun):
            best = opt
        if k in restart_grid:
            out[k] = None if best is None else decode(best.x)
    return out


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------

def _finite(rows, part, method):
    return [
        r for r in rows
        if r["partition"] == part and r["method"] == method
        and np.isfinite(float(r["error"]))
    ]


def _scaling_regression(rows, part, boot_reps=1000, seed=20260919):
    """Fit log E = beta0 + beta_N log N + beta_reg log d_reg.

    beta_N is estimated, never fixed at -1/2. Bootstrap resamples parameter
    replicates, preserving all N values for each sampled replicate.
    """
    rr = _finite(rows, part, "constructive")
    if len(rr) < 4:
        return None
    X = np.array([[1.0, np.log(float(r["N"])),
                   np.log(max(float(r["regularity_margin"]), 1e-14))]
                  for r in rr])
    y = np.log(np.array([float(r["error"]) for r in rr]))
    beta = np.linalg.lstsq(X, y, rcond=None)[0]

    rng = np.random.default_rng(seed)
    reps = sorted({int(r["replicate"]) for r in rr})
    b = []
    for _ in range(boot_reps):
        sampled = rng.choice(reps, size=len(reps), replace=True)
        rrb = []
        for j in sampled:
            rrb.extend([r for r in rr if int(r["replicate"]) == j])
        Xb = np.array([[1.0, np.log(float(r["N"])),
                        np.log(max(float(r["regularity_margin"]), 1e-14))]
                       for r in rrb])
        yb = np.log(np.array([float(r["error"]) for r in rrb]))
        if np.linalg.matrix_rank(Xb) == 3:
            b.append(np.linalg.lstsq(Xb, yb, rcond=None)[0])
    b = np.asarray(b)
    lo = np.quantile(b, .025, axis=0) if len(b) else np.full(3, np.nan)
    hi = np.quantile(b, .975, axis=0) if len(b) else np.full(3, np.nan)
    return beta, lo, hi


def summarize_rows(rows, outdir, restart_grid):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    parts = ["22", "4"]
    maxk = max(restart_grid)
    main_methods = ["constructive", "mle_constructive", f"mle_random_k{maxk}"]

    # Error vs N.
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.1), sharey=True)
    for ax, part in zip(axes, parts):
        for method in main_methods:
            xs, med, lo, hi = [], [], [], []
            for N in sorted({int(r["N"]) for r in rows if r["partition"] == part}):
                vals = np.array([float(r["error"]) for r in rows
                                 if r["partition"] == part and r["method"] == method
                                 and int(r["N"]) == N and np.isfinite(float(r["error"]))])
                if len(vals) == 0:
                    continue
                xs.append(N); med.append(np.median(vals))
                lo.append(np.quantile(vals, .1)); hi.append(np.quantile(vals, .9))
            if xs:
                ax.plot(xs, med, marker="o", label=method)
                ax.fill_between(xs, lo, hi, alpha=.15)
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("sample size N")
        ax.set_title("(2,2)" if part == "22" else "(4)")
    axes[0].set_ylabel("max parameter error")
    axes[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(outdir / "finite_sample_vs_N.pdf")
    fig.savefig(outdir / "finite_sample_vs_N.png", dpi=180)
    plt.close(fig)

    # Lead conditioning display: sqrt(N)*E versus frozen regularity margin.
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.1), sharey=True)
    sc = None
    for ax, part in zip(axes, parts):
        rr = _finite(rows, part, "constructive")
        if rr:
            x = np.array([float(r["regularity_margin"]) for r in rr])
            y = np.array([np.sqrt(float(r["N"])) * float(r["error"]) for r in rr])
            n = np.array([int(r["N"]) for r in rr])
            sc = ax.scatter(x, y, c=np.log10(n), s=16, alpha=.65)
            ax.set_xscale("log"); ax.set_yscale("log")
            ax.set_xlabel("frozen regularity margin")
            ax.set_title("(2,2)" if part == "22" else "(4)")
    axes[0].set_ylabel(r"$\sqrt{N}$ × max parameter error")
    if sc is not None:
        fig.colorbar(sc, ax=axes, label="log10 N")
    fig.savefig(outdir / "finite_sample_scaled_vs_regularity.pdf", bbox_inches="tight")
    fig.savefig(outdir / "finite_sample_scaled_vs_regularity.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Restart curve: random-start MLE as a function of K.
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.1), sharey=True)
    equivalence = []
    for ax, part in zip(axes, parts):
        Ns = sorted({int(r["N"]) for r in rows if r["partition"] == part})
        for N in Ns:
            init_vals = np.array([float(r["error"]) for r in rows
                                  if r["partition"] == part and r["method"] == "mle_constructive"
                                  and int(r["N"]) == N and np.isfinite(float(r["error"]))])
            target = np.median(init_vals) if len(init_vals) else np.nan
            meds = []
            for k in restart_grid:
                vals = np.array([float(r["error"]) for r in rows
                                 if r["partition"] == part and r["method"] == f"mle_random_k{k}"
                                 and int(r["N"]) == N and np.isfinite(float(r["error"]))])
                meds.append(np.median(vals) if len(vals) else np.nan)
            ax.plot(restart_grid, meds, marker="o", label=f"N={N:g}")
            eq = next((k for k, m in zip(restart_grid, meds)
                       if np.isfinite(target) and np.isfinite(m) and m <= 1.05 * target), None)
            equivalence.append(dict(partition=part, N=N, restart_equivalence_5pct=eq or ">" + str(maxk)))
        ax.set_xscale("log", base=2); ax.set_yscale("log")
        ax.set_xlabel("random restart budget K")
        ax.set_title("(2,2)" if part == "22" else "(4)")
    axes[0].set_ylabel("median max parameter error")
    axes[1].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(outdir / "mle_restart_curve.pdf")
    fig.savefig(outdir / "mle_restart_curve.png", dpi=180)
    plt.close(fig)

    with (outdir / "mle_restart_equivalence.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(equivalence[0].keys()))
        w.writeheader(); w.writerows(equivalence)

    # Scaling regression with beta_N estimated, not fixed.
    reg_rows = []
    for part in parts:
        out = _scaling_regression(rows, part)
        if out is None:
            continue
        beta, lo, hi = out
        reg_rows.append(dict(
            partition=part,
            beta0=beta[0], beta0_lo=lo[0], beta0_hi=hi[0],
            beta_N=beta[1], beta_N_lo=lo[1], beta_N_hi=hi[1],
            beta_reg=beta[2], beta_reg_lo=lo[2], beta_reg_hi=hi[2],
        ))
    if reg_rows:
        with (outdir / "scaling_regression.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(reg_rows[0].keys()))
            w.writeheader(); w.writerows(reg_rows)


def run(args):
    rng = np.random.default_rng(args.seed)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []

    for part in ["22", "4"]:
        for rep in range(args.replicates):
            truth = random_theta22(rng) if part == "22" else random_theta4(rng)
            p = law22_vec(truth) if part == "22" else law4_vec(truth)
            reg = regularity22(truth) if part == "22" else regularity4(truth)

            for N in args.ns:
                counts = multinomial_sample(p, N, rng)
                phat = smoothed_empirical(counts, args.pseudocount)

                t0 = time.perf_counter()
                constructive = recover22_emp(phat) if part == "22" else recover4_emp(phat)
                t_constructive = time.perf_counter() - t0

                errfun = error22 if part == "22" else error4
                rows.append(dict(partition=part, N=N, replicate=rep, method="constructive",
                                 error=errfun(constructive, truth), regularity_margin=reg,
                                 seconds=t_constructive))

                t0 = time.perf_counter()
                if constructive is None:
                    mlec = None
                else:
                    mlec = fit_mle(counts, part, 1, rng, init=constructive, maxiter=args.maxiter)
                init_seconds = time.perf_counter() - t0
                rows.append(dict(partition=part, N=N, replicate=rep, method="mle_constructive",
                                 error=errfun(mlec, truth), regularity_margin=reg,
                                 seconds=init_seconds))

                t0 = time.perf_counter()
                curve = fit_mle_restart_curve(counts, part, args.restart_grid, rng,
                                              maxiter=args.maxiter)
                random_seconds = time.perf_counter() - t0
                for k in args.restart_grid:
                    estk = curve[k]
                    rows.append(dict(partition=part, N=N, replicate=rep,
                                     method=f"mle_random_k{k}",
                                     error=errfun(estk, truth), regularity_margin=reg,
                                     seconds=random_seconds))

                kmax = max(args.restart_grid)
                print(f"part={part:>2} rep={rep:03d} N={N:>8} "
                      f"constructive={errfun(constructive, truth):.3e} "
                      f"mle-random-k{kmax}={errfun(curve[kmax], truth):.3e} "
                      f"mle-init={errfun(mlec, truth):.3e} margin={reg:.2e}")

    csv_path = outdir / "finite_sample.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    summarize_rows(rows, outdir, args.restart_grid)
    print("wrote", csv_path)
    return 0


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ns", type=int, nargs="+", default=[1000, 10000, 100000, 1000000])
    p.add_argument("--replicates", type=int, default=20)
    p.add_argument("--restart-grid", type=int, nargs="+", default=[1, 2, 4, 8, 16],
                   help="cumulative random-start MLE budgets to compare")
    p.add_argument("--maxiter", type=int, default=1200)
    p.add_argument("--pseudocount", type=float, default=0.5)
    p.add_argument("--seed", type=int, default=20260919)
    p.add_argument("--output", default=str(ROOT / "experiments" / "results"))
    p.add_argument("--quick", action="store_true")
    a = p.parse_args()
    if a.quick:
        a.ns = [1000, 10000]
        a.replicates = 2
        a.restart_grid = [1, 2]
        a.maxiter = 400
    return a


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
