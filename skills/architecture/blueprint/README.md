# /blueprint

A Claude Code skill that scans a repository and produces a comprehensive architectural blueprint — a structured `BLUEPRINT.md` with tech stack, component maps, Mermaid diagrams, data flow, API surfaces, dependency graphs, and design patterns. It spawns parallel analysis agents for speed and verifies its own output before presenting.

## Usage

```
/blueprint [target-directory]
```

If no directory is given, it analyzes the current working directory.

## How it works

Three phases:

1. **Quick scan** — gathers surface facts itself (languages, build system, monorepo signals, key docs) and forms an architecture hypothesis to focus the agents.
2. **Parallel deep analysis** — spawns four specialized agents in a single turn:

   | Agent | Focus |
   |-------|-------|
   | Structure Analyst | Directory layout, modules, entry points |
   | Dependency Analyst | External + internal dependencies, infra |
   | Pattern Analyst | Architecture patterns, design decisions |
   | API Analyst | API surfaces, routes, CLI commands |

3. **Synthesis** — cross-validates the agents' findings, fills the blueprint template, generates Mermaid diagrams, then spawns a verifier agent that spot-checks specific claims against the source before fixing any inaccuracies.

## Output

`BLUEPRINT.md` in the target directory root. A good blueprint lets someone unfamiliar with the repo understand the system in ~10 minutes: accurate Mermaid diagrams, components described by *why* they exist, and dependencies categorized by purpose.

## Skill files

```
blueprint/
├── SKILL.md                          # Orchestration logic (3 phases)
├── agents/
│   ├── structure-analyst.md          # Per-agent instructions
│   ├── dependency-analyst.md
│   ├── pattern-analyst.md
│   └── api-analyst.md
└── references/
    └── blueprint-template.md         # Output document template
```
