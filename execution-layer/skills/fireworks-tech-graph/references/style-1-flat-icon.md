# Style 1: Flat Icon (Default)

Inspired by draw.io defaults and Apple documentation style.

## Colors

```
Background:     #ffffff
Box fill:       #ffffff
Box stroke:     #d1d5db  (gray-300)
Box radius:     8px
Text primary:   #111827  (gray-900)
Text secondary: #6b7280  (gray-500)

Semantic arrow colors (pick by flow type):
  Flow A (main):   #2563eb  (blue-600)
  Flow B (alt):    #dc2626  (red-600)
  Flow C (data):   #16a34a  (green-600)
  Flow D (async):  #9333ea  (purple-600)

Icon accent backgrounds:
  Blue tint:   #eff6ff / #dbeafe
  Red tint:    #fef2f2 / #fee2e2
  Green tint:  #f0fdf4 / #dcfce7
  Purple tint: #faf5ff / #ede9fe
  Orange tint: #fff7ed / #fed7aa
  Teal tint:   #f0fdfa / #ccfbf1
```

## Typography

```
font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang SC', 
             'Microsoft YaHei', sans-serif
font-size:   16px labels, 14px sub-labels, 20-22px titles
font-weight: 400 normal, 600 semi-bold for titles
minimum:     13px (never go below this for paper readability)
```

## Box Shapes

```xml
<!-- Standard node box -->
<rect rx="8" ry="8" fill="#ffffff" stroke="#d1d5db" stroke-width="1.5"/>

<!-- Icon accent box (colored background) -->
<rect rx="8" ry="8" fill="#eff6ff" stroke="#bfdbfe" stroke-width="1.5"/>

<!-- Database cylinder (use SVG path) -->
<!-- Terminal box: rx=4, fill=#111827, stroke=#374151 -->
<!-- User/actor: circle or rounded rect with icon -->
```

## Arrows

```xml
<defs>
  <marker id="arrow-blue" markerWidth="12" markerHeight="8"
          refX="11" refY="4" orient="auto">
    <polygon points="0 0, 12 4, 0 8" fill="#2563eb"/>
  </marker>
  <marker id="arrow-red" markerWidth="12" markerHeight="8"
          refX="11" refY="4" orient="auto">
    <polygon points="0 0, 12 4, 0 8" fill="#dc2626"/>
  </marker>
</defs>

<!-- Line -->
<line stroke="#2563eb" stroke-width="2" marker-end="url(#arrow-blue)"/>
<!-- Or path for curved/orthogonal routing -->
<path stroke="#2563eb" stroke-width="2" fill="none" marker-end="url(#arrow-blue)"/>
```

## Legend

Always include a legend in the bottom-left if multiple arrow colors are used:

```xml
<g transform="translate(20, 440)">
  <line x1="0" y1="8" x2="30" y2="8" stroke="#2563eb" stroke-width="2"
        marker-end="url(#arrow-blue)"/>
  <text x="36" y="12" fill="#6b7280" font-size="14">Agent flow</text>
  <line x1="0" y1="28" x2="30" y2="28" stroke="#dc2626" stroke-width="2"
        marker-end="url(#arrow-red)"/>
  <text x="36" y="32" fill="#6b7280" font-size="14">RAG flow</text>
</g>
```

## SVG Template

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 480" 
     width="720" height="480">
  <style>
    /* NO @import — rsvg-convert cannot fetch external URLs */
    text { font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif; }
  </style>
  <defs>
    <!-- arrow markers here -->
    <!-- gradients/filters if needed -->
  </defs>
  <!-- white background -->
  <rect width="720" height="480" fill="#ffffff"/>
  <!-- diagram title (optional) -->
  <!-- nodes -->
  <!-- edges -->
  <!-- legend -->
</svg>
```
