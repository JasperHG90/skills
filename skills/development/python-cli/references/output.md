# Output contracts

Output is where a CLI most often serves one audience by breaking the other. The
fix is not to pick a side — it is to give stdout a contract and put everything
else somewhere else.

## Two Consoles

```python
# cli/console.py
from rich.console import Console

out = Console()                 # results — the thing the user asked for
err = Console(stderr=True)      # progress, warnings, errors, everything else
```

Import these two everywhere instead of constructing a `Console()` per module, so
one place controls theming and width.

The split is what makes `acme dataset list > datasets.txt` capture data and
nothing else, while the spinner and the warnings still reach the terminal.
Anything a caller would not want in that file — "connecting…", "using cached
credentials", "3 rows skipped" — goes to `err`.

Progress bars and spinners belong on stderr for the same reason. `rich.progress`
takes a console; give it `err`:

```python
from rich.progress import Progress

with Progress(console=err) as progress:
    task = progress.add_task("Fetching…", total=len(ids))
```

## `--json`

Any command that produces data gets a `--json` flag. It is what makes the tool
usable from a script, from CI, and from an agent that would otherwise be parsing
a box-drawing table with a regex.

```python
@app.command("list")
def list_datasets(
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON to stdout.")] = False,
) -> None:
    """List datasets."""
    datasets = fetch()                        # list[Dataset], a Pydantic model
    if as_json:
        out.print_json(DATASETS.dump_json(datasets).decode())
        return
    table = Table("Name", "Rows", "Updated")
    for d in datasets:
        table.add_row(d.name, str(d.rows), d.updated.isoformat())
    out.print(table)
```

Serialize a model rather than assembling a dict by hand. The JSON then has a
declared schema, the human table and the JSON cannot drift apart because both
read the same object, and there is one place to look when a consumer asks what
a field means. Build a `TypeAdapter` once at module scope for lists
(`DATASETS = TypeAdapter(list[Dataset])`) instead of per call.

What a model does *not* buy you is safety from renames: rename a field and the
JSON keys change silently. Type-checking catches the attribute access in the
table builder, not the contract you just broke. Renames need a deprecation
path (`Field(serialization_alias=...)`) or a version bump, the same as any
other published interface.

Two properties make `--json` worth trusting, and both are easy to lose:

- **stdout is JSON and nothing but JSON.** One stray `print()` and every
  downstream `json.loads` fails. This is the payoff for the two-Console split.
- **The shape is stable.** Adding a key is safe; renaming or removing one is a
  breaking change to a machine interface, even though nothing in Python
  complains.

## Colour and TTY detection

Rich already does the right thing: it drops styling when stdout is not a
terminal, and it honours the `NO_COLOR` environment variable. Do not hand-roll
`sys.stdout.isatty()` checks around your printing.

What is worth adding is `--no-color` for callers who want to force it while
still on a TTY, and `--quiet` to silence the stderr chatter without touching
stdout. Both are one line: `Console(no_color=True)` and a level check before
`err.print`.

Table borders and colour on a non-TTY are already handled, but table *layout*
is not — a wide table still wraps to the detected width. When output is being
piped, prefer `--json`; that is what it is for.

## Errors

An error message is an interface too, and its job is to let the caller fix the
problem without reading your source:

```python
err.print(f"[bold red]Error:[/] dataset {name!r} not found")
err.print("Run [bold]acme dataset list[/] to see available datasets.")
raise typer.Exit(code=1)
```

Say what failed, why, and what to do next. Print it to stderr, so a caller
redirecting stdout still sees it.

Exit codes are the part scripts actually branch on:

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | The command ran and failed — not found, permission denied, upstream error |
| `2` | The invocation was wrong. Typer already returns this for bad usage, `BadParameter`, and `no_args_is_help` |
| `>2` | Only when a caller has a concrete reason to distinguish a failure mode |

Catch exceptions you can explain, print a message, and exit. Let unexpected ones
crash with a traceback — a bug should look like a bug. Keep
`pretty_exceptions_show_locals=False` on the app so those tracebacks do not
print local variables holding tokens or connection strings.

## Help text

Help is the only documentation most people will read, and the only documentation
an agent can read at all.

- **The command's docstring is its help.** One line, imperative, saying what the
  command does — "List datasets", not "This command will list the datasets".
- **Every option gets `help=`.** An option without one is a guess.
- **Examples belong in the epilog** of commands whose usage is not obvious:
  `@app.command(epilog="Example: acme job run nightly --retries 5")`. Two real
  invocations teach more than a paragraph of prose.
- **No ASCII-art banner, no logo, no version splash.** It pushes the actual help
  below the fold, it is the first thing an agent has to parse past, and it is
  noise in every log that captures the output. The tool's name and one line of
  purpose is the entire header you need.
- **`--version` is an eager callback** on the root, so it works without a
  subcommand:

```python
from importlib.metadata import version


def _version(value: bool) -> None:
    if value:
        typer.echo(f"acme {version('acme')}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True)
    ] = False,
) -> None:
    """Manage Acme datasets and jobs."""
```

## Testing the contract

`typer.testing.CliRunner` keeps stdout and stderr separate on the result, so the
contract is directly assertable:

```python
from typer.testing import CliRunner

runner = CliRunner()


def test_json_goes_to_stdout_alone():
    result = runner.invoke(app, ["dataset", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)
    assert "Fetching" in result.stderr
```

Assert on exit codes, on the parsed `--json` structure, and on env vars being
picked up (`monkeypatch.setenv`). Avoid asserting on human-facing prose beyond
the promises you mean to keep — otherwise every wording improvement is a red
test, and the tests start discouraging the polish they were meant to protect.
