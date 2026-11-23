---
name: drawio-architecture
description: Draw, update and review architecture diagrams in draw.io (.drawio, .drawio.png) using C4 notation and one consistent house style, then verify every change by rendering the diagram and looking at it. Use whenever the user wants to create or change a draw.io / diagrams.net diagram of a system, including C4 context, container, deployment or dynamic (numbered request flow) diagrams and solution designs in draw.io, or says "update the diagram", "add a note to the drawing", "fix the arrows", "the drawio MCP is down, edit the file", or "make the .drawio match the RFC/code". Also use it to review a draw.io diagram for C4 and labeling problems. Not for Mermaid diagrams (use c4-diagrams), and not for sequence, ER or UML class diagrams.
compatibility: Python 3.10+ (standard library only). draw.io desktop 27.0.2+ for rendering (https://github.com/jgraph/drawio-desktop); on Linux headless also xvfb-run. A drawio MCP server is used when available but is not required.
---

# draw.io architecture diagrams

A diagram is a claim about a system. Make it say one thing, in C4 notation, in the same style as its siblings, and never report a change as done before you have rendered the file and looked at the picture. XML that parses can still draw an arrow straight through a box.

Do not use this skill for Mermaid or PlantUML (use `c4-diagrams` for Mermaid C4), for sequence, ER or class diagrams, or for diagrams with no system architecture in them (org charts, mind maps).

## Before you touch a file

1. **Pick the kind, scope and status.** Kind: context, container, deployment, or dynamic (a numbered flow for one scenario). Scope: the one system or flow in focus. Status: as built, or proposed. All three go on the canvas (title and scope line), because a reader only has the image.
2. **Find the source of truth.** Every element, label, header name, path and protocol must trace to code, docs or the design being drawn. Never invent a header, role or route to make an arrow read better. If something is proposed and not built, say so on the diagram.
3. **Check nobody else is editing.** Note the file's modification time before reading and check it again before writing. Editors such as the VS Code draw.io extension save in place. If the file changed under you, stop and ask: overwriting loses the other person's work, and merging blind detaches edges.
4. **Back up** the file (copy to a scratch dir) before the first edit.
5. **Inventory it:** `python scripts/drawio_inventory.py DIAGRAM` lists every element and edge with ids and full labels, and flags detached or dangling edge ends, unlabeled edges, gaps or repeats in step numbers, narrow `labelWidth`, and an embedded Mermaid source. Cite elements as `[id] label`.

## Style

Use the palette and style strings in `references/style.md`; copy them, don't approximate. When the diagram has siblings, match the siblings first and the reference second, because consistency across a set beats any single rule. For a new diagram, start from `assets/c4-template.drawio`.

| Element | Look |
| --- | --- |
| Person | grey actor, label below |
| Container or system the team owns | orange `#dca26c` box, white text; data stores as cylinders |
| External software system | purple `#8e8299` box, white text |
| Deployment node / boundary | dashed grey outline, no fill, name at top |
| Note | yellow `#fff4c4` box, linked to its subject with a dotted line |
| Proposed note | same, dashed border |
| Relationship | orthogonal, rounded, block arrow, label with translucent background |

## Labels

These carry most of the meaning, so be exact and brief.

- **Element:** `<b>Name</b><br>[Type: technology]<br>One line on what it does`. Types: `Person`, `Software System`, `Container: <technology>`, `Deployment Node`.
- **Relationship:** one direction, verb first, then the transport in brackets: `Writes the order<br>[SQL over private IP]`. Add `Auth: …` when credentials are the point, and `Returns: …` when the response matters (for example `Returns: aud = B, azp = A`).
- **Dynamic diagrams:** prefix every relationship with its step, `1:`, `2:` …, numbered in the order things happen. When you insert or remove a step, renumber all later steps and every note that cites a step number.
- **Notes:** start with `NOTE:` and state one fact the arrows can't show. Proposed behavior starts with `PROPOSED:` and uses future tense or "must", never present tense, so nobody mistakes it for what is built.
- **Title:** `<Kind> diagram: <scope>`, with `(proposed)` when the whole diagram is a design. Under it, one line of scope and a color legend if colors mean anything beyond the table above.
- Plain words, no marketing, no dates in labels. Spell out non-obvious acronyms once.

## Layout

- Flow left to right: people on the left, external systems on the edges of the canvas, the system in focus in the middle.
- One abstraction level per diagram, roughly 20 elements at most. Split rather than shrink.
- Keep labels off boxes and off other lines. Route long arrows around boxes with waypoints instead of through them.
- Put notes in free space next to their subject. Widen a note instead of letting text overflow.

## Editing

Use the drawio MCP server when it is connected. When it isn't, edit the XML directly with a small Python script (`xml.etree.ElementTree`), not with `sed` and not by hand-writing a new file, so ids, styles and geometry survive. Read `references/xml-editing.md` first: it has the file structure, recipes and gotchas. The two that bite most:

- Coordinates, including edge waypoints, are relative to the cell's `parent`. They are absolute only when the parent is the layer (`1`).
- Rewiring an edge means clearing its old waypoints and `exit*`/`entry*` style constraints, or draw.io keeps the old route.

Change only what the task asks. Leave positions, colors and wording of untouched elements alone.

## Verify

Repeat until clean:

1. `python scripts/drawio_inventory.py DIAGRAM`: `problems: none`, apart from a Mermaid reminder you have acted on.
2. `python scripts/render.py DIAGRAM -o <scratch>/out.png`, then look at the PNG. Check that nothing overlaps (labels on boxes, labels on labels, arrows through boxes, text overflowing notes) and that each arrow is readable from start to end.
3. Re-read every changed label against the source of truth.

Report only what you saw in the render. "No overlaps" is a claim about the picture, so make it from the picture.

## Review mode

When asked to review rather than change, stay read-only and go through `references/review-checklist.md`. Each finding names the element (`[id] label`), what the diagram says, what the evidence says, and where the evidence is.

## Gotchas

- draw.io desktop's CLI exports without opening a window. On Linux it needs `--no-sandbox` as root and a display (`xvfb-run -a`). `render.py` handles both.
- An edge with only `sourcePoint`/`targetPoint` renders fine but no longer follows its shapes. The inventory flags it, so fix it whether you caused it or not.
- `html=1` labels accept `<br>` and `<b>`. Literal newlines also break lines.
- A PNG saved by anything but draw.io loses its embedded source. Never write a `.drawio.png` with another tool.
