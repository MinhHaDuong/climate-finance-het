# WARNING: AI-generated, not human-reviewed
"""Construit le CSV livrable : une ligne par pays x cohorte x perimetre x horizon.

Entree  : out/activites.csv (produit par cohortes.py --out-act)
Sortie  : --output, le CSV livrable courbe-reference-decaissement.csv

Colonnes : taux ponderes par les montants, plus la dispersion inter-activites
(mediane, Q1, Q3) et le nombre d'activites exclues par la censure a droite.
"""
import argparse
import csv
import statistics
from pathlib import Path

from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("livrable_csv")

LAST = 2024
COHORTES = [("2006-2009", 2006, 2009), ("2010-2013", 2010, 2013),
            ("2014-2017", 2014, 2017), ("2018-2021", 2018, 2021),
            ("2022-2023 (JETP)", 2022, 2023),
            ("reference 2006-2020", 2006, 2020)]
PERIMETRES = [
    ("tous instruments, toutes modalites", None, None),
    ("prets ODA, toutes modalites", "pret", None),
    ("dons ODA, toutes modalites", "don", None),
    ("prets ODA, type projet C01", "pret", {"C01"}),
    ("dons ODA, type projet C01", "don", {"C01"}),
    ("tous instruments, type projet C01", None, {"C01"}),
    ("prets ODA, appui budgetaire A01/A02", "pret", {"A01", "A02"}),
]


def quantile(v, q):
    if not v:
        return None
    if len(v) == 1:
        return v[0]
    pos = q * (len(v) - 1)
    lo = int(pos); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (pos - lo) * (v[hi] - v[lo])


def main():
    io_args, extra = parse_io_args()
    # Le repertoire de sortie est cree ici plutot que par le Makefile : les
    # etapes dvc.yaml ecrivent sous data/jetp/derived/, gitignore et donc absent
    # d'un worktree neuf, et validate_io echoue sur un parent manquant.
    Path(io_args.output).parent.mkdir(parents=True, exist_ok=True)
    validate_io(output=io_args.output)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--act", type=Path, default=Path("out/activites.csv"))
    a = p.parse_args(extra)
    a.out = Path(io_args.output)
    acts = list(csv.DictReader(open(a.act, encoding="utf-8")))
    pays_list = sorted({x["pays"] for x in acts})
    rows = []
    for pays in pays_list + ["AGREGE-4-PAYS"]:
        base = acts if pays == "AGREGE-4-PAYS" else [x for x in acts if x["pays"] == pays]
        for cname, y0, y1 in COHORTES:
            for pname, instr, mod in PERIMETRES:
                cand = [x for x in base if y0 <= int(x["T"]) <= y1
                        and (instr is None or x["instr"] == instr)
                        and (mod is None or x["modalite"] in mod)]
                if not cand:
                    continue
                for h in range(5):
                    obs = [x for x in cand if int(x["T"]) + h <= LAST]
                    if not obs:
                        continue
                    den = sum(float(x["denom"]) for x in obs)
                    num = sum(float(x[f"d{h}"]) for x in obs)
                    if den <= 0:
                        continue
                    ratios = sorted(min(float(x[f"d{h}"]) / float(x["denom"]), 5.0)
                                    for x in obs if float(x["denom"]) > 0)
                    rows.append({
                        "pays": pays, "cohorte": cname,
                        "cohorte_debut": y0, "cohorte_fin": y1,
                        "perimetre": pname, "horizon_ans": h,
                        "n_activites": len(obs),
                        "engage_MUSD_const2024": round(den, 2),
                        "decaisse_cumul_MUSD_const2024": round(num, 2),
                        "taux_pondere_pct": round(100 * num / den, 2),
                        "taux_median_activite_pct": round(100 * statistics.median(ratios), 2),
                        "taux_q1_activite_pct": round(100 * quantile(ratios, .25), 2),
                        "taux_q3_activite_pct": round(100 * quantile(ratios, .75), 2),
                        "activites_exclues_censure": len(cand) - len(obs),
                    })
    cols = list(rows[0])
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    log.info("ecrit %s : %d lignes", a.out, len(rows))


if __name__ == "__main__":
    main()
