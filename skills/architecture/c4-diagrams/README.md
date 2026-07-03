# c4-diagrams

Create [C4 model](https://c4model.com/) architecture diagrams as Mermaid — system context, container, and component views, plus dynamic and deployment views when needed.

The C4 model describes one software system at successive zoom levels, like a map: Level 1 (Context) shows the system among its users and neighboring systems for any audience; Level 2 (Container) shows the deployable pieces and technology choices; Level 3 (Component) opens up a single container; Level 4 (Code) is left to IDE tooling. The skill defaults to Context + Container, enforces C4's notation rules (typed elements, technology labels, specific unidirectional relationship labels, one abstraction level per diagram), and validates each diagram against a review checklist before presenting it.

It also covers data platforms: an adaptation guide maps sources/consumers, brokers, orchestrators, warehouses, and BI tools onto the C4 levels, with data-flow arrow conventions and format/protocol/cadence labeling.

## Prerequisites

None. Diagrams are plain Mermaid and render on GitHub, in most Markdown viewers, and at [mermaid.live](https://mermaid.live). If [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) (`mmdc`) is available, the skill uses it to verify diagrams render; otherwise it validates syntax by review.

## Usage

Ask for C4 diagrams of a codebase or a described system:

```
Draw a C4 context and container diagram for this repo
```

```
Create C4 diagrams for our data platform: Kafka ingestion, dbt on Snowflake, Tableau on top
```

```
Review this container diagram against C4 conventions
```

The skill takes an optional argument — a path, system name, or description:

```
/c4-diagrams ./services/billing
```

## What it produces

One Mermaid diagram per level (`C4Context`, `C4Container`, and optionally `C4Component`, `C4Dynamic`, `C4Deployment`), each with a title, typed and described elements, technology labels, and labeled directional relationships. For large diagrams where Mermaid's experimental C4 layout degrades, it falls back to a `flowchart` that keeps the C4 notation in node and edge text.

## Structure

| File | Purpose |
|---|---|
| `SKILL.md` | Workflow: scope/audience, fact-gathering, drawing, notation rules, validation |
| `references/mermaid-c4.md` | Mermaid C4 syntax reference and flowchart fallback |
| `references/review-checklist.md` | Per-diagram quality checklist |
| `references/data-platforms.md` | Adaptation guide and worked example for data teams |

## Testing

Validate the skill's structure:

```bash
skills-ref validate ./skills/architecture/c4-diagrams
```

Smoke-test by asking for a context + container diagram of a small repo and checking the output against `references/review-checklist.md`.

## Sources

- [c4model.com](https://c4model.com/) — the canonical reference by Simon Brown
- [The C4 Model — architecture diagrams that actually make sense](https://medium.com/@abhinav.dobhal/the-c4-model-finally-architecture-diagrams-that-actually-make-sense-e1a85284e8a1)
- [C4 Modelling for Data Teams: From Chaos to Clarity](https://blog.datatraininglab.com/c4-modelling-for-data-teams-from-chaos-to-clarity-a9f499007e20)
- [r/dataengineering: C4 models and data architecture](https://www.reddit.com/r/dataengineering/comments/1i972qf/c4_models_and_data_architecture/)
