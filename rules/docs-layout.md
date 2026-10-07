---
name: docs-layout
description: What belongs in docs/ (for people using the project) versus .okf/ (for agents and people working on it). Read before writing or moving prose under docs/, .okf/, or the README.
paths: ["docs/**", ".okf/**", "README.md"]
---

# `docs/` and `.okf/`

Two places hold prose, and they have different readers.

- `docs/` is for people who USE the harness: an operator installing it in a
  repo, writing a ticket, or reading why a commit was refused. `docs/README.md`
  is the index and lists every page.
- `.okf/` is for agents and people working ON this repository: decisions and
  the alternative each rejected, lessons learned the hard way, and proposals
  not yet built. How to read and extend it is `.claude/rules/okf-bundle.md`.
  The current design (vision, invariants, values) is the bundle's root
  concept, `.okf/manifesto.md`. It links to the decisions for the why and
  never repeats a decision record.

Ticket plans and verdicts stay in `.loop/`, and neither folder copies them.

<constraint name="docs-sorted-by-reader-intent">
WHY: a page filed under the wrong heading is read by the wrong person.

`docs/` has one subdirectory per Diataxis type, created with its first page:
`how-to/` (one task, one way), `reference/` (commands, config keys, hook
entries, without instructing), `explanation/` (why the harness is shaped this
way, for example the honest boundaries of what it can and cannot verify), and
`tutorials/` (a lesson sure to succeed in one sitting). Mixing two intents in
one page is a reason to split it.
</constraint>

<constraint name="audience-gates-the-folder">
WHY: a spike, a build plan or a handoff reads as current instructions to a
user who finds it in `docs/`.

A spike, a proposal, a build plan, an audit, a handoff note, or the record of
a choice goes to `.okf/`, even when it is shaped like a guide.
</constraint>

<constraint name="docs-describe-what-exists">
WHY: v2 starts with no code, and a user page about a command that does not
exist yet is a hallucination with a table of contents.

A `docs/` page lands in the same change as the behavior it describes. Until
then the design lives in `.okf/manifesto.md` and `.okf/proposals/`.
</constraint>

<constraint name="index-tracks-the-folder">
WHY: an index is believed, so an index that disagrees with its folder is
worse than none.

Adding, renaming or removing a page under `docs/` updates `docs/README.md` in
the same change, and updates every link to the old path.
</constraint>
