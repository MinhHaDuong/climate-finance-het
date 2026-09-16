# WARNING: AI-generated, not human-reviewed
"""Courbe de reference du decaissement : cohortes d'engagement CRS energie.

Entrees
-------
data/crs_<PAYS>_<ANNEE>_micro.csv.gz : microdonnees CRS (une ligne par
activite x annee x flux x mesure x base de prix), tirees par catalog_crs.py
depuis OECD.DCD.FSD:DSD_CRS@DF_CRS(1.6). Secteur = codes objet energie
(230xx). Pays = ZAF, IDN, VNM, SEN.

Methode
-------
1. Cle d'activite = (DONOR, DONOR_PROJECT_ID). Les lignes sans
   DONOR_PROJECT_ID sont exclues de l'appariement (comptees et rapportees).
2. Annee d'engagement T = premiere annee ou l'activite porte un flux
   FLOW_TYPE = C. Cohorte = T.
3. Denominateur = somme des engagements de l'activite sur toute la fenetre
   d'observation (une activite peut etre re-engagee ; variante T seul
   calculee aussi).
4. Numerateur a l'horizon h = decaissements cumules (FLOW_TYPE = D) des
   annees T a T+h inclus.
5. Censure a droite : une cellule (cohorte, h) n'inclut que les activites
   dont T+h <= derniere annee disponible.

Prix constants (PRICE_BASE = Q, base 2024) par defaut : le ratio compare des
montants de millesimes differents.

Sorties
-------
--output   : une ligne par pays x cohorte x instrument x horizon
--out-act  : table activite par activite (audit)
"""
import argparse
import csv
import glob
import gzip
import json
import statistics
from collections import defaultdict
from pathlib import Path

from script_io_args import parse_io_args, validate_io
from utils import get_logger

log = get_logger("compute_cohortes")

# MEASURE du CRS -> instrument
MEASURE_LABEL = {
    "11": "dons ODA",
    "13": "prets ODA",
    "14": "AAP hors credit export",
    "19": "prise de participation",
    "30": "financement prive du developpement",
    "60": "instruments secteur prive",
}
# Regroupement pour la comparaison dons / prets
INSTRUMENT = {
    "11": "don",
    "13": "pret",
    "14": "autre_officiel",
    "19": "autre_officiel",
    "30": "prive",
    "60": "prive",
}

# Membres des groupes de partenaires internationaux (IPG) des JETP.
# Codes donneurs CRS. Utilise pour la restriction "bailleurs JETP".
IPG_DONORS = {
    "4",    # France
    "5",    # Allemagne
    "12",   # Royaume-Uni
    "302",  # Etats-Unis
    "701",  # Japon
    "6",    # Italie
    "3",    # Danemark
    "21",   # Norvege
    "20",   # Pays-Bas
    "18",   # Suede
    "1",    # Autriche
    "2",    # Belgique
    "22",   # Canada
    "918",  # Institutions UE
    "68",   # UE (variante)
    "count_placeholder",
}


