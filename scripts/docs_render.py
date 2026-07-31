#!/usr/bin/env python3
"""docs-kit renderer — generates docs/index.html, docs/current.html, docs/changes.html.

Deterministic, Python 3.9 stdlib only, zero LLM. The visual contract is
design/design-system.html ("change-control print"): cool paper + graphite ink,
one redline accent on the page, transit-map colors inside diagrams
(foundation blue, change violet, fast-lane teal), status as dot geometry,
title block instead of a footer.

Read model only: this script never edits markdown. Same input docs -> same
output bytes; only the generated-at stamp moves (override with DOCS_KIT_NOW,
ISO format, for reproducible builds/tests).
"""
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- constants

INK = "#16181d"
INK2 = "#454e5a"
INK3 = "#7d8794"
LINE2 = "#c8d2dc"
MARK = "#c2410c"
L1 = "#1d4ed8"
L2 = "#7c3aed"
FAST = "#0d9488"
TINT_DB = "#e8f0fe"
TINT_ASYNC = "#f1ecfe"

MONO_STACK = "ui-monospace,Menlo,Consolas,monospace"

ID_RE = re.compile(r"\b(ISSUE|PROPOSAL|DECISION|BACKLOG)-([0-9]{3,})\b")
DATE_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*\|")
AMEND_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(DECISION-[0-9]{3,})\s*(.*)$")
KIND_RE = re.compile(r"\[(db|queue|ui|svc)\]")

ID_PAGE = {"ISSUE": ("changes.html", "issues"), "PROPOSAL": ("changes.html", "proposals"),
           "DECISION": ("changes.html", "decisions"), "BACKLOG": ("changes.html", "backlog")}

# Tags are colored by destination: which layer the reference sends you to.
# Derived from ID_PAGE so the hue stays honest if a prefix ever moves sheets.
PAGE_LAYER = {"current.html": "l1", "changes.html": "l2"}

CHAR_W = 6.95  # approx mono advance at 11.5px, used to size SVG nodes


def esc(s):
    return html.escape(str(s), quote=True)


def now():
    env = os.environ.get("DOCS_KIT_NOW", "")
    if env:
        try:
            return datetime.fromisoformat(env)
        except ValueError:
            pass
    return datetime.now()


def git_ref(root):
    try:
        def run(*args):
            return subprocess.run(["git", "-C", str(root)] + list(args),
                                  capture_output=True, text=True, timeout=10)
        b = run("rev-parse", "--abbrev-ref", "HEAD")
        h = run("rev-parse", "--short", "HEAD")
        if b.returncode == 0 and h.returncode == 0:
            return "%s @ %s" % (b.stdout.strip(), h.stdout.strip())
    except Exception:
        pass
    return "no git"


def renderer_version(script_dir):
    try:
        manifest = script_dir.parent / ".claude-plugin" / "plugin.json"
        return json.loads(manifest.read_text(encoding="utf-8")).get("version", "?")
    except Exception:
        return "?"


# ---------------------------------------------------------------- frontmatter

def clean_value(v):
    v = v.strip()
    if v.startswith('"') and v.endswith('"') and len(v) >= 2:
        v = v[1:-1]
    return v.strip()


