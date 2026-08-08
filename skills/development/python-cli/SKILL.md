---
name: python-cli
description: >
  Build and improve command-line tools in Python with Typer — command tree and
  naming, lazy-loaded subgroups for fast startup, Rich output with a clean
  stdout/stderr split, a machine-readable --json mode, environment variables and
  layered config, Pydantic models as structured input, honest exit codes, and
  help text that actually helps. Use this skill whenever the user wants to
  create, scaffold, restructure, or improve a CLI, command-line tool, terminal
  app, console script, or `argparse`/`click`/`typer` program in Python; adds a
  subcommand or command group; wires env vars or a config file into commands;
  wants CLI output that is readable by humans and parseable by scripts and
  agents; or complains that their CLI is slow to start, awkward to use, or ugly
  to read. NOT for: TUIs and full-screen interfaces (Textual), HTTP APIs, or a
  one-off script with a couple of flags where `argparse` is enough.
compatibility: >
  Python 3.10+ with typer >= 0.26 and rich; pydantic and pydantic-settings for
  structured input and layered config. Verified against typer 0.27. The 0.26
  floor is where the body's version-sensitive facts hold — Click is vendored
  from 0.26, and `no_args_is_help` exits 2 only from 0.24. The lazy-group code
  itself works back to typer 0.12.
---

# Python CLIs

A CLI is a user interface, and the user is usually not the person who wrote it.
Most bad CLIs are not badly coded — they are coded without deciding who is on
the other end. Start there, then build the command tree, then make it fast.

## When not to use this skill

- **A full-screen, interactive app** — that is a TUI. Reach for Textual.
- **A script with two flags that only you run.** `argparse` is in the standard
  library and adds no dependency. This skill starts paying off at the point you
  have subcommands, config, or other people.
- **The user asked about an HTTP API or a library's public functions.** The
  interface thinking transfers; the Typer mechanics do not.

## Step 1 — Decide who the interface is for

Ask it explicitly before writing a command, because nearly every later decision
falls out of the answer. Most real CLIs serve more than one audience, and the
job is to serve each without compromising the others.

| Audience | What they need | What that means in code |
|---|---|---|
| A human at a terminal | Discoverability, readable output, forgiving errors that say what to do next | Rich tables, colour, `--help` with examples, confirmation prompts |
| A script or CI job | Stable output, stable exit codes, no prompts, no colour | `--json`, `--yes`, exit codes that mean something, `NO_COLOR` respected |
| An agent | Everything CI needs, plus self-description: it reads `--help` to learn the tool | Complete help text, machine-readable errors, no interactive-only paths |
| Another developer importing your code | A callable Python function | Keep logic out of the command body — see Step 2 |

The rule of thumb: **a human-facing default with a machine-facing escape hatch**
beats two separate tools. Ship the pretty table by default and `--json` for
everyone else. What you cannot do is force interactivity — a command that only
works when someone is there to answer a prompt is unusable to two of the four
audiences above. This is the `interface-audience` rule applied to one surface;
the same question governs an API or a library.

## Working on a CLI that already exists

Command names, option names, env var names, and exit codes are a published
contract. Someone's script, CI job, or agent depends on each of them, and
nothing in Python will warn you when you break one.

So on an existing tool, apply everything below to **new** commands, and treat
changes to existing ones as proposals: list what you would rename and why, and
let the user decide. If they accept, ship an alias and a deprecation warning
rather than a hard cut. The same goes for the framework itself — porting an
`argparse` or `click` tool to Typer is a migration the user asks for, never a
side effect of adding a subcommand.

Leave alone, unless the task is explicitly about them: existing command and
option names, exit codes, the shape of existing `--json` output, and env var
names already in use.

## Step 2 — Shape the package

The command layer parses input and prints output. Nothing else. Business logic
lives in ordinary functions the CLI calls, so it stays testable, importable, and
reusable by an API or a notebook later.

```
src/acme/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py          # root Typer app, global options, lazy subgroup map
│   ├── lazy.py          # LazyGroup (see references/lazy-groups.md)
│   ├── console.py       # the two Consoles — stdout and stderr
│   └── commands/
│       ├── dataset.py   # one module per subgroup, each exposing `app`
│       └── job.py
├── config.py            # pydantic-settings
└── core/                # the actual work — knows nothing about Typer
```

