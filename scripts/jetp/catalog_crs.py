# WARNING: AI-generated, not human-reviewed
"""Tirage OECD CRS (microdonnees activite) pour la courbe de reference JETP.

Source : OECD SDMX, dataflow OECD.DCD.FSD:DSD_CRS@DF_CRS(1.6),
endpoint https://sdmx.oecd.org/dcd-public/rest/data/...

Ordre des dimensions du DSD (11) :
  DONOR . RECIPIENT . SECTOR . MEASURE . CHANNEL . MODALITY
        . FLOW_TYPE . PRICE_BASE . MD_DIM . MD_ID . UNIT_MEASURE

MD_DIM = 'DD' selectionne les lignes de microdonnees (une par activite CRS),
qui portent OECD_ID / DONOR_PROJECT_ID / PROJECT_TITLE. MD_DIM = '_T' donne
les agregats. On tire les deux : les microdonnees pour l'appariement au
niveau activite, les agregats comme controle de couverture.

Sortie : un CSV gzip par (pays, annee) sous le repertoire --output.

L'API OCDE limite le debit (HTTP 429 au-dela d'une centaine de requetes
rapprochees) : utiliser --pause 20, un tirage complet prend ~30 min. C'est
pourquoi l'etape `jetp_pull` de dvc.yaml est `frozen` — le tirage archive
sous data/jetp/crs/ est l'entree de reference, pas un tirage neuf.
"""
import argparse
import gzip
import time
import urllib.error
import urllib.request
from pathlib import Path

from script_io_args import parse_io_args, validate_io
from utils import get_logger

BASE = ("https://sdmx.oecd.org/dcd-public/rest/data/"
        "OECD.DCD.FSD,DSD_CRS@DF_CRS,1.6/")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

DIMS = ["DONOR", "RECIPIENT", "SECTOR", "MEASURE", "CHANNEL", "MODALITY",
        "FLOW_TYPE", "PRICE_BASE", "MD_DIM", "MD_ID", "UNIT_MEASURE"]

# Codes objet CRS du secteur energie (DAC 230). Liste post-2016 ;
# les codes hérités d'avant la refonte 2016 sont ajoutés en fin de liste
# et testés séparément (voir --legacy-sectors).
ENERGY_SECTORS = [
    "23110", "23181", "23182", "23183",
    "23210", "23220", "23230", "23231", "23232", "23240", "23250",
    "23260", "23270",
    "23310", "23320", "23330", "23340", "23350", "23360",
    "23410", "23510",
    "23610", "23620", "23630", "23631", "23640", "23641", "23642",
]
# Codes energie d'avant la refonte 2016 (CRS purpose codes historiques).
LEGACY_SECTORS = [
    "23010", "23020", "23030", "23040", "23050", "23055", "23061",
    "23062", "23063", "23064", "23065", "23066", "23067", "23068",
    "23069", "23070", "23081", "23082",
]

COUNTRIES = ["ZAF", "IDN", "VNM", "SEN"]

log = get_logger("catalog_crs")


def build_key(**kw) -> str:
    return ".".join(kw.get(d, "") for d in DIMS)


def fetch(url: str, retries: int = 4, pause: float = 5.0) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read()[:200]
            if e.code == 404:
                log.info("404 (aucune donnee) %s", url[:120])
                return b""
            log.warning("HTTP %s (essai %d) %s", e.code, attempt + 1, body)
        except Exception as e:
            log.warning("erreur reseau (essai %d) : %s", attempt + 1, e)
        time.sleep(pause * (attempt + 1))
    return None


def pull_year(country: str, year: int, sectors: list[str], md_dim: str,
              outdir: Path, force: bool) -> Path | None:
    tag = "micro" if md_dim == "DD" else "agg"
    out = outdir / f"crs_{country}_{year}_{tag}.csv.gz"
    if out.exists() and not force and out.stat().st_size > 0:
        log.info("deja present : %s", out.name)
        return out
    key = build_key(RECIPIENT=country, SECTOR="+".join(sectors), MD_DIM=md_dim)
    url = (f"{BASE}{key}?startPeriod={year}&endPeriod={year}"
           f"&dimensionAtObservation=AllDimensions&format=csvfile")
    data = fetch(url)
    if data is None:
        log.error("ECHEC %s %s %s", country, year, tag)
        return None
    with gzip.open(out, "wb") as fh:
        fh.write(data)
    nl = data.count(b"\n")
    log.info("%s %s %s : %d lignes, %d octets", country, year, tag, nl, len(data))
    return out


def main() -> None:
    io_args, extra = parse_io_args()
    validate_io(output=io_args.output)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--countries", nargs="+", default=COUNTRIES)
    p.add_argument("--start", type=int, default=2006)
    p.add_argument("--end", type=int, default=2024)
    p.add_argument("--md-dim", nargs="+", default=["DD", "_T"])
    p.add_argument("--legacy-sectors", action="store_true",
                   help="ajoute les codes objet energie d'avant 2016")
    p.add_argument("--force", action="store_true")
    p.add_argument("--pause", type=float, default=0.0,
                   help="pause entre requetes (s), contre le 429 de l API OECD")
    a = p.parse_args(extra)
    outdir = Path(io_args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    sectors = ENERGY_SECTORS + (LEGACY_SECTORS if a.legacy_sectors else [])
    for c in a.countries:
        for y in range(a.start, a.end + 1):
            for md in a.md_dim:
                pull_year(c, y, sectors, md, outdir, a.force)
                time.sleep(a.pause)


if __name__ == "__main__":
    main()
