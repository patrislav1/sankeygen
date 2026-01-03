#!/usr/bin/env python3

import csv
import argparse
import plotly.graph_objects as go
from pathlib import Path
from collections.abc import Callable
from typing import Optional


class ColorPalette:
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

    @classmethod
    def get_rgba(cls, col_str: str, alpha_val: float) -> str:
        r, g, b = [int(col_str[i : i + 2], 16) for i in (0, 2, 4)]
        return f"rgba({r},{g},{b},{alpha_val})"


class SankeyNode:
    def __init__(self, name):
        self.children: dict[str, SankeyNode] = {}
        self.parent: Optional[SankeyNode] = None
        self.name = name
        self.color = ""
        self.value = 0.0
        self.index = 0
        self.is_toplevel = "/" not in name
        self.is_income = False

    def add_child(self, child: "SankeyNode"):
        if child.name not in self.children:
            self.children[child.name] = child
        child.parent = self

    def rm_child(self, child: "SankeyNode"):
        if child.name in self.children:
            self.children.pop(child.name)

    def do_recursive(self, func: Callable[["SankeyNode"], None]):
        for c in self.children.values():
            c.do_recursive(func)
        func(self)

    def __str__(self):
        return self.name

    def plotly_node(self):
        return {
            "label": f"{self.name.split('/')[-1]}<br>{int(abs(self.value))}€",
            "color": ColorPalette.get_rgba(self.color, 1.0),
        }


class SankeyLink:
    def __init__(self, source: SankeyNode, target: SankeyNode):
        self.source = source
        self.target = target
        self.value = abs(target.value if not target.is_income else source.value)

    def __str__(self):
        return f"{self.source.name} --{self.value:.2f}-> {self.target.name}"

    def plotly_link(self):
        return {
            "source": self.source.index,
            "target": self.target.index,
            "label": f"{int(self.value)}€",
            "value": self.value,
            "color": ColorPalette.get_rgba(self.target.color, 0.35),
        }


class SankeyNodePool:
    def __init__(self):
        self.nodes: dict[str, SankeyNode] = {}
        self.links: list[SankeyLink] = []

    def get_node(self, path: str) -> SankeyNode:
        path_nodes = path.split("/")
        for i, _ in enumerate(path_nodes):
            parent_node = "/".join(path_nodes[:i])
            sub_node = "/".join(path_nodes[: i + 1])
            if sub_node not in self.nodes:
                new_node = SankeyNode(sub_node)
                self.nodes[sub_node] = new_node
                if parent_node:
                    self.nodes[parent_node].add_child(new_node)
        return self.nodes[path]

    def dump(self):
        for name, node in sorted(self.nodes.items()):
            print(
                f"{name:20s} {node.value:10.2f} {'(income)' if node.is_income else ''}"
            )

    def purge(self, threshold: float):
        for name, node in list(self.nodes.items()):
            if abs(node.value) <= threshold:
                if node.parent:
                    node.parent.rm_child(node)
                self.nodes.pop(name)

    def div(self, divisor: float):
        for node in self.nodes.values():
            node.value /= divisor

    def assign_colors(self):
        palette = ColorPalette()
        for node in filter(lambda x: x.is_toplevel, self.nodes.values()):
            color = palette.pick_one()
            node.do_recursive(lambda x: setattr(x, "color", color))

    def assign_indices(self):
        for index, node in enumerate(self.nodes.values()):
            node.index = index

    def assign_income_node(self):
        income_node = sorted(self.nodes.values(), key=lambda x: x.value)[-1]
        income_node.do_recursive(lambda x: setattr(x, "is_income", True))
        self.income_node = income_node

    def create_links(self):
        for node in self.nodes.values():
            if node.is_income:
                if node.parent:
                    link = SankeyLink(node, node.parent)
                else:
                    continue
            else:
                if node.parent:
                    link = SankeyLink(node.parent, node)
                else:
                    link = SankeyLink(self.income_node, node)
            self.links.append(link)


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

    pool.assign_income_node()
    return pool


def plot_graph(pool: SankeyNodePool):
    nodes = [n.plotly_node() for n in pool.nodes.values()]
    links = [l.plotly_link() for l in pool.links]
    fig = go.Figure(
        go.Sankey(
            arrangement="perpendicular",
            node=dict(
                thickness=20,
                align="center",
                pad=25,
                label=[n["label"] for n in nodes],
                color=[n["color"] for n in nodes],
            ),
            link=dict(
                source=[l["source"] for l in links],
                target=[l["target"] for l in links],
                label=[l["label"] for l in links],
                value=[l["value"] for l in links],
                color=[l["color"] for l in links],
            ),
        )
    )
    fig.show()


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

    args = parser.parse_args()

    pool = parse_csv(args.csv_files)
    pool.div(args.div)
    pool.purge(args.threshold)
    pool.assign_colors()
    pool.assign_indices()
    pool.dump()
    pool.create_links()

    if args.plot:
        plot_graph(pool)


if __name__ == "__main__":
    main()
