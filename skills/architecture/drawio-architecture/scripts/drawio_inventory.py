#!/usr/bin/env python3
"""List every element and connection in a draw.io file, so a diagram can be read as source.

Reads .drawio / .xml files and .drawio.png / .png files exported with the diagram embedded.
Handles compressed <diagram> payloads (base64 + raw deflate + URL-encoding).

Usage:
    python drawio_inventory.py DIAGRAM [--page N]
    python drawio_inventory.py DIAGRAM --xml > out.drawio   # dump the decoded source

Output, per page:
    - vertices: [id] label  (parent id)
    - edges:    [id] source label -> target label : edge label
    - problems: unattached or dangling edge ends, unlabeled edges, step numbers that are
      missing or repeated, narrow labelWidth, and a reminder when a Mermaid source is embedded

Exit codes: 0 ok, 1 no diagram source found or file unreadable, 2 usage error.
Standard library only.
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import struct
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

WRAPPERS = {"UserObject", "object"}
# draw.io desktop writes the source under mxGraphModel, the web app under mxfile
PNG_KEYS = {b"mxfile", b"mxGraphModel"}
STEP = re.compile(r"^(\d+):")


@dataclass
class Cell:
    """One draw.io cell, with its label resolved from a wrapper element if present."""

    id: str
    label: str
    style: str
    parent: str
    vertex: bool
    edge: bool
    source: str | None
    target: str | None
    width: float = 0.0


@dataclass
class Page:
    """One diagram page and its cells."""

    name: str
    cells: dict[str, Cell] = field(default_factory=dict)
    has_mermaid: bool = False


def read_png_xml(path: Path) -> str:
    """Return the draw.io XML embedded in a PNG's tEXt/zTXt/iTXt chunk, or raise ValueError."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    pos = 8
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        ctype = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        key, _, rest = body.partition(b"\x00")
        if key not in PNG_KEYS:
            continue
        if ctype == b"tEXt":
            return urllib.parse.unquote(rest.decode("latin-1"))
        if ctype == b"zTXt":
            return urllib.parse.unquote(zlib.decompress(rest[1:]).decode("utf-8"))
        if ctype == b"iTXt":
            compressed = rest[:1] == b"\x01"
            # skip compression flag, method, language tag and translated keyword
            parts = rest[2:].split(b"\x00", 2)
            text = parts[2] if len(parts) == 3 else b""
            raw = zlib.decompress(text) if compressed else text
            return urllib.parse.unquote(raw.decode("utf-8"))
    raise ValueError(
        "PNG has no embedded draw.io source (export with 'Include a copy of my diagram')"
    )


def inflate_diagram(text: str) -> str:
    """Decode a compressed <diagram> payload into mxGraphModel XML."""
    raw = base64.b64decode(text)
    return urllib.parse.unquote(zlib.decompress(raw, -15).decode("utf-8"))


def load_root(path: Path) -> ET.Element:
    """Parse the file and inflate compressed pages in place, so the tree is plain XML."""
    if path.suffix.lower() == ".png":
        xml_text = read_png_xml(path)
    else:
        xml_text = path.read_text(encoding="utf-8")
    if not xml_text.strip():
        raise ValueError("file is empty")
    root = ET.fromstring(xml_text)
    for diagram in root.findall("diagram") if root.tag == "mxfile" else []:
        if diagram.find("mxGraphModel") is None and (diagram.text or "").strip():
            diagram.append(ET.fromstring(inflate_diagram((diagram.text or "").strip())))
            diagram.text = None
    return root


def load_pages(root: ET.Element) -> list[Page]:
    """Split a parsed draw.io tree into pages of cells."""
    if root.tag == "mxGraphModel":
        return [parse_model("Page-1", root)]
    pages = []
    for i, diagram in enumerate(root.findall("diagram")):
        model = diagram.find("mxGraphModel")
        if model is not None:
            pages.append(parse_model(diagram.get("name") or f"Page-{i + 1}", model))
    if not pages:
        raise ValueError("no mxGraphModel found")
    return pages


def parse_model(name: str, model: ET.Element) -> Page:
    """Collect cells, resolving labels that live on UserObject/object wrappers."""
    page = Page(name=name)
    rootel = model.find("root")
    if rootel is None:
        return page
    for el in rootel:
        if el.tag in WRAPPERS:
            cell = el.find("mxCell")
            label = el.get("label") or el.get("value") or ""
            page.has_mermaid |= "mermaidData" in el.attrib
        elif el.tag == "mxCell":
            cell = el
            label = el.get("value") or ""
        else:
            continue
        if cell is None:
            continue
        cid = el.get("id") or ""
        geo = cell.find("mxGeometry")
        page.cells[cid] = Cell(
            id=cid,
            label=label,
            style=cell.get("style") or "",
            parent=cell.get("parent") or "",
            vertex=cell.get("vertex") == "1",
            edge=cell.get("edge") == "1",
            source=cell.get("source"),
            target=cell.get("target"),
            width=float(geo.get("width", 0)) if geo is not None else 0.0,
        )
    return page


