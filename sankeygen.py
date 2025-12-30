#!/usr/bin/env python3

import sys
import csv
import argparse
from collections import defaultdict
import plotly.graph_objects as go
from pathlib import Path

# =====================
# Argument parsing
# =====================
parser = argparse.ArgumentParser(
    description="Generate a Sankey diagram from one or more CSV files (category path based)."
)

parser.add_argument("csv_files", nargs="+", help="One or more CSV files")

parser.add_argument(
    "--sankey",
    action="store_true",
    help="Create sankey diagram",
)

parser.add_argument(
    "--output", help="Optional: write output to HTML file (e.g. sankey.html)"
)

args = parser.parse_args()

# =====================
# Data containers
# =====================
category_totals = defaultdict(float)

# =====================
# Read CSV files
# =====================
for csv_file in args.csv_files:
    csv_path = Path(csv_file)

    if not csv_path.exists():
        print(f"⚠ File not found: {csv_path}")
        continue

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";", quotechar='"')

        for row in reader:
            category_path = row.get("Kategorie-Pfad", "").strip()
            amount_raw = row.get("Betrag", "").strip()

            if not category_path or not amount_raw:
                continue

            # German number format → float
            amount = float(amount_raw.replace(".", "").replace(",", "."))

            parts = category_path.split("/")

            # Accumulate category totals
            for i in range(1, len(parts) + 1):
                category = "/".join(parts[:i])
                category_totals[category] += amount

for k, v in sorted(category_totals.items()):
    print(f"{k:20s} {v:10.2f}")

if not args.sankey:
    sys.exit(0)

src_cat = sorted(category_totals.items(), key=lambda x: x[1])[-1]
print(f"Source category: {src_cat[0]} ({src_cat[1]:.2f})")
src_cat = src_cat[0]

sankey_edges = {}
for k, v in sorted(category_totals.items()):
    if v < 0:
        v = -v
    else:
        continue
    categories = k.split("/")
    if len(categories) < 2:
        if categories[0] == src_cat:
            continue
        categories = (src_cat, k)
    else:
        categories = ("/".join(categories[:-1]), k)
    sankey_edges[categories] = v

for (s, d), v in sorted(sankey_edges.items(), key=lambda x: x[0]):
    print(f"{s} -> {d}: {v:.2f}")

# sys.exit(0)
# =====================
# Prepare Sankey data
# =====================
labels = sorted(category_totals.keys())
label_index = {label: i for i, label in enumerate(labels)}

sources = []
targets = []
values = []

for (src, tgt), value in sankey_edges.items():
    if src not in label_index or tgt not in label_index:
        continue

    sources.append(label_index[src])
    targets.append(label_index[tgt])
    values.append(value)  # Sankey requires positive values


# =====================
# Plotly Sankey
# =====================
fig = go.Figure(
    go.Sankey(
        node=dict(pad=15, thickness=20, label=labels),
        link=dict(source=sources, target=targets, value=values),
    )
)

fig.update_layout(title_text="Sankey diagram", font_size=12)

# =====================
# Output
# =====================
if args.output:
    fig.write_html(args.output)
    print(f"✅ Sankey diagram written to: {args.output}")
else:
    fig.show()
