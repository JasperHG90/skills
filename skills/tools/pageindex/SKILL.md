---
name: pageindex
description: "Generate a hierarchical page index — a table-of-contents tree with per-section and per-block summaries — from a markdown or text document, using DSPy with ANY model (ollama, gemini, claude, openai, or anything litellm supports). Use this whenever the user wants to outline, index, map the structure of, build a TOC for, or extract the hierarchy of a document or markdown file, even if they don't say the words 'page index'. The script is self-contained and portable: it depends only on dspy, tiktoken, regex, and pydantic — no database, no server, no Memex install."
argument-hint: "[path/to/doc.md] [--model provider/model]"
---

# pageindex — document → hierarchical page index

Turn a markdown/text document into a **page index**: a nested table-of-contents
tree where each node carries its title, level, position, a 5W summary, and token
estimate, plus document-spanning "blocks" with their own synthesized summaries.

The work is done by the bundled, self-contained script at
`scripts/pageindex/`. It wraps the same PageIndex pipeline Memex uses, but
vendored to run anywhere with only `dspy`, `tiktoken`, `regex`, `pydantic`.
**Run the script — do not re-implement the indexing logic.**

## How to run

From the skill's `scripts/` directory (so the `pageindex` package is importable):

```bash
cd <skill>/scripts
python -m pageindex path/to/doc.md --model gemini/gemini-2.5-flash
```

Or one-shot with `uv` (no install needed):

```bash
uv run --with dspy --with tiktoken --with regex --with pydantic \
  python -m pageindex path/to/doc.md --model gemini/gemini-2.5-flash
```

Dependencies otherwise: `pip install -r scripts/pageindex/requirements.txt`.

## Choosing `--model`

The model id follows the **litellm `provider/model` convention**, so any provider
litellm supports works — just change the string. A few examples:

- `--model gemini/gemini-2.5-flash` (fast, cheap, reliable structured output)
- `--model anthropic/claude-sonnet-4-6`
- `--model openai/gpt-4o`
- `--model ollama_chat/llama3 --api-base http://localhost:11434` (local; ollama
  needs `--api-base`)

API keys are read from the provider-standard env var
(`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, …) unless you pass
`--api-key`. If a key is missing, the failure surfaces from litellm mid-run — set
it first.

## Options

- `--output / -o FILE` — write JSON to a file instead of stdout.
- `--full` — emit the complete result (tree **plus** blocks, body text, and the
  node→block map). Default is the **thin tree** (structure + summaries, no
  duplicated document body) — that thin tree *is* the page index for most uses.
- `--max-concurrency N` — cap concurrent LLM calls (default 20). Lower it for a
  local/rate-limited model (e.g. `--max-concurrency 2` for ollama).

Output is JSON on stdout; a one-line summary (`path_used`, coverage, node/block
counts) goes to stderr, so piping stdout stays clean.

## What you get back, and what to do with it

The JSON tree is a list of nodes, each with `title`, `level`, `children`,
`token_estimate`, `summary` (a 5W object), and `assets`. To answer the user:

- **Render it as an indented outline** (title per line, indented by `level` /
  nesting) rather than dumping raw JSON — that's what someone asking for an
  "outline" or "TOC" wants to read.
- **Report `coverage_ratio` and `path_used`** from the stderr summary so the user
  knows how much of the doc was mapped and which path ran:
  - `regex_fast` — well-structured markdown; headers came from regex (summaries
    still use the LLM).
  - `llm_scan` — unstructured doc; headers were found by the LLM.
  - `short_doc_bypass` — doc was tiny and headerless; returned as a single node
    with **no LLM call at all** (so this path needs no API key).
- **Handle the empty/degenerate case**: an unstructured doc can yield an empty
  `toc` — say so plainly instead of presenting an empty outline as success.

## Model-agnostic, honestly

Any litellm model can be passed, but the pipeline asks the model for **structured
output** (typed header lists and summaries). Strong API models (gemini, claude,
gpt) handle this reliably. Small local models (e.g. `ollama_chat/llama3`) can
fail the structured-output parse on the `llm_scan` and summary steps — if results
look empty or malformed with a local model, retry with a stronger one before
assuming the document is the problem.

## Note on provenance

`scripts/pageindex/` is a vendored snapshot of Memex's
`packages/core/src/memex_core/memory/extraction/` page-index code (models,
signatures, utils, and the `index_document` orchestrator), with the production
circuit-breaker / metrics shims removed for standalone use. It can drift from the
in-repo source over time; re-sync from those modules if behaviour needs to match
the live system.
