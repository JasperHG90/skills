# Lazy subgroups

A CLI's startup time is almost all import time. With eager subgroups, `acme
--help` imports every command module, and each of those imports whatever the
command needs — pandas, boto3, a database driver — even though the user asked
for one line of text. `LazyGroup` defers each subgroup's module until that
subgroup is actually invoked.

Reach for this only after moving heavy imports inside command bodies. That
change is free and usually enough. This one is worth it when the tree itself is
large (roughly a dozen subgroups and up) or when a subgroup's module cannot
avoid an expensive import at module scope.

## The implementation

Copy this in as `cli/lazy.py`. It has no dependencies beyond Typer.

```python
from __future__ import annotations

import importlib
from difflib import get_close_matches
from typing import Any

import typer
from typer.core import TyperGroup

try:  # Typer < 0.26 depends on Click; 0.26+ vendors it.
    from click.exceptions import UsageError
except ModuleNotFoundError:
    from typer._click.exceptions import UsageError


class LazyGroup(TyperGroup):
    """A Typer group that imports a subgroup's module only when it runs.

    Subclass it and set ``lazy_subcommands`` to map a command name to the
    module that defines it and the one-line help shown by the parent's
    ``--help``. The help string is kept here on purpose: rendering the parent's
    help asks every subcommand for its short help, so storing it inline is what
    keeps ``--help`` from importing the whole tree.
    """

    # command name -> (module path, one-line help)
    lazy_subcommands: dict[str, tuple[str, str]] = {}

    def list_commands(self, ctx: Any) -> list[str]:
        return sorted([*super().list_commands(ctx), *self.lazy_subcommands])

    def get_command(self, ctx: Any, name: str) -> Any:
        # Called once per command while rendering --help. Return a stub that
        # knows its name and one-liner; importing here would defeat the point.
        if name in self.lazy_subcommands:
            _, short_help = self.lazy_subcommands[name]
            return TyperGroup(name=name, help=short_help)
        return super().get_command(ctx, name)

    def resolve_command(self, ctx: Any, args: list[str]) -> Any:
        # Called once, with the command the user actually typed. This is the
        # only path that needs the real thing.
        if args and args[0] in self.lazy_subcommands:
            group = self._load(args[0])
            return group.name, group, args[1:]
        try:
            return super().resolve_command(ctx, args)
        except UsageError as exc:
            self._add_suggestions(ctx, args, exc)
            raise

    def _add_suggestions(self, ctx: Any, args: list[str], exc: UsageError) -> None:
        # Typer builds its "Did you mean …?" hint from self.commands, which
        # never holds the lazy names. Rebuild it over the full command list.
        if not args or not exc.message.startswith("No such command"):
            return
        matches = get_close_matches(args[0], self.list_commands(ctx))
        if matches:
            suggestions = ", ".join(repr(m) for m in matches)
            base = exc.message.rstrip(".").split(". Did you mean")[0]
            exc.message = f"{base}. Did you mean {suggestions}?"

    def _load(self, name: str) -> TyperGroup:
        module_path, _ = self.lazy_subcommands[name]
        module = importlib.import_module(module_path)
        group = typer.main.get_group(module.app)
        group.name = name
        return group
```

`_add_suggestions` is not optional polish. Typer's own `resolve_command`
builds its "Did you mean 'dataset'?" hint from `self.commands`, which by
construction never contains a lazy name — so without this, going lazy silently
deletes a framework feature, and deletes it only for the subgroups you made
lazy. That inconsistency is worse than not having suggestions at all.

The split between `get_command` and `resolve_command` is what makes this work.
Click calls `get_command` for every subcommand when it renders help, and
`resolve_command` exactly once for the command the user typed. Display gets the
stub; dispatch gets the real module.

## Wiring it up

`cli/main.py`:

```python
import typer

from acme.cli.lazy import LazyGroup


class Root(LazyGroup):
    lazy_subcommands = {
        "dataset": ("acme.cli.commands.dataset", "Manage datasets."),
        "job": ("acme.cli.commands.job", "Manage jobs."),
    }


app = typer.Typer(
    name="acme",
    cls=Root,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.callback()
def root() -> None:
    """Manage Acme datasets and jobs."""


if __name__ == "__main__":
    app()
```

The `__main__` guard is what makes `python -m acme.cli.main` work. Without it
the module imports and exits, and any arguments after it are silently
discarded — which quietly breaks the verification command below.

`cli/commands/dataset.py` — an ordinary Typer app named `app`:

```python
import typer

app = typer.Typer(no_args_is_help=True, help="Manage datasets.")


@app.command("list")
def list_datasets(limit: int = typer.Option(10, envvar="ACME_LIMIT")) -> None:
    """List datasets."""
    from acme.core.datasets import fetch  # heavy import stays in the body

    ...
```

Eagerly registered commands still work alongside lazy ones — `app.command()` on
the root and `app.add_typer()` both compose with `LazyGroup`, and `list_commands`
merges the two sets.

## The cost of getting the help string wrong

The one-liner lives in two places: the `lazy_subcommands` map and the subgroup's
own `help=`. They can drift, and nothing will tell you. Keep them identical, and
if that bothers you, treat the map as the source of truth and let the subgroup
inherit its help from its callback docstring.

## Verifying laziness holds

It is easy to add an import somewhere that quietly undoes this. Check it rather
than assuming:

```bash
python -X importtime -c "from acme.cli.main import app; app()" --help 2>&1 | tail -20
```

The command modules should not appear. Use the `-c` form rather than
`python -m acme.cli.main --help`: if the module is missing its `__main__`
guard, `-m` imports it and exits without ever rendering help, so the check
passes on a CLI that imports its whole command tree. A verification command
that cannot fail is worse than none — confirm it fails when laziness is
broken before you trust it passing. For a regression test, assert on
`sys.modules` after invoking help:

```python
def test_help_does_not_import_command_modules():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "acme.cli.commands.dataset" not in sys.modules
```

Run that test in its own process, or the assertion picks up an import some
earlier test performed.

## Gotchas

- **`typer.main.get_group()`, not `get_command()`.** `get_command()` on a Typer
  app holding a single command returns that command rather than a group, so the
  subgroup's commands end up flattened into the parent. `get_group()` always
  returns a group.
- **The root app needs `@app.callback()`.** Without it, a root holding one
  eager command collapses to a single-command program and `cls=Root` is never
  consulted.
- **Subclass `typer.core.TyperGroup`, not `click.Group`.** Recent Typer vendors
  Click as `typer._click` and does not depend on it, so `import click` fails in
  a clean install. `TyperGroup` is public and correct on both old and new Typer.
- **Shell completion keeps working, and stays lazy.** Click resolves a
  completion context through `resolve_command`, so completing `acme dataset
  <TAB>` loads that one module and offers its commands, while completing at the
  top level loads nothing.
- **Typer's docs generator only sees the stubs.** `typer acme.cli.main utils
  docs` walks the tree with `get_command`, so lazy subgroups render as a
  heading with no commands underneath. If you generate CLI reference docs that
  way, generate them from an eager build of the app.
