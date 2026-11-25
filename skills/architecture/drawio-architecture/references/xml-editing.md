# Editing draw.io XML directly

Use this when no drawio MCP server is available. Edit with `xml.etree.ElementTree` in a short Python script, run it, then render and look.

## File structure

```xml
<mxfile host="drawio">
  <diagram id="..." name="Page-1">          <!-- one per page -->
    <mxGraphModel ...>
      <root>
        <mxCell id="0"/>                     <!-- root -->
        <mxCell id="1" parent="0"/>          <!-- default layer -->
        <mxCell id="api" value="..." style="..." vertex="1" parent="1">
          <mxGeometry x="380" y="270" width="200" height="130" as="geometry"/>
        </mxCell>
        <UserObject id="e3" label="3: Charges the card&#xa;[HTTPS]">   <!-- wrapper: label lives here -->
          <mxCell edge="1" parent="1" source="api" target="pay" style="...">
            <mxGeometry relative="1" as="geometry">
              <mxPoint x="-40" y="10" as="offset"/>      <!-- label offset in px -->
              <Array as="points"><mxPoint x="480" y="600"/></Array>  <!-- waypoints, in parent's coordinates -->
            </mxGeometry>
          </mxCell>
        </UserObject>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

- **Labels** are `value` on a bare `mxCell`, or `label` on a `UserObject`/`object` wrapper. Wrappers can also carry `mermaidBaseValue`, a copy of the label. Update both.
- **Coordinates** of vertices, edge waypoints and `sourcePoint`/`targetPoint` are all in the coordinate system of the cell's `parent`. They are absolute only when the parent is the layer (`1`). draw.io often parents an edge between two shapes in the same container to that container, so check the edge's `parent` before writing waypoints. To place something next to a shape, add up the parents' offsets, or measure from the render: find a top-level cell's position in the PNG and its `x`/`y` in the XML, and the difference is the export offset.
- **Edge label position:** `mxGeometry x` (between -1 and 1 along the path, 0 is the middle) plus the `offset` point in pixels.
- **Compressed pages:** if `<diagram>` contains text instead of `<mxGraphModel>`, it is base64 of raw deflate of URL-encoded XML. `python scripts/drawio_inventory.py DIAGRAM --xml > plain.drawio` writes the decoded file. Edit that and save it uncompressed, since draw.io reads both.
- **Other wrapper attributes** such as `link`, `tooltip` or `placeholders` stay on the wrapper. Keep them when copying cells.
- **Embedded Mermaid:** a `UserObject` with `mermaidData` holds JSON whose `data` field is the Mermaid source the diagram was generated from. Apply every label and edge change there too, and replace exact substrings with an assertion that each matches once.

## Recipes

Load and save, keeping ids and attribute order:

```python
import xml.etree.ElementTree as ET
tree = ET.parse(path); root = tree.getroot()
page = root.findall("diagram")[0] if root.tag == "mxfile" else root  # ids are unique per page only
def wrapper(cid):                       # the element holding the label
    return next(e for e in page.iter() if e.get("id") == cid)
def cell(cid):                          # the mxCell, inside a wrapper or bare
    e = wrapper(cid)
    return e if e.tag == "mxCell" else e.find("mxCell")
tree.write(path, encoding="unicode")
```

| Task | Change |
| --- | --- |
| Relabel | set `label` on the wrapper (and `mermaidBaseValue` if present), or `value` on a bare `mxCell` |
| Rewire an edge | set `source`/`target`; remove the `Array as="points"` and the `exitX/exitY/entryX/entryY/exitDx/...` keys from `style`; remove `sourcePoint`/`targetPoint` |
| Reroute around boxes | add `exitX=..;exitY=..;entryX=..;entryY=..;` to `style` (0 to 1 on each axis) and waypoints in `Array as="points"`, in the edge parent's coordinates |
| Move a label off a box or line | change the `offset` point, or `mxGeometry x` along the path |
| Add a note | deep-copy an existing note (same style and parent), give it a new id, set label and geometry, insert it after the original; add a note-link edge if useful |
| Make text fit | remove `labelWidth=`; widen the shape before making it taller |
| Re-attach a floating edge end | set `source`/`target` to the shape's id and drop `sourcePoint`/`targetPoint` |

Assert as you go, so a stale id fails loudly rather than silently doing nothing:

```python
missing = set(wanted_ids) - {e.get("id") for e in page.iter()}
assert not missing, missing
```

## Exports

- `.drawio.png`: the PNG carries the source in a `zTXt`/`tEXt` chunk keyed `mxGraphModel` (desktop) or `mxfile` (web). Extract it with `drawio_inventory.py DIAGRAM.drawio.png --xml > DIAGRAM.drawio`, edit that, then export with `render.py DIAGRAM.drawio --embed -o DIAGRAM.drawio.png`. Never edit the PNG with an image tool.
- Several pages: `render.py --page N` renders page N.
