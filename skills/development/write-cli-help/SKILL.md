---
name: write-cli-help
description: >-
  Write or repair command-line help: --help output, flag descriptions, usage
  strings, command-group summaries, and the refusal messages a CLI prints when
  an input is missing or wrong. Use this whenever you add or change a flag,
  argument or subcommand in Typer, Click, argparse, Cobra, clap, oclif or any
  other CLI framework, whenever you write or edit a `help=` string, and
  whenever someone says their --help is unreadable, too terse, too long, or
  that a coding agent guessed a flag's value wrong. Use it even when the ask
  sounds tiny, like "add a --force flag": the help string ships with the flag,
  and it is the only description of that input most callers and every agent
  will ever read.
---

# Writing CLI help

## The one idea

Help text is read at two moments by readers who want opposite things.

**Orientation.** "What does this tool do, and what flags exist?" The reader is
scanning, comparing flags against each other. What helps is one short line per
flag, aligned, so the eye runs down the column. Detail hurts here, because
volume destroys the alignment that makes scanning work at all.

**Commitment.** "I have picked `--project-suffix`. What do I type?" The reader
has stopped on one flag. Now they need why it is required, what the value
becomes, where to get it, and what is legal. Brevity hurts here, because a
caller who knows only the shape of a value supplies a legal one instead of the
right one.

One column cannot serve both. Trying anyway produces a surface that serves
neither, and that is the failure this skill exists to catch, because it is the
one that looks like diligence.

## Recognize the expensive failure

Terse help is an obvious defect. Everyone can see that `--agent-name  The
agent's name.` says nothing, and someone eventually fixes it.

The costly failure is the opposite, and it survives review because every
sentence in it is true and useful:

```
│ *  --project-suffix   <917>   The number at the end of your GCP project ids. │
│                               Copy it from the project, or look yours up on  │
│                               the Project Suffix Logic page linked in        │
│                               `agentic-platform scaffold --help`. Your       │
│                               projects already exist and this command never  │
│                               contacts GCP. It only writes the ids as text,  │
│                               into .env.example so local development points  │
│                               at your dev project, and into                  │
│                               .github/workflows/dep…                         │
│                               [required]                                     │
```

Three things went wrong, and only the first is about taste:

1. **Orientation is gone.** Six flags like this and the reader cannot answer
   "what flags exist" without reading a page of prose.
2. **It is lossy.** `.github/workflows/dep…` is truncated. So is the flag's
   own name, two options down: `--agentic-platform-s…`. So is the lookup
   command
   the author added precisely so nobody would have to guess:
   `gh release list --repo rituals-data/rail-age…`. The literals most worth
   writing down are exactly the ones the column destroys.
3. **`[required]` is buried** nine lines below the flag it applies to.

An option's description column is the narrowest and most hostile space in the
entire interface, and it is where people put their most important prose.

## There are three surfaces, and they are not the same width

| Surface | Width | Attention |
|---|---|---|
| Option description | ~40 to 50 chars | scanning, low |
| Command or group help, including epilog | full terminal | moderate |
| Refusal or error message | full terminal | total, the reader is blocked |

Detail belongs in the widest surface with the most attention. Most CLIs put it
in the narrowest with the least. Invert that, and most help problems dissolve
without anything being deleted.

## Look at it before you write a word

Rendering is a constraint, not a formatting concern discovered later. Measure
the column before spending it.

```bash
python3 ~/.claude/skills/write-cli-help/scripts/audit_help.py -- mycli scaffold agent
```

The script renders `--help` at 80, 100 and 120 columns, then reports
truncation, flags whose description runs long enough to break scanning, help
strings that only restate the flag name, literals too wide to ever fit, and
required or default markers stranded away from their flag. It exits non-zero
when it finds something.

Run it on the command you are about to touch, and run it again when you are
done. Eighty columns is the number that matters: it is the default width of a
pipe, of CI logs, and of the text an agent receives.

## The summary line

One line per flag. It fits the description column without wrapping. It
distinguishes this flag from its neighbors. It does not restate the flag name.

```
--project-prefix <rail-storebuddy>  Start of your GCP project ids
--project-suffix <917>              Number at the end of them
--output <./rail-fleet-agent>       Where to write it (must not exist)
--package <rail_store_buddy>        Python package for the code
--agent-name <shelf_scout>          Agent's name [default: --package]
```

