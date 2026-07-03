---
name: c4-diagrams
description: Create C4 model architecture diagrams (system context, container, component, plus dynamic and deployment views) as Mermaid, for software systems and data platforms. Use when the user says "C4", "C4 model", "context diagram", "container diagram", "component diagram", "system context", "architecture diagram", "diagram this system", "visualize the architecture", "diagram the data platform / pipeline", or wants audience-appropriate views of a system at different zoom levels. Also use to review or fix an existing C4 diagram. For a full written blueprint document of a repository, use the blueprint skill instead.
argument-hint: "[system, codebase path, or description]"
---

# C4 Architecture Diagrams

You produce C4 model diagrams: a small, fixed set of zoom levels over one software system, like map zoom levels — each level answers a different audience's questions. The output is one Mermaid diagram per level, each following the notation rules below.

Do not fire this skill for: full repository blueprint documents (use `blueprint`), entity-relationship/schema diagrams, sequence diagrams outside a C4 dynamic view, network topology, org charts, or UML class diagrams. C4 describes the static structure of *one* software system and its neighbors; if the user wants "everything about this repo documented", that is `blueprint`, not this.

## The abstractions

Everything in a C4 diagram is one of these. Getting the level right matters more than any visual choice.

| Abstraction | Definition | Examples |
|---|---|---|
| Person | A human user of the system — actor, role, persona | Customer, Data Analyst, Support Agent |
| Software System | The highest level of abstraction; delivers value to its users. The thing you are diagramming, plus external systems it talks to | Internet Banking System, Salesforce, E-mail System |
| Container | A separately runnable/deployable unit that executes code or stores data. Not a Docker container (though it may be deployed as one) | Web app, mobile app, API service, database, message broker, scheduled job, serverless function |
| Component | A grouping of related functionality inside a container, behind a well-defined interface. Not separately deployable | `SecurityComponent`, GPS validator, retry handler |
| Code element | Classes, functions, interfaces implementing a component | — |

Hierarchy: a software system contains containers, a container contains components, a component is implemented by code. People use software systems.

## Workflow

### 1. Establish scope and audience

Identify the single system in scope and who each diagram is for. This decides which levels to draw:

| Level | Audience | Draw it when |
|---|---|---|
| 1 — System Context | Everyone, including non-technical | Always. Start here. |
| 2 — Container | Architects, developers, ops | Almost always — this is the most useful diagram for most teams. |
| 3 — Component | Developers working inside a container | Only for containers whose internals others genuinely need to understand. Skip by default. |
| 4 — Code | Developers | Don't hand-draw. Generate from an IDE/tooling if truly needed, which it rarely is. |

Context + Container is the right default; produce more only when asked or clearly valuable. Supplementary views when the question calls for them: **system landscape** (several systems across an enterprise — the only case where multiple systems are *in scope* on one diagram), **dynamic** (order of interactions for one runtime scenario), **deployment** (mapping of containers onto infrastructure).

### 2. Gather facts

For a codebase: identify deployable units (entry points, Dockerfiles, `docker-compose.yml`, IaC, CI deploy jobs), data stores, queues, external services (API clients, SDK dependencies, environment variables pointing at hosts), and the kinds of users. Deployables and datastores become containers; everything the system talks to but the team doesn't own becomes an external system.

For a described system: ask for, or infer and confirm, the users, the external systems, the deployable pieces, and the technology of each. Don't invent containers the user never mentioned — a wrong diagram is worse than a question.

### 3. Draw

Default to Mermaid C4 syntax (`C4Context`, `C4Container`, `C4Component`, `C4Dynamic`, `C4Deployment`) — it renders on GitHub and keeps diagrams versionable next to code. Syntax reference: `references/mermaid-c4.md`. Read it before writing your first diagram; the element macros and their argument order are not guessable.

One diagram per level, one abstraction level per diagram — a Container diagram never shows components, a Context diagram never shows containers. Keep each diagram under roughly 20 elements; past that, split by subsystem or drop detail rather than shrinking boxes.

### 4. Apply notation rules

These come from the C4 review checklist and are what separates a C4 diagram from generic boxes-and-arrows:

- Every diagram has a title stating type and scope: `System Context diagram for Internet Banking System`.
- Every element states its type and carries a one-line description of its responsibility. Containers and components also state technology: `Container: Spring Boot / Java`.
- Every relationship is a unidirectional line with a specific label — the verb carries intent. "Sends customer update events to" beats "uses"; never leave an arrow unlabeled. If the relationship genuinely runs both ways with different intents, draw two arrows.
- Container-level (inter-process) relationships also state protocol/technology: `JSON/HTTPS`, `SMTP`, `JDBC`.
- Pick one arrow convention — either direction of dependency ("reads from") or direction of data flow ("sends data to") — and keep it consistent within a diagram; for data pipelines, data-flow direction is usually clearer.
- Acronyms the audience may not know are spelled out in descriptions.
- Every diagram has a key/legend. Mermaid's C4 renderer draws none, so add a one-line caption below the diagram explaining the coding (e.g. "Grey elements are outside the team's ownership").
- Color and shape carry no inherent meaning in C4 — if you style elements, keep the coding consistent across diagrams.

These rules reappear as the verify-time checklist in `references/review-checklist.md`; when editing either, keep the two in sync.

### 5. Validate

Before presenting, check every diagram against `references/review-checklist.md` and fix what fails. Then verify the Mermaid actually renders: if mermaid-cli is available (`command -v mmdc`, or npx in an environment with network access) run it on each diagram per the rendering check in `references/mermaid-c4.md`; otherwise re-read the source against the syntax reference — the C4 grammar is strict about argument order and unquoted commas, and a diagram that doesn't render is worth nothing.

## Data platforms and pipelines

C4 was built for application software but maps well onto data work; the mapping is spelled out with an example in `references/data-platforms.md`. Read it whenever the target is a data platform, warehouse, or pipeline. The short version: sources and consumers become people/external systems at Level 1; broker, orchestrator, transformation jobs, warehouse, and BI tool become containers at Level 2 with data format + protocol + cadence (batch/stream) on every data-movement arrow; the stages inside a single job become components at Level 3.

## Reviewing an existing diagram

When asked to review or fix a diagram rather than create one: run it against `references/review-checklist.md`, report each violation with the offending element or relationship, and — only if asked to fix — rewrite it using `references/mermaid-c4.md`. The end state of a review is a violation list; the end state of a fix is a diagram that passes the checklist and renders.

## Gotchas

- "Container" predates Docker and does not mean Docker container. A database is a container; a Lambda function is a container.
- C4 diagrams show static structure. Ordering, branching, and "what happens when X" belong in a dynamic diagram, not in numbered arrows on a container diagram.
- Mermaid's C4 support is officially experimental: long labels overflow boxes, and auto-layout degrades past ~10 elements. Mitigations — keep names and descriptions short, use `UpdateLayoutConfig` to control row width, and if layout stays unreadable fall back to a plain `flowchart` with `subgraph` boundaries while keeping all C4 notation rules (types, technology, descriptions, labeled arrows) in the node and edge text.
- A person must be a human. Upstream systems that push data in are external software systems, not people.
- Diagrams describing an existing codebase are claims about that codebase — verify container lists against what is actually deployed (compose files, IaC, CI) rather than against directory names.

## Reference files

| File | When to read |
|---|---|
| `references/mermaid-c4.md` | Step 3 — before writing any Mermaid C4 syntax |
| `references/review-checklist.md` | Step 5 — validating each finished diagram |
| `references/data-platforms.md` | When the target system is a data platform or pipeline |
