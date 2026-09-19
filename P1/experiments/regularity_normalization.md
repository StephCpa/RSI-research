# Frozen numerical regularity-margin specification

This file freezes the **finite-sample conditioning diagnostic** used by
`finite_sample.py`. It is deliberately distinct from the symbolic algebraic
certificate `Delta_pi` in the theorem.

The goal is scale invariance: each factor is normalized before the minimum is
taken, so the diagnostic cannot be tuned after seeing which normalization makes
the plots look best.

## General rules

- Singular-value factor:
  [
  d_{sv}(A)=\sigma_{min}(A)/\sigma_{max}(A).
  ]
- Determinant/cofactor factor:
  [
  d_{det}(A)=|\det A|/\prod_i\|A_{i,:}\|_2.
  ]
- Quadratic discriminant for (a t^2+b t+c):
  [
  d_{disc}=\frac{\max(b^2-4ac,0)}{a^2+b^2+c^2}.
  ]
- Mixture-weight and reliability factors are already dimensionless.

The reported regularity margin is the minimum of the relevant normalized
factors. For an existential reconstruction over several charts/groupings, take
the maximum margin over admissible charts.

## Partition (2,2)

`regularity22(theta)` is the minimum of:

1. (\sigma_{min}(R_{MM})/\sigma_{max}(R_{MM}));
2. atom imbalance
   [
   |S_+-S_-|/(S_++S_-);
   ]
3. (|1-2\eta_A|);
4. (|1-2\eta_B|);
5. the smaller of the two product-component separation ratios
   (\sigma_{min}/\sigma_{max}) for the A-side and B-side 4×2 component matrices;
6. atom mass (S_++S_-);
7. (min(c_+,c_-));
8. (min(S_+,S_-)).

## Partition (4)

For each of the three 2|2 flattenings (g), define:

1. **corner-free-minor signal.** For each corner-free 3×3 determinant polynomial
   [
   f(z)=c_0+c_1z+c_2z^2+c_3z^3,
   ]
   with affine entry coefficients (a_{ij}+zb_{ij}), use
   [
   d_{minor}=
   \frac{\|c\|_2}
        {\left(\sum_{ij}(a_{ij}^2+b_{ij}^2)\right)^{3/2}}.
   ]
   The grouping uses the maximum over its corner-free minors.

2. **corner recovery slopes.** Each linear corner determinant has slope equal to
   a 2×2 cofactor determinant. Normalize it as
   [
   |\det C|/(\|C_{1,:}\|_2\|C_{2,:}\|_2).
   ]
   Keep both corner factors.

3. **rank-2 product quadratic.** If the restricted product equation is
   (At^2+Bt+C=0), use
   [
   d_{disc}=\max(B^2-4AC,0)/(A^2+B^2+C^2).
   ]

4. reliability margin (|1-2\eta|);
5. (min(c_+,c_-));
6. (min(S_+,S_-)).

The grouping margin is the minimum of these factors. The partition-level margin
is

[
d_{reg}^{(4)}(\theta)=\max_g d_g(\theta),
]

matching the theorem's **existential** regularity condition: only one grouping
needs to be nondegenerate.

## Use in plots

The main conditioning display is

[
\sqrt N\,\|\hat\theta-\theta\|_\infty
\quad\text{versus}\quad d_{reg}(\theta).
]

The auxiliary regression is

[
\log E=\beta_0+\beta_N\log N+\beta_{reg}\log d_{reg}+\epsilon.
]

(eta_N) is estimated with a bootstrap CI; it is **not fixed** at (-1/2).
