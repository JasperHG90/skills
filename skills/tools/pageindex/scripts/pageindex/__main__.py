"""CLI for the standalone PageIndex generator.

Usage (run from the ``scripts/`` directory so ``pageindex`` is importable):

    python -m pageindex DOC.md --model gemini/gemini-2.5-flash
    python -m pageindex DOC.md --model ollama_chat/llama3 --api-base http://localhost:11434
    python -m pageindex DOC.md --model anthropic/claude-sonnet-4-6 --full -o out.json

The model id follows the litellm ``provider/model`` convention, so any provider
litellm supports works. Provider API keys are read from the standard env var
(ANTHROPIC_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY / ...) unless --api-key is
given.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import dspy

from .indexer import index_document


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pageindex",
        description="Generate a hierarchical page index (TOC tree + summaries) from a "
        "markdown/text document using DSPy with any LLM.",
    )
    p.add_argument("input", help="Path to the markdown/text document to index.")
    p.add_argument(
        "--model",
        required=True,
        help="litellm model id, e.g. gemini/gemini-2.5-flash, "
        "anthropic/claude-sonnet-4-6, openai/gpt-4o, ollama_chat/llama3.",
    )
    p.add_argument(
        "--api-base",
        default=None,
        help="Override the provider base URL (e.g. http://localhost:11434 for ollama).",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="Provider API key. If omitted, litellm reads the provider-standard env var.",
    )
    p.add_argument(
        "-o",
        "--output",
        default=None,
        help="Write JSON here instead of stdout.",
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="Emit the complete PageIndexOutput (toc + blocks + body text + node-to-block "
        "map). Default is the thin tree (titles, levels, nesting, summaries, token "
        "counts) with no duplicated body text.",
    )
    p.add_argument(
        "--max-concurrency",
        type=int,
        default=20,
        help="Cap concurrent LLM calls (scan/refine/summarize). Lower it on a "
        "memory-constrained or rate-limited host (e.g. local ollama). Default 20.",
    )
    return p


def _serialize(result: object, *, full: bool) -> str:
    # `--full`: complete dump (PageIndexOutput is a pydantic model).
    # default: the thin tree, which json_tree() already returns as a JSON string —
    # so it must NOT be passed through json.dumps again (that would double-encode).
    if full:
        return json.dumps(result.model_dump(mode="json"), indent=2)  # type: ignore[attr-defined]
    return result.json_tree()  # type: ignore[attr-defined]


async def _run(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.is_file():
        print(f"error: input file not found: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        print(f"error: input file is empty: {path}", file=sys.stderr)
        return 2

    lm = dspy.LM(
        model=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
    )

    result = await index_document(
        text,
        lm,
        scan_max_concurrency=args.max_concurrency,
        refine_max_concurrency=args.max_concurrency,
        summarize_max_concurrency=args.max_concurrency,
    )

    payload = _serialize(result, full=args.full)

    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        dest = args.output
    else:
        sys.stdout.write(payload + "\n")
        dest = "stdout"

    # One-line summary to stderr so it never pollutes the JSON on stdout.
    print(
        f"pageindex: path_used={result.path_used} "  # type: ignore[attr-defined]
        f"coverage={result.coverage_ratio:.1%} "  # type: ignore[attr-defined]
        f"nodes={len(result.toc)} blocks={len(result.blocks)} "  # type: ignore[attr-defined]
        f"-> {dest}",
        file=sys.stderr,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
