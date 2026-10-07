# Worked rewrites

Real before-and-after pairs. The first is full length, the rest are short.

## Contents

- [The wall](#the-wall)
- [The restated name](#the-restated-name)
- [The URL that cannot fit](#the-url-that-cannot-fit)
- [Examples that teach a fake transform](#examples-that-teach-a-fake-transform)
- [The refusal that rewards guessing](#the-refusal-that-rewards-guessing)

## The wall

**Before.** Every sentence is true, and the flag is unusable anyway.

```python
project_suffix: Annotated[str, typer.Option(
    metavar="<917>",
    help="The number at the end of your GCP project ids. Copy it from the "
    "project, or look yours up on the Project Suffix Logic page linked in "
    "`agentic-platform scaffold --help`. Your projects already exist and this "
    "command never contacts GCP. It only writes the ids as text, into "
    ".env.example so local development points at your dev project, and into "
    ".github/workflows/deploy.yaml so CI deploys into the right one. Nothing "
    "checks the value.",
)],
```

At 80 columns this renders as 23 lines in a 22-character column, with
`.github/workflows/dep…` truncated and `[required]` stranded 22 lines below
the flag. There is a second tell: the help spends its scarcest resource on a
pointer to another help surface. When an option's description is forwarding
the reader elsewhere, the detail already wants to live elsewhere.

**After, the summary line.** One line, fits, does not restate the name.

```python
project_suffix: Annotated[str, typer.Option(
    metavar="<917>",
    help="Number at the end of your GCP project ids",
)],
```

**After, the detail surface.** Full width, so nothing truncates and the four
questions all get answered.

```
--project-suffix <917>                                            [required]

  Why it is required   This command never contacts GCP, so it cannot
                       discover the id and has to be told. A wrong value
                       points the generated repo at a project that does
                       not exist, and nothing fails until deploy.
  Where to find it     Copy the trailing number from any of your project
                       ids: rail-storebuddy-dev-917.
  What it becomes      Written as text into .env.example and into
                       .github/workflows/deploy.yaml.
  What is legal        Any string. Nothing validates it.
```

Note what the width bought: `.github/workflows/deploy.yaml` survives intact,
where the column had cut it to `.github/workflows/dep…`. The fact the author
added is now a fact the reader receives.

"What is legal: any string, nothing validates it" is worth printing precisely
because it is bad news. A caller who knows nothing is checked treats the value
with the care it needs.

## The restated name

**Before.**

```python
agent_name: Annotated[str, typer.Option(help="The agent's name.")]
```

This shipped, and an agent that had just run `--help` invented `depot_tools`
from the repository prefix. The help adds no fact the flag name does not
already carry, so there was nothing to check the guess against.

**After.**

```python
agent_name: Annotated[str | None, typer.Option(
    metavar="<shelf_scout>",
    help="Agent's name [default: the package name]",
)] = None,
```

with the rest on the detail surface: it goes into the agent's name in code and
into its Agent2Agent card, which is how other services find it, so renaming
later breaks anything that already resolved the card. Must be a valid Python
identifier, so underscores and no hyphens.

## The URL that cannot fit

**Before.** Unbreakable token in a 22-character column. It truncates, and the
address is lost.

```python
help="... look yours up at https://confluence.example.com/wiki/spaces/RAIL/pages/12345/Project+Suffix+Logic",
```

**After.** The URL moves to the group help, which is full width. The option
says only that a lookup exists.

```python
app = typer.Typer(
    epilog="Project suffix lookup:\n"
           "  https://confluence.example.com/wiki/spaces/RAIL/pages/12345/",
)
```

The same applies to shell commands. A `gh release list --repo <org>/<repo>`
lookup does not fit a column either, and truncating it produces a command that
looks copy-pasteable and is not.

## Examples that teach a fake transform

**Before.**

```
--project-prefix <rail-store-buddy>
--package        <store_buddy>
```

Side by side these demonstrate a rule: drop the leading token, underscore the
rest. A reader completing the pattern applies it to their real prefix instead
of asking whether the transform exists. It does not.

**After.** Pick examples that no other example in the same command can produce.

```
--project-prefix <rail-storebuddy>
--package        <shelf_scout>
```

## The refusal that rewards guessing

**Before.**

```
--agent-name is required when no terminal is attached
```

True, and it implies exactly one move: supply the flag. The cheapest way to
supply it is to invent it, so the message rewards the failure it exists to
prevent.

**After.** An error message has the reader's full attention and the full
terminal width. It is the best surface in the CLI, so use it.

```
--agent-name was not supplied, and there is no terminal to ask on.

It is what this agent is called in code and in its Agent2Agent card, which
is how other services find it. Renaming later breaks anything that already
resolved the card, so it is worth getting right the first time.

It must be a valid Python identifier: underscores, no hyphens.

Ask whoever owns this agent what it should be called, then re-run with
--agent-name <their answer>. To take the package name instead, re-run with
--agent-name shelf_scout.
```

The last paragraph matters most. A refusal that names two concrete next moves
ends the interaction. One that names none invites a guess.