Wire the entry point in `pyproject.toml` so the tool is a real command, not a
`python -m` incantation:

```toml
[project.scripts]
acme = "acme.cli.main:app"
```

## Step 3 — Build the root app

```python
app = typer.Typer(
    name="acme",
    cls=Root,                            # your LazyGroup subclass — see Step 5
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich",
)


@app.callback()
def root() -> None:
    """Manage Acme datasets and jobs."""
```

Each default is load-bearing:

- **`no_args_is_help=True`** — a bare `acme` prints help instead of an error.
  Someone who types the tool's name is asking what it does; answer the question.
- **`pretty_exceptions_show_locals=False`** — Typer's default traceback prints
  local variables, which is how tokens and connection strings end up in CI logs
  and pasted issues.
- **`add_completion=True`** — shell completion is close to free and is the
  cheapest discoverability you will ever ship.
- **The `@app.callback()` is not optional** — see the first gotcha below. Its
  docstring becomes the root help.

Command docstrings are rendered help, not API documentation: keep them to one
imperative line, and document parameters in `help=` on each option rather than
in a docstring section. This is the deliberate exception to the repo's
numpy-style docstring rule — a `Parameters` block would be printed verbatim
into `--help`.

## Step 4 — Name the commands

Use `<noun> <verb>`: `acme dataset list`, `acme job run`. The noun-first order
groups related commands together in help output and matches how people search
their shell history.

**Nouns are singular.** `acme dataset list`, not `acme datasets list`. Singular
reads correctly for every verb in the group (`dataset delete <id>` operates on
one thing), plural only reads correctly for the listing ones, and a mixed
codebase forces users to remember which groups got which. Pick singular and hold
it everywhere — this is the convention `docker container ls` and `kubectl get
pod` settled on.

**A group needs more than one command to exist.** If `acme config` only ever
holds `show`, make it `acme config` — a command, not a group. A subgroup wrapping
a single command costs the user a word on every invocation and buys nothing. Add
the group at the moment the second command arrives.

Verbs come from a small shared set — `list`, `get`, `create`, `delete`, `run`,
`show` — reused across every group. A user who learns `dataset list` should be
able to guess `job list` without reading anything.

## Step 5 — Keep startup fast with lazy subgroups

CLI startup is the tool's first impression, and it is spent almost entirely on
imports. A root module that imports every command module, which each import
pandas or boto3 at module scope, pays for the whole tree on every invocation —
including `acme --help`.

Two tiers, in order:

1. **Import heavy libraries inside the function that needs them**, not at module
   scope. This is most of the win, costs nothing, and needs no machinery.
2. **When the tree is large enough that even the command modules hurt, load them
   lazily.** `references/lazy-groups.md` has a `LazyGroup` you can copy in
   whole: subgroups are declared as `name -> (module path, one-line help)`, the
   module is imported only when that subgroup is actually invoked, and root
   `--help` renders from the static help strings without importing anything.

Measure before reaching for tier 2 — `python -X importtime -c "from
acme.cli.main import app; app()" --help 2>&1 | tail -20` names the expensive
import directly.

## Step 6 — Take input

Full detail in `references/inputs.md`. The decisions that matter:

- **Arguments are the thing being acted on; options are how.** `acme job run
  nightly --retries 3`. If a parameter is required and there is only one of it,
  it is an argument.
- **Every option that could come from the environment gets an explicit
  `envvar=`.** `typer.Option(envvar="ACME_REGION")`. Typer's
  `auto_envvar_prefix` also works, but it derives `ACME_JOB_RUN_REGION` —
  prefix, command path, *and* option name — which almost nobody predicts. Name
  the variables yourself.
- **Secrets come from the environment, never from a flag.** Anything on the
  command line is in `ps` output and shell history.
- **Config layers, and the precedence is part of the interface:** explicit flag
  beats environment variable beats config file beats default. Document it in
  `--help`; implement it with `pydantic-settings`.
- **Structured input is a Pydantic model behind a `parser=`.** Take a path to a
  JSON file, accept `-` for stdin, validate into a model, and convert
  *everything* the parser can raise — `OSError` for a mistyped path as well as
  `ValidationError` — into `typer.BadParameter`. The parser is the boundary;
  whatever escapes it reaches the user as a traceback.

