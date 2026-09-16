# WARNING: AI-generated, not human-reviewed
"""Tableau final : reference groupee par pays, instrument et modalite.

Entree : out/activites.csv (compute_cohortes.py --out-act).
Sortie : --output, CSV livrable ; tableaux texte journalises.
"""
import argparse
import csv
import statistics
from pathlib import Path

from script_io_args import parse_io_args, validate_io
from utils import get_logger

LAST = 2024

log = get_logger("summarize_reference_groupee")


def pool(acts, h, pays=None, instr=None, mod=None, t0=2006, t1=2020):
    sel = [a for a in acts
           if (pays is None or a["pays"] == pays)
           and t0 <= int(a["T"]) <= t1
           and int(a["T"]) + h <= LAST
           and (instr is None or a["instr"] == instr)
           and (mod is None or a["modalite"] in mod)]
    den = sum(float(a["denom"]) for a in sel)
    num = sum(float(a[f"d{h}"]) for a in sel)
    return sel, den, num, (100 * num / den if den else None)


def main():
    io_args, extra = parse_io_args()
    # Le repertoire de sortie est cree ici plutot que par le Makefile : les
    # etapes dvc.yaml ecrivent sous data/jetp/derived/, gitignore et donc absent
    # d'un worktree neuf, et validate_io echoue sur un parent manquant.
    Path(io_args.output).parent.mkdir(parents=True, exist_ok=True)
    validate_io(output=io_args.output)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--act", type=Path, default=Path("out/activites.csv"))
    p.add_argument("--pays", nargs="+", default=["VNM", "ZAF", "IDN", "SEN"])
    a = p.parse_args(extra)
    a.out = Path(io_args.output)
    acts = list(csv.DictReader(open(a.act, encoding="utf-8")))

    rows = []
    combos = [
        ("tous instruments, toutes modalites", None, None),
        ("prets ODA, toutes modalites", "pret", None),
        ("dons ODA, toutes modalites", "don", None),
        ("prets ODA, type projet (C01)", "pret", {"C01"}),
        ("tous instruments, type projet (C01)", None, {"C01"}),
        ("prets ODA, appui budgetaire (A01/A02)", "pret", {"A01", "A02"}),
    ]
    log.info(f"{'pays':5s} {'perimetre':40s} {'n':>4s} {'engage M$':>10s} "
          + " ".join(f"h={h:1d}" for h in range(5)))
    for pays in a.pays + [None]:
        for label, instr, mod in combos:
            line = {"pays": pays or "AGREGE", "perimetre": label}
            n0 = den0 = 0
            vals = []
            for h in range(5):
                sel, den, num, r = pool(acts, h, pays, instr, mod)
                line[f"taux_h{h}_pct"] = round(r, 1) if r is not None else ""
                if h == 0:
                    n0, den0 = len(sel), den
                vals.append(f"{r:5.1f}" if r is not None else "    .")
            line["n_activites"] = n0
            line["engage_MUSD"] = round(den0, 1)
            # dispersion entre cohortes annuelles a h=4
            per_year = []
            for y in range(2006, 2021):
                s, d, nm, rr = pool(acts, 4, pays, instr, mod, y, y)
                if d > 0:
                    per_year.append(rr)
            if len(per_year) >= 3:
                ps = sorted(per_year)
                line["h4_cohortes_n"] = len(ps)
                line["h4_min_pct"] = round(min(ps), 1)
                line["h4_mediane_pct"] = round(statistics.median(ps), 1)
                line["h4_max_pct"] = round(max(ps), 1)
                line["h4_ecart_type"] = round(statistics.pstdev(ps), 1)
            if n0:
                rows.append(line)
                log.info(f"{line['pays']:5s} {label:40s} {n0:4d} {den0:10.1f} "
                      + " ".join(vals))
        log.info("")

    cols = ["pays", "perimetre", "n_activites", "engage_MUSD"] + \
           [f"taux_h{h}_pct" for h in range(5)] + \
           ["h4_cohortes_n", "h4_min_pct", "h4_mediane_pct", "h4_max_pct",
            "h4_ecart_type"]
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


if __name__ == "__main__":
    main()
