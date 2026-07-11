#!/usr/bin/env python3
"""Generate a draw.io Org Chart from staff profiles.

Recursive tree layout: each manager's direct reports are grouped under them.
Light theme with colored department accents. Auto-centered horizontally.

Reads staff profiles from ~/brain/people/ (or custom path) and resolves
manager relationships from frontmatter fields.

Usage:
    python3 generate-org-chart.py [people_dir] [output_path]

Generic version — reads from brain, no hardcoded company names.
"""

import os, re, sys
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Profile parsing
# ═══════════════════════════════════════════════════════════════════════════════

def parse_profiles(people_dir):
    """Parse all staff profiles. Returns {slug: {...}}."""
    profiles = {}
    for fname in sorted(os.listdir(people_dir)):
        if not fname.endswith(".md") or fname.startswith("_"):
            continue
        slug = fname[:-3]
        with open(os.path.join(people_dir, fname)) as f:
            content = f.read()
        
        name_m = re.search(r"^# (.+)", content, re.MULTILINE)
        role_m = re.search(r"\*\*Role:\*\*\s*(.+)", content)
        dept_m = re.search(r"\*\*Department:\*\*\s*(.+)", content)
        mgr_m = re.search(r"\*\*Manager:\*\*\s*(.+)", content)
        reports_m = re.search(r"\*\*Reports to:\*\*\s*\[\[(.+?)\]\]", content)
        
        name = name_m.group(1).strip() if name_m else slug.replace("-", " ").title()
        role = role_m.group(1).strip() if role_m else "—"
        department = dept_m.group(1).strip() if dept_m else "—"
        manager_raw = mgr_m.group(1).strip() if mgr_m else (reports_m.group(1).strip() if reports_m else None)
        
        is_ceo = "ceo" in role.lower() or "founder" in role.lower()
        if is_ceo:
            manager_raw = None
        
        profiles[slug] = {
            "name": name, "role": role, "department": department,
            "manager_raw": manager_raw, "is_ceo": is_ceo,
        }
    return profiles


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Manager resolution
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_manager(profiles, slug):
    """Match manager_raw string to a profile slug."""
    p = profiles[slug]
    mgr_raw = (p.get("manager_raw") or "").strip().rstrip(".")
    if not mgr_raw or mgr_raw.lower() in ("n/a", "—", "none"):
        return None
    
    # Exact slug match
    mgr_slug = mgr_raw.lower().replace(" ", "-").replace("(", "").replace(")", "")
    if mgr_slug in profiles:
        return mgr_slug
    
    # Substring match against profile names
    for other_slug, other in profiles.items():
        if mgr_raw.lower() in other["name"].lower() or other["name"].lower() in mgr_raw.lower():
            return other_slug
    
    # First-name fallback
    first = mgr_raw.split()[0].lower()
    for other_slug, other in profiles.items():
        if first in other["name"].lower():
            return other_slug
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Tree building
# ═══════════════════════════════════════════════════════════════════════════════

def build_tree(profiles):
    """Build children map. Root = CEO (or first profile)."""
    root = None
    for slug, p in profiles.items():
        if p["is_ceo"]:
            root = slug
            break
    if not root:
        root = next(iter(profiles))
    
    children = {s: [] for s in profiles}
    for slug in profiles:
        mgr = resolve_manager(profiles, slug)
        if mgr and mgr in children:
            children[mgr].append(slug)
    
    # Ensure every node appears exactly once
    seen = set()
    def collect(s):
        if s in seen: return
        seen.add(s)
        for c in children.get(s, []):
            collect(c)
    collect(root)
    # Remove orphans from children map
    for s in list(children):
        if s not in seen:
            del children[s]
    
    return root, children


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Recursive tree layout
# ═══════════════════════════════════════════════════════════════════════════════

NODE_W, NODE_H = 170, 62
H_GAP, V_GAP = 20, 70

