#!/usr/bin/env python3

import sys
import csv
import argparse
from collections import defaultdict
from plotly import colors
import plotly.graph_objects as go
from pathlib import Path


class ColorPicker:
    COLOR_PALETTE = [
        "4E79A7",  # blue
        "F28E2B",  # orange
        "E15759",  # red
        "76B7B2",  # teal
        "59A14F",  # green
        "EDC948",  # yellow
        "B07AA1",  # purple
        "FF9DA7",  # pink
        "9C755F",  # brown
        "BAB0AC",  # gray
        "8CD17D",  # lime green
        "FF9F80",  # salmon
        "A0CBE8",  # light blue
        "C9C9C9",  # light gray
        "D37295",  # rose
    ]

    def __init__(self):
        self.index = 0

    def pick_one(self) -> str:
        result = self.COLOR_PALETTE[self.index]
        self.index += 1
        self.index %= len(self.COLOR_PALETTE)
        return result

    def get_rgba(self, col_str: str, alpha_val: float) -> str:
        r, g, b = [int(col_str[i : i + 2], 16) for i in (0, 2, 4)]
        return f"rgba({r},{g},{b},{alpha_val})"


class SankeyNode:
    def __init__(self, name):
        self.children: dict[str, SankeyNode] = {}
        self.parents: dict[str, SankeyNode] = {}
        self.name = name
        self.value = 0.0

    def add_child(self, child: "SankeyNode"):
        if child.name not in self.children:
            self.children[child.name] = child
        if self.name not in child.parents:
            child.parents[self.name] = self

    def rm_child(self, child: "SankeyNode"):
        if child.name in self.children:
            self.children.pop(child.name)


class SankeyNodePool:
    def __init__(self):
        self.pool: dict[str, SankeyNode] = {}

    def get_node(self, path: str) -> SankeyNode:
        path_nodes = path.split("/")
        for i, _ in enumerate(path_nodes):
            parent_node = "/".join(path_nodes[:i])
            sub_node = "/".join(path_nodes[: i + 1])
            if sub_node not in self.pool:
                new_node = SankeyNode(sub_node)
                self.pool[sub_node] = new_node
                if parent_node:
                    self.pool[parent_node].add_child(new_node)
        return self.pool[path]

    def dump(self):
        for name, node in sorted(self.pool.items()):
            print(f"{name:20s} {node.value:10.2f}")

    def purge(self, threshold: float):
        for name, node in list(self.pool.items()):
            if abs(node.value) <= threshold:
                for p in node.parents.values():
                    p.rm_child(node)
                self.pool.pop(name)

    def div(self, divisor: float):
        for node in self.pool.values():
            node.value /= divisor


def parse_csv(files) -> SankeyNodePool:
    pool = SankeyNodePool()
    for csv_file in files:
        csv_path = Path(csv_file)

        if not csv_path.exists():
            raise RuntimeError(f"File not found: {csv_path}")

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";", quotechar='"')

            for row in reader:
                category_path = row.get("Kategorie-Pfad", "").strip()
                amount_raw = row.get("Betrag", "").strip()

                if not category_path or not amount_raw:
                    continue

                # Parse German number format
                amount = float(amount_raw.replace(".", "").replace(",", "."))

                parts = category_path.split("/")

                # Accumulate category totals
                for i, _ in enumerate(parts):
                    node = pool.get_node("/".join(parts[: i + 1]))
                    node.value += amount  # / args.div
    return pool


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Sankey diagram from one or more CSV files (category path based)."
    )

    parser.add_argument("csv_files", nargs="+", help="One or more CSV files")

    parser.add_argument(
        "--div",
        type=int,
        default=1,
        help="Divisor for values (e.g. 12 to show monthly averages from a one year dataset)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="Lower threshold for nodes to show up",
    )

    parser.add_argument(
        "--plot",
        action="store_true",
        help="Plot sankey diagram",
    )

    parser.add_argument(
        "--output", help="Optional: write output to HTML file (e.g. sankey.html)"
    )

    args = parser.parse_args()

    pool = parse_csv(args.csv_files)
    pool.div(args.div)
    pool.purge(args.threshold)
    pool.dump()


if __name__ == "__main__":
    main()
