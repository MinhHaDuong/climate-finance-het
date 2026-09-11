#!/usr/bin/env python3
"""Figure 1 du papier court JETP — l'écart à la norme, distribution par pays.

Un panneau par pays. Dans chacun, la distribution des taux de décaissement
observés à 3 et 4 ans pour les prêts-projet du secteur énergie (un point par
activité, aire proportionnelle au montant engagé), et la barre de position
observée de la cohorte JETP sur le MÊME instrument.

Trois avertissements portés par la figure elle-même :
  - projet n'est pas programme : tout ici est prêt-projet C01, l'appui
    budgétaire A01/A02 est exclu des deux côtés de la comparaison ;
  - la cohorte JETP n'est pas observable à 3 ou 4 ans (le CRS s'arrête en
    2024) — sa barre est à h = 2 et le dit ;
  - les effectifs JETP sont des poignées d'activités, affichés tels quels.

Entrée  : analyse-crs/out/activites.csv
Sorties : figure-distribution-decaissement.{pdf,png} + .csv des points tracés
"""
import pathlib, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).parent
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                   "/home/haduong/CNRS/projets/actifs/jetp/papier-court-mesure/analyse-crs/out/activites.csv")

PAYS = {"VNM": "Viêt Nam", "IDN": "Indonésie", "ZAF": "Afrique du Sud", "SEN": "Sénégal"}
NORME_H3, NORME_H4, JETP_C = "#8cb8e8", "#2a78d6", "#eb6834"   # bleu séquentiel + orange catégoriel
JETP_H = 2

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 9,
    "axes.edgecolor": "#c9c9c4", "axes.linewidth": 0.8,
    "xtick.color": "#6b6b66", "ytick.color": "#2b2b28",
    "text.color": "#2b2b28", "axes.labelcolor": "#2b2b28",
})

d = pd.read_csv(SRC)
d = d[(d.denom > 0) & (d.instr == "pret") & (d.modalite == "C01")].copy()
for h in (2, 3, 4):
    d[f"r{h}"] = 100 * d[f"d{h}"] / d.denom
hist, jetp = d[d["T"] <= 2020], d[d["T"].between(2022, 2023)]

rng = np.random.default_rng(0)
fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.6), sharex=True)
traces = []

for ax, (code, nom) in zip(axes.flat, PAYS.items()):
    h_ = hist[hist.pays == code]
    for i, (h, couleur) in enumerate([(3, NORME_H3), (4, NORME_H4)]):
        y = 1 - i * 0.55
        v, w = h_[f"r{h}"].values, h_.denom.values
        if len(v):
            q1, med, q3 = np.percentile(v, [25, 50, 75])
            ax.hlines(y, q1, q3, color=couleur, lw=7, alpha=.28, zorder=2)
            ax.vlines(med, y - .11, y + .11, color=couleur, lw=2.4, zorder=4)
            ax.scatter(v, y + rng.uniform(-.09, .09, len(v)), s=8 + 92 * w / w.max(),
                       facecolor=couleur, alpha=.45, edgecolor="white", lw=.6, zorder=3)
            pond = 100 * h_[f"d{h}"].sum() / h_.denom.sum()
            ax.plot([pond], [y], marker="D", ms=6, color=couleur,
                    markeredgecolor="white", markeredgewidth=1, zorder=5)
            ax.text(-4, y, f"{h} ans", ha="right", va="center", fontsize=8.5, color=couleur)
            traces += [{"pays": nom, "serie": f"norme h={h}", "taux_pct": float(x)} for x in v]

    g = jetp[jetp.pays == code]
    if len(g):
        pos = 100 * g[f"d{JETP_H}"].sum() / g.denom.sum()
        ax.axvline(pos, color=JETP_C, lw=2.4, zorder=6)
        cote = "left" if pos > 50 else "right"
        dx = -3 if cote == "left" else 3
        ax.annotate(f"JETP {pos:.0f} % à {JETP_H} ans\nn = {len(g)} prêt-projet", (pos + dx, -0.30),
                    color=JETP_C, fontsize=7.8, fontweight="bold",
                    ha="right" if cote == "left" else "left", va="center",
                    annotation_clip=False)
        traces.append({"pays": nom, "serie": f"JETP h={JETP_H}", "taux_pct": float(pos)})

    ax.set_title(f"{nom}   ·   norme : n = {len(h_)} prêts-projet", fontsize=9.5, loc="left", pad=5)
    ax.set_xlim(-14, 104); ax.set_ylim(-0.62, 1.32)
    ax.set_yticks([]); ax.set_xticks(range(0, 101, 25))
    ax.grid(axis="x", color="#e6e6e2", lw=.7); ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

for ax in axes[1]:
    ax.set_xlabel("part de l'engagement décaissée (%)")
h = [plt.Line2D([], [], ls="", marker="o", ms=7, mfc=NORME_H3, mec="white", label="activité, norme à 3 ans"),
     plt.Line2D([], [], ls="", marker="o", ms=7, mfc=NORME_H4, mec="white", label="activité, norme à 4 ans"),
     plt.Line2D([], [], ls="", marker="D", ms=6, color="#2a78d6", mec="white", label="taux pondéré du portefeuille"),
     plt.Line2D([], [], color=JETP_C, lw=2.4, label="cohorte JETP observée")]
fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(.5, -.015), fontsize=8)
fig.suptitle("L'écart à la norme : où se place le JETP dans la distribution du pays",
             fontsize=11.5, x=.012, ha="left", y=.985)
fig.text(.012, .935, "Prêts-projet ODA au secteur énergie (CRS C01) — l'appui budgétaire est exclu des deux côtés. "
         "Aire du point ∝ montant engagé.", fontsize=8, color="#6b6b66", ha="left")
fig.text(.012, -.075, "Source : OCDE CRS, microdonnées, tirage du 2026-09-08. Norme : engagements ≤ 2020, observés à 3 et 4 ans. "
         "La cohorte JETP (2022-2023) n'est pas observable au-delà de 2 ans.", fontsize=7.5, color="#6b6b66", ha="left")
fig.tight_layout(rect=[0, .05, 1, .915])
for ext in ("pdf", "png"):
    fig.savefig(HERE / f"figure-distribution-decaissement.{ext}", dpi=200, bbox_inches="tight")
pd.DataFrame(traces).to_csv(HERE / "figure-distribution-decaissement.csv", index=False)
print(f"{len(traces)} points -> {HERE/'figure-distribution-decaissement.pdf'}")