def parse_frontmatter(text):
    """Minimal YAML subset: scalars, inline [a, b] lists, block '- item' lists."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    fm, body_start, key = {}, None, None
    for i, raw in enumerate(lines[1:], start=1):
        if raw.strip() == "---":
            body_start = i + 1
            break
        if re.match(r"^\s+-\s", raw) and key is not None:
            fm.setdefault(key, [])
            if isinstance(fm[key], list):
                fm[key].append(clean_value(re.sub(r"^\s+-\s?", "", raw)))
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", raw)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fm[key] = [clean_value(x) for x in inner.split(",") if clean_value(x)] if inner else []
        elif val == "":
            fm[key] = []  # may become a block list; empty scalar treated as empty
        else:
            fm[key] = clean_value(val)
    if body_start is None:
        return {}, text
    return fm, "\n".join(lines[body_start:])


def as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip():
        return [v]
    return []


def as_str(v):
    if isinstance(v, str):
        return v
    return ""


# ---------------------------------------------------------------- markdown subset

def link_ids(escaped_text, here):
    """Turn ID-NNN mentions into cross-page tag links. Input is already escaped."""
    def repl(m):
        prefix = m.group(1)
        page, anchor = ID_PAGE[prefix]
        href = ("#" + anchor) if page == here else (page + "#" + anchor)
        layer = PAGE_LAYER.get(page)
        return '<a class="tag id%s" href="%s">%s</a>' % (
            " " + layer if layer else "", href, m.group(0))
    return ID_RE.sub(repl, escaped_text)


def inline_md(s, here):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return link_ids(s, here)


def md_to_html(md, here):
    """Supported subset: h1-h4, paragraphs, ul/ol (2 levels), fenced code,
    tables, blockquotes, hr, inline code/bold/italic/links. Unknown lines
    render as escaped paragraphs — never broken HTML."""
    out, lines, i = [], md.split("\n"), 0
    n = len(lines)

    def flush_para(buf):
        if buf:
            out.append("<p>%s</p>" % " ".join(inline_md(x, here) for x in buf))
            buf.clear()

    para = []
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_para(para)
            i += 1
            code = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>%s</code></pre>" % esc("\n".join(code)))
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            flush_para(para)
            level = min(len(m.group(1)) + 3, 6)  # h1 body heading -> h4 on page
            out.append("<h%d>%s</h%d>" % (level, inline_md(m.group(2), here), level))
            i += 1
            continue
        if stripped in ("---", "***", "___"):
            flush_para(para)
            out.append("<hr>")
            i += 1
            continue
        if stripped.startswith(">"):
            flush_para(para)
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>%s</blockquote>" % " ".join(inline_md(q, here) for q in quote if q.strip()))
            continue
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s|:-]+\|\s*$", lines[i + 1]):
            flush_para(para)
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join("<th>%s</th>" % inline_md(c, here) for c in header)
            trs = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline_md(c, here) for c in r) for r in rows)
            out.append('<table class="data"><tr>%s</tr>%s</table>' % (th, trs))
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            flush_para(para)
            items, tag = [], ("ol" if m.group(2)[0].isdigit() else "ul")
            while i < n:
                mm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not mm:
                    break
                depth = 1 if len(mm.group(1)) >= 2 else 0
                items.append((depth, inline_md(mm.group(3), here)))
                i += 1
            buf, open_sub = [], False
            for depth, txt in items:
                if depth and not open_sub:
                    buf.append("<%s>" % tag)
                    open_sub = True
                if not depth and open_sub:
                    buf.append("</%s></li>" % tag)
                    open_sub = False
                elif not depth and buf:
                    buf.append("</li>")
                buf.append("<li>%s" % txt)
            if open_sub:
                buf.append("</%s></li>" % tag)
            elif buf:
                buf.append("</li>")
            out.append("<%s>%s</%s>" % (tag, "".join(buf), tag))
            continue
        if not stripped:
            flush_para(para)
            i += 1
            continue
        para.append(stripped)
        i += 1
    flush_para(para)
    return "\n".join(out)


# ---------------------------------------------------------------- icons & svg bits

ICONS = {
    "pkg": '<rect x="2.5" y="3" width="11" height="10" rx="1"/><path d="M2.5 6.2h11M8 6.2V13"/>',
    "flag": '<path d="M4.5 13.5V2.5"/><path d="M4.5 3h7.5l-1.8 2.4L12 7.8H4.5"/>',
    "layers": '<rect x="3" y="2.5" width="10" height="4.2" rx="1"/><rect x="3" y="9.3" width="10" height="4.2" rx="1"/>',
    "issue": '<circle cx="8" cy="8" r="5.5"/><path d="M8 5.2v3.4"/><path d="M8 10.9v.1"/>',
    "doc": '<path d="M4.5 2.5H10l2.5 2.5v8.5h-8z"/><path d="M10 2.5V5h2.5"/><path d="M6.5 8.5h3.5M6.5 10.8h3.5"/>',
    "seal": '<circle cx="8" cy="8" r="5.5"/><path d="M5.6 8.1l1.7 1.7 3.1-3.4"/>',
    "list": '<path d="M3.5 4.2h.01M6.5 4.2H13M3.5 8h.01M6.5 8H13M3.5 11.8h.01M6.5 11.8H13"/>',
    "svc": '<rect x="2.8" y="2.8" width="10.4" height="10.4" rx="1.5"/><rect x="6" y="6" width="4" height="4"/>',
    "db": '<ellipse cx="8" cy="4.2" rx="5" ry="1.9"/><path d="M3 4.2v7.6c0 1 2.2 1.9 5 1.9s5-.9 5-1.9V4.2"/>',
    "bolt": '<path d="M9 2.5 4.8 9h2.7L6.3 13.5 10.9 7H8.2z"/>',
    "globe": '<circle cx="8" cy="8" r="5.5"/><path d="M2.5 8h11"/><path d="M8 2.5c1.9 1.6 1.9 9.4 0 11-1.9-1.6-1.9-9.4 0-11z"/>',
    "ui": '<rect x="2.5" y="3" width="11" height="9" rx="1"/><path d="M2.5 5.8h11"/><path d="M4.3 4.4h.01"/>',
}


def symbol_defs(names):
    parts = []
    for name in names:
        parts.append('<symbol id="i-%s" viewBox="0 0 16 16"><g fill="none" stroke="currentColor" '
                     'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">%s</g></symbol>'
                     % (name, ICONS[name]))
    return "".join(parts)


def use_icon(name, x, y, color, size=15):
    return '<use href="#i-%s" x="%g" y="%g" width="%d" height="%d" color="%s"/>' % (name, x, y, size, size, color)


def marker_def(mid, color):
    return ('<marker id="%s" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M1 1.5 8 5 1 8.5" fill="none" stroke="%s" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></marker>' % (mid, color))


def farrow(color=INK, dashed=False):
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    return ('<span class="farrow"><svg width="26" height="10" viewBox="0 0 26 10" fill="none">'
            '<path d="M1 5h19" stroke="%s" stroke-width="1.5" stroke-linecap="round"%s/>'
            '<path d="M17 1.5 21 5l-4 3.5" stroke="%s" stroke-width="1.5" stroke-linecap="round" '
            'stroke-linejoin="round"/></svg></span>' % (color, dash, color))


def svg_text(x, y, text, size=12, weight="700", fill=INK, anchor=None, ls=None):
    extra = ' text-anchor="%s"' % anchor if anchor else ""
    lsattr = ' letter-spacing="%s"' % ls if ls else ""
    return ('<text x="%g" y="%g" font-family="%s" font-size="%g" font-weight="%s" fill="%s"%s%s>%s</text>'
            % (x, y, MONO_STACK, size, weight, fill, extra, lsattr, esc(text)))


# ---------------------------------------------------------------- system map & pipeline

L1_STATIONS = [("Products", "pkg", "current.html#products", 140),
               ("Roadmap", "flag", "current.html#roadmap", 450),
               ("Architecture", "layers", "current.html#architecture", 760)]
L2_STATIONS = [("Issue", "issue", "changes.html#issues", 140),
               ("Proposal", "doc", "changes.html#proposals", 345),
               ("Decision", "seal", "changes.html#decisions", 550),
               ("Backlog", "list", "changes.html#backlog", 760)]


def station(cx, cy, color, icon, name, href=None, label_dy=-24):
    """Metro-style station: filled colored circle, white icon inside, mono label."""
    core = ('<circle cx="%d" cy="%d" r="13" fill="%s"/>' % (cx, cy, color)
            + use_icon(icon, cx - 7, cy - 7, "#ffffff", 14)
            + svg_text(cx, cy + label_dy, name, 12, "700", INK, anchor="middle"))
    if href:
        return '<a href="%s">%s</a>' % (href, core)
    return core


def svg_system_map():
    s = ['<svg viewBox="0 0 880 268" width="100%" role="img" aria-label="docs system map: '
         'blue foundation line, violet change line, teal fast-lane bypass, orange amendment edge">',
         "<defs>", marker_def("map-ah", MARK),
         symbol_defs(["pkg", "flag", "layers", "issue", "doc", "seal", "list"]), "</defs>",
         svg_text(30, 62, "L1", 10, "700", L1, ls="1.5"),
         svg_text(30, 196, "L2", 10, "700", L2, ls="1.5"),
         '<line x1="140" y1="58" x2="760" y2="58" stroke="%s" stroke-width="2.5"/>' % L1,
         '<line x1="140" y1="192" x2="760" y2="192" stroke="%s" stroke-width="2.5"/>' % L2,
         '<path d="M140 205 C 210 246, 690 246, 760 205" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="6 5" class="dashrun"/>' % FAST,
         '<path d="M560 176 C 600 126, 664 96, 742 74" fill="none" stroke="%s" stroke-width="1.7" stroke-dasharray="5 4" class="dashrun" marker-end="url(#map-ah)"/>' % MARK,
         svg_text(650, 116, "AMENDS", 9.5, "700", MARK, ls="1.2"),
         svg_text(450, 262, "FAST LANE · NO ARCHITECTURE CHANGE & REVERT < 1 DAY", 9.5, "400", FAST,
                  anchor="middle", ls="1.2")]
    for name, icon, href, cx in L1_STATIONS:
        s.append(station(cx, 58, L1, icon, name, href))
    for name, icon, href, cx in L2_STATIONS:
        s.append(station(cx, 192, L2, icon, name, href))
    s.append("</svg>")
    return "".join(s)


def svg_pipeline(counts):
    xs = [120, 330, 545, 760]
    names = ["Issue", "Proposal", "Decision", "Backlog"]
    icons = ["issue", "doc", "seal", "list"]
    s = ['<svg viewBox="0 0 880 196" width="100%" role="img" aria-label="change pipeline with '
         'fast-lane bypass">', "<defs>", symbol_defs(["issue", "doc", "seal", "list"]), "</defs>",
         '<line x1="120" y1="78" x2="760" y2="78" stroke="%s" stroke-width="2.5"/>' % L2,
         '<path d="M120 91 C 195 152, 685 152, 760 91" fill="none" stroke="%s" stroke-width="2" stroke-dasharray="6 5" class="dashrun"/>' % FAST]
    for j in range(4):
        s.append(station(xs[j], 78, L2, icons[j], names[j]))
        s.append(svg_text(xs[j], 110, str(counts[j]), 10, "400", INK3, anchor="middle"))
    s.append(svg_text(440, 188, "FAST LANE · NO ARCHITECTURE CHANGE & REVERT < 1 DAY", 9.5, "400",
                      FAST, anchor="middle", ls="1.2"))
    s.append("</svg>")
    return "".join(s)


# ---------------------------------------------------------------- data-flow graph

EDGE_RE = re.compile(r"\s*(~>|->)\s*")


def parse_flows(data_flow):
    """Lines of 'a -> b -> c', 'a ~> b', optional trailing ': label' on 2-node lines.
    Returns (edges, ok) where edges = [(src, dst, async_flag, label)]."""
    edges = []
    for raw in as_list(data_flow):
        for line in str(raw).replace(";", "\n").split("\n"):
            line = line.strip().rstrip(".")
            if not line:
                continue
            label = ""
            if line.count("->") + line.count("~>") == 1 and ":" in line.split(">", 1)[-1]:
                line, label = line.rsplit(":", 1)
                label = label.strip()
            parts = EDGE_RE.split(line)
            # parts: node, op, node, op, node...
            if len(parts) < 3:
                continue
            nodes = [p.strip() for p in parts[0::2]]
            ops = parts[1::2]
            if any(not nd for nd in nodes):
                return [], False
            for k, op in enumerate(ops):
                edges.append((nodes[k], nodes[k + 1], op == "~>", label if len(ops) == 1 else ""))
    return edges, True


def parse_components(entries):
    """'name [kind] — description' (or ': '). Returns ordered dict name -> (kind, desc)."""
    comps = {}
    for raw in as_list(entries):
        text = str(raw).strip()
        if not text:
            continue
        name, desc = text, ""
        for sep in (" — ", " – ", " -- ", ": "):
            if sep in text:
                name, desc = text.split(sep, 1)
                break
        kind = "svc"
        m = KIND_RE.search(name)
        if m:
            kind = m.group(1)
            name = KIND_RE.sub("", name)
        comps[name.strip()] = (kind, desc.strip())
    return comps


NODE_STYLE = {  # kind -> (border, dashed, badge_bg, icon_color, icon, label_fill)
    "svc": (INK, False, "#f4f6f8", INK2, "svc", INK),
    "db": (L1, False, TINT_DB, L1, "db", INK),
    "queue": (L2, False, TINT_ASYNC, L2, "bolt", INK),
    "ui": (LINE2, True, "#f4f6f8", INK3, "ui", INK2),
    "ext": (LINE2, True, "#f4f6f8", INK3, "globe", INK2),
}


def layer_nodes(edges):
    """Longest-path layering; deterministic. Returns None on a cycle."""
    nodes, preds = [], {}
    for a, b, _asyn, _lbl in edges:
        for nd in (a, b):
            if nd not in preds:
                preds[nd] = set()
                nodes.append(nd)
        preds[b].add(a)
    layer, visiting = {}, set()

    def depth(nd):
        if nd in layer:
            return layer[nd]
        if nd in visiting:
            raise ValueError("cycle")
        visiting.add(nd)
        d = 0 if not preds[nd] else 1 + max(depth(p) for p in sorted(preds[nd]))
        visiting.discard(nd)
        layer[nd] = d
        return d

    try:
        for nd in nodes:
            depth(nd)
    except ValueError:
        return None
    return layer


def svg_dag(edges, comps, fig_no="1"):
    layer = layer_nodes(edges)
    if layer is None:
        return None
    cols = {}
    for nd in sorted(layer, key=lambda x: (layer[x], x.lower())):
        cols.setdefault(layer[nd], []).append(nd)
    ncols = max(cols) + 1

    def kind_of(nd):
        if nd in comps:
            return comps[nd][0]
        low = nd.lower()
        return "ui" if low in ("client", "browser", "user", "app") else "ext"

    def node_w(nd):
        return int(48 + CHAR_W * len(nd))

    col_w = {c: max(node_w(nd) for nd in cols[c]) for c in cols}
    GAP, ROW_H, NODE_H, TOP = 46, 60, 34, 16
    x0, col_x = 16, {}
    for c in range(ncols):
        col_x[c] = x0
        x0 += col_w.get(c, 0) + GAP
    width = x0 - GAP + 16
    max_rows = max(len(v) for v in cols.values())
    height = TOP + max_rows * ROW_H + 26

    pos = {}
    for c, members in cols.items():
        pad = (max_rows - len(members)) * ROW_H / 2.0
        for r, nd in enumerate(members):
            pos[nd] = (col_x[c], TOP + pad + r * ROW_H)

    s = ['<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="data flow graph">'
         % (width, height), "<defs>", marker_def("dag-a", INK), marker_def("dag-t", FAST),
         symbol_defs(sorted({NODE_STYLE[kind_of(nd)][4] for nd in layer}))]
    s.append("</defs>")

    labels = []
    for a, b, asyn, lbl in edges:
        ax, ay = pos[a]
        bx, by = pos[b]
        x1 = ax + node_w(a)
        y1 = ay + NODE_H / 2
        x2 = bx - 6
        y2 = by + NODE_H / 2
        color, mid = (FAST, "dag-t") if asyn else (INK, "dag-a")
        dash = ' stroke-dasharray="5 4" class="dashrun"' if asyn else ""
        if abs(y1 - y2) < 1:
            d = "M%g %g H%g" % (x1, y1, x2)
        else:
            cx1 = x1 + (x2 - x1) * 0.45
            cx2 = x1 + (x2 - x1) * 0.55
            d = "M%g %g C %g %g, %g %g, %g %g" % (x1, y1, cx1, y1, cx2, y2, x2, y2)
        s.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s marker-end="url(#%s)"/>'
                 % (d, color, dash, mid))
        if not asyn:
            s.append('<path d="%s" class="pkt"/>' % d)
        text = lbl.strip() if lbl else ""
        if text:
            mx = (x1 + x2) / 2
            my = y1 - 11 if abs(y1 - y2) < 1 else (y1 + y2) / 2 - 10
            chip_w = len(text) * 5.6 + 12
            chip_fill, chip_stroke = ("#e6faf5", "#7fd4c4") if asyn else ("#ffffff", "#e2e8ee")
            labels.append('<rect x="%g" y="%g" width="%g" height="16" rx="2" fill="%s" stroke="%s"/>'
                          % (mx - chip_w / 2, my - 12, chip_w, chip_fill, chip_stroke))
            labels.append(svg_text(mx, my, text, 9, "700" if asyn else "500",
                                   FAST if asyn else INK3, anchor="middle", ls=".6"))
    s.extend(labels)

    for nd in sorted(layer, key=lambda x: (layer[x], x.lower())):
        x, y = pos[nd]
        border, dashed, badge_bg, icon_color, icon, label_fill = NODE_STYLE[kind_of(nd)]
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        s.append('<rect x="%g" y="%g" width="%d" height="%d" rx="2" fill="#ffffff" stroke="%s" stroke-width="1.5"%s/>'
                 % (x, y, node_w(nd), NODE_H, border, dash))
        s.append('<rect x="%g" y="%g" width="22" height="22" rx="4" fill="%s"/>' % (x + 6, y + 6, badge_bg))
        s.append(use_icon(icon, x + 10, y + 10, icon_color, 14))
        s.append(svg_text(x + 36, y + 21.5, nd, 11.5, "650", label_fill))
    s.append("</svg>")
    caption = ('FIG %s · from <code>data_flow</code> — '
               '<span style="color:%s;font-weight:700">▪ service</span> · '
               '<span style="color:%s;font-weight:700">▪ datastore</span> · '
               '<span style="color:%s;font-weight:700">▪ worker/queue</span> · '
               'dashed node = external · <span style="color:%s;font-weight:700">teal dashed edge = async</span>'
               % (fig_no, INK2, L1, L2, FAST))
    return '<div class="plot">%s<p class="figcap">%s</p></div>' % ("".join(s), caption)


def flow_groups(edges):
    """Connected components (undirected), each a separate figure when large."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for a, b, _x, _y in edges:
        union(a, b)
    groups = {}
    for e in edges:
        groups.setdefault(find(e[0]), []).append(e)
    return [groups[k] for k in sorted(groups, key=lambda k: min(x[0].lower() for x in groups[k]))]


