#!/usr/bin/env python3
"""Strip invisible/zero-width Unicode characters from text files.

Pre-commit fixer: rewrites offending files in place and exits non-zero when
anything changed, so the commit aborts and the user re-stages the clean files.
These characters render as nothing, slip past human review, and are a known
supply-chain vector for hiding instructions in skill/prompt files.

The targets are declared by numeric codepoint, never as literal characters --
otherwise this script would strip the entries out of its own source the first
time it ran over itself.
"""

from __future__ import annotations

import sys

# Codepoint -> name, for reporting. All render as zero or near-zero width.
INVISIBLE = {
    0x200B: "ZERO WIDTH SPACE",
    0x200C: "ZERO WIDTH NON-JOINER",
    0x200D: "ZERO WIDTH JOINER",
    0x2060: "WORD JOINER",
    0xFEFF: "ZERO WIDTH NO-BREAK SPACE / BOM",
    0x00AD: "SOFT HYPHEN",
    0x200E: "LEFT-TO-RIGHT MARK",
    0x200F: "RIGHT-TO-LEFT MARK",
}

_TRANSLATION = {cp: None for cp in INVISIBLE}


def fix_file(path: str) -> bool:
    """Return True if the file was modified."""
    try:
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
    except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
        return False  # binary or unreadable -> not our concern

    cleaned = original.translate(_TRANSLATION)
    if cleaned == original:
        return False

    for lineno, line in enumerate(original.splitlines(), start=1):
        hits = sorted({INVISIBLE[ord(ch)] for ch in line if ord(ch) in INVISIBLE})
        if hits:
            print(f"  {path}:{lineno}: stripped {', '.join(hits)}")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(cleaned)
    return True


def main(argv: list[str]) -> int:
    changed = [p for p in argv if fix_file(p)]
    if changed:
        print(
            f"Stripped invisible Unicode from {len(changed)} file(s); re-stage and commit."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
