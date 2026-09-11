# WARNING: AI-generated, not human-reviewed
"""Synthese : reference groupee (portefeuille) et dispersion.

Entree : out/<pays>_activites.csv produit par cohortes.py --out-act.
Sortie : --output, CSV de dispersion par bailleur ; tableaux texte sur stdout.
"""
import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

from script_io_args import parse_io_args, validate_io


def load(p):
    with open(p, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh)]


def pooled(acts, h, instr=None, tmin=2006, tmax=2020):
    sel = [a for a in acts if tmin <= int(a["T"]) <= tmax
           and int(a["T"]) + h <= 2024
           and (instr is None or a["instr"] == instr)]
    num = sum(float(a[f"d{h}"]) for a in sel)
    den = sum(float(a["denom"]) for a in sel)
    return sel, num, den, (100 * num / den if den else None)


def main():
    io_args, extra = parse_io_args()
    # Le repertoire de sortie est cree ici plutot que par le Makefile : les
    # etapes dvc.yaml ecrivent sous data/jetp/derived/, gitignore et donc absent
    # d'un worktree neuf, et validate_io echoue sur un parent manquant.
    Path(io_args.output).parent.mkdir(parents=True, exist_ok=True)
    validate_io(output=io_args.output)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--act", type=Path, required=True)
    p.add_argument("--pays", default="VNM")
    p.add_argument("--tmin", type=int, default=2006)
    p.add_argument("--tmax", type=int, default=2020)
    a = p.parse_args(extra)
    a.out_donneur = Path(io_args.output)
    acts = [r for r in load(a.act) if r["pays"] == a.pays]

    print(f"### {a.pays} — reference groupee, engagements {a.tmin}-{a.tmax}\n")
    print("instrument | h | n | engage M$ | decaisse M$ | taux pondere %")
    for instr in [None, "pret", "don", "autre_officiel"]:
        for h in range(5):
            sel, num, den, r = pooled(acts, h, instr, a.tmin, a.tmax)
            if not sel:
                continue
            print(f"{instr or 'tous':16s} | {h} | {len(sel):3d} | {den:9.1f} | "
                  f"{num:9.1f} | {r:6.1f}")
        print()

    # dispersion entre cohortes annuelles (prets)
    print(f"### {a.pays} — dispersion entre cohortes annuelles, prets, h=4\n")
    per_year = {}
    for y in range(a.tmin, a.tmax + 1):
        sel, num, den, r = pooled(acts, 4, "pret", y, y)
        if sel and den > 0:
            per_year[y] = (len(sel), den, r)
    for y, (n, den, r) in sorted(per_year.items()):
        print(f"  {y}  n={n:2d}  engage={den:8.1f} M$  taux={r:6.1f} %")
    vals = [v[2] for v in per_year.values()]
    if vals:
        vals_s = sorted(vals)
        print(f"\n  min={min(vals):.1f}  Q1={statistics.quantiles(vals_s, n=4)[0]:.1f} "
              f" mediane={statistics.median(vals_s):.1f} "
              f" Q3={statistics.quantiles(vals_s, n=4)[2]:.1f}  max={max(vals):.1f}")
        print(f"  moyenne non ponderee={statistics.mean(vals):.1f}  "
              f"ecart-type={statistics.pstdev(vals):.1f}  n_cohortes={len(vals)}")

    # dispersion entre bailleurs (prets)
    print(f"\n### {a.pays} — dispersion entre bailleurs, prets, h=4, "
          f"engagements {a.tmin}-{a.tmax}\n")
    sel, _, _, _ = pooled(acts, 4, "pret", a.tmin, a.tmax)
    byd = defaultdict(lambda: [0.0, 0.0, 0])
    for x in sel:
        d = x["agency"] or x["donor"]
        byd[d][0] += float(x["denom"])
        byd[d][1] += float(x["d4"])
        byd[d][2] += 1
    rows = []
    for d, (den, num, n) in sorted(byd.items(), key=lambda kv: -kv[1][0]):
        r = 100 * num / den if den else None
        rows.append({"bailleur": d, "n_activites": n,
                     "engage_MUSD": round(den, 1),
                     "decaisse_h4_MUSD": round(num, 1),
                     "taux_h4_pct": round(r, 1) if r is not None else ""})
        print(f"  {d[:42]:42s} n={n:2d} engage={den:8.1f} taux={r:6.1f} %")
    if a.out_donneur and rows:
        with open(a.out_donneur, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
