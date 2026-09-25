#!/usr/bin/env python3
"""Figure 1 du papier court JETP — le décaissé du paquet annoncé contre la norme du pays.

Un panneau par pays, chacun à SON horizon. Les quatre JETP n'ayant pas été
signés la même année, un horizon commun les compterait inégalement : l'Afrique
du Sud a eu trois ans depuis sa signature, le Sénégal un seul. Chaque panneau
est donc lu à l'horizon réellement écoulé pour ce pays, la norme du pays étant
prise au même horizon.

Deux dénominateurs, délibérément :
  - la distribution rapporte le décaissé à l'ENGAGEMENT SIGNÉ (norme d'exécution) ;
  - la barre rapporte le décaissé au PAQUET ANNONCÉ (ce qui a été promis).
L'écart entre les deux mesure ce qui n'a jamais quitté l'annonce.

La norme couvre les prêts officiels de type projet, APD et autres flux
officiels : s'en tenir à l'APD excluait les prêts IBRD, donc l'Eskom Just
Energy Transition Project, principal prêt-projet du JETP sud-africain.

Entrée  : analyse-crs/out/activites.csv
Sorties : figure-distribution-decaissement.{pdf,png} + .csv des points tracés
"""
import argparse
import csv
import pathlib

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", nargs="?", type=pathlib.Path, default=pathlib.Path(
    "/home/haduong/CNRS/projets/actifs/jetp/papier-court-mesure/analyse-crs/out/activites.csv"))
parser.add_argument("--rates", type=pathlib.Path, default=ROOT / "data/jetp/rates.csv")
parser.add_argument("--senegal-rate-date", help="Date of the cited EUR/USD ledger rate")
parser.add_argument("--senegal-rate-basis", help="Basis of the cited EUR/USD ledger rate")
parser.add_argument("--output-dir", type=pathlib.Path, default=HERE)
args = parser.parse_args()
if bool(args.senegal_rate_date) != bool(args.senegal_rate_basis):
    parser.error("Senegal rate date and basis must be supplied together")


def senegal_package_usd(path, date, basis):
    """Use one exact, cited ledger key; never guess an exchange rate."""
    with path.open(newline="", encoding="utf-8") as file:
        rows = [row for row in csv.DictReader(file)
                if (row["currency"], row["date"], row["basis"]) == ("EUR", date, basis)]
    if len(rows) != 1:
        raise ValueError(f"Expected one EUR/USD rate for date={date}, basis={basis} in {path}; found {len(rows)}")
    row = rows[0]
    try:
        rate = float(row["rate_to_usd"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Senegal EUR/USD ledger rate must be numeric") from exc
    if not np.isfinite(rate) or rate <= 0 or not row["line_id"] or not row["recorded_at"]:
        raise ValueError("Senegal EUR/USD ledger rate needs a positive value, line_id and recorded_at")
    return 2500 * rate, row["line_id"]


if args.senegal_rate_date:
    senegal_package, rate_line = senegal_package_usd(
        args.rates, args.senegal_rate_date, args.senegal_rate_basis)
else:
    senegal_package, rate_line = None, None
    print("Senegal: no cited EUR/USD rate selected; package percentage withdrawn")
FIN = pd.Timestamp("2024-12-31")           # dernière année du tirage CRS

# pays -> (nom, signature, paquet annoncé en M USD, libellé du paquet, 1re année de cohorte)
JETP = {
    "ZAF": ("Afrique du Sud", "2021-11-02", 8500.0, "8,5 Md$", 2022),
    "IDN": ("Indonésie", "2022-11-15", 20000.0, "20 Md$", 2022),
    "VNM": ("Viêt Nam", "2022-12-14", 15500.0, "15,5 Md$", 2022),
    "SEN": ("Sénégal", "2023-06-22", senegal_package, "2,5 Md€", 2023),
}
NORME, BARRE = "#2a78d6", "#eb6834"

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 9,
    "axes.edgecolor": "#c9c9c4", "axes.linewidth": .8,
    "xtick.color": "#6b6b66", "text.color": "#2b2b28", "axes.labelcolor": "#2b2b28",
})

brut = pd.read_csv(args.source)
brut = brut[brut.denom > 0].copy()
proj = brut[brut.instr.isin(["pret", "autre_officiel"]) & (brut.modalite == "C01")]

rng = np.random.default_rng(0)
fig, axes = plt.subplots(2, 2, figsize=(7.4, 5.3), sharex=True)
traces = []

