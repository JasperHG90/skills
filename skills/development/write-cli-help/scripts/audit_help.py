#!/usr/bin/env python3
"""Render a CLI's --help at several widths and report what breaks.

Framework-agnostic on purpose: it runs the command and analyzes the rendered
text, so it works for Typer, Click, argparse, Cobra, clap, oclif and anything
else that prints help to stdout. Nothing is introspected and nothing is
imported from the CLI under test.

Exit codes: 0 clean, 1 findings, 2 the command could not be run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass

BOX_CHARS = "│┃╭╮╰╯├┤┬┴┼─━┏┓┗┛┠┨╔╗╚╝║═"

# Metavars that name a type rather than show a value. The point of a metavar is
# to spend free column width on a concrete example, so a type name wastes it.
GENERIC_METAVARS = {
    "text",
    "str",
    "string",
    "value",
    "val",
    "arg",
    "x",
    "name",
    "integer",
    "int",
    "number",
    "num",
    "float",
    "path",
    "file",
    "dir",
    "directory",
    "filename",
    "<str>",
    "<int>",
    "<path>",
    "<value>",
    "<text>",
    "<name>",
    "<file>",
}

# Words that carry no information when checking whether a help string merely
# restates the flag it is attached to.
STOPWORDS = {
    "the",
    "a",
    "an",
    "of",
    "for",
    "to",
    "this",
    "that",
    "its",
    "your",
    "is",
    "be",
    "will",
    "which",
    "use",
    "used",
    "in",
    "on",
    "at",
    "as",
}

MARKER_RE = re.compile(r"\[(required|default:|env var:|env:)", re.IGNORECASE)
# The lookahead keeps wrapped prose like "...pass --quiet." from reading as a
# flag declaration; a real one is followed by space, comma, equals or nothing.
FLAG_RE = re.compile(r"^(\s*)(?:\*\s+)?(-{1,2}[A-Za-z0-9][\w-]*)(?=$|[\s,=])")
URLISH_RE = re.compile(r"(https?://\S+|\S*/\S+)")


@dataclass
class Finding:
    width: int
    severity: str
    check: str
    flag: str
    detail: str

    def render(self) -> str:
        where = self.flag or "(help body)"
        return f"  [{self.severity}] {self.check}: {where}\n      {self.detail}"


def run_help(argv: list[str], width: int) -> str:
    """Run the command with --help at a fixed terminal width."""
    env = dict(os.environ)
    env["COLUMNS"] = str(width)
    env["TERM"] = "dumb"
    # Stop CLI frameworks and pagers from adding colour or paging.
    env["NO_COLOR"] = "1"
    env["TERMINAL_WIDTH"] = str(width)
    env.pop("FORCE_COLOR", None)

    cmd = [*argv, "--help"]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        raise SystemExit(f"audit_help: command not found: {argv[0]}")
    except subprocess.TimeoutExpired:
        raise SystemExit(f"audit_help: timed out running: {' '.join(cmd)}")

    out = proc.stdout or proc.stderr
    if not out.strip():
        raise SystemExit(
            f"audit_help: '{' '.join(cmd)}' printed nothing (exit {proc.returncode})"
        )
    return out


def declutter(line: str) -> str:
    """Drop box-drawing, ANSI escapes and overstrike, preserving columns."""
    line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
    # `git --help` and friends render through man/groff, which bolds by
    # overstriking: char, backspace, char. Left in, it reads as doubled text.
    line = re.sub(r".\x08", "", line)
    return "".join(" " if ch in BOX_CHARS else ch for ch in line).rstrip()


def panel_segments(raw: list[str], total: int) -> list[list[int]]:
    """Group row indices into independently-sized option tables.

    Two things make this necessary. A full-width epilog is not an options
    table, but its entries often start with a flag name at column 0 and wrap
    underneath, which reads exactly like a table row with a long description.
    And rich sizes EACH panel's columns to that panel's own widest entry, so
    one description column measured across the whole output describes none of
    them: a one-row panel gets judged against a six-row panel's width.

    Rich draws every panel in a box, so the boxes give both answers at once.
    Frameworks that draw no box get a single segment covering everything,
    which is the old behavior and right for them.
    """
    segments: list[list[int]] = []
    current: list[int] = []
    for i, line in enumerate(raw):
        stripped = line.lstrip()
        if stripped.startswith(("╭", "┏", "╔")):
            current = []
        elif stripped.startswith(("╰", "┗", "╚")):
            if current:
                segments.append(current)
            current = []
        elif stripped.startswith(("│", "┃", "║")):
            current.append(i)
    if current:
        segments.append(current)
    return segments or [list(range(total))]


def find_description_column(lines: list[str], flag_rows: list[int]) -> int:
    """Infer where the description column starts.

    Continuation lines (wrapped description text under a flag) all begin at the
    description column, so their indent is the most reliable signal available
    without knowing the framework.
    """
    flag_set = set(flag_rows)
    indents = [
        len(ln) - len(ln.lstrip())
        for i, ln in enumerate(lines)
        if ln.strip() and i not in flag_set and (len(ln) - len(ln.lstrip())) >= 4
    ]
    if not indents:
        return 0
    return Counter(indents).most_common(1)[0][0]


def flag_rows_of(lines: list[str], desc_col: int) -> list[int]:
    """Rows that declare a flag.

    A line indented to the description column is wrapped prose, even when it
    happens to start with a flag reference, so it is excluded. desc_col is
    inferred from a provisional pass, hence the guard: with no continuation
    lines to learn from there is nothing to exclude against.
    """
    rows = [i for i, ln in enumerate(lines) if FLAG_RE.match(ln)]
    if desc_col < 4:
        return rows
    return [i for i in rows if (len(lines[i]) - len(lines[i].lstrip())) < desc_col]


def flag_blocks(lines: list[str], desc_col: int) -> list[tuple[str, int, list[int]]]:
    """Return (flag, row, continuation_rows) for every flag in the output."""
    flag_rows = flag_rows_of(lines, desc_col)
    blocks: list[tuple[str, int, list[int]]] = []
    for pos, row in enumerate(flag_rows):
        match = FLAG_RE.match(lines[row])
        assert match is not None
        flag = match.group(2)
        stop = flag_rows[pos + 1] if pos + 1 < len(flag_rows) else len(lines)
        cont: list[int] = []
        for i in range(row + 1, stop):
            if not lines[i].strip():
                break
            cont.append(i)
        blocks.append((flag, row, cont))
    return blocks


def describe(line: str, desc_col: int) -> str:
    return line[desc_col:].strip() if len(line) > desc_col else ""


def metavar_of(line: str, flag: str, desc_col: int) -> str:
    """Text sitting between the flag name and the description column."""
    start = line.find(flag) + len(flag)
    end = desc_col if desc_col > start else len(line)
    segment = line[start:end].strip()
    # A short-form alias (-o) is not a metavar.
    segment = re.sub(r"^,?\s*-{1,2}[\w.-]+\s*", "", segment).strip()
    return segment


def content_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS}


def audit(
    argv: list[str], width: int, wall: int, verbose_ratio: float
) -> list[Finding]:
    raw = run_help(argv, width).splitlines()
    lines = [declutter(ln) for ln in raw]
    findings: list[Finding] = []

    # Each panel is measured on its own, because rich sizes each one's columns
    # independently. Analyzing them together describes none of them.
    analyzed: list[tuple[str, int, list[int], int]] = []
    # Every row that STARTS an entry, subcommands included. A group's help is
    # mostly its command table, so counting only flags would judge a group by a
    # denominator that excludes most of what it prints.
    entries = 0
    for segment in panel_segments(raw, len(lines)):
        keep = set(segment)
        scope = [ln if i in keep else "" for i, ln in enumerate(lines)]
        # Provisional pass to learn the description column, then a real pass
        # that uses it to tell a flag declaration from prose mentioning a flag.
        provisional = [i for i, ln in enumerate(scope) if FLAG_RE.match(ln)]
        desc_col = find_description_column(scope, provisional)
        for i in segment:
            text = lines[i]
            indent = len(text) - len(text.lstrip())
            if text.strip() and (desc_col < 4 or indent < desc_col):
                entries += 1
        for flag, row, cont in flag_blocks(scope, desc_col):
            analyzed.append((flag, row, cont, desc_col))

    # Truncation anywhere in the body, attributed to a flag when possible.
    owner_by_row: dict[int, str] = {}
    for flag, row, cont, _ in analyzed:
        owner_by_row[row] = flag
        for i in cont:
            owner_by_row[i] = flag

    # Only the single-character ellipsis counts. A literal "..." at end of line
    # is nearly always legitimate notation (`<path>...` variadic, `--quiet...`
    # repeatable in clap), and flagging it buries the real findings.
    for i, line in enumerate(lines):
        if "…" in line:
            snippet = line.strip()[-58:]
            findings.append(
                Finding(
                    width,
                    "error",
                    "truncated",
                    owner_by_row.get(i, ""),
                    f"text is cut off and unrecoverable: ...{snippet}",
                )
            )

    for flag, row, cont, desc_col in analyzed:
        avail = max(width - desc_col - 2, 10)
        head = describe(lines[row], desc_col)
        body = " ".join(describe(lines[i], desc_col) for i in cont).strip()
        full = f"{head} {body}".strip()

        if len(cont) > wall:
            findings.append(
                Finding(
                    width,
                    "warn",
                    "wall",
                    flag,
                    f"description runs {len(cont) + 1} lines in a "
                    f"{avail}-char column; move detail to a full-width surface",
                )
            )

        first = re.split(r"(?<=[.!?])\s", full)[0] if full else ""
        if first:
            words = content_words(first)
            name_words = content_words(flag.lstrip("-").replace("-", " "))
            if words and name_words and words <= name_words:
                findings.append(
                    Finding(
                        width,
                        "error",
                        "restates-name",
                        flag,
                        f'"{first}" adds no fact the flag name does not already carry',
                    )
                )
        elif not cont:
            findings.append(
                Finding(width, "error", "no-help", flag, "no description at all")
            )

        meta = metavar_of(lines[row], flag, desc_col)
        if meta and meta.lower() in GENERIC_METAVARS:
            findings.append(
                Finding(
                    width,
                    "warn",
                    "generic-metavar",
                    flag,
                    f"metavar '{meta}' names a type; a concrete example is "
                    f"free column width",
                )
            )

        for token in URLISH_RE.findall(full):
            token = token.strip("`'\",")
            if len(token) > avail:
                findings.append(
                    Finding(
                        width,
                        "error",
                        "literal-too-wide",
                        flag,
                        f"'{token[:40]}...' is {len(token)} chars and cannot "
                        f"fit a {avail}-char column at any wrap",
                    )
                )
                break

        for offset, i in enumerate(cont, start=1):
            if MARKER_RE.search(lines[i]) and offset > 2:
                marker = MARKER_RE.search(lines[i]).group(0)  # type: ignore[union-attr]
                findings.append(
                    Finding(
                        width,
                        "warn",
                        "stranded-marker",
                        flag,
                        f"'{marker}...' sits {offset} lines below the flag; "
                        f"markers are scanned, not read",
                    )
                )
                break

    # Total volume, counting the epilog. Every check above looks only inside the
    # options panels, which means a help whose detail was moved OUT of the
    # column and into a book-length epilog passes all of them. Moving a wall is
    # not fixing it, so the last check is simply how much there is to read.
    # uv, which is the calibration, runs about 4.6 lines per option.
    counted = max(entries, len({flag for flag, _, _, _ in analyzed}))
    if counted:
        per_entry = len(lines) / counted
        if per_entry > verbose_ratio:
            findings.append(
                Finding(
                    width,
                    "warn",
                    "too-long",
                    "",
                    f"{len(lines)} lines for {counted} entries is "
                    f"{per_entry:.1f} each; cut text rather than moving it "
                    f"(uv runs about 4.6)",
                )
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="audit_help.py",
        description="Render a CLI's --help at several widths and report what "
        "breaks: truncation, walls of prose, help that restates the flag "
        "name, literals too wide to fit, and stranded [required] markers.",
        epilog=(
            "Examples:\n"
            "  audit_help.py -- mycli\n"
            "  audit_help.py -- mycli scaffold agent\n"
            "  audit_help.py --widths 80 -- uv run mypkg --json\n\n"
            "Eighty columns is the number that matters: it is the default "
            "width of a pipe, of CI logs, and of the text an agent receives."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--widths",
        metavar="80",
        type=int,
        nargs="+",
        default=[80, 100, 120],
        help="Terminal widths to render at (default: 80 100 120)",
    )
    parser.add_argument(
        "--wall",
        metavar="3",
        type=int,
        default=3,
        help="Description lines past which a flag counts as a wall (default: 3)",
    )
    parser.add_argument(
        "--lines-per-option",
        metavar="7",
        type=float,
        default=7.0,
        help="Total --help lines per option past which it counts as too long "
        "(default: 7; uv runs about 4.6)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit findings as JSON on stdout"
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        metavar="-- CMD ...",
        help="The command to run, after --. '--help' is appended for you.",
    )
    args = parser.parse_args()

    argv = [a for a in args.command if a != "--"]
    if not argv:
        parser.error("no command given; put it after --, e.g. -- mycli sub")

    all_findings: list[Finding] = []
    for width in args.widths:
        all_findings.extend(audit(argv, width, args.wall, args.lines_per_option))

    if args.json:
        print(json.dumps([asdict(f) for f in all_findings], indent=2))
        return 1 if all_findings else 0

    target = " ".join(argv)
    if not all_findings:
        widths = ", ".join(str(w) for w in args.widths)
        print(f"audit_help: `{target} --help` is clean at {widths} columns.")
        return 0

    # Findings repeat across widths; the narrowest is the one that matters, so
    # report per width rather than deduplicating and losing that signal.
    for width in args.widths:
        at_width = [f for f in all_findings if f.width == width]
        if not at_width:
            print(f"\n=== {width} columns: clean ===")
            continue
        errors = sum(1 for f in at_width if f.severity == "error")
        print(f"\n=== {width} columns: {len(at_width)} findings ({errors} errors) ===")
        for finding in at_width:
            print(finding.render())

    print(f"\naudit_help: {len(all_findings)} findings for `{target}`.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
