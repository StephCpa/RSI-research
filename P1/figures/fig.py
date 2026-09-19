# Reproduces Figure 1 of the P1 memo: majority-gate false-accept floor,
# and the identified set for precision vs. a gold audit in U^+.
# Parameters: lamE=0.09 easy positives, cp=0.21 DS positives, accuracies 0.85,
# lamE_minus = lamB_minus = 0; c_- takes the remaining mass.
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import binom, beta as Beta
plt.rcParams.update({"font.size":9,"font.family":"serif","axes.spines.top":False,"axes.spines.right":False})
a = 0.85
lamE = 0.09      # easy positives (Y=+1, all views accept)
cp = 0.21        # Dawid-Skene positives
V = np.arange(5, 27, 2)
def gate(lamB):
    cm = 1 - lamE - cp - lamB
    maj_p = 1 - binom.cdf(V//2, V, a)        # P(majority accepts | DS positive)
    maj_m = 1 - binom.cdf(V//2, V, 1-a)      # P(majority accepts | DS negative)
    TP_DS, FP_DS = cp*maj_p, cm*maj_m
    S = lamE + lamB
    PA = TP_DS + FP_DS + S
    FA = FP_DS + lamB
    prec = (TP_DS + lamE)/PA
    lo, hi = TP_DS/PA, (TP_DS + S)/PA
    # unanimous-accept stratum
    u_TP, u_FP = cp*a**V, cm*(1-a)**V
    u = u_TP + u_FP + S
    r = (u_FP + lamB)/u                        # P(Y=-1 | unanimous accept)
    FP_rest = FP_DS - u_FP                     # identified under the model
    return dict(FA=FA, prec=prec, lo=lo, hi=hi, PA=PA, u=u, r=r, FP_rest=FP_rest)
fig, ax = plt.subplots(1,2, figsize=(6.6,2.55))
for lamB, ls, lab in [(0.035,"-","blind mass $\\lambda_{B+}=0.035$"),(0.014,"--","after a detecting transformation, $\\lambda_{B+}=0.014$")]:
    g = gate(lamB)
    ax[0].plot(V, g["FA"], "k"+ls, lw=1.2, label=lab)
    ax[0].axhline(lamB, color="0.5", lw=0.6, ls=":")
ax[0].set_ylim(0, 0.06); ax[0].set_xlabel("conditionally independent views $|V|$")
ax[0].set_ylabel("false-accept mass"); ax[0].set_title("(a) majority gate: the floor is $\\lambda_{B+}$", fontsize=9)
ax[0].legend(fontsize=6.3, frameon=False, loc="upper right")
g = gate(0.035)
ax[1].fill_between(V, g["lo"], g["hi"], color="0.85", label="identified set from agreement data")
ax[1].plot(V, g["prec"], "k-", lw=1.2, label="true precision")
n = 200; k = np.round(g["r"]*n)
r_lo = Beta.ppf(0.025, k, n-k+1); r_hi = Beta.ppf(0.975, k+1, n-k)
p_lo = 1 - (g["FP_rest"] + g["u"]*r_hi)/g["PA"]; p_hi = 1 - (g["FP_rest"] + g["u"]*r_lo)/g["PA"]
idx = slice(None,None,2)
ax[1].errorbar(V[idx], g["prec"][idx], yerr=[(g["prec"]-p_lo)[idx], (p_hi-g["prec"])[idx]], fmt="none", ecolor="k", capsize=2, lw=0.8, label="95% CI with 200 gold labels in $U^+$")
ax[1].set_ylim(0.4,1.02); ax[1].set_xlabel("conditionally independent views $|V|$")
ax[1].set_ylabel("precision of accepted set"); ax[1].set_title("(b) what agreement vs. a gold audit certifies", fontsize=9)
ax[1].legend(fontsize=6.3, frameon=False, loc="lower left")
from pathlib import Path
out = Path(__file__).resolve().parent
plt.tight_layout()
plt.savefig(out / "fig_gate_v02.pdf")
plt.savefig(out / "fig_gate_v02.png", dpi=150)
for key in ["FA","prec","lo","hi"]:
    print(key, np.round(g[key][[0,-1]],3))
print("CI width at V=5 and V=25:", np.round((p_hi-p_lo)[[0,-1]],3))
print("limit precision:", (cp+lamE)/(cp+lamE+0.035))