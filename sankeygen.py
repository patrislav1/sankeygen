#!/usr/bin/env python3

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
    "--expenses-only",
    action="store_true",
    help="Only include negative amounts (expenses)",
)

parser.add_argument(
    "--title", default="Expenses by Category", help="Title of the Sankey diagram"
)

parser.add_argument(
    "--output", help="Optional: write output to HTML file (e.g. sankey.html)"
)

args = parser.parse_args()

# =====================
# Data containers
# =====================
category_totals = defaultdict(float)
sankey_edges = defaultdict(float)

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

            if args.expenses_only and amount >= 0:
                continue

            parts = category_path.split("/")

            # Accumulate category totals
            for i in range(1, len(parts) + 1):
                category = "/".join(parts[:i])
                category_totals[category] += amount

            # Build Sankey edges (FULL paths!)
            for i in range(1, len(parts)):
                parent = "/".join(parts[:i])
                child = "/".join(parts[: i + 1])
                sankey_edges[(parent, child)] += amount

print("=== Kategorien-Summen ===")
for category, sum in sorted(category_totals.items()):
    print(f"{category:30s} {sum:10.2f}")

print("\n=== Sankey-Edges (Source -> Target) ===")
for (source, target), value in sankey_edges.items():
    print(f"{source} -> {target}: {value:.2f}")


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
    values.append(abs(value))  # Sankey requires positive values


# =====================
# Plotly Sankey
# =====================
fig = go.Figure(
    go.Sankey(
        node=dict(pad=15, thickness=20, label=labels),
        link=dict(source=sources, target=targets, value=values),
    )
)

fig.update_layout(title_text=args.title, font_size=12)

# =====================
# Output
# =====================
if args.output:
    fig.write_html(args.output)
    print(f"✅ Sankey diagram written to: {args.output}")
else:
    fig.show()
