# Taking input

Four channels carry input into a CLI — arguments, options, environment
variables, and config files — and each suits a different caller. Putting a value
on the wrong channel is what makes a tool annoying in one context and unusable
in another.

## Arguments vs options

An **argument** is the thing being acted on. An **option** is how to act on it.

```python
from typing import Annotated

import typer


@app.command()
def run(
    name: Annotated[str, typer.Argument(help="Job to run.")],
    retries: Annotated[int, typer.Option(help="Attempts before giving up.")] = 3,
) -> None:
    """Run a job."""
```

Required inputs are arguments; optional ones are options with defaults. Beyond
two arguments, positions stop being memorable — promote the rest to named
options even where they are required. `Annotated` is the current Typer style and
the one to write; the older `name: str = typer.Argument(...)` form still works,
and there is no reason to churn a codebase that uses it.

## Environment variables

Name every variable explicitly:

```python
region: Annotated[str, typer.Option(envvar="ACME_REGION")] = "eu-west-1"
```

Typer also supports `context_settings={"auto_envvar_prefix": "ACME"}`, which
derives names automatically — but it derives them from the prefix, the command
path, *and* the option name, so `acme job run --region` reads
`ACME_JOB_RUN_REGION`. That is hard to guess, and renaming a command silently
changes the variable. Explicit `envvar=` names survive refactors and can be
documented.

Typer prints the variable name in `--help` for any option that has one, which is
most of the documentation you owe your users.

**Secrets only ever come from the environment.** A `--token` flag lands in `ps`
output, in shell history, and in CI logs that echo their commands. If a token
must be passable per-invocation, accept a *path* to a file containing it, or
read it from stdin.

## Layered config

Most CLIs eventually need a config file, and the moment they do, precedence
becomes part of the interface. Use the order callers expect — **flag beats
environment variable beats config file beats default** — and say so in help
text. `pydantic-settings` implements it:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration resolved from the environment and .env."""

    model_config = SettingsConfigDict(env_prefix="ACME_", env_file=".env")

    region: str = "eu-west-1"
    retries: int = 3
```

Build `Settings` once in the root callback and hand it down through `ctx.obj`,
so a bad value surfaces at startup rather than at the first attribute access
deep inside a command. Catch the failure there as well — a mistyped env var is
user misconfiguration, not a bug, and it should read like one:

```python
@app.callback()
def root(ctx: typer.Context) -> None:
    """Manage Acme datasets and jobs."""
    try:
        ctx.obj = Settings()
    except ValidationError as exc:
        err.print(f"[bold red]Invalid configuration:[/]\n{exc}")
        raise typer.Exit(code=2) from exc
```

Without the `except`, a value like `ACME_RETRIES=notanint` exits 1 with a full
traceback — indistinguishable from a crash, and the wrong exit code for what is
really a usage error. Then let an explicitly
passed flag override the settings value — `typer.Option(default=None)` plus
`value if value is not None else settings.region` keeps "not given" distinct
from "given the same as the default".

## Pydantic models as parameters

Typer maps parameters by type, and it has no idea what to do with a Pydantic
model. Give it a `parser=` and it does:

```python
import sys
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError


class JobSpec(BaseModel):
    """A job submission, as supplied by the caller."""

    name: str = Field(description="Job name.")
    retries: int = Field(default=3, ge=0, description="Attempts before failing.")


def parse_spec(value: str | None) -> JobSpec | None:
    if value is None:
        return None
    try:
        raw = sys.stdin.read() if value == "-" else Path(value).read_text()
        return JobSpec.model_validate_json(raw)
    except (OSError, ValidationError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@app.command()
def submit(
    spec: Annotated[
        JobSpec | None,
        typer.Option(
            parser=parse_spec,
            metavar="PATH",
            help="Path to a JSON job spec, or - for stdin.",
        ),
    ] = None,
) -> None:
    """Submit a job."""
```

Four things earn their place here:

- **`model_validate_json` on the raw text**, not `json.loads` then validate. A
  malformed file raises `ValidationError` like every other failure, so one
  `except` covers the whole boundary.
- **Re-raising as `typer.BadParameter`** turns Pydantic's error into a proper
  usage error: the message is framed as "Invalid value for '--spec'", it goes to
  stderr, and the process exits 2. Without it the user gets a traceback for
  their own typo.
- **The file read is inside the `try`, and `OSError` is caught alongside
  `ValidationError`.** The likeliest mistake with a "path to a JSON file"
  option is mistyping the path, and catching only `ValidationError` leaves that
  case — the headline one — crashing with a `FileNotFoundError` traceback and
  exit 1. The parser *is* the boundary: everything it can raise has to become a
  `BadParameter`, or it becomes a traceback.
- **`-` meaning stdin** is the convention every Unix tool follows, and it is
  what makes the command composable in a pipe.

Set `metavar` too. Typer derives the placeholder in `--help` from the parser
function's name, so without it the help reads `--spec <parse_spec>`.

Pydantic's error text names every bad field and why. Pass it through rather than
flattening it to "invalid spec" — the caller cannot fix what you do not tell
them.

## Prompting

`typer.Option(prompt=True)` and `typer.confirm()` are good for humans and fatal
for everyone else: a prompt in CI hangs until the job times out. Every
destructive command that confirms needs a `--yes` to skip it, and reading from a
non-TTY stdin should fail with a clear message rather than block.

```python
if not yes and sys.stdin.isatty():
    typer.confirm(f"Delete dataset {name}?", abort=True)
elif not yes:
    raise typer.BadParameter("Refusing to delete without --yes when not interactive.")
```