# ---------------------------------------------------------------- shared page shell

CSS = r"""
:root {
  --paper: #ffffff; --film: #f4f6f8; --well: #fbfcfd; --grid-faint: #e9eef3;
  --line: #e2e8ee; --line-2: #c8d2dc;
  --ink: #16181d; --ink-2: #454e5a; --ink-3: #7d8794;
  /* four hue families. each: line · deep (text on wash) · edge (borders) · wash (fills) */
  --mark: #c2410c; --mark-2: #ea580c; --mark-deep: #9a3412; --mark-edge: #f3c3a3;
  --mark-wash: #fdf0e7; --mark-film: #fef7f2;
  --l1: #1d4ed8; --l1-deep: #1e3a8a; --l1-edge: #b6c8f2; --l1-wash: #eef3ff;
  --l2: #7c3aed; --l2-deep: #5b21b6; --l2-edge: #cdb8f5; --l2-wash: #f5f0ff;
  --fastc: #0d9488; --fast-deep: #115e59; --fast-edge: #8fd6ca; --fast-wash: #e6faf5;
  --approve: #15803d; --approve-wash: #eaf6ee;
  --reject: #b91c1c; --reject-wash: #fdeeee;
  --hl: rgba(234,88,12,.22); /* highlighter — the redline pen, laid flat */
  --mono: ui-monospace, "SF Mono", Menlo, "Cascadia Mono", Consolas, "Liberation Mono", monospace;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --r: 2px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: var(--paper); color: var(--ink-2); font: 15px/1.65 var(--sans); -webkit-font-smoothing: antialiased; }
:focus-visible { outline: 2px solid var(--mark-2); outline-offset: 2px; }
@keyframes pktflow { to { stroke-dashoffset: -50; } }
@keyframes dashrun { to { stroke-dashoffset: -198; } }
@keyframes pulse-o { 0% { box-shadow: 0 0 0 0 rgba(234,88,12,.4); } 70% { box-shadow: 0 0 0 6px rgba(234,88,12,0); } 100% { box-shadow: 0 0 0 0 rgba(234,88,12,0); } }
@keyframes pulse-g { 0% { box-shadow: 0 0 0 0 rgba(22,163,74,.45); } 70% { box-shadow: 0 0 0 6px rgba(22,163,74,0); } 100% { box-shadow: 0 0 0 0 rgba(22,163,74,0); } }
.pkt { fill: none; stroke: #ffffff; stroke-width: 2.2; stroke-linecap: round; stroke-dasharray: 5 45; animation: pktflow 2.4s linear infinite; }
svg .dashrun { animation: dashrun 16s linear infinite; }
.dot.d-progress { animation: pulse-o 2.2s ease-out infinite; }
.dot.d-live { background: var(--approve); border-color: var(--approve); animation: pulse-g 2.2s ease-out infinite; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } * { transition: none !important; animation: none !important; } .pkt { display: none; } }
a { color: var(--ink); text-decoration: underline; text-decoration-color: var(--mark); text-decoration-thickness: 1.5px; text-underline-offset: 3px; }
a:hover { color: var(--mark); }
.topnav { position: sticky; top: 0; z-index: 10; background: rgba(255,255,255,.94); backdrop-filter: blur(6px); border-bottom: 1px solid var(--line); }
.topnav-in { max-width: 1200px; margin: 0 auto; padding: 0 32px; height: 54px; display: flex; align-items: center; gap: 28px; }
.brand { font: 700 13px var(--mono); letter-spacing: -.01em; color: var(--ink); }
.brand .dim { color: var(--ink-3); font-weight: 500; }
.tabs { display: flex; gap: 22px; align-self: stretch; }
.tabs a { display: flex; align-items: center; padding: 0 2px; margin-bottom: -1px; border-bottom: 2px solid transparent; font: 500 13px var(--sans); color: var(--ink-2); text-decoration: none; }
.tabs a:hover { color: var(--ink); }
.tabs a.active { color: var(--ink); border-bottom-color: var(--mark-2); font-weight: 600; }
.nav-meta { margin-left: auto; font: 11px var(--mono); color: var(--ink-3); }
.page { max-width: 1200px; margin: 0 auto; padding: 0 32px; display: grid; grid-template-columns: 224px minmax(0,1fr); gap: 0 56px; }
.page.solo { display: block; max-width: 944px; }
.sidebar { position: sticky; top: 54px; align-self: start; max-height: calc(100vh - 54px); overflow-y: auto; padding: 34px 0 48px; }
.toc-title { font: 700 10px var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); margin: 0 0 10px 13px; }
.toc { list-style: none; margin: 0 0 20px; padding: 0; }
.toc a { display: block; padding: 4.5px 13px; border-left: 2px solid var(--line); font-size: 13px; color: var(--ink-2); text-decoration: none; }
.toc a:hover { color: var(--ink); border-left-color: var(--line-2); }
.toc .sub a { padding-left: 27px; font-size: 12.5px; }
.content { padding: 42px 0 96px; max-width: 880px; }
.kicker { display: flex; align-items: center; gap: 10px; margin: 0; font: 700 11px var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); }
.kicker::before { content: ""; width: 22px; height: 2px; background: var(--mark-2); }
h1 { font: 750 27px/1.25 var(--mono); letter-spacing: -.035em; color: var(--ink); margin: 10px 0 8px; }
.lede { color: var(--ink-2); font-size: 15.5px; margin: 0 0 8px; max-width: 640px; }
.meta-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 16px 0 0; padding-bottom: 22px; }
.hue-rule { display: flex; gap: 2px; height: 3px; margin: 0; }
.hue-rule i { background: var(--c); border-radius: 1.5px; }
h2 { position: relative; display: flex; align-items: baseline; gap: 12px; font: 700 16.5px/1.3 var(--mono); letter-spacing: -.02em; color: var(--ink); margin: 60px 0 8px; padding-top: 22px; border-top: 1px solid var(--line); scroll-margin-top: 74px; --sec: var(--ink-3); --sec-wash: var(--film); --sec-edge: var(--line-2); }
h2::before { content: ""; position: absolute; top: -1.5px; left: 0; width: 54px; height: 3px; border-radius: 1.5px; background: var(--sec); }
h2.s-l1 { --sec: var(--l1); --sec-wash: var(--l1-wash); --sec-edge: var(--l1-edge); }
h2.s-l2 { --sec: var(--l2); --sec-wash: var(--l2-wash); --sec-edge: var(--l2-edge); }
h2.s-fast { --sec: var(--fastc); --sec-wash: var(--fast-wash); --sec-edge: var(--fast-edge); }
h2.s-mark { --sec: var(--mark); --sec-wash: var(--mark-wash); --sec-edge: var(--mark-edge); }
h2.s-ink::before { background: var(--line-2); }
h2.s-lines::before { background: linear-gradient(90deg, var(--l1) 0 50%, var(--l2) 50% 100%); }
.page.solo h2 { font-size: 15px; border-top: 0; padding-top: 0; margin: 48px 0 14px; }
.page.solo h2::before { top: -11px; }
h2 .idx { flex: none; font: 700 11px var(--mono); color: var(--sec); border: 1px solid var(--sec-edge); border-radius: var(--r); padding: 2px 7px; background: var(--sec-wash); letter-spacing: .04em; }
h2 .src { margin-left: auto; align-self: center; }
.h2sub { font: 400 13px var(--sans); color: var(--ink-3); margin: -2px 0 14px; max-width: 660px; }
.page.solo .h2sub { margin: -8px 0 12px; }
h2 .dim2 { font: 500 10.5px var(--mono); color: var(--ink-3); letter-spacing: .08em; }
h3 { font: 700 12px var(--mono); letter-spacing: .09em; text-transform: uppercase; color: var(--ink); margin: 30px 0 10px; scroll-margin-top: 74px; }
h3 .dim2 { font: 500 10.5px var(--mono); color: var(--ink-3); letter-spacing: .05em; }
h4 { font-size: 13.5px; color: var(--ink); margin: 16px 0 4px; }
p { margin: 8px 0; color: var(--ink-2); max-width: 660px; }
p strong, li strong { color: var(--ink); }
.tag { display: inline-flex; align-items: center; gap: 6px; padding: 1.5px 8px; border: 1px solid var(--line-2); border-radius: var(--r); background: var(--paper); font: 500 11.5px/1.7 var(--mono); color: var(--ink-2); white-space: nowrap; }
.tag.id { color: var(--ink); background: var(--film); font-weight: 650; }
.tag.hard { border-color: var(--ink); color: var(--ink); font-weight: 650; }
.tag.l1 { --h: var(--l1); --hd: var(--l1-deep); --he: var(--l1-edge); --hw: var(--l1-wash); }
.tag.l2 { --h: var(--l2); --hd: var(--l2-deep); --he: var(--l2-edge); --hw: var(--l2-wash); }
.tag.l1, .tag.l2 { color: var(--hd); border-color: var(--he); }
.tag.id.l1, .tag.id.l2 { background: var(--hw); padding-left: 11px; box-shadow: inset 3px 0 0 var(--h); }
.tag.lane-fast { border: 1.5px dashed var(--fastc); background: var(--fast-wash); color: var(--fast-deep); font-weight: 700; letter-spacing: .05em; }
.tag.lane-full { border: 1.5px solid var(--l2); background: var(--l2-wash); color: var(--l2-deep); font-weight: 700; letter-spacing: .05em; }
a.tag { text-decoration: none; }
a.tag:hover { border-color: var(--mark); color: var(--mark); }
a.tag.id.l1:hover, a.tag.id.l2:hover { box-shadow: inset 3px 0 0 var(--mark); }
.hl { background: linear-gradient(100deg, transparent 0, var(--hl) 4%, var(--hl) 96%, transparent 100%); color: var(--ink); font-weight: 500; padding: 1px 3px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
.status { display: inline-flex; align-items: center; gap: 7px; font: 650 11px var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--ink-2); }
.dot { flex: none; width: 10px; height: 10px; border-radius: 50%; border: 1.5px solid var(--ink); background: var(--paper); }
.d-progress { border-color: var(--mark-2); background: linear-gradient(90deg, var(--mark-2) 50%, transparent 50%); }
.d-done { background: var(--ink); }
.d-exploring { border-style: dashed; border-color: var(--ink-3); }
.d-promoted { background: var(--l2); border-color: var(--l2); box-shadow: inset 0 0 0 2.5px var(--paper); }
.d-archived { background: var(--line-2); border-color: var(--line-2); }
.status.live { color: var(--mark); }
.stamp { display: inline-block; padding: 2px 9px; border: 1.5px solid currentColor; border-radius: var(--r); font: 700 10.5px/1.8 var(--mono); letter-spacing: .1em; text-transform: uppercase; }
.st-approved { color: var(--approve); background: var(--approve-wash); }
.st-rejected { color: var(--reject); background: var(--reject-wash); }
.rail { display: flex; align-items: flex-start; margin: 30px 0 4px; }
.rail .st { flex: none; display: flex; flex-direction: column; align-items: center; gap: 9px; min-width: 116px; text-align: center; }
.rail .st .c { width: 16px; height: 16px; border-radius: 50%; background: var(--l1); box-shadow: 0 0 0 4px var(--l1-wash); }
.rail .st a { font: 700 12.5px var(--mono); color: var(--ink); text-decoration: none; }
.rail .st a:hover { color: var(--mark); }
.rail .st small { font: 400 11px var(--sans); color: var(--ink-3); margin-top: -4px; }
.rail .trk { flex: 1; height: 2.5px; margin-top: 7px; background: linear-gradient(90deg, var(--l1), var(--l1-deep)); }
.plot { border: 1px solid var(--line); border-radius: var(--r); padding: 20px; background-color: var(--well); background-image: linear-gradient(var(--grid-faint) 1px, transparent 1px), linear-gradient(90deg, var(--grid-faint) 1px, transparent 1px); background-size: 24px 24px; margin: 14px 0; overflow-x: auto; }
.plot svg { min-width: 560px; }
.plot svg a:hover text { fill: var(--mark); }
.plot svg a:hover circle { stroke: var(--mark); }
.figcap { font: 500 11px var(--mono); color: var(--ink-3); margin-top: 12px; }
.flow { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; margin: 10px 0; }
.farrow { flex: none; display: inline-flex; }
.flow-label { width: 100%; font: 700 10px var(--mono); text-transform: uppercase; letter-spacing: .1em; color: var(--ink-3); margin-top: 6px; }
.board { display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 22px; margin: 18px 0; }
.col-h { display: flex; align-items: center; justify-content: space-between; border-top: 2px solid var(--ink); padding: 8px 0 10px; font: 700 11px var(--mono); letter-spacing: .08em; text-transform: uppercase; color: var(--ink); }
.col-h .n { font: 600 11px var(--mono); color: var(--ink-3); }
.col-h.now { border-top-color: var(--mark-2); }
.col-h.now .n { color: var(--mark); }
.col-h.later { border-top-color: var(--line-2); color: var(--ink-3); }
.item { border: 1px solid var(--line); border-radius: var(--r); background: var(--paper); padding: 9px 11px; margin-bottom: 8px; font-size: 13px; }
.item .im { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.item .it { color: var(--ink); font-weight: 600; margin: 4px 0 0; line-height: 1.45; }
.item.muted .it { color: var(--ink-3); font-weight: 500; }
table.spec { width: 100%; border-collapse: collapse; font-size: 13.5px; }
table.spec th { text-align: left; font: 650 10px var(--mono); text-transform: uppercase; letter-spacing: .09em; color: var(--ink-3); padding: 7px 14px 7px 0; width: 124px; vertical-align: top; border-bottom: 1px solid var(--film); }
table.spec td { padding: 7px 0; color: var(--ink-2); border-bottom: 1px solid var(--film); }
table.spec tr:last-child th, table.spec tr:last-child td { border-bottom: 0; }
table.data { width: 100%; border-collapse: collapse; font-size: 13.5px; }
table.data th { text-align: left; font: 700 10px var(--mono); text-transform: uppercase; letter-spacing: .09em; color: var(--ink-3); padding: 8px 12px 8px 0; border-bottom: 1.5px solid var(--ink); }
table.data td { padding: 9px 12px 9px 0; border-bottom: 1px solid var(--line); color: var(--ink-2); vertical-align: top; }
table.data tr:hover td { background: var(--mark-film); }
table.data td.rev { font-weight: 700; color: var(--mark); }
.mono { font-family: var(--mono); font-size: 12.5px; white-space: nowrap; }
.dim { color: var(--ink-3); }
.devtag { font: 700 10.5px var(--mono); letter-spacing: .09em; text-transform: uppercase; color: var(--mark); white-space: nowrap; }
.card { border: 1px solid var(--line-2); border-radius: var(--r); background: var(--paper); margin: 14px 0; }
.card.l1 { border-top: 2px solid var(--l1); }
.card.l2 { border-top: 2px solid var(--l2); }
.card-h { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 16px; border-bottom: 1px solid var(--line); }
.card-h .t { font: 700 14.5px var(--mono); letter-spacing: -.02em; color: var(--ink); }
.card-b { padding: 12px 16px 14px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.klabel { font: 700 10px var(--mono); text-transform: uppercase; letter-spacing: .1em; color: var(--ink-3); margin: 0 0 4px; }
.scope { list-style: none; margin: 6px 0; padding: 0; font-size: 13.5px; }
.scope li { padding: 3px 0 3px 22px; position: relative; color: var(--ink-2); }
.scope.in li::before { content: "\2713"; position: absolute; left: 2px; color: var(--ink); font-weight: 700; }
.scope.out li::before { content: "\2715"; position: absolute; left: 2px; color: var(--ink-3); font-weight: 700; }
details.more { margin-top: 10px; }
details.more summary { cursor: pointer; font: 600 12px var(--mono); color: var(--mark); list-style: none; text-transform: uppercase; letter-spacing: .06em; }
details.more summary::before { content: "+ "; }
details.more[open] summary::before { content: "\2212 "; }
details.more .md { margin-top: 8px; }
.md { font-size: 14px; max-width: 660px; }
.md pre { background: var(--film); border: 1px solid var(--line); border-radius: var(--r); padding: 12px 14px; overflow-x: auto; }
.md pre code { background: none; padding: 0; }
.md blockquote { margin: 10px 0; padding: 2px 14px; border-left: 3px solid var(--line-2); color: var(--ink-3); }
.md ul, .md ol { padding-left: 22px; }
.note { border: 1px solid var(--line); border-left: 3px solid var(--ink); border-radius: var(--r); background: var(--film); padding: 10px 14px; font-size: 13.5px; color: var(--ink-2); margin: 14px 0; }
.note.dev { border-color: var(--mark-edge); border-left-color: var(--mark-2); background: var(--mark-wash); }
.note .lbl { font: 700 10.5px var(--mono); letter-spacing: .09em; color: var(--ink); text-transform: uppercase; margin-right: 8px; }
.note.dev .lbl { color: var(--mark-deep); }
.constraints { list-style: none; margin: 10px 0; padding: 0; }
.constraints li { border-left: 2px solid var(--ink); padding: 6px 12px; margin: 6px 0; background: var(--film); border-radius: 0 var(--r) var(--r) 0; font-size: 13.5px; color: var(--ink-2); }
.empty { border: 1.5px dashed var(--line-2); border-radius: var(--r); padding: 18px; text-align: center; color: var(--ink-3); font-size: 13px; }
code { font: 12.5px var(--mono); background: var(--film); border-radius: var(--r); padding: 1.5px 5px; color: var(--ink); }
.comps { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; margin: 14px 0; }
.comp { border: 1px solid var(--line); border-radius: var(--r); padding: 10px 13px; background: var(--paper); }
.comp .cn { font: 650 13px var(--mono); color: var(--ink); display: flex; align-items: center; gap: 9px; }
.comp .cr { font-size: 12.5px; color: var(--ink-2); margin-top: 5px; line-height: 1.5; }
.ibadge { flex: none; width: 24px; height: 24px; border-radius: 4px; display: inline-flex; align-items: center; justify-content: center; }
.hubgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
a.hub { display: block; border: 1px solid var(--line-2); border-radius: var(--r); padding: 16px 18px; text-decoration: none; color: inherit; background: var(--paper); }
a.hub:hover { border-color: var(--ink); }
a.hub:hover .ht { color: var(--mark); }
.hub .hk { font: 700 10px var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); }
.hub .hk.k1 { color: var(--l1); }
.hub .hk.k2 { color: var(--l2); }
.hub .ht { font: 700 15px var(--mono); letter-spacing: -.02em; color: var(--ink); margin: 7px 0 5px; }
.hub .hd { font-size: 13px; color: var(--ink-2); line-height: 1.55; min-height: 40px; }
.hub .hs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.reflist { border: 1px solid var(--line-2); border-radius: var(--r); overflow: hidden; }
.refrow { display: flex; align-items: baseline; gap: 14px; padding: 10px 16px; border-bottom: 1px solid var(--line); font-size: 13.5px; }
.refrow:last-child { border-bottom: 0; }
.refrow .rf { flex: none; width: 172px; font: 650 12.5px var(--mono); }
.refrow .rf a { text-decoration: none; }
.refrow .rf a:hover { color: var(--mark); }
.refrow .rd { color: var(--ink-2); }
.refrow .rn { margin-left: auto; font: 500 11px var(--mono); color: var(--ink-3); white-space: nowrap; }
.refrow.is-empty .rd, .refrow.is-empty .rf a { color: var(--ink-3); }
.tblock { display: flex; flex-wrap: wrap; gap: 1px; background: var(--line-2); border: 1.5px solid var(--ink); border-radius: var(--r); overflow: hidden; margin-top: 72px; }
.tb { flex: 1 1 150px; background: var(--paper); padding: 9px 13px; }
.tb .tl { font: 650 9.5px var(--mono); letter-spacing: .12em; text-transform: uppercase; color: var(--ink-3); }
.tb .tv { font: 650 12px var(--mono); color: var(--ink); margin-top: 3px; }
@media (max-width: 960px) { .page { grid-template-columns: 1fr; } .sidebar { position: static; max-height: none; padding-bottom: 0; } .grid2 { grid-template-columns: 1fr; } .rail .st { min-width: 84px; } }
@media (max-width: 760px) { .hubgrid { grid-template-columns: 1fr; } .refrow .rf { width: 132px; } }
"""