def layout_subtree(slug, children, positions, subtree_widths, depth=0):
    """Recursively lay out a subtree. Returns (min_x, max_x) bounds."""
    kids = children.get(slug, [])
    
    if not kids:
        # Leaf node
        x = 0  # will be offset later
        y = depth * (NODE_H + V_GAP)
        positions[slug] = (x, y)
        subtree_widths[slug] = NODE_W
        return 0, NODE_W
    
    # Lay out children first
    kid_positions = []
    for child in kids:
        layout_subtree(child, children, positions, subtree_widths, depth + 1)
        kid_positions.append(child)
    
    # Calculate total children width and center them
    total_kids_width = sum(subtree_widths[c] for c in kid_positions) + (len(kid_positions) - 1) * H_GAP
    start_x = -total_kids_width / 2
    
    current_x = start_x
    for child in kid_positions:
        cx, cy = positions[child]
        offset = current_x - cx + subtree_widths[child] / 2 - NODE_W / 2
        # Shift this child and all its descendants
        _shift_subtree(child, children, positions, offset)
        current_x += subtree_widths[child] + H_GAP
    
    # Position parent centered above children
    parent_x = (start_x + total_kids_width) / 2 - NODE_W / 2
    parent_y = depth * (NODE_H + V_GAP)
    positions[slug] = (parent_x, parent_y)
    subtree_widths[slug] = max(NODE_W, total_kids_width)
    
    return start_x, start_x + max(NODE_W, total_kids_width)


def _shift_subtree(slug, children, positions, dx):
    """Shift a node and all its descendants by dx."""
    x, y = positions[slug]
    positions[slug] = (x + dx, y)
    for child in children.get(slug, []):
        _shift_subtree(child, children, positions, dx)


def layout_all(root, children):
    """Full tree layout. Returns (positions, node_w, node_h, canvas_bounds)."""
    positions = {}
    subtree_widths = {}
    layout_subtree(root, children, positions, subtree_widths)
    
    # Find min/max to normalize all positions to positive coordinates
    min_x = min(x for x, y in positions.values())
    min_y = min(y for x, y in positions.values())
    
    margin = 60
    for slug in list(positions):
        x, y = positions[slug]
        positions[slug] = (x - min_x + margin, y - min_y + margin)
    
    max_x = max(x + NODE_W for x, y in positions.values()) + margin
    max_y = max(y + NODE_H for x, y in positions.values()) + margin
    return positions, NODE_W, NODE_H, (max_x, max_y)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Department colors (light theme accents)
# ═══════════════════════════════════════════════════════════════════════════════

# Default department colors — edit for your organization
DEPT_ACCENT = {
    "Management":               "#d32f2f",  # red
    "Business Development":     "#1976d2",  # blue
    "HR & Operations":          "#c2185b",  # pink
    "Finance & Accounting":     "#7b1fa2",  # purple
    "Marketing":                "#e65100",  # orange
    "Project & Technical Support": "#f57c00",  # amber
}

def get_dept_accent(dept):
    """Get the accent color for a department."""
    # Direct match
    if dept in DEPT_ACCENT:
        return DEPT_ACCENT[dept]
    # Short-name aliases
    ALIASES = {
        "BD": "Business Development",
        "HR": "HR & Operations",
        "Presales": "Business Development",
        "Finance": "Finance & Accounting",
    }
    if dept in ALIASES:
        return DEPT_ACCENT[ALIASES[dept]]
    # Fuzzy: match "Project and Technical Support" → "Project & Technical Support"
    for key in DEPT_ACCENT:
        if dept.replace(" & ", " and ") == key.replace(" & ", " and "):
            return DEPT_ACCENT[key]
    # All Product/Engineering variants → green
    if any(kw in dept for kw in ["Product", "Engineering", "AI Delivery"]):
        return "#2e7d32"
    return "#546e7a"  # default gray


# ═══════════════════════════════════════════════════════════════════════════════
# 6. XML generation
# ═══════════════════════════════════════════════════════════════════════════════

