# House style

Copy these style strings verbatim into the `style` attribute. They are the same strings `assets/c4-template.drawio` uses. All labels use `html=1`.

| Element | Style |
| --- | --- |
| Title | `text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;fontFamily=Trebuchet MS;fontSize=26;fontStyle=1;` |
| Scope line | `text;html=1;align=left;verticalAlign=top;whiteSpace=wrap;fontFamily=Trebuchet MS;fontSize=14;fontColor=#666666;` |
| Person | `shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fillColor=#e6e6e6;strokeColor=#8a8a8a;fontFamily=Trebuchet MS;fontSize=14;` |
| Deployment node / boundary | `rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#666666;dashed=1;dashPattern=6 4;verticalAlign=top;fontFamily=Trebuchet MS;fontSize=14;container=1;collapsible=0;` |
| Container / owned system | `rounded=0;whiteSpace=wrap;html=1;fillColor=#dca26c;strokeColor=#b9804b;fontColor=#ffffff;fontFamily=Trebuchet MS;fontSize=16;shadow=1;` |
| Data store | `shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=10;whiteSpace=wrap;html=1;fillColor=#dca26c;strokeColor=#b9804b;fontColor=#ffffff;fontFamily=Trebuchet MS;fontSize=16;shadow=1;` |
| External software system | `rounded=0;whiteSpace=wrap;html=1;fillColor=#8e8299;strokeColor=#6f6479;fontColor=#ffffff;fontFamily=Trebuchet MS;fontSize=16;shadow=1;` |
| Note | `rounded=0;whiteSpace=wrap;html=1;fillColor=#fff4c4;strokeColor=#e3c66b;fontColor=#000000;fontFamily=Trebuchet MS;fontSize=14;spacing=10;` |
| Proposed note | Note style plus `dashed=1;dashPattern=6 4;` |
| Relationship | `edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;endSize=8;strokeWidth=1.5;jumpStyle=arc;jumpSize=12;fontFamily=Trebuchet MS;fontSize=14;labelBackgroundColor=light-dark(#E8E8E88D,#2a2a2a8D);` |
| Note link | `endArrow=none;dashed=1;dashPattern=1 4;html=1;strokeColor=#666666;` |

## Sizes

| Element | Width x height |
| --- | --- |
| Container, system, data store | 200 x 130 (grow height for long descriptions) |
| Person | 50 x 72 |
| Note | 220-450 wide; height to fit the text at about 18 px per line |
| Gap between boxes | at least 120, so a relationship label fits between them |

## Why these choices

- **Orange vs purple** separates what the team owns from what it depends on, which is the first question a reader asks. Use grey only when a sibling diagram set already uses grey for externals.
- **Dashed, unfilled boundaries** group without competing with the boxes inside them.
- **Translucent label backgrounds** keep labels readable where they cross a line, in light and dark mode (`light-dark(...)`).
- **`jumpStyle=arc`** shows where lines cross instead of letting them look connected.
- **No `labelWidth`.** It wraps text narrower than the box and makes notes overflow.

## Adapting to an existing set

If sibling diagrams use other colors or fonts, match them and write the mapping in the scope line ("Blue: owned. Grey: external."). Never mix two palettes in one diagram set.