TABS = [("Overview", "index.html"), ("Foundation", "current.html"), ("Changes", "changes.html")]


def page_html(ctx, title, active, sidebar, content, sheet_name):
    tabs = "".join('<a href="%s"%s>%s</a>' % (href, ' class="active"' if name == active else "", name)
                   for name, href in TABS)
    side = ('<aside class="sidebar"><p class="toc-title">On this sheet</p><ul class="toc">%s</ul></aside>'
            % sidebar) if sidebar else ""
    shell_cls = "page" if sidebar else "page solo"
    main_tag = "main" if sidebar else 'main class="content" style="margin:0 auto"'
    tblock = "".join('<div class="tb"><div class="tl">%s</div><div class="tv">%s</div></div>' % (esc(k), esc(v))
                     for k, v in [("Project", ctx["project"]), ("Sheet", sheet_name),
                                  ("Rev", ctx["ref"]), ("Generated", ctx["stamp"]),
                                  ("By", "docs-kit render v%s" % ctx["version"])])
    return ("<!doctype html>\n<!-- GENERATED by docs-kit docs-render — do not edit; "
            "regenerate with /docs-kit:docs-render -->\n"
            '<html lang="vi"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>%s</title><style>%s</style></head><body>"
            '<nav class="topnav"><div class="topnav-in">'
            '<span class="brand">%s <span class="dim">/ docs</span></span>'
            '<div class="tabs">%s</div><span class="nav-meta">generated %s</span></div></nav>'
            '<div class="%s">%s<%s><div class="content">%s'
            '<div class="tblock">%s</div></div></main></div></body></html>'
            % (esc(title), CSS, esc(ctx["project"]), tabs, esc(ctx["date"]), shell_cls, side,
               main_tag, content, tblock))


