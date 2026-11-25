# Review checklist

Read-only. For each finding give: element (`[id] label` from the inventory), what the diagram says, what the evidence says, the citation, and a severity (major, minor, nit).

## Truth

- [ ] Every element and relationship in scope exists in the code, docs or design it claims to show, with matching names, technologies, paths and header names.
- [ ] Nothing in scope is missing from the diagram.
- [ ] Proposed or unbuilt behavior is marked as such (`PROPOSED:`, "must", or `(proposed)` in the title), never stated in present tense.
- [ ] Sibling diagrams use the same names, headers and terms for the same things.

## C4

- [ ] Title states kind and scope. One line states scope, status, and a legend if colors carry meaning.
- [ ] Every element has a name, a `[Type: technology]` and a one-line description.
- [ ] Every relationship points one way, starts with a verb, and names the protocol or transport.
- [ ] One abstraction level. Components are not on a container diagram, and other systems appear as whole systems.
- [ ] Boundaries and deployment nodes are named.
- [ ] Dynamic diagrams: steps are numbered 1..N with no gaps, and notes cite the right step numbers.

## Picture

Render it and look. These only show in the image.

- [ ] No label sits on a box, another label or another line.
- [ ] No arrow runs through a box. Crossings use arcs.
- [ ] Note text fits inside its note.
- [ ] Colors follow the style, or the documented palette of the sibling set.

## Source

`scripts/drawio_inventory.py` flags the first four. Check the last one by hand.

- [ ] No detached or dangling edge ends.
- [ ] No unlabeled relationships (dotted note links excepted).
- [ ] No missing or repeated step numbers.
- [ ] No `labelWidth` narrower than its box.
- [ ] Embedded Mermaid source, if any, matches the cells.