def escape_xml(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_nodes(profiles, positions):
    """Generate draw.io vertex cells — light theme with colored left-accent border."""
    lines = []
    STRIP_W = 6  # width of colored accent strip
    
    for slug, (x, y) in sorted(positions.items(), key=lambda kv: (kv[1][1], kv[1][0])):
        p = profiles[slug]
        accent = get_dept_accent(p["department"])
        
        name = escape_xml(p["name"])
        raw_role = p["role"]
        if len(raw_role) > 40:
            raw_role = raw_role[:38] + "…"
        role = escape_xml(raw_role)
        
        # Clean white box with colored left border effect
        label = f"&lt;b&gt;{name}&lt;/b&gt;&lt;br&gt;&lt;font style=&quot;font-size:9px;color:#666666;&quot;&gt;{role}&lt;/font&gt;"
        
        style = (
            f"rounded=1;whiteSpace=wrap;html=1;"
            f"fillColor=#ffffff;strokeColor=#cccccc;strokeWidth=1;"
            f"fontColor=#333333;fontSize=13;arcSize=8;"
            f"verticalAlign=middle;"
        )
        
        # Draw a thin accent strip as a separate small rectangle on the left
        strip_id = f"{slug}_strip"
        lines.append(f'''        <mxCell id="{strip_id}" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor={accent};strokeColor=none;arcSize=8;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{STRIP_W}" height="{NODE_H}" as="geometry"/>
        </mxCell>''')
        
        lines.append(f'''        <mxCell id="{slug}" value="{label}" style="{style}" vertex="1" parent="1">
          <mxGeometry x="{x + STRIP_W - 3}" y="{y}" width="{NODE_W - STRIP_W + 3}" height="{NODE_H}" as="geometry"/>
        </mxCell>''')
    
    return "\n".join(lines)


def generate_edges(root, children, positions):
    """Generate edge cells — orthogonal arrows from parent to children."""
    lines = []
    eid = 2000
    for parent in children:
        for child in children[parent]:
            if child not in positions or parent not in positions:
                continue
            style = (
                "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
                "jettySize=auto;html=1;strokeColor=#999999;strokeWidth=1;"
                "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                "entryX=0.5;entryY=0;entryDx=0;entryDy=0;"
            )
            lines.append(f'''        <mxCell id="{eid}" value="" style="{style}" edge="1" parent="1" source="{parent}" target="{child}">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>''')
            eid += 1
    return "\n".join(lines)


def generate_legend(profiles, positions, canvas_h):
    """Generate a legend box showing department colors."""
    dept_color_map = {}
    for slug, p in profiles.items():
        dept = p["department"]
        if dept not in dept_color_map:
            dept_color_map[dept] = get_dept_accent(dept)
    
    legend_x = 30
    legend_y = canvas_h + 30
    item_h = 22
    legend_h = len(dept_color_map) * item_h + 40
    legend_w = 280
    
    lines = []
    # Legend container
    lines.append(f'''        <mxCell id="legend_bg" value="&lt;b&gt;Departments&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fafafa;strokeColor=#dddddd;fontColor=#333333;fontSize=11;verticalAlign=top;align=left;spacingLeft=8;spacingTop=4;" vertex="1" parent="1">
          <mxGeometry x="{legend_x}" y="{legend_y}" width="{legend_w}" height="{legend_h}" as="geometry"/>
        </mxCell>''')
    
    for i, (dept, accent) in enumerate(sorted(dept_color_map.items())):
        iy = legend_y + 24 + i * item_h
        short_dept = dept.replace("Product - ", "").replace("Project & ", "")
        if len(short_dept) > 30:
            short_dept = short_dept[:28] + "…"
        short_dept = escape_xml(short_dept)
        
        lines.append(f'''        <mxCell id="leg_{i}_swatch" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor={accent};strokeColor=none;" vertex="1" parent="1">
          <mxGeometry x="{legend_x + 10}" y="{iy}" width="12" height="12" as="geometry"/>
        </mxCell>''')
        lines.append(f'''        <mxCell id="leg_{i}_label" value="{short_dept}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;fontSize=10;fontColor=#555555;" vertex="1" parent="1">
          <mxGeometry x="{legend_x + 28}" y="{iy - 2}" width="240" height="16" as="geometry"/>
        </mxCell>''')
    
    return "\n".join(lines), legend_y + legend_h + 20


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Main
# ═══════════════════════════════════════════════════════════════════════════════

def generate_drawio(people_dir, output_path):
    profiles = parse_profiles(people_dir)
    root, children = build_tree(profiles)
    positions, nw, nh, (canvas_w, canvas_h) = layout_all(root, children)
    
    nodes_xml = generate_nodes(profiles, positions)
    edges_xml = generate_edges(root, children, positions)
    legend_xml, total_h = generate_legend(profiles, positions, canvas_h)
    
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="Hermes Agent" modified="{now}" agent="Hermes Org Chart Generator" version="21.6.2">
  <diagram name="Org Chart" id="org-chart-1">
    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{max(canvas_w, 600)}" pageHeight="{total_h + 10}" math="0" shadow="0" background="#f5f5f5">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
{nodes_xml}
{edges_xml}
{legend_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(xml)
    
    print(f"✓ Org chart: {output_path}")
    print(f"  {len(profiles)} staff, canvas {canvas_w:.0f}x{total_h:.0f}")


if __name__ == "__main__":
    people_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/brain/people")
    output_path = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/brain/HR/Org-Chart.drawio")
    generate_drawio(people_dir, output_path)