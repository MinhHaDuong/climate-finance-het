"""Probe: Œconomia manuscript bibliography vs refined corpus (ticket 0288 angle).

Extracts cited keys from manuscript.qmd, resolves them in main.bib,
matches each against refined_works.csv by DOI then normalized title,
and reports the misses with entry type and year.
"""

import argparse
import csv
import logging
import re
import sys
import unicodedata

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def norm_doi(d: str) -> str:
    d = d.strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if d.startswith(p):
            d = d[len(p):]
    return d.strip("/ ")


def parse_bib(path: str) -> dict[str, dict]:
    text = open(path, encoding="utf-8").read()
    entries = {}
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        etype, key = m.group(1).lower(), m.group(2)
        start = m.end()
        depth = 1
        i = text.index("{", m.start())
        # walk braces from the entry-opening brace
        depth, j = 0, i
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[start:j]
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*[{\"]", body):
            fname = fm.group(1).lower()
            k = fm.end() - 1
            if body[k] == '"':
                end = body.index('"', k + 1)
                fields[fname] = body[k + 1:end]
            else:
                d2, k2 = 0, k
                while k2 < len(body):
                    if body[k2] == "{":
                        d2 += 1
                    elif body[k2] == "}":
                        d2 -= 1
                        if d2 == 0:
                            break
                    k2 += 1
                fields[fname] = body[k + 1:k2]
        val = {f: re.sub(r"[{}]", "", v).strip() for f, v in fields.items()}
        val["_type"] = etype
        entries[key] = val
    return entries


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qmd", required=True)
    ap.add_argument("--bib", required=True)
    ap.add_argument("--corpus", required=True)
    args = ap.parse_args()

    qmd = open(args.qmd, encoding="utf-8").read()
    # strip code blocks to avoid @ false positives
    qmd = re.sub(r"```.*?```", "", qmd, flags=re.S)
    keys = set(re.findall(r"@([A-Za-z][A-Za-z0-9_:.#$%&+?<>~/-]*[A-Za-z0-9])", qmd))

    bib = parse_bib(args.bib)
    cited = {k: bib[k] for k in keys if k in bib}
    log.info("cited keys found in qmd: %d ; resolved in bib: %d", len(keys & set(bib)), len(cited))
    unresolved = sorted(k for k in keys if k not in bib)
    if unresolved:
        log.info("tokens not in bib (ignored, likely emails/tables): %s", ", ".join(unresolved[:15]))

    corpus_dois: set[str] = set()
    corpus_titles: set[str] = set()
    csv.field_size_limit(sys.maxsize)
    with open(args.corpus, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        doi_col = next((c for c in cols if c.lower() == "doi"), None)
        title_col = next((c for c in cols if c.lower() in ("title", "display_name")), None)
        log.info("corpus columns used: doi=%s title=%s (of %d cols)", doi_col, title_col, len(cols))
        for row in reader:
            if doi_col and row.get(doi_col):
                corpus_dois.add(norm_doi(row[doi_col]))
            if title_col and row.get(title_col):
                corpus_titles.add(norm_title(row[title_col]))
    log.info("corpus: %d dois, %d titles", len(corpus_dois), len(corpus_titles))

    hits, misses = [], []
    for key, e in sorted(cited.items()):
        doi = norm_doi(e.get("doi", "")) if e.get("doi") else ""
        title = norm_title(e.get("title", "")) if e.get("title") else ""
        how = None
        if doi and doi in corpus_dois:
            how = "doi"
        elif title and title in corpus_titles:
            how = "title"
        (hits if how else misses).append((key, e, how))

    log.info("\n=== IN CORPUS: %d ===", len(hits))
    for key, e, how in hits:
        log.info("  [%s] %s (%s) %s", how, key, e.get("year", "?"), e.get("title", "")[:70])
    log.info("\n=== NOT IN CORPUS: %d ===", len(misses))
    for key, e, _ in misses:
        log.info("  %-12s %-35s (%s) doi=%s\n      %s",
                 e["_type"], key, e.get("year", "?"),
                 e.get("doi", "-")[:40], e.get("title", "")[:90])


if __name__ == "__main__":
    main()
