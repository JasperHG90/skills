# C4 diagram review checklist

Run every finished diagram through this list. Fix failures before presenting; if an item is deliberately violated, say so and why when presenting the diagram.

## Diagram

- [ ] Title states the diagram type and scope ("Container diagram for X"), so the reader knows the abstraction level without guessing.
- [ ] One abstraction level only: a Context diagram shows no containers, a Container diagram shows no components.
- [ ] Exactly one system is in scope (except system landscape diagrams).
- [ ] Element count is roughly 20 or fewer; split the diagram or drop detail otherwise.
- [ ] A key/legend explains any coding the notation itself doesn't (Mermaid draws no legend, so a caption below the diagram covers e.g. "grey = external").
- [ ] The intended audience could read this diagram cold — acronyms they may not know are expanded in a description.

## Elements

- [ ] Every element's type is visible (Person / Software System / Container / Component, external or not).
- [ ] Every element has a short description of its responsibility — the "at a glance" test.
- [ ] Every container and component states its technology.
- [ ] External elements (not owned by the team) are marked as external.
- [ ] People are humans; upstream/downstream software is modeled as external systems, not people.

## Relationships

- [ ] Every line is an arrow (unidirectional) with a label.
- [ ] Labels are specific verbs reflecting intent — no bare "uses", "talks to", "integrates with".
- [ ] Inter-process relationships (container level and up) state protocol/technology.
- [ ] One arrow convention per diagram — dependency direction or data-flow direction, not a mix.
- [ ] Two-way interactions with distinct intents are two labeled arrows, not one double-headed line.

## Set of diagrams

- [ ] Levels are consistent with each other: every container on the Container diagram belongs to the system on the Context diagram; every external system a container talks to appears at Level 1.
- [ ] Styling (color, shape) means the same thing on every diagram in the set.
- [ ] The Mermaid source parses and renders (see rendering check in `mermaid-c4.md`).