## Step 7 — Give output a contract

Full detail in `references/output.md`. The shape of it:

- **Two Consoles, one purpose each.** Results go to stdout; progress, warnings,
  and errors go to stderr. `acme dataset list > out.txt` should capture data and
  nothing else, and the diagnostics should still reach the terminal.
- **`--json` on any command that produces data.** Serialize a Pydantic model —
  the flag then has a schema behind it instead of a hand-built dict that drifts.
- **Rich handles colour detection**; do not fight it. It already drops styling
  when stdout is not a TTY and honours `NO_COLOR`.
- **No ASCII-art banner, ever.** It is the first thing a human sees and the
  first thing an agent has to parse past, it pushes the actual help below the
  fold, and it is noise in every log that captures it. The tool's name and one
  line of purpose is the whole header.

## Step 8 — Fail usefully

Exit codes are the API that scripts consume, so use them deliberately: `0`
success, `1` the command ran and failed, `2` the user's invocation was wrong
(Typer already returns 2 for bad usage and for `no_args_is_help`). Reserve
distinct codes above 2 only when a caller has a reason to branch on them.

Catch the exceptions you can explain and re-raise them as messages plus
`typer.Exit(code=1)`. An error worth printing says what failed, why, and what to
do next. Let genuinely unexpected exceptions crash with a traceback — a bug
should look like a bug, not like a handled error.

## Step 9 — Test it

`typer.testing.CliRunner` runs commands in-process. Recent versions keep stdout
and stderr separate on the result, which lets you assert the contract from
Step 7 directly:

```python
def test_list_writes_data_to_stdout_only():
    result = runner.invoke(app, ["dataset", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)          # stdout parses as JSON
    assert "connecting" in result.stderr      # progress went elsewhere
```

Test the exit codes, the `--json` shape, and that env vars are picked up
(`monkeypatch.setenv`). Test help text only where it carries a promise you
intend to keep — asserting on prose makes every wording change a test failure.

## Gotchas

These cost real debugging time and none of them are guessable:

- **A single-command Typer app is not a group.** A Typer app holding exactly
  one command and no `@app.callback()` collapses into a single-command program,
  silently ignoring `cls=` and `no_args_is_help`. Symptom: your subcommands
  appear flattened at the root. (The root's `name=` is decorative either way —
  the program name in help comes from `sys.argv[0]`.)
- **`typer.main.get_command()` collapses too.** Use `typer.main.get_group()`
  when you need a group back from a `Typer` instance.
- **Typer vendors Click from 0.26** (`typer._click`) and no longer depends on
  it, so `import click` raises `ModuleNotFoundError` in a fresh install.
  Subclass `typer.core.TyperGroup`, which is the supported surface on every
  version.
- **Rendering root `--help` calls `get_command()` for every subcommand** to read
  its one-liner. That is why naive lazy loading still imports the whole tree on
  `--help`, and why the `LazyGroup` in the reference keeps static help strings.
- **`no_args_is_help` exits 2, not 0** — from Typer 0.24; before that it exited
  0. Fine for humans either way, but a CI step that runs the bare command
  changes behaviour across that boundary.
- **Going lazy drops Typer's "Did you mean …?" suggestions** unless you rebuild
  them, because Typer derives them from `self.commands`, which never holds a
  lazy name. The `LazyGroup` in the reference restores them.

## Done when

- `acme`, `acme --help`, and `acme <group> --help` all print something useful.
- Every command has a one-line docstring; every option has `help=`.
- Data goes to stdout, everything else to stderr, and `--json` parses.
- Exit codes distinguish success, failure, and misuse.
- No secret can be passed as a flag, and no traceback prints locals.
- Startup is fast enough that `--help` feels instant.
- Tests cover the exit codes and the `--json` contract.

## References

- `references/lazy-groups.md` — copy-in `LazyGroup` implementation, wiring, and
  how to verify laziness actually holds.
- `references/inputs.md` — arguments vs options, env vars, layered config with
  `pydantic-settings`, Pydantic models as parameters, stdin.
- `references/output.md` — the two-Console setup, Rich tables and progress,
  `--json`, colour detection, error rendering.
