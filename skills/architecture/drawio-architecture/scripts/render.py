#!/usr/bin/env python3
"""Render a draw.io file to PNG with the draw.io desktop CLI, so the result can be looked at.

Usage:
    python render.py DIAGRAM [-o OUT.png] [--page N] [--embed]

--embed writes the diagram source into the PNG (needed when the deliverable is a .drawio.png
that people keep editing). Without -o the PNG lands next to the input as <name>.render.png,
so a .drawio.png is never overwritten by accident.

Exit codes: 0 rendered, 1 draw.io not found, bad --page or output, or export failed.
Standard library only.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_inventory import load_root  # noqa: E402

CANDIDATES = {
    "Darwin": ["/Applications/draw.io.app/Contents/MacOS/draw.io"],
    "Windows": [
        r"C:\Program Files\draw.io\draw.io.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\draw.io\draw.io.exe"),
    ],
    "Linux": ["/opt/drawio/drawio", "/usr/bin/drawio", "/snap/bin/drawio"],
}


def find_drawio() -> str | None:
    """Return the draw.io executable: $DRAWIO, then PATH, then known install locations."""
    env = os.environ.get("DRAWIO")
    if env and Path(env).exists():
        return env
    for name in ("drawio", "draw.io"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in CANDIDATES.get(platform.system(), []):
        if Path(candidate).exists():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("diagram", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument(
        "--page", type=int, help="page to render (1-based); default is the first"
    )
    parser.add_argument(
        "--embed", action="store_true", help="embed the diagram source in the PNG"
    )
    args = parser.parse_args()

    exe = find_drawio()
    if exe is None:
        sys.stderr.write(
            "draw.io desktop not found. Install it (https://github.com/jgraph/drawio-desktop/releases) "
            "or set DRAWIO to its executable.\n"
        )
        return 1
    out = args.output or args.diagram.with_name(args.diagram.name + ".render.png")
    if out.resolve() == args.diagram.resolve() or (
        out.exists() and out.samefile(args.diagram)
    ):  # samefile also catches case-only differences and hardlinks
        sys.stderr.write("refusing to overwrite the input; pass a different -o\n")
        return 1
    cmd = [
        exe,
        "--export",
        "--format",
        "png",
        "--scale",
        "1",
        "--border",
        "10",
        "--output",
        str(out),
    ]
    if args.page is not None:
        try:
            root = load_root(args.diagram)
        except Exception as exc:  # any unreadable input gets the same one-line error
            sys.stderr.write(f"{args.diagram}: cannot read draw.io source: {exc}\n")
            return 1
        pages = len(root.findall("diagram")) if root.tag == "mxfile" else 1
        if not 1 <= args.page <= pages:
            sys.stderr.write(f"--page must be 1..{pages}\n")
            return 1
        cmd += ["--page-index", str(args.page)]  # 1-based since draw.io 27.0.2
    if args.embed:
        cmd.append("--embed-diagram")
    if platform.system() == "Linux":
        cmd.append("--no-sandbox")  # electron refuses to start as root without it
    cmd.append(str(args.diagram))
    if (
        platform.system() == "Linux"
        and not os.environ.get("DISPLAY")
        and shutil.which("xvfb-run")
    ):
        cmd = ["xvfb-run", "-a", *cmd]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not out.exists():
        sys.stderr.write(
            f"export failed ({result.returncode}): {result.stderr.strip() or result.stdout.strip()}\n"
        )
        return 1
    sys.stdout.write(f"{out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
