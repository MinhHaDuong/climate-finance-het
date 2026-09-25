"""The Senegal CRS/package comparison requires an explicit sourced FX rate."""

import csv
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "conception/jetp/papier-court-mesure/figure-distribution-decaissement.py"


def _inputs(tmp_path):
    source = tmp_path / "activites.csv"
    with source.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["pays", "denom", "instr", "modalite", "T", "d1", "d2", "d3"])
        writer.writeheader()
        for country in ("ZAF", "IDN", "VNM", "SEN"):
            writer.writerow(dict(pays=country, denom=100, instr="pret", modalite="C01",
                                 T=2020, d1=10, d2=20, d3=30))
            writer.writerow(dict(pays=country, denom=100, instr="pret", modalite="C01",
                                 T=2023, d1=10, d2=20, d3=30))
    rates = tmp_path / "rates.csv"
    rates.write_text("currency,date,basis,rate_to_usd,line_id,recorded_at\n", encoding="utf-8")
    return source, rates


def _run(tmp_path, source, rates, *options):
    return subprocess.run([sys.executable, str(SCRIPT), str(source), "--rates", str(rates),
                           "--output-dir", str(tmp_path), *options],
                          capture_output=True, text=True)


def test_uncited_rate_withdraws_senegal_percentage(tmp_path):
    source, rates = _inputs(tmp_path)
    result = _run(tmp_path, source, rates)
    assert result.returncode == 0, result.stderr
    assert "package percentage withdrawn" in result.stdout
    rows = list(csv.DictReader((tmp_path / "figure-distribution-decaissement.csv").open()))
    assert len([row for row in rows if row["serie"] == "décaissé / paquet annoncé"]) == 3
    assert not any(row["pays"] == "Sénégal" and row["serie"] == "décaissé / paquet annoncé"
                   for row in rows)


def test_missing_or_mismatched_ledger_key_fails(tmp_path):
    source, rates = _inputs(tmp_path)
    key = ("--senegal-rate-date", "2023-06-22", "--senegal-rate-basis", "signature")
    missing = _run(tmp_path, source, rates, *key)
    assert missing.returncode != 0
    assert "Expected one EUR/USD rate" in missing.stderr

    with rates.open("a") as file:
        file.write("EUR,2023-06-23,signature,1.1,L-example,2026-09-25\n")
    mismatched = _run(tmp_path, source, rates, *key)
    assert mismatched.returncode != 0
    assert "Expected one EUR/USD rate" in mismatched.stderr


def test_uncited_ledger_row_fails(tmp_path):
    source, rates = _inputs(tmp_path)
    with rates.open("a") as file:
        file.write("EUR,2023-06-22,signature,1.1,,2026-09-25\n")
    result = _run(tmp_path, source, rates, "--senegal-rate-date", "2023-06-22",
                  "--senegal-rate-basis", "signature")
    assert result.returncode != 0
    assert "line_id" in result.stderr


def test_selected_cited_rate_restores_senegal_percentage(tmp_path):
    source, rates = _inputs(tmp_path)
    with rates.open("a") as file:
        file.write("EUR,2023-06-22,signature,1.1,L-fixture,2026-09-25\n")
    result = _run(tmp_path, source, rates, "--senegal-rate-date", "2023-06-22",
                  "--senegal-rate-basis", "signature")
    assert result.returncode == 0, result.stderr
    rows = list(csv.DictReader((tmp_path / "figure-distribution-decaissement.csv").open()))
    selected = [row for row in rows if row["pays"] == "Sénégal"
                and row["serie"] == "décaissé / paquet annoncé"]
    assert len(selected) == 1
    assert float(selected[0]["taux_pct"]) == 100 * 10 / (2500 * 1.1)