def plain(label: str) -> str:
    """Strip HTML from a label and collapse whitespace for one-line display."""
    text = re.sub(r"<br\s*/?>|</div>|</p>", " ", label, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(html.unescape(text).split())


def edge_labels(page: Page) -> dict[str, str]:
    """Labels drawn as child text cells of an edge (draw.io's 'add text to edge')."""
    out: dict[str, str] = {}
    for cell in page.cells.values():
        parent = page.cells.get(cell.parent)
        if parent is not None and parent.edge and cell.vertex and cell.label:
            out[parent.id] = (out.get(parent.id, "") + " " + plain(cell.label)).strip()
    return out


def end_problem(page: Page, cid: str, end: str, ref: str | None) -> str | None:
    """Describe what is wrong with one edge end, if anything."""
    if not ref:
        return f"[{cid}] {end} not attached to a shape: it will not follow when shapes move"
    if ref not in page.cells:
        return f"[{cid}] {end} points at missing cell '{ref}'"
    return None


def report(page: Page) -> list[str]:
    """Render one page as text, with problems listed last."""
    lines = [f"== page: {page.name}"]
    child_labels = edge_labels(page)
    name = {cid: plain(c.label) or f"<{cid}>" for cid, c in page.cells.items()}
    problems: list[str] = []
    lines.append("-- vertices")
    for c in page.cells.values():
        parent = page.cells.get(c.parent)
        if not c.vertex or not c.label or (parent is not None and parent.edge):
            continue
        lines.append(f"[{c.id}] {plain(c.label)}  (parent {c.parent})")
        match = re.search(r"labelWidth=([\d.]+)", c.style)
        if match and c.width and float(match.group(1)) < c.width - 20:
            problems.append(
                f"[{c.id}] labelWidth={match.group(1)} is narrower than the box "
                f"({c.width:g}): text wraps early"
            )
    lines.append("-- edges")
    steps: list[int] = []
    for c in page.cells.values():
        if not c.edge:
            continue
        src = name.get(c.source or "", "(unattached)")
        tgt = name.get(c.target or "", "(unattached)")
        label = plain(c.label) or child_labels.get(c.id, "")
        lines.append(f"[{c.id}] {src} -> {tgt} : {label or '(no label)'}")
        for end, ref in (("source", c.source), ("target", c.target)):
            problem = end_problem(page, c.id, end, ref)
            if problem:
                problems.append(problem)
        if not label and "endArrow=none" not in c.style:
            problems.append(f"[{c.id}] edge has no label")
        step = STEP.match(label)
        if step:
            steps.append(int(step.group(1)))
    if steps:
        counts = Counter(steps)
        missing = sorted(set(range(1, max(steps) + 1)) - set(steps))
        repeated = sorted(n for n, k in counts.items() if k > 1)
        if missing:
            problems.append(f"step numbers missing: {missing}")
        if repeated:
            problems.append(f"step numbers repeated: {repeated}")
    if page.has_mermaid:
        problems.append(
            "embedded Mermaid source (mermaidData): apply label and edge changes there too"
        )
    lines.append("-- problems")
    lines.extend(problems or ["none"])
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "diagram", type=Path, help="a .drawio, .xml, .drawio.png or .png file"
    )
    parser.add_argument("--page", type=int, help="only this page (1-based)")
    parser.add_argument(
        "--xml", action="store_true", help="print the decoded draw.io XML and exit"
    )
    args = parser.parse_args()
    try:
        root = load_root(args.diagram)
        if args.xml:
            sys.stdout.write(ET.tostring(root, encoding="unicode") + "\n")
            return 0
        pages = load_pages(root)
    except (OSError, ValueError, ET.ParseError, zlib.error, struct.error) as exc:
        sys.stderr.write(f"{args.diagram}: cannot read draw.io source: {exc}\n")
        return 1
    if args.page is not None:
        if not 1 <= args.page <= len(pages):
            sys.stderr.write(f"--page must be 1..{len(pages)}\n")
            return 2
        pages = [pages[args.page - 1]]
    sys.stdout.write("\n".join(line for page in pages for line in report(page)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
