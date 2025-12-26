#!/usr/bin/env python3

import csv
from collections import defaultdict
from pathlib import Path

# =====================
# Einstellungen
# =====================
CSV_DATEI = "/home/patrick/Documents/hibiscus/hibiscus-export-20251226.csv"  # Pfad zu deiner CSV
KATEGORIE_SPALTE = "Kategorie-Pfad"
BETRAG_SPALTE = "Betrag"

# =====================
# Datenstrukturen
# =====================
# Summen pro Kategorie (inkl. Überkategorien)
kategorie_summen = defaultdict(float)

# Sankey-Kanten: (Quelle, Ziel) -> Betrag
sankey_edges = defaultdict(float)
# =====================
# CSV einlesen
# =====================
with open(CSV_DATEI, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=";", quotechar='"')

    for row in reader:
        kategorie_pfad = row.get(KATEGORIE_SPALTE, "").strip()
        betrag_raw = row.get(BETRAG_SPALTE, "").strip()

        if not kategorie_pfad or not betrag_raw:
            continue

        # Betrag normalisieren (deutsches Format)
        betrag = float(betrag_raw.replace(".", "").replace(",", "."))

        # Kategorien aufsplitten
        teile = kategorie_pfad.split("/")

        # 1) Summen je Kategorie + Überkategorien
        for i in range(1, len(teile) + 1):
            kat = "/".join(teile[:i])
            kategorie_summen[kat] += betrag

        # 2) Sankey-Kanten erzeugen
        for parent, child in zip(teile[:-1], teile[1:]):
            sankey_edges[(parent, child)] += betrag


# =====================
# Ausgabe
# =====================
print("=== Kategorien-Summen ===")
for kategorie, summe in sorted(kategorie_summen.items()):
    print(f"{kategorie:30s} {summe:10.2f}")

print("\n=== Sankey-Kanten (Source -> Target) ===")
for (source, target), value in sankey_edges.items():
    print(f"{source} -> {target}: {value:.2f}")
