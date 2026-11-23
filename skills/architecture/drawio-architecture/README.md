# drawio-architecture

Draw, update and review architecture diagrams in [draw.io](https://www.drawio.com/) using C4 notation and one consistent house style. The skill checks every change by rendering the diagram and looking at the result.

It covers C4 context, container, deployment and dynamic (numbered request flow) diagrams. It gives the agent:

- a fixed palette and copy-paste style strings, plus a starter template;
- labeling rules for elements, relationships, step numbers and notes, including how to mark proposed behavior;
- recipes for editing `.drawio` XML directly when no drawio MCP server is available;
- a render-and-inspect loop, so overlapping labels and arrows through boxes are caught before anyone sees them;
- a read-only review checklist.

For C4 diagrams in Mermaid, use [`c4-diagrams`](../c4-diagrams) instead.

## Prerequisites

- Python 3.10+ (scripts use the standard library only).
- [draw.io desktop](https://github.com/jgraph/drawio-desktop/releases) for rendering. On headless Linux, also `xvfb-run`. Set `DRAWIO` if the executable is not on `PATH` or in a standard location.
- Optional: a drawio MCP server. The skill uses it when connected and falls back to editing the XML.

## Usage

```
Draw a dynamic diagram of the login flow: browser, API gateway, auth service, user DB.
```

```
Update docs/internal-route.drawio: agent A now does the token exchange itself. Keep the style.
```

```
Review architecture/hub.drawio.png against the Terraform in infra/.
```

## Scripts

| Script | Does |
| --- | --- |
| `scripts/drawio_inventory.py DIAGRAM [--page N] [--xml]` | Lists elements and edges with ids and full labels. Flags detached or dangling edge ends, unlabeled edges, step-number gaps, narrow `labelWidth` and embedded Mermaid sources. Reads `.drawio` and `.drawio.png`, compressed or not. `--xml` prints the decoded source. |
| `scripts/render.py DIAGRAM [-o OUT] [--page N] [--embed]` | Exports a PNG with the draw.io CLI. `--embed` keeps the diagram source inside the PNG. |

## Files

- `assets/c4-template.drawio`: starter diagram showing every element type in the house style.
- `references/style.md`: palette, style strings, sizes.
- `references/xml-editing.md`: file structure and editing recipes.
- `references/review-checklist.md`: what a review checks.

## Testing

```bash
python scripts/drawio_inventory.py assets/c4-template.drawio   # expect "problems: none"
python scripts/render.py assets/c4-template.drawio -o /tmp/template.png
```

`evals/evals.json` holds test prompts for the skill-creator eval loop.