def tag(text, cls="tag", href=None):
    if href:
        return '<a class="%s" href="%s">%s</a>' % (cls, href, esc(text))
    return '<span class="%s">%s</span>' % (cls, esc(text))


def id_tag(ident, here, cls="tag id"):
    m = ID_RE.search(ident or "")
    if not m:
        return tag(ident or "?", "tag")
    page, anchor = ID_PAGE[m.group(1)]
    href = ("#" + anchor) if page == here else (page + "#" + anchor)
    layer = PAGE_LAYER.get(page)
    return tag(m.group(0), "%s %s" % (cls, layer) if layer else cls, href)


def status_dot(kind):
    return '<span class="dot d-%s"></span>' % kind if kind else '<span class="dot"></span>'


def status_badge(label, dot, live=False):
    return ('<span class="status%s">%s%s</span>'
            % (" live" if live else "", status_dot(dot) if dot != "open" else '<span class="dot"></span>', esc(label)))


def lane_tag(lane):
    if lane == "fast":
        return '<span class="tag lane-fast">fast</span>'
    if lane == "full":
        return '<span class="tag lane-full">full</span>'
    return ""


def slugify(text, seen=None):
    """Anchor slug that survives Vietnamese file names.

    A plain [^a-z0-9] filter drops every diacritic-bearing letter outright, so
    'phân-quyền' and 'phần-quyền' both collapse to 'ph-n-quy-n' — two products,
    one HTML id, and a sidebar link that jumps to the wrong card. Decompose to
    NFD and drop the combining marks instead, so the base letters survive.
    'đ' has no decomposition, so it is mapped by hand.

    Pass `seen` to guarantee uniqueness within a page; names that still collide
    after folding get a numeric suffix rather than a duplicate id.
    """
    s = unicodedata.normalize("NFD", str(text)).lower().replace("đ", "d")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"
    if seen is None:
        return s
    base, n = s, 2
    while s in seen:
        s, n = "%s-%d" % (base, n), n + 1
    seen.add(s)
    return s


# Roadmap column labels the renderer recognises, and the temporal weight each
# carries. Headings are labels and stay English (see STANDARD §11), but a
# Vietnamese heading is a likely slip, and the failure is silent — the column
# simply loses its colour — so the obvious equivalents are accepted too.
#   (kind, matched at the start of the heading, matched anywhere in it)
# "now" must be a prefix — as a substring it would fire on "Known issues".
# The not-doing family is the opposite: the shipped template writes
# "Explicitly not doing", so the phrase is not at the start. It is checked
# first, because it is the stronger signal wherever it appears.
ROADMAP_KINDS = [
    ("not-doing", (), ("not doing", "won't do", "không làm", "khong lam")),
    ("now", ("now", "bây giờ", "đang làm", "dang lam"), ()),
    ("next", ("next", "tiếp theo", "tiep theo"), ()),
    ("later", ("later", "để sau", "de sau", "sau này"), ()),
]


def roadmap_kind(heading):
    """Map a roadmap '##' heading to now / next / later / not-doing, or None."""
    h = (heading or "").strip().lower()
    for kind, prefixes, anywhere in ROADMAP_KINDS:
        if any(h.startswith(p) for p in prefixes) or any(p in h for p in anywhere):
            return kind
    return None


def section_sub(text):
    """One Vietnamese gloss line under an English section heading."""
    return '<p class="h2sub">%s</p>' % esc(text)


def hue_rule(segments):
    """The 3px strip under the meta row: the hue budget this sheet actually spends,
    drawn to scale from real counts. segments = [(css var, weight, label)];
    empty segments drop out so the strip never lies about a zero."""
    live = [(c, w, lbl) for c, w, lbl in segments if w > 0]
    if not live:
        # nothing documented yet: no hue has been spent, so the strip is graphite.
        # It still terminates the page header, which is all it does on an empty sheet.
        return '<div class="hue-rule" aria-hidden="true"><i style="--c:var(--line);flex:1"></i></div>'
    # "noun: n" rather than "n noun" — reads correctly at any count, no plural agreement
    return ('<div class="hue-rule" role="img" aria-label="%s">%s</div>'
            % (esc(" · ".join("%s: %d" % (lbl, w) for _c, w, lbl in live)),
               "".join('<i style="--c:var(--%s);flex:%d"></i>' % (c, w) for c, w, _l in live)))


def empty_state(msg):
    return '<div class="empty">%s</div>' % msg


# ---------------------------------------------------------------- doc loading

def md_files(folder):
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.suffix == ".md" and p.name != "README.md" and not p.name.startswith("."))


def load_docs(docs):
    def load(folder):
        out = []
        for p in md_files(docs / folder):
            fm, body = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            out.append({"path": p, "fm": fm, "body": body})
        return out

    return {
        "products": load("01_products"),
        "issues": load("20_issues"),
        "proposals": load("21_proposals"),
        "decisions": load("22_decisions"),
        "backlog": load("23_backlog"),
    }


def doc_title(doc):
    for line in doc["body"].split("\n"):
        m = re.match(r"^#\s+(.*)$", line.strip())
        if m:
            t = m.group(1).strip()
            t = re.sub(r"^(ISSUE|PROPOSAL|DECISION|BACKLOG)-[0-9]{3,}\s*[—:\-]\s*", "", t)
            return t
    return doc["path"].stem


def fm_str(doc, key, default=""):
    v = doc["fm"].get(key, default)
    return as_str(v) if not isinstance(v, list) else (v[0] if v else default)


def trim(s, n=110):
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# ---------------------------------------------------------------- page: current

