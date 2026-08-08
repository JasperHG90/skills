# python-cli

A skill for building command-line tools in Python that are pleasant for people
*and* usable by scripts and agents. It is opinionated: Typer for the command
tree, Rich for output, Pydantic for structured input and config.

## What it does

Given "build me a CLI for this", "add a `deploy` subcommand", or "my CLI takes
two seconds to print `--help`", the skill works through:

1. **Who the interface is for** — human at a terminal, CI script, agent, or
   another developer importing the code. Nearly every later decision falls out
   of this, and it is the step people skip.
2. **Package shape** — commands parse and print; the actual work lives in
   ordinary functions the CLI calls, so it stays testable and importable.
3. **Root app defaults** — `no_args_is_help`, completion, and
   `pretty_exceptions_show_locals=False` (Typer's default traceback prints
   locals, which is how tokens reach CI logs).
4. **Command naming** — `<noun> <verb>`, singular nouns, and no subgroup until
   it holds a second command.
5. **Fast startup** — heavy imports inside command bodies first, then lazily
   loaded subgroups when the tree gets big.
6. **Input** — arguments vs options, explicit `envvar=` names, layered config
   with `pydantic-settings`, Pydantic models behind a `parser=`, `-` for stdin.
7. **Output** — separate stdout/stderr Consoles, Rich tables for humans,
   `--json` for everyone else, honest exit codes.
8. **Tests** — `CliRunner`, asserting the exit codes and the `--json` contract.

## Prerequisites

Python 3.10+, `typer` (≥ 0.26) and `rich`; `pydantic` and `pydantic-settings`
for the structured-input and config sections. Install with `uv add typer rich
pydantic pydantic-settings`.

The guidance was verified against **typer 0.27**. The 0.26 floor is where the
version-sensitive facts hold: Click is vendored from 0.26 (so `import click`
fails in a clean install, and the lazy-group code subclasses
`typer.core.TyperGroup`), and `no_args_is_help` exits 2 only from 0.24. The
`LazyGroup` itself runs on typer 0.12.

## Contents

| File | What's in it |
|---|---|
| `SKILL.md` | The workflow, the naming conventions, the gotchas, the done-when checklist |
| `references/lazy-groups.md` | Copy-in `LazyGroup` implementation, wiring, and how to verify laziness holds |
| `references/inputs.md` | Arguments vs options, env vars, layered config, Pydantic models as parameters, prompting |
| `references/output.md` | Two-Console setup, `--json`, colour detection, error messages, exit codes, help text, tests |

## The four things people get wrong

- **A Typer app with one command and no `@app.callback()` is not a group.** Your
  `cls=`, `no_args_is_help`, and group name are silently ignored and subcommands
  appear flattened at the root.
- **Naive lazy loading still imports everything on `--help`,** because rendering
  the root help asks every subcommand for its one-line description. The
  `LazyGroup` in the reference keeps those strings statically to avoid it.
- **`auto_envvar_prefix` derives names from the command path** — `acme job run
  --region` reads `ACME_JOB_RUN_REGION`, which nobody guesses and a command
  rename silently changes. Name env vars explicitly.
- **Going lazy deletes Typer's "Did you mean …?" suggestions,** because they are
  built from `self.commands`, which never holds a lazy name. The `LazyGroup` in
  the reference rebuilds them.

## Related

- [`../python-review`](../python-review/README.md) — reviewing the code once it
  exists.
- [`interface-audience`](../../../rules/interface-audience.md) — the general
  principle behind Step 1, applied beyond CLIs to APIs, libraries, and agent
  tools.

## Validating

The skill produces code, so validate by running it: `--help` at every level,
`--json` piped through `jq`, a non-zero exit on failure, and
`python -X importtime -c "from <pkg>.cli.main import app; app()" --help` to
confirm startup stays cheap.
