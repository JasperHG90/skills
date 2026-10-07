# Framework notes

Where the width is set, how to build a detail surface, and what truncates.

Checked against Typer 0.27.2 / Click 8.5.0. Everything else is stable API.

## Contents

- [The pattern already exists: ripgrep](#the-pattern-already-exists-ripgrep)
- [Typer and Click](#typer-and-click)
- [argparse](#argparse)
- [clap (Rust)](#clap-rust)
- [Cobra (Go)](#cobra-go)
- [Forcing a width when you test](#forcing-a-width-when-you-test)

## The pattern already exists: ripgrep

Before designing a detail surface, look at one that works. ripgrep splits
`-h` from `--help` and the difference is 135 lines against 1564.

`rg -h`, the orientation tier:

```
  -M, --max-columns=NUM           Omit lines longer than this limit.
```

`rg --help`, the commitment tier, same flag:

```
    -M NUM, --max-columns=NUM
        When given, ripgrep will omit lines longer than this limit in bytes.
        Instead of printing long lines, only the number of matches in that line
        is printed.

        When this flag is omitted or is set to 0, then it has no effect.
```

Two things carry over regardless of framework. The long tier puts the flag on
its own line, which buys the description the full terminal width instead of a
column. And it allows paragraph breaks, which a column cannot render at all.

## Typer and Click

Typer wraps Click and renders through Rich by default
(`rich_markup_mode="rich"`).

**What truncates.** Rich truncates any unbreakable token wider than the
description column and marks it `…`. That includes URLs, file paths,
dotted identifiers, and shell commands. It will also truncate the flag's own
name when the flag column is too narrow, which is how
`--agentic-platform-sdk-version` renders as `--agentic-platform-s…` at 80
columns. Truncation is silent and lossy.

**Never put a URL in an option's `help`.** It is unbreakable, so it truncates.
With `rich_markup_mode="markdown"` a link renders with the address hidden,
which is useless to anyone reading `--help` as text, agents included.

**Width.** Rich honors the `COLUMNS` environment variable. To stop the help
from narrowing on small terminals, widen the content box through Click:

```python
app = typer.Typer(context_settings={"max_content_width": 100})
```

This raises the ceiling. It does not help when the real terminal is narrower,
so it is not a substitute for a summary line that fits.

**Metavar** renders in the flag column, in place of the type name:

```python
project_suffix: Annotated[str, typer.Option(
    metavar="<917>",
    help="Number at the end of your GCP project ids",
)]
```

**Panels** group options under headings, which restores some scanning ability
when a command has many flags:

```python
typer.Option(..., rich_help_panel="Cache options")
```

**Detail surfaces**, in order of preference:

- A real command. This is the most discoverable and has no width ceiling:
  ```python
  @app.command()
  def explain(flag: Annotated[str, typer.Argument(metavar="<--project-suffix>")]):
      """Why a flag is needed, where to find its value, and what is legal."""
  ```
- `epilog=`, on the `Typer()` or on a command. Rendered full width under the
  options block, so it is the cheapest place to put a "Details" section or a
  docs URL.
- Disable Rich entirely with `typer.Typer(rich_markup_mode=None)` when you want
  Click's plain formatter and control over wrapping.

## argparse

**Width** comes from `shutil.get_terminal_size()`, which reads `COLUMNS`
first, so the same environment variable works for testing.

**Keep your own formatting** in the description and epilog, which argparse
otherwise re-wraps:

```python
argparse.ArgumentParser(
    description="One line saying what this does.",
    epilog="Details:\n  --flag  ...",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
```

`RawDescriptionHelpFormatter` leaves the description and epilog alone while
still wrapping option help. `RawTextHelpFormatter` stops wrapping option help
too, which means you own every line break.

**Widen the option column** when flag names are long, instead of letting the
descriptions squeeze:

```python
formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=36)
```

argparse does not truncate. It wraps, so nothing is lost, but a wall is still
a wall.

## clap (Rust)

clap has the two-tier split built in, which is why ripgrep gets it for free:

```rust
#[arg(
    short = 'M',
    long,
    value_name = "NUM",
    help = "Omit lines longer than this limit.",
    long_help = "When given, ripgrep will omit lines longer than this \
                 limit in bytes. Instead of printing long lines, only \
                 the number of matches in that line is printed.",
)]
max_columns: Option<usize>,
```

`-h` renders `help`. `--help` renders `long_help`. Set both. When only `help`
is set, clap shows it in both tiers and the long tier buys you nothing.

`value_name` is the metavar. Width comes from the terminal, overridable in
tests with `COLUMNS`.

## Cobra (Go)

`Short` is the orientation tier and appears in the parent's command list.
`Long` is the commitment tier and prints on `--help`. `Example` prints below
it, which is the natural home for copy-pasteable invocations:

```go
&cobra.Command{
    Use:     "create",
    Short:   "Create a pull request",
    Long:    "...full width, paragraphs allowed...",
    Example: "  gh pr create --title 'Fix' --body 'Closes #1'",
}
```

Flag help comes from pflag and is a single string with no long form, so per
flag detail goes in `Long` or in a `explain` subcommand.

## Forcing a width when you test

Every framework above reads `COLUMNS`. Eighty is the number that matters: it
is the default width of a pipe, of CI logs, and of the text an agent receives.

```bash
COLUMNS=80 mycli scaffold agent --help
```

Note that a pipe already narrows most of these to 80, so `mycli --help | cat`
and `mycli --help > file` show you the reader's view rather than yours.