def build_current(ctx, docs, data):
    here = "current.html"
    products = data["products"]
    backlog_by_id = {fm_str(d, "id"): d for d in data["backlog"]}
    # one slug per product, computed once: the card id and the sidebar link
    # must agree, and dedupe only works if both read the same answer
    seen_slugs = set()
    slugs = {d["path"]: slugify(d["path"].stem, seen_slugs) for d in products}

    # roadmap sections
    roadmap_file = docs / "00_roadmap" / "roadmap.md"
    sections = []
    if roadmap_file.is_file():
        _fm, body = parse_frontmatter(roadmap_file.read_text(encoding="utf-8", errors="replace"))
        current_h, bullets = None, []
        for line in body.split("\n"):
            m = re.match(r"^##\s+(.*)$", line.strip())
            if m:
                if current_h is not None:
                    sections.append((current_h, bullets))
                current_h, bullets = m.group(1).strip(), []
            elif re.match(r"^\s*-\s+", line) and current_h is not None:
                bullets.append(re.sub(r"^\s*-\s+", "", line).strip())
        if current_h is not None:
            sections.append((current_h, bullets))

    # architecture
    arch_file = docs / "02_architecture" / "architecture.md"
    arch_fm, arch_body = ({}, "")
    if arch_file.is_file():
        arch_fm, arch_body = parse_frontmatter(arch_file.read_text(encoding="utf-8", errors="replace"))
    comps = parse_components(arch_fm.get("components", []))
    edges, flow_ok = parse_flows(arch_fm.get("data_flow", []))
    amends = []
    for entry in as_list(arch_fm.get("amended_by", [])):
        m = AMEND_RE.match(str(entry).strip())
        if m:
            amends.append({"date": m.group(1), "decision": m.group(2), "summary": m.group(3).strip()})
        elif str(entry).strip():
            amends.append({"date": "", "decision": str(entry).strip(), "summary": ""})
    rev_letter = {a["decision"]: chr(65 + i) for i, a in enumerate(amends)}
    latest_rev = chr(64 + len(amends)) if amends else None

    # --- header + rail
    now_count = sum(len(b) for h, b in sections if roadmap_kind(h) == "now")
    next_count = sum(len(b) for h, b in sections if roadmap_kind(h) == "next")
    meta = [tag(ctx["ref"]), tag("generated " + ctx["stamp"]),
            tag("%d product%s" % (len(products), "" if len(products) == 1 else "s")),
            tag("%d component%s" % (len(comps), "" if len(comps) == 1 else "s"))]
    if latest_rev:
        meta.append(tag("REV " + latest_rev, "tag id l1"))
    arch_sub = "%d components" % len(comps) + (" · rev %s" % latest_rev if latest_rev else "")
    rail = ('<div class="rail">'
            '<div class="st"><span class="c"></span><a href="#products">Products</a><small>%s</small></div>'
            '<div class="trk"></div>'
            '<div class="st"><span class="c"></span><a href="#roadmap">Roadmap</a><small>%s</small></div>'
            '<div class="trk"></div>'
            '<div class="st"><span class="c"></span><a href="#architecture">Architecture</a><small>%s</small></div>'
            "</div>"
            % ("%d documented" % len(products),
               "%d now · %d next" % (now_count, next_count), arch_sub))

    parts = ['<p class="kicker">Layer 1 · Foundation — state</p>',
             "<h1>Foundation — current state</h1>",
             '<p class="lede">Products, roadmap và architecture đúng như đang được ghi trong '
             "<code>docs/</code>. Trang này sinh tự động — markdown mới là nguồn sự thật.</p>",
             '<div class="meta-row">%s</div>' % "".join(meta),
             # a Layer 1 sheet spends one hue — plus redline for every amendment it carries
             hue_rule([("l1", len(products) + len(comps), "foundation entries"),
                       ("mark-2", len(amends), "amendments")]),
             rail]

    # --- products
    parts.append('<h2 id="products" class="s-l1"><span class="idx">§1</span>Products '
                 '<span class="src tag">docs/01_products/</span></h2>')
    parts.append(section_sub("Sản phẩm — ai dùng, giải quyết vấn đề gì, phạm vi tới đâu"))
    if not products:
        parts.append(empty_state("NO PRODUCTS — thêm một file vào <code>docs/01_products/</code> "
                                 "rồi chạy lại <code>/docs-kit:docs-render</code>"))
    for d in products:
        slug = slugs[d["path"]]
        name = fm_str(d, "name") or doc_title(d)
        rows = "".join("<tr><th>%s</th><td>%s</td></tr>" % (k, inline_md(fm_str(d, k), here))
                       for k in ("users", "problem") if fm_str(d, k))
        scope_in = "".join("<li>%s</li>" % inline_md(x, here) for x in as_list(d["fm"].get("scope_in")))
        scope_out = "".join("<li>%s</li>" % inline_md(x, here) for x in as_list(d["fm"].get("scope_out")))
        metric = fm_str(d, "success_metric")
        metric_tag = ('<span class="tag hard" style="margin-left:auto">TARGET · %s</span>'
                      % esc(trim(metric, 48))) if metric else ""
        body_html = md_to_html(d["body"], here)
        details = ('<details class="more"><summary>Full document</summary><div class="md">%s</div></details>'
                   % body_html) if body_html.strip() else ""
        parts.append(
            '<div class="card l1" id="p-%s"><div class="card-h"><span class="t">%s</span>%s%s</div>'
            '<div class="card-b"><table class="spec">%s</table>'
            '<div class="grid2" style="margin-top:12px">'
            '<div><p class="klabel">In scope</p><ul class="scope in">%s</ul></div>'
            '<div><p class="klabel">Out of scope</p><ul class="scope out">%s</ul></div></div>%s</div></div>'
            % (slug, esc(name), tag(d["path"].name), metric_tag, rows,
               scope_in or "<li>—</li>", scope_out or "<li>—</li>", details))

    # --- roadmap
    parts.append('<h2 id="roadmap" class="s-l1"><span class="idx">§2</span>Roadmap '
                 '<span class="src tag">docs/00_roadmap/roadmap.md</span></h2>')
    parts.append(section_sub("Kế hoạch theo giai đoạn — đang làm, sắp làm, để sau"))
    if not sections:
        parts.append(empty_state("NO ROADMAP — điền vào <code>docs/00_roadmap/roadmap.md</code>"))
    else:
        parts.append("<p>Các cột phản chiếu đúng những mục <code>##</code> trong file roadmap; dòng nào "
                     "dẫn một id <code>BACKLOG</code> sẽ mang luôn status dot đang sống của item đó.</p>")
        cols = []
        for heading, bullets in sections:
            kind = roadmap_kind(heading)
            muted = kind == "not-doing"
            items = []
            for b in bullets:
                m = re.search(r"\bBACKLOG-[0-9]{3,}\b", b)
                dot, badge, refs = "", "", ""
                text = b
                if m and m.group(0) in backlog_by_id:
                    st = fm_str(backlog_by_id[m.group(0)], "status")
                    dot_kind = {"open": "open", "in-progress": "progress", "done": "done"}.get(st, "open")
                    dot = status_dot(dot_kind if dot_kind != "open" else "open")
                    dot = '<span class="dot%s"></span>' % ("" if dot_kind == "open" else " d-" + dot_kind)
                    badge = id_tag(m.group(0), here)
                    text = ID_RE.sub("", b).strip(" —:-·")
                other_ids = [x.group(0) for x in ID_RE.finditer(b) if not x.group(0).startswith("BACKLOG")]
                if other_ids:
                    refs = "".join(id_tag(x, here, "tag") for x in other_ids)
                    text = ID_RE.sub("", text if m else b).strip(" ()—:-·")
                head = ('<div class="im">%s%s</div>' % (dot, badge)) if (dot or badge) else ""
                tail = ('<div class="im" style="margin-top:5px">%s</div>' % refs) if refs else ""
                items.append('<div class="item%s">%s<div class="it"%s>%s</div>%s</div>'
                             % (" muted" if muted else "", head,
                                ' style="margin-top:0"' if not head else "",
                                inline_md(text, here) if not (dot or badge or refs) else esc(text), tail))
            col_cls = ("col-h now" if kind == "now"
                       else "col-h later" if kind in ("later", "not-doing") else "col-h")
            cols.append('<div><div class="%s">%s <span class="n">%d</span></div>%s</div>'
                        % (col_cls, esc(heading), len(bullets),
                           "".join(items) or empty_state("empty")))
        parts.append('<div class="board">%s</div>' % "".join(cols))

    # --- architecture
    parts.append('<h2 id="architecture" class="s-l1"><span class="idx">§3</span>Architecture '
                 '<span class="src tag">docs/02_architecture/architecture.md</span></h2>')
    parts.append(section_sub("Kiến trúc hệ thống — chỉ sửa được qua Decision"))
    parts.append('<div class="note"><span class="lbl">Note</span>Chỉ được sửa <b>qua</b> '
                 'Decision workflow — mọi revision trong <a href="#a-rev">revision block</a> '
                 "đều phải dẫn Decision của nó. Hook của docs-kit sẽ cảnh báo nếu có ai sửa thẳng.</div>")

    parts.append('<h3 id="a-components">Components</h3>')
    if comps:
        cards = []
        for name, (kind, desc) in comps.items():
            _b, _d, badge_bg, icon_color, icon, _lf = NODE_STYLE.get(kind, NODE_STYLE["svc"])
            icon_svg = ('<span class="ibadge" style="background:%s"><svg width="14" height="14" '
                        'viewBox="0 0 16 16" style="color:%s"><g fill="none" stroke="currentColor" '
                        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">%s</g></svg></span>'
                        % (badge_bg, icon_color, ICONS[icon]))
            cards.append('<div class="comp"><div class="cn">%s%s</div><div class="cr">%s</div></div>'
                         % (icon_svg, esc(name), inline_md(desc, here) if desc else "&nbsp;"))
        parts.append('<div class="comps">%s</div>' % "".join(cards))
    else:
        parts.append(empty_state("NO COMPONENTS — điền danh sách <code>components</code> trong "
                                 "<code>docs/02_architecture/architecture.md</code>"))

    parts.append('<h3 id="a-flow">Data flow</h3>')
    if edges and flow_ok:
        groups = flow_groups(edges) if len({n for e in edges for n in e[:2]}) > 12 else [edges]
        for gi, group in enumerate(groups):
            fig_no = "1" if len(groups) == 1 else "1%s" % chr(97 + gi)
            dag = svg_dag(group, comps, fig_no)
            if dag:
                parts.append(dag)
            else:
                parts.append('<div class="note"><span class="lbl">Note</span>'
                             "<code>data_flow</code> có chu trình — hiển thị dạng text bên dưới.</div>")
                parts.append('<div class="md">%s</div>' % md_to_html("\n".join(
                    "- `%s` %s `%s`" % (a, "⇝" if x else "→", b) for a, b, x, _l in group), here))
    elif as_list(arch_fm.get("data_flow")):
        parts.append('<div class="note"><span class="lbl">Note</span>Không đọc được '
                     "<code>data_flow</code> — hiển thị nguyên văn. Cú pháp cạnh: "
                     "<code>a -&gt; b</code>, <code>a ~&gt; b</code> (async), <code>a -&gt; b : label</code>.</div>")
        parts.append("<pre><code>%s</code></pre>" % esc("\n".join(str(x) for x in as_list(arch_fm.get("data_flow")))))
    else:
        parts.append(empty_state("NO DATA FLOW — thêm cạnh vào <code>data_flow</code> "
                                 "(<code>a -&gt; b</code>, <code>a ~&gt; b</code> async, "
                                 "<code>a -&gt; b : label</code>)"))

    parts.append('<h3 id="a-stack">Tech stack</h3>')
    stack = as_list(arch_fm.get("tech_stack"))
    if stack:
        parts.append('<div class="meta-row" style="padding-bottom:0;margin-top:8px">%s</div>'
                     % "".join(tag(x) for x in stack))
    else:
        parts.append(empty_state("NO TECH STACK — chưa liệt kê gì"))

    parts.append('<h3 id="a-constraints">Constraints</h3>')
    constraints = as_list(arch_fm.get("constraints"))
    if constraints:
        parts.append('<ul class="constraints">%s</ul>'
                     % "".join("<li>%s</li>" % inline_md(c, here) for c in constraints))
    else:
        parts.append(empty_state("NO CONSTRAINTS — chưa ghi ràng buộc nào"))

    parts.append('<h3 id="a-rev">Revision block <span class="dim2">· FROM AMENDED_BY</span></h3>')
    if amends:
        rows = []
        for a in reversed(amends):
            rows.append('<tr><td class="mono rev">%s</td><td class="mono">%s</td>'
                        "<td>%s</td><td>%s</td></tr>"
                        % (rev_letter[a["decision"]], esc(a["date"] or "—"),
                           id_tag(a["decision"], here), inline_md(a["summary"] or "—", here)))
        parts.append('<table class="data"><tr><th style="width:56px">rev</th>'
                     '<th style="width:110px">date</th><th style="width:150px">decision</th>'
                     "<th>description</th></tr>%s</table>" % "".join(rows))
    else:
        parts.append(empty_state("NO REVISIONS — <code>amended_by</code> đang rỗng; "
                                 "architecture chưa bị sửa lần nào kể từ lúc scaffold"))

    body_html = md_to_html(arch_body, here)
    if body_html.strip():
        parts.append('<details class="more" style="margin-top:20px"><summary>Full architecture document'
                     "</summary><div class=\"md\">%s</div></details>" % body_html)

    sidebar = ['<li><a href="#products">§1 Products</a></li>']
    for d in products:
        slug = slugs[d["path"]]
        sidebar.append('<li class="sub"><a href="#p-%s">%s</a></li>'
                       % (slug, esc(trim(fm_str(d, "name") or doc_title(d), 26))))
    sidebar.append('<li><a href="#roadmap">§2 Roadmap</a></li>')
    sidebar.append('<li><a href="#architecture">§3 Architecture</a></li>')
    for anchor, label in [("a-components", "Components"), ("a-flow", "Data flow"),
                          ("a-stack", "Tech stack"), ("a-constraints", "Constraints"),
                          ("a-rev", "Revision block")]:
        sidebar.append('<li class="sub"><a href="#%s">%s</a></li>' % (anchor, label))

    return page_html(ctx, "%s · Foundation — current state" % ctx["project"],
                     "Foundation", "".join(sidebar), "".join(parts), "FOUNDATION — CURRENT"), latest_rev


# ---------------------------------------------------------------- page: changes

ISSUE_DOTS = {"exploring": "exploring", "open": "open", "promoted": "promoted", "archived": "archived"}
BACKLOG_DOTS = {"open": "open", "in-progress": "progress", "done": "done"}


def dot_html(kind):
    return '<span class="dot%s"></span>' % ("" if kind == "open" else " d-" + kind)