**Spend the metavar.** It renders in the flag column, costs nothing from the
description budget, and carries the concrete example that otherwise eats a
sentence. `<917>` does more work than "for example, 917" and is free. A flag
whose value has any shape at all should have a metavar showing that shape.

**Keep markers adjacent.** `[required]`, `[default: ...]` and `[env var: ...]`
are scanned, not read. They have to sit where the eye already is.

## Cut before you move anything

Relocating a wall produces a wall. The first move on any over-long help string
is to DELETE, and only what survives deletion gets a home.

**Budget: one to three sentences per option, and three only when the third
earns it.** That is the whole allowance, on every surface combined. If an
entry needs more, the usual cause is that it is explaining the system rather
than the input.

Calibrate against a CLI known for good help. `uv venv --help` is 116 lines for
about 25 options, roughly one sentence each:

```
  -p, --python <PYTHON>      The Python interpreter to use for the virtual
                             environment. [env: UV_PYTHON=]
      --managed-python       Require use of uv-managed Python versions
```

That is the density to hit. A command with half uv's options and more than
uv's lines is over budget, and no amount of correct formatting fixes it.

Three tests for a sentence before it survives:

- **Does the caller have to know this to supply a value?** Background on why
  the system works this way does not. Docs and code comments take it.
- **Is it already in the summary line or the metavar?** "Must not exist" in a
  summary needs no paragraph under it.
- **Would they find out anyway, immediately and cheaply?** A constraint the
  next run reports in a clear refusal does not need pre-announcing.

Most options need nothing on the detail surface at all. Reach for it for the
few facts that are expensive to discover and impossible to infer: a value that
is never validated, a name that other systems resolve later, a lookup command,
an absolute path.

## The detail surface

Everything that survived the cut goes somewhere reachable, and the summary
view says where. Answer four questions, in this order:

| Question | Why it is there |
|---|---|
| Why is it required? | a caller who knows the purpose supplies the right value, not merely a legal one |
| What does it become? | a caller who cannot see the consequence cannot tell a wrong answer from a right one, and neither can the reviewer reading the diff |
| Where does the value come from? | an input with no stated origin reads as the caller's to invent, so a caller holding no value invents one |
| What is legal? | with no shape to satisfy, the nearest plausible string wins, and a plausible wrong value builds a tree that parses |

The first question is the one almost never written, and the one that prevents
the most damage. Answer only the ones that are live for a given input: four
questions is the checklist, not the output shape, and writing all four for
every flag is how a detail surface becomes the wall it replaced.

Pick the surface that fits the CLI. In rough order of preference:

- **A dedicated verb**, `mycli explain --project-suffix`, when the CLI already
  has subcommands. Full width, no ceiling, addressable per flag.
- **The command epilog**, printed under the options block at full width, when
  the command has few enough flags that a "Details" section stays readable.
- **A man page or docs URL**, named once in the group help, when the project
  already maintains one.
- **`--help-verbose`**, as a fallback when none of the above fit.

Whichever you choose, it has to satisfy one rule: **the summary view names the
detail surface, on its own line, at full width.** A detail surface nobody is
told about is a file nobody opens.

```
  --explain FLAG   why it's needed, where to find the value, what's legal
```

## Write for the agent reader too

A coding agent runs `--help`, reads it as text, and then picks values. It does
not scroll back, it does not run a second command unless the first one named
it, and it cannot recover a truncated token: `rituals-data/rail-age…` is
unrecoverable, and the agent will invent the rest rather than stop.

This has already cost real work. A flag shipped as `help="The agent's name."`,
the one flag on its command carrying neither an example nor a constraint, and
an agent that had just read `--help` invented `depot_tools` from the repository
prefix. Every fact it needed was written down, in a skill file the agent had
not loaded.

Two consequences:

- **Never let a literal truncate.** Commands, paths, URLs, and identifiers
  either fit or move to a full-width surface. A URL in an option's help is
  always wrong: it is an unbreakable token, so it truncates, and in Markdown
  rendering modes it hides the address entirely, which is useless to a reader
  consuming `--help` as text.