def load(country: str, datadir: Path, price_base: str):
    rows = []
    for f in sorted(glob.glob(str(datadir / f"crs_{country}_*_micro.csv.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["PRICE_BASE"] == price_base:
                    rows.append(r)
    return rows


def build_activities(rows):
    """Agrege les lignes en activites. Retourne (activites, diagnostics)."""
    acts = {}
    diag = {"lignes": len(rows), "sans_project_id": 0,
            "valeur_engagee_totale": 0.0, "valeur_engagee_sans_id": 0.0}
    for r in rows:
        v = float(r["OBS_VALUE"])
        if r["FLOW_TYPE"] == "C":
            diag["valeur_engagee_totale"] += v
        pid = r["DONOR_PROJECT_ID"].strip()
        if not pid:
            diag["sans_project_id"] += 1
            if r["FLOW_TYPE"] == "C":
                diag["valeur_engagee_sans_id"] += v
            continue
        k = (r["DONOR"], pid)
        a = acts.setdefault(k, {
            "donor": r["DONOR"], "donor_name": r["Donor"] if "Donor" in r else "",
            "agency": r["DONOR_AGENCY"], "pid": pid,
            "titre": r["PROJECT_TITLE"], "C": defaultdict(float),
            "D": defaultdict(float), "measures_C": defaultdict(float),
            "secteurs": set(), "finance_types": set(),
            "modalites_C": defaultdict(float),
        })
        y = int(r["TIME_PERIOD"])
        a[r["FLOW_TYPE"]][y] += v
        if r["FLOW_TYPE"] == "C":
            a["measures_C"][r["MEASURE"]] += v
            a["modalites_C"][r["MODALITY"]] += v
        a["secteurs"].add(r["SECTOR"])
        if r["FINANCETYPE_CODE"]:
            a["finance_types"].add(r["FINANCETYPE_CODE"])
        if not a["titre"] and r["PROJECT_TITLE"]:
            a["titre"] = r["PROJECT_TITLE"]
    return acts, diag


def classify(a):
    """Instrument dominant de l'activite, par la mesure des engagements."""
    if not a["measures_C"]:
        return None, None
    m = max(a["measures_C"].items(), key=lambda kv: kv[1])[0]
    return m, INSTRUMENT.get(m, "autre_officiel")


def cohort_profile(acts, last_year, horizons, cohort_defs, denom_mode):
    """Profil de decaissement par cohorte x instrument x horizon."""
    out = []
    per_act = []
    for a in acts.values():
        if not a["C"]:
            continue
        T = min(a["C"])
        measure, instr = classify(a)
        if instr is None:
            continue
        c_all = sum(a["C"].values())
        c_T = a["C"][T]
        denom = c_all if denom_mode == "total" else c_T
        if denom <= 0:
            continue
        modalite = (max(a["modalites_C"].items(), key=lambda kv: kv[1])[0]
                    if a["modalites_C"] else "")
        rec = {"T": T, "instr": instr, "measure": measure, "denom": denom,
               "modalite": modalite,
               "donor": a["donor"], "agency": a["agency"], "pid": a["pid"],
               "titre": a["titre"], "c_all": c_all, "c_T": c_T}
        for h in horizons:
            rec[f"d{h}"] = sum(v for y, v in a["D"].items() if T <= y <= T + h)
        per_act.append(rec)

    for cname, (y0, y1) in cohort_defs.items():
        for instr in ["tous", "don", "pret"]:
            sel = [r for r in per_act if y0 <= r["T"] <= y1
                   and (instr == "tous" or r["instr"] == instr)]
            for h in horizons:
                # censure a droite : T+h doit etre observable
                obs = [r for r in sel if r["T"] + h <= last_year]
                if not obs:
                    continue
                num = sum(r[f"d{h}"] for r in obs)
                den = sum(r["denom"] for r in obs)
                ratios = [min(r[f"d{h}"] / r["denom"], 5.0) for r in obs
                          if r["denom"] > 0]
                ratios.sort()
                out.append({
                    "cohorte": cname, "cohorte_debut": y0, "cohorte_fin": y1,
                    "instrument": instr, "horizon_ans": h,
                    "n_activites": len(obs),
                    "engage_MUSD": round(den, 2),
                    "decaisse_cumul_MUSD": round(num, 2),
                    "taux_pondere_pct": round(100 * num / den, 2) if den else None,
                    "taux_median_activite_pct": round(100 * statistics.median(ratios), 2) if ratios else None,
                    "taux_q1_pct": round(100 * quantile(ratios, .25), 2) if ratios else None,
                    "taux_q3_pct": round(100 * quantile(ratios, .75), 2) if ratios else None,
                    "activites_censurees_exclues": len(sel) - len(obs),
                })
    return out, per_act


def quantile(sorted_vals, q):
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (pos - lo) * (sorted_vals[hi] - sorted_vals[lo])


def main():
    io_args, extra = parse_io_args()
    # Le repertoire de sortie est cree ici plutot que par le Makefile : les
    # etapes dvc.yaml ecrivent sous data/jetp/derived/, gitignore et donc absent
    # d'un worktree neuf, et validate_io echoue sur un parent manquant.
    Path(io_args.output).parent.mkdir(parents=True, exist_ok=True)
    validate_io(output=io_args.output)
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datadir", type=Path, default=Path("data"))
    p.add_argument("--countries", nargs="+", default=["VNM", "ZAF", "IDN", "SEN"])
    p.add_argument("--price-base", default="Q", choices=["Q", "V"],
                   help="Q = prix constants base 2024, V = prix courants")
    p.add_argument("--last-year", type=int, default=2024)
    p.add_argument("--horizons", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    p.add_argument("--denom", default="total", choices=["total", "premier"],
                   help="denominateur : engagements totaux de l activite, "
                        "ou engagement de la seule annee T")
    p.add_argument("--out-act", type=Path)
    p.add_argument("--out-diag", type=Path)
    p.add_argument("--annual-cohorts", action="store_true",
                   help="une cohorte par annee d engagement au lieu des blocs de 4 ans")
    a = p.parse_args(extra)
    a.out_csv = Path(io_args.output)

    cohort_defs = {"2010-2013": (2010, 2013), "2014-2017": (2014, 2017),
                   "2018-2021": (2018, 2021), "2022-2023": (2022, 2023),
                   "2006-2009": (2006, 2009)}
    if a.annual_cohorts:
        cohort_defs = {str(y): (y, y) for y in range(2006, 2024)}
    all_rows, all_acts, diags = [], [], {}
    for c in a.countries:
        rows = load(c, a.datadir, a.price_base)
        if not rows:
            log.warning("aucune donnee pour %s", c)
            continue
        acts, diag = build_activities(rows)
        prof, per_act = cohort_profile(acts, a.last_year, a.horizons,
                                       cohort_defs, a.denom)
        for r in prof:
            r["pays"] = c
        for r in per_act:
            r["pays"] = c
        all_rows += prof
        all_acts += per_act
        diag["activites"] = len(acts)
        diag["annees"] = sorted({int(x["TIME_PERIOD"]) for x in rows})
        diags[c] = diag
        log.info("%s : %d lignes, %d activites, %.1f%% de la valeur engagee "
                 "porte un DONOR_PROJECT_ID", c, diag["lignes"], len(acts),
                 100 * (1 - diag["valeur_engagee_sans_id"] /
                        max(diag["valeur_engagee_totale"], 1e-9)))

    cols = ["pays", "cohorte", "cohorte_debut", "cohorte_fin", "instrument",
            "horizon_ans", "n_activites", "engage_MUSD", "decaisse_cumul_MUSD",
            "taux_pondere_pct", "taux_median_activite_pct", "taux_q1_pct",
            "taux_q3_pct", "activites_censurees_exclues"]
    a.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in sorted(all_rows, key=lambda r: (r["pays"], r["cohorte_debut"],
                                                 r["instrument"], r["horizon_ans"])):
            w.writerow({k: r.get(k) for k in cols})
    log.info("ecrit %s (%d lignes)", a.out_csv, len(all_rows))

    if a.out_act:
        acols = ["pays", "T", "instr", "measure", "modalite", "donor", "agency", "pid",
                 "titre", "c_all", "c_T", "denom"] + [f"d{h}" for h in a.horizons]
        with open(a.out_act, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=acols, extrasaction="ignore")
            w.writeheader()
            for r in sorted(all_acts, key=lambda r: (r["pays"], r["T"])):
                w.writerow(r)
        log.info("ecrit %s (%d activites)", a.out_act, len(all_acts))
    if a.out_diag:
        a.out_diag.write_text(json.dumps(diags, indent=2, default=list),
                              encoding="utf-8")


if __name__ == "__main__":
    main()