def build_changes(ctx, docs, data, audit):
    here = "changes.html"
    issues, proposals, decisions, backlog = (data["issues"], data["proposals"],
                                             data["decisions"], data["backlog"])
    by_id = {}
    for group in (issues, proposals, decisions, backlog):
        for d in group:
            ident = fm_str(d, "id")
            if ident:
                by_id[ident] = d
    proposal_of_issue = {fm_str(p, "issue_ref"): p for p in proposals if fm_str(p, "issue_ref")}
    decision_of_proposal = {fm_str(d, "proposal_ref"): d for d in decisions if fm_str(d, "proposal_ref")}
    backlog_of_source = {}
    for b in backlog:
        backlog_of_source.setdefault(fm_str(b, "source_ref"), []).append(b)

    in_flight = sum(1 for b in backlog if fm_str(b, "status") == "in-progress")
    meta = [tag("%d issues" % len(issues)), tag("%d proposals" % len(proposals)),
            tag("%d decisions" % len(decisions)), tag("%d backlog items" % len(backlog))]
    if in_flight:
        meta.append('<span class="status live">%s%d in flight</span>' % (dot_html("progress"), in_flight))

    parts = ['<p class="kicker">Layer 2 · Change — process</p>',
             "<h1>Change pipeline</h1>",
             '<p class="lede">Mọi thay đổi từ Issue đầu tiên tới Backlog item hoàn tất, kèm dấu vết '
             "truy nguyên. Fast lane là đường tắt; thứ gì đụng tới Architecture đều phải đi full lane.</p>",
             '<div class="meta-row">%s</div>' % "".join(meta),
             # the change sheet's real lane split: full line vs bypass, plus recorded deviations
             hue_rule([("l2", len(proposals), "full lane"),
                       ("fastc", sum(1 for b in backlog
                                     if fm_str(b, "source_ref").startswith("ISSUE-")), "fast lane"),
                       ("mark-2", audit["deviations_30d"], "deviations / 30d")]),
             '<div class="plot" style="margin:26px 0 14px">%s'
             '<p class="figcap">FIG 1 · <span style="color:%s;font-weight:700">change line</span> '
             "— số ở mỗi ga là số thật; <span style=\"color:%s;font-weight:700\">tuyến teal</span> "
             "bỏ qua Proposal và Decision</p></div>"
             % (svg_pipeline([len(issues), len(proposals), len(decisions), len(backlog)]), L2, FAST)]

    # --- issues board
    parts.append('<h2 id="issues" class="s-l2"><span class="idx">§1</span>Issues '
                 '<span class="src tag">docs/20_issues/</span></h2>')
    parts.append(section_sub("Vấn đề được nêu — điểm khởi đầu bắt buộc của mọi thay đổi"))
    if not issues:
        parts.append(empty_state("NO ISSUES — mọi thay đổi đều bắt đầu bằng một file trong <code>docs/20_issues/</code>"))
    else:
        cols = []
        for st in ("exploring", "open", "promoted", "archived"):
            members = [d for d in issues if fm_str(d, "status") == st]
            if not members:
                continue
            items = []
            for d in sorted(members, key=lambda x: fm_str(x, "id"), reverse=True):
                ident = fm_str(d, "id")
                nxt = ""
                if st == "promoted":
                    p = proposal_of_issue.get(ident)
                    if p is not None:
                        nxt = "→ " + fm_str(p, "id")
                    else:
                        bs = backlog_of_source.get(ident, [])
                        if bs:
                            nxt = "→ " + fm_str(bs[0], "id")
                muted = " muted" if st == "archived" else ""
                tail = ('<div class="im" style="margin-top:5px">%s</div>' % tag(nxt)) if nxt else ""
                items.append('<div class="item%s"><div class="im">%s%s%s</div>'
                             '<div class="it">%s</div>%s</div>'
                             % (muted, dot_html(ISSUE_DOTS[st]),
                                id_tag(ident, here, "tag id" if st != "archived" else "tag"),
                                lane_tag(fm_str(d, "lane")),
                                esc(trim(fm_str(d, "description") or doc_title(d), 90)), tail))
            col_cls = ("col-h now" if st == "open"
                       else "col-h later" if st == "archived" else "col-h")
            cols.append('<div><div class="%s">%s <span class="n">%d</span></div>%s</div>'
                        % (col_cls, st.replace("-", " "), len(members), "".join(items)))
        parts.append('<div class="board">%s</div>' % "".join(cols))

    # --- proposals
    parts.append('<h2 id="proposals" class="s-l2"><span class="idx">§2</span>Proposals '
                 '<span class="src tag">docs/21_proposals/</span></h2>')
    parts.append(section_sub("Phương án đề xuất — chỉ Issue đi full lane mới cần"))
    if not proposals:
        parts.append(empty_state("NO PROPOSALS — Issue đi full lane sẽ có một file trong <code>docs/21_proposals/</code>"))
    else:
        rows = []
        for p in sorted(proposals, key=lambda x: fm_str(x, "id"), reverse=True):
            ident = fm_str(p, "id")
            dec = decision_of_proposal.get(ident)
            dec_cell = "<span class=\"dim\">pending</span>"
            if dec is not None:
                outcome = fm_str(dec, "outcome")
                stamp = ('<span class="stamp st-%s">%s</span>' % (esc(outcome), esc(outcome))
                         if outcome in ("approved", "rejected") else esc(outcome))
                dec_cell = "%s %s" % (id_tag(fm_str(dec, "id"), here), stamp)
            rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                        % (id_tag(ident, here), id_tag(fm_str(p, "issue_ref"), here, "tag"),
                           esc(trim(fm_str(p, "proposed") or doc_title(p))), dec_cell))
        parts.append('<table class="data"><tr><th style="width:140px">id</th>'
                     '<th style="width:110px">from</th><th>proposed</th>'
                     '<th style="width:210px">decision</th></tr>%s</table>' % "".join(rows))

    # --- decisions
    parts.append('<h2 id="decisions" class="s-l2"><span class="idx">§3</span>Decisions '
                 '<span class="src tag">docs/22_decisions/</span></h2>')
    parts.append(section_sub("Kết luận đã duyệt — thứ duy nhất sửa được Architecture"))
    if not decisions:
        parts.append(empty_state("NO DECISIONS — Proposal được duyệt sẽ về đây"))
    else:
        rows = []
        for d in sorted(decisions, key=lambda x: fm_str(x, "id"), reverse=True):
            outcome = fm_str(d, "outcome")
            stamp = ('<span class="stamp st-%s">%s</span>' % (esc(outcome), esc(outcome))
                     if outcome in ("approved", "rejected") else esc(outcome))
            amendment = fm_str(d, "architecture_amendment") or "none"
            am_cell = "<span class=\"dim\">—</span>" if amendment in ("none", "") \
                else inline_md(amendment, here)
            rev = ctx.get("rev_letter", {}).get(fm_str(d, "id"))
            if rev and amendment not in ("none", ""):
                am_cell = "REV %s — %s" % (rev, am_cell)
            rows.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                        % (id_tag(fm_str(d, "id"), here), stamp, esc(fm_str(d, "decided_by") or "—"),
                           id_tag(fm_str(d, "proposal_ref"), here, "tag"), am_cell))
        parts.append('<table class="data"><tr><th style="width:150px">id</th>'
                     '<th style="width:120px">outcome</th><th style="width:100px">decided by</th>'
                     '<th style="width:130px">from</th><th>architecture amendment</th></tr>%s</table>'
                     % "".join(rows))

    # --- traceability
    chains = []
    for d in sorted(decisions, key=lambda x: fm_str(x, "id"), reverse=True):
        dec_id = fm_str(d, "id")
        prop_id = fm_str(d, "proposal_ref")
        prop = by_id.get(prop_id)
        issue_id = fm_str(prop, "issue_ref") if prop else ""
        segs = [id_tag(x, here) for x in (issue_id, prop_id, dec_id) if x]
        arrow = farrow(L2)
        chain = arrow.join(segs)
        bl = backlog_of_source.get(dec_id, [])
        if bl:
            b = bl[0]
            st = fm_str(b, "status")
            chain += arrow + id_tag(fm_str(b, "id"), here)
            chain += ('<span class="status%s">%s%s</span>'
                      % (" live" if st == "in-progress" else "",
                         dot_html(BACKLOG_DOTS.get(st, "open")), esc(st)))
        chains.append('<div class="flow"><span class="flow-label"%s style="color:%s">Full lane</span>%s</div>'
                      % ("" , L2, chain))
    for b in sorted(backlog, key=lambda x: fm_str(x, "id"), reverse=True):
        src = fm_str(b, "source_ref")
        if src.startswith("ISSUE-"):
            st = fm_str(b, "status")
            chains.append('<div class="flow"><span class="flow-label" style="color:%s">Fast lane</span>'
                          "%s%s%s"
                          '<span class="status%s">%s%s</span>%s</div>'
                          % (FAST, id_tag(src, here), farrow(FAST, dashed=True), id_tag(fm_str(b, "id"), here),
                             " live" if st == "in-progress" else "",
                             dot_html(BACKLOG_DOTS.get(st, "open")), esc(st),
                             '<span class="tag lane-fast">fast</span>'))
    if chains:
        parts.append('<h3 id="traces">Traceability</h3>'
                     "<p>Dấu vết truy nguyên của từng thay đổi, dựng lại từ các trường <code>*_ref</code>:</p>"
                     + "".join(chains))

    # --- backlog board
    parts.append('<h2 id="backlog" class="s-l2"><span class="idx">§4</span>Backlog '
                 '<span class="src tag">docs/23_backlog/</span></h2>')
    parts.append(section_sub("Việc đã chốt — đang chờ, đang làm, hoặc đã xong"))
    if not backlog:
        parts.append(empty_state("NO BACKLOG ITEMS — việc được đẩy lên sẽ về <code>docs/23_backlog/</code>"))
    else:
        cols = []
        for st, col_label in (("open", "Open"), ("in-progress", "In progress"), ("done", "Done")):
            members = [b for b in backlog if fm_str(b, "status") == st]
            if not members:
                continue
            items = []
            for b in sorted(members, key=lambda x: fm_str(x, "id"), reverse=True):
                src = fm_str(b, "source_ref")
                lane = "fast" if src.startswith("ISSUE-") else ""
                tail = ('<div class="im" style="margin-top:5px"><span class="tag">src %s</span>%s</div>'
                        % (esc(src), lane_tag(lane))) if src else ""
                items.append('<div class="item"><div class="im">%s%s</div><div class="it">%s</div>%s</div>'
                             % (dot_html(BACKLOG_DOTS[st]), id_tag(fm_str(b, "id"), here),
                                esc(trim(fm_str(b, "description") or doc_title(b), 90)), tail))
            col_cls = "col-h now" if st == "in-progress" else "col-h"
            cols.append('<div><div class="%s">%s <span class="n">%d</span></div>%s</div>'
                        % (col_cls, col_label, len(members), "".join(items)))
        parts.append('<div class="board">%s</div>' % "".join(cols))

    # --- audit
    parts.append('<h2 id="audit" class="s-ink"><span class="idx">§5</span>Audit log '
                 '<span class="src tag">docs/92_audit/LOG.md</span></h2>')
    parts.append(section_sub("Nhật ký chỉ ghi thêm — nơi tra dấu vết khi cần đối chiếu"))
    if audit["entries"]:
        if audit["deviations_30d"]:
            parts.append('<div class="note dev"><span class="lbl">Deviation</span>'
                         "Đã ghi nhận %d deviation trong 30 ngày gần nhất.</div>"
                         % audit["deviations_30d"])
        rows = []
        for e in audit["entries"][:5]:
            ref_cell = id_tag(e["ref"], here, "tag") if ID_RE.search(e["ref"]) else esc(e["ref"] or "—")
            dev_cell = ('<span class="devtag">deviation · %s</span>' % esc(e["deviation"])
                        if e["deviation"] not in ("-", "", "—") else '<span class="dim">—</span>')
            rows.append('<tr><td class="mono">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                        % (esc(e["date"]), inline_md(e["what"], here), ref_cell, dev_cell))
        parts.append('<table class="data"><tr><th style="width:110px">date</th><th>what happened</th>'
                     '<th style="width:150px">ref</th><th style="width:210px">deviation</th></tr>%s</table>'
                     % "".join(rows))
        if len(audit["entries"]) > 5:
            parts.append('<p style="font-size:12.5px;color:var(--ink-3);margin-top:10px">Đang hiện 5 dòng '
                         "mới nhất trong %d dòng — log đầy đủ ở <code>docs/92_audit/LOG.md</code>.</p>"
                         % len(audit["entries"]))
    else:
        parts.append(empty_state("NO AUDIT ENTRIES — docs-sync sẽ ghi thêm một dòng cho mỗi sự kiện đáng kể"))

    sidebar = ['<li><a href="#issues">§1 Issues</a></li>',
               '<li><a href="#proposals">§2 Proposals</a></li>',
               '<li><a href="#decisions">§3 Decisions</a></li>']
    if chains:
        sidebar.append('<li class="sub"><a href="#traces">Traceability</a></li>')
    sidebar.append('<li><a href="#backlog">§4 Backlog</a></li>')
    sidebar.append('<li><a href="#audit">§5 Audit log</a></li>')

    return page_html(ctx, "%s · Change pipeline" % ctx["project"], "Changes",
                     "".join(sidebar), "".join(parts), "CHANGE PIPELINE")


# ---------------------------------------------------------------- page: index

LAYER3 = [("30_conventions", "Quy ước code, đặt tên, luật review"),
          ("40_services", "Ghi chú vận hành theo từng service"),
          ("50_runbooks", "Quy trình xử lý sự cố và bảo trì"),
          ("60_fe-integration", "Hướng dẫn tích hợp frontend"),
          ("70_deploy", "Môi trường và quy trình deploy")]


def build_index(ctx, docs, data, audit, latest_rev, check_result):
    here = "index.html"
    products, backlog = data["products"], data["backlog"]
    comps = ctx.get("component_count", 0)
    counts = {s: sum(1 for b in backlog if fm_str(b, "status") == s)
              for s in ("open", "in-progress", "done")}

    meta = [tag(ctx["ref"]), tag("generated " + ctx["stamp"])]
    if check_result is not None:
        if check_result == 0:
            meta.append('<span class="status">%sdocs-check clean</span>' % dot_html("live"))
        else:
            meta.append('<span class="status live">%sdocs-check · %d error%s</span>'
                        % (dot_html("progress"), check_result, "" if check_result == 1 else "s"))
    if counts["in-progress"]:
        meta.append('<span class="status live">%s%d in flight</span>'
                    % (dot_html("progress"), counts["in-progress"]))

    hub1_stats = [tag("%d products" % len(products)), tag("%d components" % comps)]
    if latest_rev:
        hub1_stats.append(tag("REV " + latest_rev, "tag id l1"))
    hub2_stats = [tag("%d open" % counts["open"]), tag("%d in-progress" % counts["in-progress"]),
                  tag("%d done" % counts["done"])]
    if audit["deviations_30d"]:
        hub2_stats.append(tag("%d deviation%s / 30d" % (audit["deviations_30d"],
                                                        "" if audit["deviations_30d"] == 1 else "s")))

    refrows = []
    l3_files = 0
    for folder, desc in LAYER3:
        n = len(md_files(docs / folder))
        l3_files += n
        cls = "refrow is-empty" if n == 0 else "refrow"
        count = "empty" if n == 0 else "%d file%s" % (n, "" if n == 1 else "s")
        refrows.append('<div class="%s"><span class="rf"><a href="%s/">%s/</a></span>'
                       '<span class="rd">%s</span><span class="rn">%s</span></div>'
                       % (cls, folder, folder, desc, count))
    audit_count = ("%d entries · last %s" % (len(audit["entries"]), audit["entries"][0]["date"])
                   if audit["entries"] else "no entries yet")
    qa_n = len(md_files(docs / "93_qa"))
    oversight = ('<div class="refrow"><span class="rf"><a href="changes.html#audit">92_audit/</a></span>'
                 '<span class="rd">Audit log chỉ ghi thêm — nơi tra cứu truy nguyên</span>'
                 '<span class="rn">%s</span></div>'
                 '<div class="refrow%s"><span class="rf"><a href="93_qa/">93_qa/</a></span>'
                 '<span class="rd">Ghi chú QA và ma trận test</span><span class="rn">%s</span></div>'
                 % (audit_count, " is-empty" if qa_n == 0 else "",
                    "empty" if qa_n == 0 else "%d file%s" % (qa_n, "" if qa_n == 1 else "s")))

    content = (
        '<p class="kicker">docs / overview</p>'
        "<h1>%s — documentation</h1>"
        '<p class="lede">Bản đồ sinh tự động của toàn bộ <code>docs/</code>. Bản rút gọn 30 giây nằm ở '
        '<a href="README.md">README.md</a>; các file markdown luôn là nguồn sự thật.</p>'
        '<div class="meta-row">%s</div>'
        "%s"
        '<div class="plot" style="margin:28px 0 0">%s'
        '<p class="figcap">FIG 1 · mô hình ba lớp — mỗi tuyến một màu: '
        '<span style="color:%s;font-weight:700">foundation</span> · '
        '<span style="color:%s;font-weight:700">change</span> · '
        '<span style="color:%s;font-weight:700">fast lane</span> · '
        '<span style="color:%s;font-weight:700">amendment</span>. Mọi ga đều là link.</p></div>'
        '<h2 class="s-lines"><span class="idx">§1</span>Sheets</h2>'
        '<p class="h2sub">Hai trang chi tiết — trạng thái và tiến trình</p>'
        '<div class="hubgrid">'
        '<a class="hub" href="current.html"><span class="hk k1">Layer 1 · state</span>'
        '<div class="ht">Foundation — current state</div>'
        '<div class="hd">Products, roadmap và architecture như đang được ghi. Chỉ sửa qua '
        'Decision.</div><div class="hs">%s</div></a>'
        '<a class="hub" href="changes.html"><span class="hk k2">Layer 2 · process</span>'
        '<div class="ht">Change pipeline</div>'
        '<div class="hd">Issue → Proposal → Decision → Backlog, kèm truy nguyên đầy đủ '
        'và audit log.</div><div class="hs">%s</div></a></div>'
        '<h2 class="s-ink"><span class="idx">§2</span>Reference <span class="dim2">LAYER 3 · EDIT DIRECTLY, '
        'NO DECISION NEEDED</span></h2>'
        '<p class="h2sub">Tài liệu tra cứu — sửa thẳng, không cần Decision</p>'
        '<div class="reflist">%s</div>'
        '<h2 class="s-ink"><span class="idx">§3</span>Oversight</h2>'
        '<p class="h2sub">Giám sát — audit log và ghi chú QA</p>'
        '<div class="reflist">%s</div>'
        '<div class="note"><span class="lbl">Rule</span><b class="hl">Thay đổi code chạm tới schema, '
        "API contract hay ranh giới component đều cần một Decision có sẵn từ trước</b> — chưa có thì "
        "mở Issue trước đã. Bảng lane test và trigger: <code>docs/README.md</code>.</div>"
        % (esc(ctx["project"]), "".join(meta),
           # the whole corpus by layer — how much of docs/ is state, process, reference
           hue_rule([("l1", len(products) + comps, "Layer 1"),
                     ("l2", counts["open"] + counts["in-progress"] + counts["done"], "Layer 2"),
                     ("line-2", l3_files, "Layer 3")]),
           svg_system_map(), L1, L2, FAST, MARK,
           "".join(hub1_stats), "".join(hub2_stats), "".join(refrows), oversight))
    return page_html(ctx, "%s · docs" % ctx["project"], "Overview", None, content, "OVERVIEW")


# ---------------------------------------------------------------- audit + validator

def load_audit(docs, today):
    log = docs / "92_audit" / "LOG.md"
    entries = []
    if log.is_file():
        for line in log.read_text(encoding="utf-8", errors="replace").split("\n"):
            m = DATE_LINE_RE.match(line.strip())
            if not m:
                continue
            cells = [c.strip() for c in line.strip().split("|")]
            entries.append({"date": cells[0], "what": cells[1] if len(cells) > 1 else "",
                            "ref": cells[2] if len(cells) > 2 else "",
                            "deviation": cells[3] if len(cells) > 3 else "-"})
    entries.sort(key=lambda e: e["date"], reverse=True)
    cutoff = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    dev30 = sum(1 for e in entries if e["deviation"] not in ("-", "", "—") and e["date"] >= cutoff)
    return {"entries": entries, "deviations_30d": dev30}


def run_validator(script_dir, root):
    validator = script_dir / "docs_validate.sh"
    if not validator.is_file():
        return None
    try:
        r = subprocess.run(["bash", str(validator), str(root / "docs")], capture_output=True,
                           text=True, timeout=60)
        if r.returncode == 0:
            return 0
        return sum(1 for ln in (r.stdout + r.stderr).split("\n") if ln.startswith("FAIL ")) or 1
    except Exception:
        return None


# ---------------------------------------------------------------- main

def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    docs = root / "docs"
    if not docs.is_dir():
        print("docs-render: no docs/ directory under %s — run /docs-kit:docs-init first" % root,
              file=sys.stderr)
        return 2

    script_dir = Path(__file__).resolve().parent
    dt = now()
    ctx = {
        "project": root.name,
        "ref": git_ref(root),
        "date": dt.strftime("%Y-%m-%d"),
        "stamp": dt.strftime("%Y-%m-%d %H:%M"),
        "version": renderer_version(script_dir),
    }

    data = load_docs(docs)
    audit = load_audit(docs, dt)

    # rev letters shared between pages
    arch_file = docs / "02_architecture" / "architecture.md"
    amends = []
    if arch_file.is_file():
        arch_fm, _ = parse_frontmatter(arch_file.read_text(encoding="utf-8", errors="replace"))
        for entry in as_list(arch_fm.get("amended_by", [])):
            m = AMEND_RE.match(str(entry).strip())
            if m:
                amends.append(m.group(2))
        ctx["component_count"] = len(parse_components(arch_fm.get("components", [])))
    ctx["rev_letter"] = {dec: chr(65 + i) for i, dec in enumerate(amends)}

    current_html, latest_rev = build_current(ctx, docs, data)
    changes_html = build_changes(ctx, docs, data, audit)
    check_result = run_validator(script_dir, root)
    index_html = build_index(ctx, docs, data, audit, latest_rev, check_result)

    for name, content in (("index.html", index_html), ("current.html", current_html),
                          ("changes.html", changes_html)):
        (docs / name).write_text(content, encoding="utf-8")
        print("WROTE docs/%s" % name)
    print("RENDER OK — open docs/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