- **A fact needed to supply an input belongs in the help and in the refusal**,
  both of which ship with the binary. Prose in a README or a skill file may
  route and sequence and interpret. When it is the only place a constraint,
  origin, or lookup command is written, it has taken ownership of an interface
  it does not ship, and the fact moves into the code in the same change that
  notices.

## Group help carries the preconditions

A caller who learns about a missing prerequisite from a failure learns it far
from the cause, often in a different repository, days later. Group help is full
width and nearly free, so it is where prerequisites go.

Name what must already exist, what provides each one, and whether its absence
blocks the run now or only a later step. That ordering is the useful part: a
caller needs to know which gaps to fix before running and which to raise a
request for while the work proceeds.

```
Generate a repository from a bundled template.

This command checks none of the following. Scaffolding succeeds without them,
and you find out at deploy time, in the repository it just generated. Before
you deploy, your GCP project needs:

  Vertex AI API enabled          run the /scaffold-infra-repo skill
  Access via a Google group      run the /scaffold-infra-repo skill
  A Shared VPC subnet attached   run the /request-subnet skill
  Local credentials              gcloud auth application-default login

The subnet is the one that blocks deployment outright: the org policy
constraints/run.allowedVPCEgress rejects a Cloud Run service with no VPC
egress.
```

The last paragraph is the part a caller cannot infer. A precondition the
command does not itself check is the one most worth printing, because nothing
else in the run will mention it.

## Refusals are help text with a captive reader

An error message is the only help you can be certain was read. It has full
width and the reader's complete attention, because they are blocked. Treat it
as the best surface you have, rather than as a status code with a sentence
attached.

`--agent-name is required when no terminal is attached` states a fact about the
environment and implies one move, which is to supply the flag. The cheapest way
to supply it is to invent it, so the message rewards the failure it exists to
prevent.

A refusal says what the value is, where it comes from, and what to do next. The
caller has to be able to act on the message alone, having read nothing else:

```
--owner was not supplied.

It is the team that owns this spoke, in GitHub style, and it becomes the
owner line in CODEOWNERS. It must start with @rituals-data/, and the part
after the slash is the team's slug, the last part of its URL.

Find yours at https://github.com/orgs/rituals-data/teams, then re-run with
--owner @rituals-data/<slug>.
```

## Anti-patterns

**Restating the flag name.** `--agent-name`, "The agent's name." The help has
to add a fact the name does not already carry.

**Promising a constraint the code does not enforce.** Help that describes a
shape nothing validates is a lie the caller discovers three files later. Help
that omits a shape the code does enforce is a refusal they could not have
avoided. The two move together: a value described as a valid Python identifier
is checked as one before anything is written, and a value checked as one says
so.

**Two wordings for one value.** Two commands taking the same input use the same
help string. Shipping `"GCP project suffix."` on one and `"GCP project suffix,
e.g. 908."` on another teaches the reader that the value is two things, and the
thinner description is the one that gets believed.

**Examples that derive from each other.** A `--prefix` example of
`rail-store-buddy` beside a `--package` example of `store_buddy` demonstrates a
transform: drop the leading token, underscore the rest. A reader completing the
pattern applies it to their real prefix instead of asking whether the transform
is real. Pick examples for caller-authored inputs that no other example in the
same command can produce.

**Explaining the implementation instead of the choice.** A caller does not need
to know which function writes the file. They need to know what changes on disk
if they pick a different value.

## Before you call it done

- `audit_help.py` exits zero at 80 columns.
- No option's text runs past three sentences across all surfaces combined.
- Total `--help` length is in `uv`'s league: about 4 to 5 lines per option,
  counting the detail surface. Count them.
- Every flag has a one-line summary that fits and does not restate its name.
- Every flag with a shaped value has a metavar carrying a concrete example.
- No literal (command, path, URL, identifier) truncates anywhere.
- The summary view names the detail surface on its own line.
- Group help names the prerequisites the command does not check.
- Every constraint stated in help is enforced in code, and the reverse.
- Refusals name the fix and the origin of the value, not just the symptom.

## Reference files

- `references/frameworks.md`: where the width is set, how to add a detail
  surface, and what truncates, for Typer, Click, argparse, Cobra and clap. It
  opens with ripgrep, whose `-h` and `--help` differ by 135 lines against 1564,
  as a worked example of the two-tier split done well.
- `references/rewrites.md`: worked before-and-after rewrites, including the
  full repair of the truncating example above.
