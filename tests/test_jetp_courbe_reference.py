"""Non-régression du portage de la chaîne CRS JETP (ticket 0713).

La chaîne produisait `courbe-reference-decaissement-2026-09-08.csv` hors dépôt.
Après portage sous `scripts/jetp/` + DVC, elle doit rendre exactement la même
table, cellule par cellule, **rejouée sur les mêmes `.csv.gz` archivés** — pas
sur un nouveau tirage OCDE, qui mesurerait les révisions de l'OCDE et non le
portage (ticket 0713 § Test).

Deux tiers :

- tier rapide : le résultat central du papier (98,6 % appui budgétaire contre
  37,3 % type projet, à quatre ans) est pinné sur la référence versionnée, de
  sorte qu'une réécriture silencieuse de la référence se voie ;
- tier `integration` : la chaîne portée est rejouée en sous-processus depuis
  `data/jetp/crs/` et sa sortie est comparée à la référence. Le test **échoue**
  si les données DVC sont absentes — un skip silencieux rendrait « tout va bien » indiscernable
  de « je n'ai pas pu regarder ».
"""

import csv
import os
import subprocess
import sys

import pytest
from _source_roots import source_root_env

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REFERENCE = os.path.join(
    BASE, "conception", "jetp", "papier-court-mesure",
    "courbe-reference-decaissement-2026-09-08.csv",
)
CRS_DIR = os.path.join(BASE, "data", "jetp", "crs")
JETP_SCRIPTS = os.path.join(BASE, "scripts", "jetp")

# Le résultat central : appui budgétaire A01/A02 contre type projet C01,
# agrégé sur les quatre pays, cohortes d'engagement 2006-2020, horizon 4 ans.
RESULTAT_CENTRAL = {
    "prets ODA, appui budgetaire A01/A02": 98.56,
    "prets ODA, type projet C01": 37.35,
}


pytestmark = [
    pytest.mark.wp_jetp,
    pytest.mark.wp_finance,
]

def _read(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _central(rows):
    out = {}
    for r in rows:
        if (r["pays"] == "AGREGE-4-PAYS"
                and r["cohorte"] == "reference 2006-2020"
                and r["horizon_ans"] == "4"
                and r["perimetre"] in RESULTAT_CENTRAL):
            out[r["perimetre"]] = float(r["taux_pondere_pct"])
    return out


def test_reference_porte_le_resultat_central():
    """La référence versionnée porte bien 98,6 % contre 37,3 % à quatre ans."""
    assert _central(_read(REFERENCE)) == RESULTAT_CENTRAL


@pytest.mark.integration
def test_chaine_portee_reproduit_la_reference(tmp_path):
    """`compute_cohortes.py` puis `export_courbe_reference.py` rendent la référence à l'identique."""
    assert os.path.isdir(CRS_DIR), (
        f"{CRS_DIR} absent : lancer `dvc pull data/jetp/crs` avant ce test. "
        "Pas de skip — une donnée manquante n'est pas une non-régression."
    )
    gz = [f for f in os.listdir(CRS_DIR) if f.endswith("_micro.csv.gz")]
    assert len(gz) == 80, f"attendu 80 tirages micro archivés, vu {len(gz)}"

    env = dict(os.environ, **source_root_env())
    act = tmp_path / "activites.csv"
    subprocess.run(
        [sys.executable, os.path.join(JETP_SCRIPTS, "compute_cohortes.py"),
         "--datadir", CRS_DIR,
         "--output", str(tmp_path / "cohortes_bloc.csv"),
         "--out-act", str(act),
         "--out-diag", str(tmp_path / "diag.json")],
        check=True, env=env,
    )
    produit = tmp_path / "courbe-reference-decaissement.csv"
    subprocess.run(
        [sys.executable, os.path.join(JETP_SCRIPTS, "export_courbe_reference.py"),
         "--act", str(act), "--output", str(produit)],
        check=True, env=env,
    )

    obtenu, attendu = _read(produit), _read(REFERENCE)
    assert len(obtenu) == len(attendu)
    assert obtenu[0].keys() == attendu[0].keys()
    for i, (o, a) in enumerate(zip(obtenu, attendu)):
        assert o == a, f"ligne {i + 2} diverge :\n  obtenu {o}\n  attendu {a}"
    assert _central(obtenu) == RESULTAT_CENTRAL