for ax, (code, (nom, sig, paquet, lib, an0)) in zip(axes.flat, JETP.items()):
    h = int((FIN - pd.Timestamp(sig)).days / 365.25)          # horizon propre au pays
    norme = proj[(proj.pays == code) & (proj["T"] <= 2020)]
    v, w = (100 * norme[f"d{h}"] / norme.denom).values, norme.denom.values
    q1, med, q3 = np.percentile(v, [25, 50, 75])
    pond = 100 * norme[f"d{h}"].sum() / norme.denom.sum()

    ax.hlines(.55, q1, q3, color=NORME, lw=9, alpha=.25, zorder=2)
    ax.vlines(med, .40, .70, color=NORME, lw=2.4, zorder=4)
    ax.scatter(v, .55 + rng.uniform(-.11, .11, len(v)), s=8 + 92 * w / w.max(),
               facecolor=NORME, alpha=.42, edgecolor="white", lw=.6, zorder=3)
    ax.plot([pond], [.55], marker="D", ms=6.5, color=NORME,
            markeredgecolor="white", markeredgewidth=1, zorder=5)

    cohorte = brut[(brut.pays == code) & (brut["T"] >= an0)]
    if paquet is not None:
        pos = 100 * cohorte[f"d{h}"].sum() / paquet
        ax.axvline(pos, color=BARRE, lw=2.6, zorder=6)
        cote = pos > 55
        ax.annotate(f"{pos:.1f} % du paquet annoncé\ndécaissé", (pos + (-3 if cote else 3), .03),
                    color=BARRE, fontsize=8, fontweight="bold",
                    ha="right" if cote else "left", va="center", annotation_clip=False)
    else:
        ax.text(.5, .09, "Taux paquet indisponible : conversion €/$ non sourcée",
                transform=ax.transAxes, color=BARRE, fontsize=7.5, ha="center")

    ax.set_title(f"{nom}  ·  {h} an{'s' if h > 1 else ''}  ·  paquet {lib}",
                 fontsize=9.5, loc="left", pad=5)
    ax.set_xlim(-8, 104); ax.set_ylim(-.22, .95)
    ax.set_yticks([]); ax.set_xticks(range(0, 101, 25))
    ax.grid(axis="x", color="#e6e6e2", lw=.7); ax.set_axisbelow(True)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    traces += [{"pays": nom, "horizon_ans": h, "serie": "norme, activité", "taux_pct": float(x)} for x in v]
    traces.append({"pays": nom, "horizon_ans": h, "serie": "norme, pondérée", "taux_pct": float(pond)})
    if paquet is not None:
        traces.append({"pays": nom, "horizon_ans": h, "serie": "décaissé / paquet annoncé", "taux_pct": float(pos)})

for ax in axes[1]:
    ax.set_xlabel("part décaissée (%)")
leg = [plt.Line2D([], [], ls="", marker="o", ms=7, mfc=NORME, mec="white",
                  label="norme du pays : une activité, aire ∝ montant engagé"),
       plt.Line2D([], [], ls="", marker="D", ms=6.5, color=NORME, mec="white",
                  label="norme, taux pondéré du portefeuille"),
       plt.Line2D([], [], color=BARRE, lw=2.6, label="décaissé JETP / paquet annoncé")]
fig.legend(handles=leg, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(.5, -.02), fontsize=8)
fig.suptitle("Le décaissé du paquet annoncé, contre la norme d'exécution du pays",
             fontsize=11.5, x=.012, ha="left", y=.99)
fig.text(.012, .925, "Chaque pays à son propre horizon, le temps écoulé depuis sa signature : les quatre JETP\n"
         "n'ont pas été signés la même année. Norme et barre y sont prises au même horizon.",
         fontsize=8, color="#6b6b66", ha="left", va="top")
senegal_note = ("Sénégal : paquet de 2,5 Md€ (déclaration politique du 22 juin 2023) ; "
                "taux €/$ non sourcé, barre retirée.") if rate_line is None else (
                "Sénégal : 2,5 Md€ (déclaration politique du 22 juin 2023) ; "
                f"taux €/$ : {args.senegal_rate_date}, {args.senegal_rate_basis}, ligne {rate_line}.")
footer = ("Source : OCDE CRS, microdonnées, tirage du 2026-09-08 (dernière année 2024).\n"
          "Norme : prêts officiels de type projet (C01), secteur énergie, engagements ≤ 2020, rapportés à l'engagement signé.\n"
          "Barre : toutes opérations engagées depuis la signature, rapportées au paquet annoncé.\n"
          + senegal_note)
fig.text(.012, -.055, footer,
         fontsize=7.2, color="#6b6b66", ha="left", va="top")
fig.tight_layout(rect=[0, .06, 1, .875])
for ext in ("pdf", "png"):
    metadata = {"CreationDate": None, "ModDate": None} if ext == "pdf" else None
    fig.savefig(args.output_dir / f"figure-distribution-decaissement.{ext}",
                dpi=200, bbox_inches="tight", metadata=metadata)
pd.DataFrame(traces).to_csv(args.output_dir / "figure-distribution-decaissement.csv", index=False)
print(f"{len(traces)} points tracés")
