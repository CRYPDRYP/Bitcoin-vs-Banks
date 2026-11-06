#!/usr/bin/env python3
"""
Convert a NotebookLM mind-map JSON export into an Obsidian Canvas (.canvas) file.

NotebookLM mind maps are interactive trees. `notebooklm download mind-map` saves
them as JSON; this turns that JSON into the open JSON-Canvas format Obsidian renders
natively, laid out left-to-right as a tidy tree — so you can view and edit the map
right inside your vault.

Standalone use:
    python integrations/mindmap_canvas.py input.json [output.canvas]

NotebookLM's exact node keys aren't documented and have shifted across versions, so
the parser is deliberately generous about which keys hold a node's label vs. its
children.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Keys that may hold a node's text, in priority order.
LABEL_KEYS = ("label", "name", "title", "text", "topic", "heading", "value", "content")
# Keys that may hold a node's children list.
CHILD_KEYS = ("children", "nodes", "subtopics", "subTopics", "items", "branches",
              "child", "subtopic", "sub_nodes", "childNodes")
# Envelope keys to unwrap when the real tree is nested under one of them.
WRAP_KEYS = ("root", "mindMap", "mind_map", "mindmap", "tree", "data", "graph", "result")

# Layout geometry (px).
NODE_W, NODE_H, H_GAP, V_GAP = 280, 60, 90, 28
# Obsidian preset colours cycled by depth.
DEPTH_COLORS = ("4", "6", "5", "2", "3", "1")


# --------------------------------------------------------------------------- #
# Parsing → a uniform {"label": str, "children": [...]} tree
# --------------------------------------------------------------------------- #


def parse_tree(data) -> dict:
    """Normalize any NotebookLM mind-map JSON into a {label, children} tree."""
    if isinstance(data, (str, bytes)):
        data = json.loads(data)
    return _node(data)


def _node(obj) -> dict:
    if isinstance(obj, list):
        return {"label": "Mind Map", "children": [_node(o) for o in obj]}
    if not isinstance(obj, dict):
        return {"label": str(obj), "children": []}

    # Unwrap envelopes like {"root": {...}} when this dict isn't itself a node.
    if not any(k in obj for k in LABEL_KEYS):
        for w in WRAP_KEYS:
            if isinstance(obj.get(w), (dict, list)):
                return _node(obj[w])

    label = next((obj[k].strip() for k in LABEL_KEYS
                  if isinstance(obj.get(k), str) and obj[k].strip()), "•")

    children: list = []
    for k in CHILD_KEYS:
        if isinstance(obj.get(k), list):
            children = [_node(c) for c in obj[k]]
            break
    return {"label": label, "children": children}


# --------------------------------------------------------------------------- #
# Layout → Obsidian Canvas JSON
# --------------------------------------------------------------------------- #


def _layout(root: dict) -> dict[int, tuple[int, int]]:
    """Assign (x, y) to every node: x by depth, y by in-order leaf position."""
    pos: dict[int, tuple[int, int]] = {}
    cursor = {"row": 0}

    def place(node: dict, depth: int) -> float:
        x = depth * (NODE_W + H_GAP)
        kids = node["children"]
        if not kids:
            y = cursor["row"] * (NODE_H + V_GAP)
            cursor["row"] += 1
        else:
            ys = [place(c, depth + 1) for c in kids]
            y = (min(ys) + max(ys)) / 2
        pos[id(node)] = (x, int(y))
        return y

    place(root, 0)
    return pos


def to_canvas(root: dict) -> dict:
    """Build an Obsidian JSON-Canvas document from a {label, children} tree."""
    pos = _layout(root)
    nodes: list[dict] = []
    edges: list[dict] = []
    seq = {"n": 0}

    def nid() -> str:
        seq["n"] += 1
        return f"n{seq['n']:04d}"

    def walk(node: dict, depth: int, parent_id: str | None):
        x, y = pos[id(node)]
        node_id = nid()
        nodes.append({
            "id": node_id,
            "type": "text",
            "text": node["label"],
            "x": x, "y": y,
            "width": NODE_W, "height": NODE_H,
            "color": DEPTH_COLORS[depth % len(DEPTH_COLORS)],
        })
        if parent_id is not None:
            edges.append({
                "id": f"e{seq['n']:04d}",
                "fromNode": parent_id, "fromSide": "right",
                "toNode": node_id, "toSide": "left",
            })
        for child in node["children"]:
            walk(child, depth + 1, node_id)

    walk(root, 0, None)
    return {"nodes": nodes, "edges": edges}


def convert(src: str | Path, dst: str | Path | None = None) -> Path:
    """Convert a mind-map JSON file to a .canvas file; return the output path."""
    src = Path(src)
    data = json.loads(src.read_text(encoding="utf-8"))
    canvas = to_canvas(parse_tree(data))
    out = Path(dst) if dst else src.with_suffix(".canvas")
    out.write_text(json.dumps(canvas, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: mindmap_canvas.py <input.json> [output.canvas]", file=sys.stderr)
        return 2
    out = convert(args[0], args[1] if len(args) > 1 else None)
    print(f"✓ Canvas written → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
