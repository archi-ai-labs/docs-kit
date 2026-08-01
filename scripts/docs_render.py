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
import itertools
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
L1_WASH = "#eef3ff"   # --l1-wash, so a figure can fill with a hue it already spends
L2 = "#7c3aed"
FAST = "#0d9488"
TINT_DB = "#e8f0fe"
TINT_ASYNC = "#f1ecfe"

MONO_STACK = "ui-monospace,Menlo,Consolas,monospace"

ID_RE = re.compile(r"\b(ISSUE|PROPOSAL|DECISION|BACKLOG)-([0-9]{3,})\b")
# A markdown link whose visible text is just an id. Promoting the id to a chip
# means removing the WHOLE link — dropping only the id leaves '[](p/ISSUE-1-x.md)'
# on the page, and mangles the href besides.
MD_LINK_ID_RE = re.compile(
    r"\[\s*(?:ISSUE|PROPOSAL|DECISION|BACKLOG)-[0-9]{3,}\s*\]\([^)\s]*\)")
DATE_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*\|")
AMEND_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(DECISION-[0-9]{3,})\s*(.*)$")
KIND_RE = re.compile(r"\[(db|queue|ui|svc)\]")
CODE_RE = re.compile(r"`([^`]+)`")  # a component's anchor in the source tree

ID_PAGE = {"ISSUE": ("changes.html", "issues"), "PROPOSAL": ("changes.html", "proposals"),
           "DECISION": ("changes.html", "decisions"), "BACKLOG": ("changes.html", "backlog")}

# Tags are colored by destination: which layer the reference sends you to.
# Derived from ID_PAGE so the hue stays honest if a prefix ever moves sheets.
PAGE_LAYER = {"current.html": "l1", "changes.html": "l2"}

CHAR_W = 6.95  # approx mono advance at 11.5px, used to size SVG nodes
# Usable width inside .plot at full desktop width: .content 880 − 2×20 padding
# − 2×1 border. A figure wider than this is drawn at natural size and scrolls;
# anything at or under it may stretch to fill, but is never scaled down.
CONTENT_W = 838

# `markerUnits` defaults to `strokeWidth`, so a marker's real size is
# `markerWidth ÷ viewBox × stroke-width` — not `markerWidth`. `marker_def()`, the
# arrowhead of every flow figure, is 7 ÷ 10 × 1.6 = 11.2 user units of box holding
# 7.8 of ink. The crow's foot and the UML triangle were written at 12 ÷ 12 × 1.6
# = 19.2, which is 70% larger than everything else in the system on a 20px row
# pitch — nobody chose that number, it just never got compared. MARKER_W matches
# them to the others by INK rather than by box, because the foot's toes span 11 of
# its 12 viewBox units while the chevron spans 7 of 10: equal boxes would still
# draw unequal line.
MARKER_W = 5.5    # 5.5 ÷ 12 × 1.6 = 8.8 box · 8.1 ink

# The density budget for the graph. It no longer picks a presentation — there is
# only one, the graph — it decides when to WARN. Past any of these the flow is
# still drawn, at natural size, scrolling inside its own frame; the note just
# suggests splitting it across Architecture docs. See STANDARD §10.
FLOW_MAX_NODES = 20
FLOW_MAX_EDGES = 32
FLOW_MAX_ROWS = 10  # nodes stacked in one column


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

def strip_comment(v):
    """Drop a YAML inline comment — an unquoted '#' at the start or after
    whitespace. Without this, 'components: []   # what goes here' parses as the
    literal string rather than an empty list, and a documented example becomes a
    phantom component. Quoted '#' (a colour, a ticket ref) is left alone."""
    out, quote = [], None
    for k, ch in enumerate(v):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
            continue
        if ch == "#" and (k == 0 or v[k - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out)


def clean_value(v):
    v = strip_comment(v).strip()
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
        key, val = m.group(1), strip_comment(m.group(2)).strip()
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


def ids_in(text):
    """Ids in reading order, deduped — a bullet may cite the same id twice
    (once as link text, once inside the href) and must still show one chip."""
    out = []
    for m in ID_RE.finditer(text):
        if m.group(0) not in out:
            out.append(m.group(0))
    return out


def strip_ids(text):
    """Drop id mentions that have been promoted to their own chips."""
    text = MD_LINK_ID_RE.sub("", text)
    text = ID_RE.sub("", text)
    return re.sub(r"\s{2,}", " ", text).strip(" ()[]—–:-·,")


class FigCounter:
    """Figures are numbered per sheet, in the order they appear on it."""

    def __init__(self):
        self.n = 0

    def next(self):
        self.n += 1
        return str(self.n)


def md_to_html(md, here, comps=None, figs=None):
    """Supported subset: h1-h4, paragraphs, ul/ol (2 levels), fenced code,
    tables, blockquotes, hr, inline code/bold/italic/links. A ```flow fence
    becomes a sequence figure. Unknown lines render as escaped paragraphs —
    never broken HTML."""
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
        if FENCE_OPEN_RE.match(line):
            flush_para(para)
            info, code, i = scan_fence(lines, i)
            body = "\n".join(code)
            fig = seq_figure(body, comps or {}, figs, here) if info == "flow" else None
            # An unparseable flow block falls back to its own source text — the
            # renderer never guesses at a diagram it could not read.
            out.append(fig or ("<pre><code>%s</code></pre>" % esc(body)))
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
    """'name [kind] `path/in/repo` — what it does'. The kind and the code path are
    optional; everything after the dash is prose. Stays a flat one-line grammar on
    purpose — the validator parses this with awk, and authors write it by hand.
    Returns an ordered dict: name -> {kind, desc, code}."""
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
        kind, code = "svc", ""
        m = KIND_RE.search(name)
        if m:
            kind = m.group(1)
            name = KIND_RE.sub("", name)
        m = CODE_RE.search(name)
        if m:
            code = m.group(1).strip()
            name = CODE_RE.sub("", name)
        comps[name.strip()] = {"kind": kind, "desc": desc.strip(), "code": code}
    return comps


def component_facts(name, edges, comps):
    """What the flow graph already knows about a component. Derived, never authored —
    an upstream list that disagrees with data_flow would just be a second thing to
    keep in sync."""
    upstream = [a for a, b, _x, _l in edges if b == name]
    downstream = [b for a, b, _x, _l in edges if a == name]
    upstream = sorted(set(upstream), key=str.lower)
    downstream = sorted(set(downstream), key=str.lower)
    if not upstream and downstream:
        role = "source — nothing in the flow writes to it"
    elif upstream and not downstream:
        role = "sink — the flow ends here"
    elif len(upstream) + len(downstream) >= 5:
        role = "hub — %d in · %d out" % (len(upstream), len(downstream))
    elif upstream or downstream:
        role = "relay — %d in · %d out" % (len(upstream), len(downstream))
    else:
        role = "not wired into data_flow"
    return {"upstream": upstream, "downstream": downstream, "role": role}


NODE_STYLE = {  # kind -> (border, dashed, badge_bg, icon_color, icon, label_fill)
    "svc": (INK, False, "#f4f6f8", INK2, "svc", INK),
    "db": (L1, False, TINT_DB, L1, "db", INK),
    "queue": (L2, False, TINT_ASYNC, L2, "bolt", INK),
    "ui": (LINE2, True, "#f4f6f8", INK3, "ui", INK2),
    "ext": (LINE2, True, "#f4f6f8", INK3, "globe", INK2),
}


def feedback_arcs(edges):
    """Indices of the edges to lift out so the rest is acyclic — a cycle in
    data_flow means request/response, a callback, a cache read-back or a retry,
    all of them normal, so the graph keeps its shape and these edges are drawn
    as back-edges instead of the whole figure changing style.

    DFS from each root in name order; an edge into a node still on the stack is
    a back edge. Not the minimum feedback arc set (that is NP-hard) but a stable
    one: every iteration order here is sorted, so the same input always lifts
    the same edges — which is what keeps the rendered bytes reproducible."""
    adj, nodes = {}, set()
    for a, b, _asyn, _lbl in edges:
        nodes.add(a)
        nodes.add(b)
    for i, (a, b, _asyn, _lbl) in enumerate(edges):
        adj.setdefault(a, []).append((b, i))
    for a in adj:
        adj[a].sort(key=lambda t: (t[0].lower(), t[1]))

    WHITE, GREY, BLACK = 0, 1, 2
    color = dict.fromkeys(nodes, WHITE)
    back = set()
    for root in sorted(nodes, key=str.lower):
        if color[root] != WHITE:
            continue
        color[root] = GREY
        stack = [[root, 0]]
        while stack:
            frame = stack[-1]
            kids = adj.get(frame[0], [])
            if frame[1] >= len(kids):
                color[frame[0]] = BLACK
                stack.pop()
                continue
            tgt, idx = kids[frame[1]]
            frame[1] += 1
            if color[tgt] == GREY:      # closes a cycle, including a self-loop
                back.add(idx)
            elif color[tgt] == WHITE:
                color[tgt] = GREY
                stack.append([tgt, 0])
    return back


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


def kind_of(nd, comps):
    if nd in comps:
        return comps[nd]["kind"]
    low = nd.lower()
    return "ui" if low in ("client", "browser", "user", "app") else "ext"


def svg_size(width, height, label):
    """A figure is drawn at its natural size and never scaled below it — shrinking
    to fit is what turns a busy diagram into an unreadable one. Small figures may
    still stretch up to the column; wide ones scroll inside .plot instead."""
    fit = 'width="100%"' if width <= CONTENT_W else 'width="%d" height="%d"' % (width, height)
    return '<svg viewBox="0 0 %d %d" %s role="img" aria-label="%s">' % (width, height, fit, label)


def chip_w_for(text):
    return len(text) * 5.6 + 12


def wrap_label(text, limit=17):
    """Split a long edge label into two balanced lines. A gap is widened to hold
    its widest label, so one long label pushes the whole figure wider; wrapping
    keeps the graph inside the column instead of sending it off to a scrollbar."""
    words = text.split()
    if len(text) <= limit or len(words) < 2:
        return [text]
    best, cut = None, 1
    for i in range(1, len(words)):
        cost = max(len(" ".join(words[:i])), len(" ".join(words[i:])))
        if best is None or cost < best:
            best, cut = cost, i
    return [" ".join(words[:cut]), " ".join(words[cut:])]


def chip_box(lines):
    """(width, height) of the label chip for these lines."""
    return max(chip_w_for(x) for x in lines), 16 if len(lines) == 1 else 27


# An entity box is a header band plus one line per column — the only node in the
# engine whose height is not NODE_H, and the reason the layout measures heights
# instead of multiplying by a row pitch.
ENTITY_HEAD_H = 26
ENTITY_COL_H = 20


# Struct routing, the geometry of a relation that is not a flow. One lane per
# relation in the column gap: MIN_RUN of visible line at each end so an arrowhead
# never eats its own segment, PITCH between neighbouring lanes, and SLOT_MIN as
# the point below which two arrowheads landing on one band stop reading as two.
STRUCT_PITCH, STRUCT_MIN_RUN, STRUCT_SLOT_MIN = 12.0, 24.0, 12.0


def assign_lanes(shapes, lanes):
    """Put each bundle on one of `lanes` (x positions, left to right) so that as
    few lines cross as possible. Returns lane index per bundle.

    A bundle is `(feeders, head_y, target_x)` where feeders are the `(x, y)` it
    collects from. Exhaustive up to 7 bundles — a gap busier than that is already
    past the reading budget the figures are drawn to — and a deterministic sort
    above that, so the picture never depends on how long a search was allowed to
    run. Ties break on the permutation itself, which keeps the result stable."""
    n = len(shapes)
    if n <= 1:
        return list(range(n))

    def drawn(shape, lx):
        feeds, hy, tx = shape
        hs = [(min(fx, lx), max(fx, lx), fy) for fx, fy in feeds]
        hs.append((min(lx, tx), max(lx, tx), hy))
        ys = [fy for _fx, fy in feeds] + [hy]
        return hs, ([(lx, min(ys), max(ys))] if max(ys) - min(ys) > .01 else [])

    def crossings(perm):
        laid = [drawn(sh, lanes[p]) for sh, p in zip(shapes, perm)]
        return sum(1
                   for i, (hs, _) in enumerate(laid)
                   for j, (_, vs) in enumerate(laid) if i != j
                   for (ha, hb, hy) in hs
                   for (vx, va, vb) in vs
                   if ha < vx < hb and va < hy < vb)

    if n <= 7:
        return list(min(itertools.permutations(range(n)),
                        key=lambda p: (crossings(p), p)))
    ranked = sorted(range(n), key=lambda i: (shapes[i][1], shapes[i][0][0][1], i))
    lane_of = [0] * n
    for k, i in enumerate(ranked):
        lane_of[i] = k
    return lane_of


def svg_dag(edges, comps, fig_no="1", shapes=None, aria="data flow graph",
            caption=None, wrap=True, initial=None, entity_rows=None,
            entity_tag=None, marks=None, dashed=None, defs="",
            route="flow", anchor=None):
    """The one layered-graph engine. `shapes` switches it from data-flow nodes
    (icon badge, kind tint) to flowchart nodes (step / decide / terminal), state
    machine nodes (state / final) or ERD entities; each of those is the same
    layering problem with different boxes, and giving any of them its own engine
    would mean maintaining the back-edge routing more than once. `initial` names
    the one node drawn with the start stroke.

    `entity_rows` maps a node to its column lines and makes that node an entity —
    a box as tall as the table is long. It is deliberately NOT called `rows`: the
    label loops below bind a local `rows`, and a closure over a shadowed name
    would silently measure a wrapped label instead of a table. A row whose tag set
    contains "sep" gets a hairline drawn above it, which is how a class box splits
    fields from methods without a second kind of node. `entity_tag` puts a short
    stereotype in the header band — inside it, so no box grows taller for it.

    `marks` maps an edge index to (start marker id, end marker id), either of
    which may be None for a bare end; absent index keeps the default arrowhead.
    `dashed` is a set of edge indices drawn with a STATIC dash — graphite, and
    without the marching animation, because marching dashes already mean async and
    a UML realization arrow is not an async call.
    `defs` is extra <defs> content from the caller. Between them this function
    stays ignorant of what a crow's foot is — it places markers by id, and the
    figure that needs them defines them.

    `route="struct"` is for figures whose edges are STRUCTURE rather than
    movement. A foreign key and a UML generalization do not flow anywhere, so the
    data-flow curve leaving the middle of a box says the wrong thing about them
    twice over: it starts nowhere in particular, and the middle of a tall entity
    box is a column that has nothing to do with the key being drawn. A struct edge
    leaves the row it comes from, runs to a vertical lane of its own in the column
    gap, and lands on the target's border. `anchor` maps an edge index to
    `(source row, target row)`, either of which may be None for "the header band —
    this relation belongs to the type, not to any one member".

    It is paint, not layout. Layering, the feedback arc set and the return lanes
    are the same code either way; only the path between two already-placed boxes
    changes, so "one layered-graph engine" still holds.

    `wrap=False` returns the bare <svg> so a caller can compose its own frame."""
    # Cycles do not change the style — they lose their back-edges for the
    # purpose of layering, then get them drawn back in below the rows.
    back_idx = feedback_arcs(edges)
    # Both lists carry the edge's index in `edges`, because `marks` is keyed by it
    # and the back list gets re-sorted into lanes further down.
    fwd = [(i, e) for i, e in enumerate(edges) if i not in back_idx]
    back = [(i, e) for i, e in enumerate(edges) if i in back_idx]
    layer = layer_nodes([e for _i, e in fwd])
    if layer is None:
        return None
    # A node reachable only over a back-edge still needs a column of its own.
    for a, b, _asyn, _lbl in [e for _i, e in back]:
        for nd in (a, b):
            if nd not in layer:
                layer[nd] = 0
    cols = {}
    for nd in sorted(layer, key=lambda x: (layer[x], x.lower())):
        cols.setdefault(layer[nd], []).append(nd)
    ncols = max(cols) + 1

    # Sugiyama's ordering step, which this engine skipped. Alphabetical order is
    # deterministic but blind: it can put a node above another whose edges all go
    # the other way, and then nothing the router does can stop the two bundles
    # crossing — the fix has to be the ORDER, not the drawing. So order each
    # column by the mean index of the nodes it points at in the column to its
    # right, sweeping right to left. A node with no successor keeps its place.
    # Ties fall back to alphabetical, so the whole pass is still reproducible byte
    # for byte and needs no iteration count to converge.
    succ = {}
    for _a, _b, _asyn, _lbl in [e for _i, e in fwd]:
        succ.setdefault(_a, []).append(_b)
    for c in range(ncols - 2, -1, -1):
        right_idx = dict((nd, i) for i, nd in enumerate(cols.get(c + 1, [])))
        here_idx = dict((nd, i) for i, nd in enumerate(cols[c]))

        def bary(nd, _r=right_idx, _h=here_idx):
            seen = [_r[t] for t in succ.get(nd, []) if t in _r]
            return sum(seen) / float(len(seen)) if seen else float(_h[nd])

        cols[c] = sorted(cols[c], key=lambda nd: (bary(nd), nd.lower()))

    def node_w(nd):
        if entity_rows is not None and nd in entity_rows:
            # An entity is as wide as its widest column line, not as its name.
            # +8 leaves room for the PK / FK tag between the name and the type;
            # the header has to hold the name and its stereotype side by side.
            head = len(nd) + 2 + len((entity_tag or {}).get(nd, "")) + 2
            widest = max([head] + [len(r[0]) + len(r[1]) + 8
                                   + (2 if ({"public", "private"} & set(r[2])) else 0)
                                   for r in entity_rows[nd]])
            return int(30 + CHAR_W * widest)
        if shapes is None:
            return int(48 + CHAR_W * len(nd))   # room for the 22px icon badge
        # A diamond wastes its corners, so the same text needs a wider box.
        return int((64 if shapes.get(nd) == "decide" else 30) + CHAR_W * len(nd))

    def node_h(nd):
        if entity_rows is not None and nd in entity_rows:
            return ENTITY_HEAD_H + ENTITY_COL_H * len(entity_rows[nd])
        return NODE_H

    col_w = {c: max(node_w(nd) for nd in cols[c]) for c in cols}
    # ROW_GAP, not a row pitch: with every node one height the two are the same
    # arithmetic, but only the gap survives boxes of different heights.
    GAP_MIN, ROW_GAP, NODE_H, TOP = 46, 26, 34, 16

    # ---- struct routing, part 1: which edges, and how many lanes each gap owes.
    # Counted here because the gap widths below have to hold the lanes, and the
    # count needs only the layering — no geometry yet.
    def anchor_of(ei, end):
        return (anchor or {}).get(ei, (None, None))[end]

    def band_h(nd, row):
        """The height a connection point has to live inside."""
        if entity_rows is None or nd not in entity_rows:
            return node_h(nd)
        return ENTITY_HEAD_H if row is None or not 0 <= row < len(entity_rows[nd]) \
            else ENTITY_COL_H

    routed, buckets, converge, lane_n = {}, {}, {}, {}
    if route == "struct":
        for ei, (a, b, _asyn, _lbl) in fwd:
            # Orthogonal routing needs neighbouring columns; in an ERD or a class
            # diagram that is every edge. One that skips a column would have to run
            # its horizontal straight through whatever sits between, so it keeps
            # the curve rather than being drawn through a box.
            if layer[b] == layer[a] + 1:
                routed[ei] = (layer[a], "L", a, b)
        for ei, (a, b, _asyn, _lbl) in back:
            # A self-referencing key enters its own box from the side. As a return
            # lane it costs a 126px lobe below the rows and 51px of canvas for one
            # edge; entering from the gap beside it, it costs nothing.
            if a == b and layer[a] >= 1:
                routed[ei] = (layer[a] - 1, "R", a, b)
        for ei in sorted(routed):
            gap, _side, _a, b = routed[ei]
            buckets.setdefault((gap, b, anchor_of(ei, 1)), []).append(ei)
        for key, members in buckets.items():
            gap, b, drow = key
            # Several relations landing on one anchor each want their own
            # arrowhead. Two fit in a 26px header band; three foreign keys into a
            # 20px primary-key column do not, and pretending otherwise draws one
            # thick smudge. Below the threshold they share a trunk instead — every
            # tail still carries its own marker on its own row, so each relation is
            # still traceable back to exactly one place.
            room = (band_h(b, drow) - 10.0) / max(1, len(members) - 1)
            converge[key] = len(members) > 1 and room < STRUCT_SLOT_MIN
            lane_n[gap] = lane_n.get(gap, 0) + (1 if converge[key] else len(members))
        # A self key that joined a trunk is no longer a back-edge, and must not
        # reserve a return lane nor the canvas height that goes with one.
        back = [(i, e) for i, e in back if i not in routed]

    # Every label lives in the gap right after its source column, and each gap is
    # widened to hold its widest label. Labels therefore never reach into a column,
    # which is what used to put chips on top of node boxes.
    # Only forward labels live in a gap; a back-edge label rides its own return
    # lane below the rows, so it must not widen a column gap it never enters.
    labelled = [(a, b, asyn, lbl.strip()) for _i, (a, b, asyn, lbl) in fwd
                if lbl and lbl.strip()]
    gap_w = {}
    for c in range(ncols):
        gap_w[c] = GAP_MIN
    for a, _b, _asyn, text in labelled:
        c = layer[a]
        gap_w[c] = max(gap_w[c], chip_box(wrap_label(text))[0] + 18)
    # GAP_MIN exists to hold label chips, and a struct edge has no label — so the
    # gap collapses to the minimum and the arrowhead ends up nearly touching the
    # lane it came from. Widen only the gaps that actually carry lanes.
    for c, n in lane_n.items():
        gap_w[c] = max(gap_w[c], 2 * STRUCT_MIN_RUN + (n - 1) * STRUCT_PITCH)

    x0, col_x = 16, {}
    for c in range(ncols):
        col_x[c] = x0
        x0 += col_w.get(c, 0) + gap_w[c]
    width = x0 - gap_w[ncols - 1] + 16
    col_h = {c: sum(node_h(nd) for nd in cols[c]) + ROW_GAP * (len(cols[c]) - 1)
             for c in cols}
    tallest = max(col_h.values())
    # A wrapped back-edge label is two rows tall, so the lanes have to spread far
    # enough that one lane's chip cannot land on the next lane's line.
    back_rows = [wrap_label(e[3].strip()) if e[3] and e[3].strip() else []
                 for _i, e in back]
    LANE_H = 28 if any(len(r) > 1 for r in back_rows) else 15
    # One gap below the deepest box, so a return lane never starts against it.
    rows_bottom = TOP + tallest + ROW_GAP
    height = rows_bottom + (10 + len(back) * LANE_H + 16 if back else 26)

    pos = {}
    for c, members in cols.items():
        y = TOP + (tallest - col_h[c]) / 2.0   # short columns ride the middle
        for nd in members:
            pos[nd] = (col_x[c], y)
            y += node_h(nd) + ROW_GAP

    s = [svg_size(width, height, aria),
         "<defs>", marker_def("dag-a", INK), marker_def("dag-t", FAST), defs,
         "" if shapes is not None
         else symbol_defs(sorted({NODE_STYLE[kind_of(nd, comps)][4] for nd in layer}))]
    s.append("</defs>")

    labels, placed = [], []

    def branch_style(src_node, asyn):
        """(chip fill, chip stroke, ink, weight). A label on an edge out of a
        decide node IS the branch name — the most load-bearing text in a
        flowchart — so it takes the diamond's own hue instead of the muted grey
        every other edge label gets. No new hue is spent: it is the same L1."""
        if asyn:
            return "#e6faf5", "#7fd4c4", FAST, "700"
        if shapes is not None and shapes.get(src_node) == "decide":
            return "#ffffff", L1, L1, "700"
        return "#ffffff", "#e2e8ee", INK3, "500"


    def free_y(cx, cw, ch, y):
        """Nudge a chip off any chip already placed. Deterministic: the offsets are
        tried in a fixed order, and edges arrive in document order."""
        for dy in (0, -19, 19, -38, 38, -57, 57):
            box = (cx - cw / 2, y - 12 + dy, cw, ch)
            if not any(not (box[0] + box[2] <= p[0] or p[0] + p[2] <= box[0]
                            or box[1] + box[3] <= p[1] or p[1] + p[3] <= box[1])
                       for p in placed):
                placed.append(box)
                return y + dy
        placed.append((cx - cw / 2, y - 12, cw, ch))
        return y

    def marker_attrs(ei, default_end, start=True, end=True):
        """(start, end) marker ids for one edge. A relationship carries its
        cardinality at both ends and no arrowhead, so either end may be bare.

        A struct edge that shares a trunk is drawn in pieces, so a piece asks only
        for the end it owns: the feeder keeps its own tail marker on its own row,
        the trunk's head keeps the arrival marker."""
        mstart, mend = (marks or {}).get(ei, (None, default_end))
        return (('' if not (start and mstart) else ' marker-start="url(#%s)"' % mstart)
                + ('' if not (end and mend) else ' marker-end="url(#%s)"' % mend))

    def dash_attr(ei, static):
        """A static dash — graphite, and without the marching animation, because
        marching dashes already mean async and a UML realization is not a call."""
        return ' stroke-dasharray="6 4"' if ei in static else ''

    # ---- struct routing, part 2: the lines themselves. --------------------
    # Struct edges are never async and never labelled — `parse_erd` and
    # `parse_class` both emit `(src, dst, False, "")` — so none of the label,
    # packet or teal machinery below applies to them, and none of it is repeated
    # here. What is left is pure geometry.
    joins, static_dash = [], frozenset(dashed or ())

    def anchor_y(nd, row):
        """Where a relation touches a box: the row it comes from, or the header
        band when it belongs to the type rather than to any one member."""
        y = pos[nd][1]
        if entity_rows is None or nd not in entity_rows:
            return y + node_h(nd) / 2.0
        if row is None or not 0 <= row < len(entity_rows[nd]):
            return y + ENTITY_HEAD_H / 2.0
        return y + ENTITY_HEAD_H + ENTITY_COL_H * row + ENTITY_COL_H / 2.0

    def slot_ys(base, height, k):
        """k connection points centred in a band. Capped at 14 so two arrowheads
        in a header band sit apart without drifting onto the border."""
        if k <= 1:
            return [base]
        pitch = min(14.0, (height - 10.0) / (k - 1))
        return [base + (i - (k - 1) / 2.0) * pitch for i in range(k)]

    def side_x(ei):
        gap, side, a, _b = routed[ei]
        return pos[a][0] + node_w(a) if side == "L" else pos[a][0]

    if routed:
        # Departure. Two relations that both belong to the type — `extends` and
        # `implements` — leave the same header band, and leaving it at the same y
        # draws one on top of the other: the dashed line paints over the solid one
        # and the shared run reads as a single line forking for no reason. Rank
        # them by where they are going, so the two cannot cross on the way out.
        src_y, dst_y = {}, {}
        leaving = {}
        for ei in sorted(routed):
            _gap, _side, a, _b = routed[ei]
            leaving.setdefault((a, anchor_of(ei, 0)), []).append(ei)
        for (a, arow), members in sorted(leaving.items(), key=lambda kv: (kv[0][0], kv[1])):
            members.sort(key=lambda e: (anchor_y(routed[e][3], anchor_of(e, 1)), e))
            for e, yy in zip(members, slot_ys(anchor_y(a, arow), band_h(a, arow),
                                              len(members))):
                src_y[e] = yy
        # Arrival. Same rule at the other end: the upper source takes the upper
        # slot. A converged bucket has one arrival point, so its members share it.
        for key in sorted(buckets, key=lambda k: (k[0], k[1], -1 if k[2] is None else k[2])):
            _gap, b, drow = key
            members = sorted(buckets[key], key=lambda e: (src_y[e], e))
            ys = ([anchor_y(b, drow)] * len(members) if converge[key]
                  else slot_ys(anchor_y(b, drow), band_h(b, drow), len(members)))
            for e, yy in zip(members, ys):
                dst_y[e] = yy

        bundles = {}
        for key in sorted(buckets, key=lambda k: (k[0], k[1], -1 if k[2] is None else k[2])):
            gap, b, _drow = key
            members = sorted(buckets[key], key=lambda e: (src_y[e], e))
            for group in ([members] if converge[key] else [[e] for e in members]):
                bundles.setdefault(gap, []).append((group, b))

        for gap, group_list in sorted(bundles.items()):
            n = len(group_list)
            lo = col_x[gap] + col_w[gap] + STRUCT_MIN_RUN
            hi = col_x[gap] + col_w[gap] + gap_w[gap] - STRUCT_MIN_RUN
            lanes = ([(lo + hi) / 2.0] if n == 1
                     else [lo + i * (hi - lo) / (n - 1.0) for i in range(n)])
            lane_of = assign_lanes(
                [([(side_x(e), src_y[e]) for e in g], dst_y[g[0]], pos[b][0])
                 for g, b in group_list], lanes)
            for (group, b), li in zip(group_list, lane_of):
                lx, tx, hy = lanes[li], pos[b][0], dst_y[group[0]]
                if len(group) == 1:
                    e = group[0]
                    fx, fy = side_x(e), src_y[e]
                    d = ("M%g %g H%g" % (fx, fy, tx) if abs(fy - hy) < .01
                         else "M%g %g H%g V%g H%g" % (fx, fy, lx, hy, tx))
                    s.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s%s/>'
                             % (d, INK, dash_attr(e, static_dash),
                                marker_attrs(e, "dag-a")))
                    continue
                # Two feeders reaching the trunk from opposite sides at the same y
                # draw one unbroken line straight through the junction, and the eye
                # reads it as "these two connect to each other" — which is never
                # what either of them means. Row anchoring makes that collision a
                # coincidence away: a child's key and the parent's own key can
                # easily sit at the same height. The one arriving from the far side
                # steps aside, since it is already the odd one out.
                taken, step = [hy], {}
                for e in sorted(group, key=lambda x: (src_y[x], routed[x][1] == "R", x)):
                    fy = src_y[e]
                    for cand in [fy] + [fy + d for d in (14, -14, 28, -28, 42, -42)]:
                        if all(abs(cand - t) > 9.99 for t in taken):
                            step[e] = cand
                            taken.append(cand)
                            break
                    else:
                        step[e] = fy
                for e in group:
                    fx, fy, jy = side_x(e), src_y[e], step[e]
                    d = ("M%g %g H%g" % (fx, fy, lx) if abs(jy - fy) < .01 else
                         "M%g %g H%g V%g H%g"
                         % (fx, fy, fx + (12 if lx > fx else -12), jy, lx))
                    s.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s%s/>'
                             % (d, INK, dash_attr(e, static_dash),
                                marker_attrs(e, None, end=False)))
                ys = [step[e] for e in group] + [hy]
                # A trunk can only wear one arrival symbol, so it wears the one most
                # of its members carry — pure counting, so this function still does
                # not know what any of those symbols mean. Where a minority
                # disagrees, say one nullable key among several mandatory ones, the
                # ○ for "zero or one" drops out of the picture and the `null` flag
                # in the table beside it is what carries that fact.
                ends = [(marks or {}).get(e, (None, "dag-a"))[1] for e in group]
                lead = min(group, key=lambda e: (
                    -ends.count((marks or {}).get(e, (None, "dag-a"))[1]), e))
                s.append('<path d="M%g %g V%g" fill="none" stroke="%s" stroke-width="1.6"%s/>'
                         % (lx, min(ys), max(ys), INK, dash_attr(lead, static_dash)))
                s.append('<path d="M%g %g H%g" fill="none" stroke="%s" stroke-width="1.6"%s%s/>'
                         % (lx, hy, tx, INK, dash_attr(lead, static_dash),
                            marker_attrs(lead, "dag-a", start=False)))
                joins.extend((lx, yy) for yy in sorted(set(ys)))

    for ei, (a, b, asyn, lbl) in fwd:
        if ei in routed:
            continue
        ax, ay = pos[a]
        bx, by = pos[b]
        x1 = ax + node_w(a)
        y1 = ay + node_h(a) / 2.0
        # An arrowhead's TIP lands on the target's border. Every marker here puts
        # its tip on the path's own end point — the chevron's point is at viewBox
        # x=8, which is its refX; the triangle's apex at 12, which is its refX — so
        # the end point is the tip, and it belongs on the box. This used to be
        # `bx - 6`, which stood every arrowhead in every figure 6px short of what it
        # pointed at. With a 19.2-unit crow's foot the gap read as part of the
        # symbol; at 8.8 it read as a line that stopped early. Back-edges below the
        # rows already landed on the box bottom — this makes the two agree.
        x2 = bx
        y2 = by + node_h(b) / 2.0
        color, mid = (FAST, "dag-t") if asyn else (INK, "dag-a")
        dash = ' stroke-dasharray="5 4" class="dashrun"' if asyn else ""
        if ei in (dashed or ()):   # static dash: marching dashes mean async
            dash = ' stroke-dasharray="6 4"'
        if abs(y1 - y2) < 1:
            d = "M%g %g H%g" % (x1, y1, x2)
        else:
            cx1 = x1 + (x2 - x1) * 0.45
            cx2 = x1 + (x2 - x1) * 0.55
            d = "M%g %g C %g %g, %g %g, %g %g" % (x1, y1, cx1, y1, cx2, y2, x2, y2)
        s.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s%s/>'
                 % (d, color, dash, marker_attrs(ei, mid)))
        # The packet means data moving along the edge. A foreign key is a shape of
        # the schema, not a flow, so an edge with its own endpoint markers gets none.
        if not asyn and ei not in (marks or {}):
            s.append('<path d="%s" class="pkt"/>' % d)
        text = lbl.strip() if lbl else ""
        if text:
            c = layer[a]
            mx = col_x[c] + col_w[c] + gap_w[c] / 2.0
            rows = wrap_label(text)
            cw, ch = chip_box(rows)
            t = 0.5 if x2 == x1 else max(0.0, min(1.0, (mx - x1) / float(x2 - x1)))
            my = free_y(mx, cw, ch, y1 + (y2 - y1) * t - 10)
            chip_fill, chip_stroke, ink, wt = branch_style(a, asyn)
            labels.append('<rect x="%g" y="%g" width="%g" height="%d" rx="2" fill="%s" stroke="%s"/>'
                          % (mx - cw / 2, my - 12, cw, ch, chip_fill, chip_stroke))
            base = [my] if len(rows) == 1 else [my - 1, my + 10]
            for row, by in zip(rows, base):
                labels.append(svg_text(mx, by, row, 9, wt, ink, anchor="middle", ls=".6"))

    # Back-edges ride return lanes under the rows. Nothing else is drawn down
    # there, so a backwards arrow reads as backwards from its route alone — no
    # extra hue is spent on it, and it stays distinct from the teal dashed async
    # edges it may itself be one of.
    def span_of(e):
        # The horizontal run actually drawn, centre to centre — column origins
        # would rank two lanes by a distance neither of them travels.
        return abs((pos[e[0]][0] + node_w(e[0]) / 2.0)
                   - (pos[e[1]][0] + node_w(e[1]) / 2.0))

    # Narrowest span takes the shallowest lane. The other way round, a short
    # return nested inside a long one has to cross the long one's horizontal run
    # on its way down; this way each drop stops short of every deeper lane.
    for k, (ei, (a, b, asyn, lbl)) in enumerate(
            sorted(back, key=lambda p: (span_of(p[1]), p[1][0].lower(), p[1][1].lower()))):
        ly = rows_bottom + 10 + k * LANE_H
        ax, ay = pos[a]
        bx, by = pos[b]
        sx, sy = ax + node_w(a) / 2.0, ay + node_h(a)
        tx, ty = bx + node_w(b) / 2.0, by + node_h(b)
        color, mid = (FAST, "dag-t") if asyn else (INK, "dag-a")
        dash = ' stroke-dasharray="5 4" class="dashrun"' if asyn else ""
        if ei in (dashed or ()):   # static dash: marching dashes mean async
            dash = ' stroke-dasharray="6 4"'
        if a == b:  # feeds itself: a retry, or its own queue
            d = "M%g %g C %g %g, %g %g, %g %g" % (sx - 9, sy, sx - 34, ly, sx + 34, ly, sx + 9, sy)
        else:
            d = "M%g %g C %g %g, %g %g, %g %g" % (sx, sy, sx, ly, tx, ly, tx, ty)
        s.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s%s/>'
                 % (d, color, dash, marker_attrs(ei, mid)))
        if not asyn and ei not in (marks or {}):
            s.append('<path d="%s" class="pkt"/>' % d)
        text = lbl.strip() if lbl else ""
        if text:
            rows = wrap_label(text)
            cw, ch = chip_box(rows)
            mx = (sx + 44) if a == b else (sx + tx) / 2.0
            mx = max(cw / 2 + 4, min(width - cw / 2 - 4, mx))  # keep the chip on canvas
            chip_fill, chip_stroke, ink, wt = branch_style(a, asyn)
            labels.append('<rect x="%g" y="%g" width="%g" height="%d" rx="2" fill="%s" stroke="%s"/>'
                          % (mx - cw / 2, ly - ch / 2.0, cw, ch, chip_fill, chip_stroke))
            base = [ly + 3.5] if len(rows) == 1 else [ly - 1.5, ly + 9.5]
            for row, ry in zip(rows, base):
                labels.append(svg_text(mx, ry, row, 9, wt, ink, anchor="middle", ls=".6"))
    # Junction dots go on last of the lines, so a dot always sits on top of the
    # trunk it marks. A dot is what separates "joins here" from "crosses here",
    # and it is the only notation a shared trunk needs to stay readable.
    s.extend('<circle cx="%g" cy="%g" r="2.4" fill="%s"/>' % (jx, jy, INK)
             for jx, jy in joins)
    s.extend(labels)

    for nd in sorted(layer, key=lambda x: (layer[x], x.lower())):
        x, y = pos[nd]
        w, h = node_w(nd), node_h(nd)
        if entity_rows is not None and nd in entity_rows:
            s.append('<rect x="%g" y="%g" width="%d" height="%d" rx="3" fill="#ffffff" '
                     'stroke="%s" stroke-width="1.5"/>' % (x, y, w, h, INK))
            s.append('<path d="M%g %g H%g" stroke="%s" stroke-width="1"/>'
                     % (x, y + ENTITY_HEAD_H, x + w, INK))
            s.append(svg_text(x + 10, y + 17.5, nd, 11.5, "700", INK))
            stereo = (entity_tag or {}).get(nd, "")
            if stereo:
                # Graphite, and inside the band: a stereotype names no layer, so it
                # buys no hue, and giving it its own line would change every height.
                s.append(svg_text(x + w - 10, y + 17.5, stereo, 9, "600", INK3,
                                  anchor="end"))
            for r, row in enumerate(entity_rows[nd]):
                cname, ctype, tags = row[0], row[1], row[2]
                cy = y + ENTITY_HEAD_H + ENTITY_COL_H * r + 14
                if "sep" in tags:
                    s.append('<path d="M%g %g H%g" stroke="%s" stroke-width="1"/>'
                             % (x, cy - 14, x + w, INK))
                key = "pk" in tags
                # Visibility rides in the left margin. Graphite, like PK / FK: it
                # names no layer. Absent for an ERD row, so nothing there shifts.
                vis = "+" if "public" in tags else "−" if "private" in tags else ""
                if vis:
                    s.append(svg_text(x + 9, cy, vis, 10.5, "700", INK3))
                s.append(svg_text(x + (20 if vis else 10), cy, cname, 10.5,
                                  "700" if key else "500", INK if key else INK2))
                if ctype:   # a collapsed method signature leaves this side empty
                    s.append(svg_text(x + w - 10, cy, ctype, 10.5, "500", INK3,
                                      anchor="end"))
                # pk/fk stay graphite: they name no layer, so they buy no hue.
                if key or "fk" in tags:
                    s.append(svg_text(x + w - 10 - CHAR_W * (len(ctype) + 1), cy,
                                      "PK" if key else "FK", 8.5, "700", INK3, anchor="end"))
            continue
        if shapes is not None:
            shape = shapes.get(nd, "step")
            if shape == "decide":
                # Deliberately the heaviest object on the page. A flowchart exists
                # to answer one question — where does this branch — and all three
                # shapes used to carry the same 1.5px stroke on the same white, so
                # a reader had no way in. Wash fill and a 2px stroke make the branch
                # points what you see first. No new hue is spent: L1 is already the
                # diamond's colour and this only fills it with its own wash.
                s.append('<path d="M%g %g L%g %g L%g %g L%g %g Z" fill="%s" stroke="%s" '
                         'stroke-width="2"/>'
                         % (x, y + h / 2.0, x + w / 2.0, y, x + w, y + h / 2.0,
                            x + w / 2.0, y + h, L1_WASH, L1))
            elif shape in ("start", "end"):
                # The entry keeps the filled pill and full-weight ink; the exit is
                # drawn light. Scanning for "where does this begin" should land on
                # one answer, not on two identical capsules at opposite ends.
                fill, stroke, sw = (("#f4f6f8", INK, 1.5) if shape == "start"
                                    else ("#ffffff", INK3, 1.25))
                s.append('<rect x="%g" y="%g" width="%d" height="%d" rx="%g" fill="%s" '
                         'stroke="%s" stroke-width="%g"/>'
                         % (x, y, w, h, h / 2.0, fill, stroke, sw))
            elif shape in ("state", "final"):
                # The start state is marked by its stroke — no dot beside the box and
                # no pseudo-node. A dot would sit in the label gap, which is exactly
                # where edge chips get placed; a pseudo-node would put a box on the
                # figure that is not a state and inflate the count.
                stroke, sw = (L1, 2) if nd == initial else (INK, 1.5)
                s.append('<rect x="%g" y="%g" width="%d" height="%d" rx="8" fill="#ffffff" '
                         'stroke="%s" stroke-width="%g"/>' % (x, y, w, h, stroke, sw))
                if shape == "final":
                    # Drawn INWARD, never as an outer ring: column widths come from
                    # node_w(), so a ring would push the box past its own column and
                    # either overlap the next one or force a shrink — and figures here
                    # never shrink to fit.
                    s.append('<rect x="%g" y="%g" width="%g" height="%g" rx="5" fill="none" '
                             'stroke="%s" stroke-width="1"/>'
                             % (x + 3.5, y + 3.5, w - 7, h - 7, INK))
            else:
                # A step is what happens between branch points. At 1.25px graphite
                # it reads as ground rather than figure, which is the whole point of
                # giving the diamond somewhere to stand out from.
                s.append('<rect x="%g" y="%g" width="%d" height="%d" rx="2" fill="#ffffff" '
                         'stroke="%s" stroke-width="1.25"/>' % (x, y, w, h, INK2))
            s.append(svg_text(x + w / 2.0, y + h / 2.0 + 4.5, nd, 11.5, "650",
                              L1 if shape == "decide" else INK2 if shape == "end"
                              else INK, anchor="middle"))
            continue
        border, dashed, badge_bg, icon_color, icon, label_fill = NODE_STYLE[kind_of(nd, comps)]
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        s.append('<rect x="%g" y="%g" width="%d" height="%d" rx="2" fill="#ffffff" stroke="%s" stroke-width="1.5"%s/>'
                 % (x, y, w, h, border, dash))
        s.append('<rect x="%g" y="%g" width="22" height="22" rx="4" fill="%s"/>' % (x + 6, y + 6, badge_bg))
        s.append(use_icon(icon, x + 10, y + 10, icon_color, 14))
        s.append(svg_text(x + 36, y + 21.5, nd, 11.5, "650", label_fill))
    s.append("</svg>")
    if not wrap:
        return "".join(s)
    if caption is None:
        caption = ('FIG %s · graph · from <code>data_flow</code> — '
                   '<span style="color:%s;font-weight:700">▪ service</span> · '
                   '<span style="color:%s;font-weight:700">▪ datastore</span> · '
                   '<span style="color:%s;font-weight:700">▪ worker/queue</span> · '
                   'dashed node = external · '
                   '<span style="color:%s;font-weight:700">teal dashed edge = async</span>'
                   % (fig_no, INK2, L1, L2, FAST))
    if back:
        caption += ' · %d cạnh quay ngược chạy dưới các hàng' % len(back)
    return '<div class="plot">%s<p class="figcap">%s</p></div>' % ("".join(s), caption)


def within_budget(edges):
    """Is this flow still comfortable at natural size? It no longer decides which
    style to draw — there is only the graph — it decides whether to warn. A cycle
    is not part of the answer any more either: back-edges get drawn, not degraded.
    Measures the layout that actually ships, so the split matches svg_dag's."""
    if not edges:
        return True
    back_idx = feedback_arcs(edges)
    layer = layer_nodes([e for i, e in enumerate(edges) if i not in back_idx])
    if layer is None:
        return False
    for a, b, _asyn, _lbl in edges:
        for nd in (a, b):
            layer.setdefault(nd, 0)
    cols = {}
    for nd in layer:
        cols.setdefault(layer[nd], []).append(nd)
    return (len(layer) <= FLOW_MAX_NODES and len(edges) <= FLOW_MAX_EDGES
            and max(len(v) for v in cols.values()) <= FLOW_MAX_ROWS)


def edge_table(edges, here):
    """The complete, exact record of every edge — the figure shows the shape,
    this shows the words. Also the accessible reading of the figure, which is why
    it is printed with every graph rather than kept as a fallback."""
    rows = []
    for a, b, asyn, lbl in edges:
        rows.append('<tr><td class="mono">%s</td><td>%s</td><td class="mono">%s</td><td>%s</td></tr>'
                    % (esc(a),
                       ('<span class="tag lane-fast">async</span>' if asyn
                        else '<span class="dim">sync</span>'),
                       esc(b),
                       inline_md(lbl.strip(), here) if lbl and lbl.strip() else '<span class="dim">—</span>'))
    return ('<table class="data"><tr><th style="width:180px">from</th>'
            '<th style="width:90px">kind</th><th style="width:180px">to</th>'
            "<th>carries</th></tr>%s</table>" % "".join(rows))


# ---------------------------------------------------------------- business flows

SEQ_HEAD_RE = re.compile(r"^(title|trigger|outcome|code)\s*:\s*(.*)$", re.I)
SEQ_MAX_LANES = 8
SEQ_MAX_STEPS = 16


def parse_edge_line(line):
    """One line of the shared edge grammar → [(src, dst, async, label)], empty if
    the line carries no edge. `data_flow`, ```flow``` and ```flowchart``` all read
    their steps through here, so the three can never drift into three dialects."""
    if "->" not in line and "~>" not in line:
        return []
    label = ""
    if line.count("->") + line.count("~>") == 1 and ":" in line.split(">", 1)[-1]:
        line, label = line.rsplit(":", 1)
        label = label.strip()
    parts = EDGE_RE.split(line)
    if len(parts) < 3:
        return []
    nodes = [p.strip() for p in parts[0::2]]
    ops = parts[1::2]
    if any(not nd for nd in nodes):
        return []
    return [(nodes[k], nodes[k + 1], op == "~>", label if len(ops) == 1 else "")
            for k, op in enumerate(ops)]


def parse_sequence(src):
    """A ```flow fence: optional 'title/trigger/outcome/code' headers, then steps in
    the same edge grammar as data_flow. Returns (meta, steps) or None if no step
    parsed — a business flow reads as a scenario, so order is significant and the
    steps are kept exactly as written."""
    meta, steps = {}, []
    for raw in src.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = SEQ_HEAD_RE.match(line)
        if m:  # checked before the arrow test: a trigger may itself contain '->'
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        steps.extend(parse_edge_line(line))
    if not steps:
        return None
    return meta, steps


def svg_sequence(steps, comps):
    """Lifelines left to right, time down the page. Participants are ordered by
    first appearance, so the picture follows the story rather than the alphabet."""
    lanes = []
    for a, b, _x, _l in steps:
        for nd in (a, b):
            if nd not in lanes:
                lanes.append(nd)
    n = len(lanes)
    at = {nd: i for i, nd in enumerate(lanes)}

    lane_w = int(max(120, max(CHAR_W * len(nd) for nd in lanes) + 52))
    LEFT, HEAD_H, STEP_H = 30, 46, 46

    # Measure the labels before committing to a canvas: a step label is centred on
    # its arrow (or hangs right of a self-call) and can reach past the outermost
    # lifeline, so the canvas is padded to hold it rather than clipping it.
    over_l = over_r = 0.0
    for a, b, _asyn, lbl in steps:
        text = lbl.strip() if lbl else ""
        if not text:
            continue
        cw = chip_w_for(text)
        xa = LEFT + at[a] * lane_w + lane_w / 2.0
        xb = LEFT + at[b] * lane_w + lane_w / 2.0
        lo, hi = (xa + 40, xa + 40 + cw) if a == b else ((xa + xb) / 2.0 - cw / 2.0,
                                                         (xa + xb) / 2.0 + cw / 2.0)
        over_l = max(over_l, 4 - lo)
        over_r = max(over_r, hi - (LEFT + n * lane_w))
    LEFT += int(over_l)
    width = LEFT + n * lane_w + int(over_r) + 16
    height = HEAD_H + len(steps) * STEP_H + 30

    def lx(nd):
        return LEFT + at[nd] * lane_w + lane_w / 2.0

    s = [svg_size(width, height, "business flow sequence"), "<defs>",
         marker_def("seq-a", INK), marker_def("seq-t", FAST),
         symbol_defs(sorted({NODE_STYLE[kind_of(nd, comps)][4] for nd in lanes})), "</defs>"]

    for nd in lanes:
        x = lx(nd)
        border, dashed, badge_bg, icon_color, icon, label_fill = NODE_STYLE[kind_of(nd, comps)]
        bw = int(CHAR_W * len(nd) + 42)
        s.append('<rect x="%g" y="6" width="%d" height="30" rx="2" fill="#ffffff" stroke="%s" '
                 'stroke-width="1.5"%s/>'
                 % (x - bw / 2.0, bw, border, ' stroke-dasharray="5 4"' if dashed else ""))
        s.append('<rect x="%g" y="11" width="20" height="20" rx="4" fill="%s"/>'
                 % (x - bw / 2.0 + 5, badge_bg))
        s.append(use_icon(icon, x - bw / 2.0 + 8, 14, icon_color, 14))
        s.append(svg_text(x - bw / 2.0 + 31, 25, nd, 11, "650", label_fill))
        s.append('<path d="M%g %d V%d" stroke="%s" stroke-width="1" stroke-dasharray="3 4"/>'
                 % (x, HEAD_H - 6, height - 18, LINE2))

    for k, (a, b, asyn, lbl) in enumerate(steps):
        y = HEAD_H + k * STEP_H + 22
        color, mid = (FAST, "seq-t") if asyn else (INK, "seq-a")
        dash = ' stroke-dasharray="5 4" class="dashrun"' if asyn else ""
        s.append(svg_text(LEFT - 12, y + 4, str(k + 1), 10, "700", INK3, anchor="end"))
        x1, x2 = lx(a), lx(b)
        if a == b:  # a self-call: the component doing its own work, not a hop
            d = "M%g %g H%g V%g H%g" % (x1, y - 8, x1 + 34, y + 8, x1 + 4)
            s.append('<path d="%s" fill="none" stroke="%s" stroke-width="1.6"%s '
                     'marker-end="url(#%s)"/>' % (d, color, dash, mid))
            mx, my = x1 + 46, y + 4
            anchor = "start"
        else:
            back = x2 < x1
            xa = x1 + (-9 if back else 9)
            xb = x2 + (9 if back else -9)
            s.append('<path d="M%g %g H%g" fill="none" stroke="%s" stroke-width="1.6"%s '
                     'marker-end="url(#%s)"/>' % (xa, y, xb, color, dash, mid))
            if not asyn:
                s.append('<path d="M%g %g H%g" class="pkt"/>' % (xa, y, xb))
            mx, my = (x1 + x2) / 2.0, y - 8
            anchor = "middle"
        text = lbl.strip() if lbl else ""
        if text:
            cw = chip_w_for(text)
            # masked, so a long label reads cleanly where it crosses a lifeline
            s.append('<rect x="%g" y="%g" width="%g" height="15" rx="2" fill="%s" stroke="%s"/>'
                     % ((mx - cw / 2.0) if anchor == "middle" else mx - 6, my - 11, cw,
                        "#e6faf5" if asyn else "#ffffff", "#7fd4c4" if asyn else "#e2e8ee"))
            s.append(svg_text(mx, my, text, 9, "700" if asyn else "500",
                              FAST if asyn else INK2,
                              anchor=None if anchor == "start" else anchor, ls=".5"))
    s.append("</svg>")
    return "".join(s)


NIL = '<span class="nil">·</span>'


def band_row(name, gloss, cols, here):
    """The leading column of a table under a figure, printed once as a band instead
    of repeated on every row it owns. What was a column of the same word four to
    six times over becomes one heading with rows hanging off it."""
    return ('<tr class="band"><td colspan="%d"><code>%s</code>%s</td></tr>'
            % (cols, esc(name),
               ('<span class="gloss">%s</span>' % inline_md(gloss, here)) if gloss else ""))


def branch_table(edges, gloss, here, out_head, dead="không có cạnh đi ra"):
    """One table where a flowchart used to ship two.

    Under a chart there was a two-column list of branch points and a five-column
    list of edges, and between them they never answered the question a reader
    actually arrives with: at THIS branch point, how many ways out are there and
    where does each one go. Banding the edges by their source answers it — and
    answers it without dropping a row, so the table is still the figure's exact
    wording and its full accessible reading.

    A state machine is the same table with the same shape: the band is the source
    state and what it means, the rows under it are the transitions out of it. The
    `~>` kind stays, because in a lifecycle it says the move is made by a
    background job rather than by the user. `gloss` is what a source means — the
    question at a branch point, the meaning of a state."""
    order, groups = [], {}
    for k, (a, b, asyn, lbl) in enumerate(edges):
        if a not in groups:
            order.append(a)
            groups[a] = []
        groups[a].append((k + 1, b, asyn, lbl))
    rows = []
    for a in order + sorted(set(gloss) - set(groups), key=lambda s: s.lower()):
        rows.append(band_row(a, gloss.get(a, ""), 4, here))
        if a not in groups:
            # A final state has a meaning and no way out. Its meaning is worth a
            # line; inventing an edge for it is not.
            rows.append('<tr><td class="mono nil">·</td><td colspan="3">'
                        '<span class="dim">%s</span></td></tr>' % dead)
            continue
        for n, b, asyn, lbl in groups[a]:
            rows.append('<tr><td class="mono">%d</td><td class="zone">%s</td>'
                        '<td class="mono zone">→ %s</td><td>%s</td></tr>'
                        % (n, inline_md(lbl.strip(), here) if lbl and lbl.strip() else NIL,
                           esc(b),
                           '<span class="tag lane-fast">async</span>' if asyn
                           else '<span class="dim">sync</span>'))
    return ('<table class="data"><tr><th style="width:40px">#</th>'
            '<th class="zone" style="width:260px">%s</th>'
            '<th class="zone" style="width:200px">đi tới</th>'
            "<th>kiểu</th></tr>%s</table>" % (esc(out_head), "".join(rows)))


def seq_steps_table(steps, here, last_col="step"):
    """The exact words behind a figure. `last_col` is the only thing a state machine
    needs to change — its rows are transitions and its labels are events — so it
    reuses this rather than growing a second table function with identical columns.
    The kind column stays for it too: `~>` in a lifecycle means the move is made by
    a background job, not by the user."""
    rows = []
    for k, (a, b, asyn, lbl) in enumerate(steps):
        rows.append('<tr><td class="mono">%d</td><td class="mono">%s</td><td>%s</td>'
                    '<td class="mono">%s</td><td>%s</td></tr>'
                    % (k + 1, esc(a),
                       ('<span class="tag lane-fast">async</span>' if asyn
                        else '<span class="dim">sync</span>'), esc(b),
                       inline_md(lbl.strip(), here) if lbl and lbl.strip() else '<span class="dim">—</span>'))
    return ('<table class="data"><tr><th style="width:40px">#</th><th style="width:150px">from</th>'
            '<th style="width:90px">kind</th><th style="width:150px">to</th><th>%s</th></tr>%s</table>'
            % (esc(last_col), "".join(rows)))


FENCE_OPEN_RE = re.compile(r"^(\s{0,3})(`{3,})(.*)$")


def scan_fence(lines, i):
    """Fence starting at lines[i] → (info, body_lines, index_after). A fence closes
    only on a marker at least as long as its opener (CommonMark), so a ```flow
    example shown inside a ````markdown block is part of that block, not a flow."""
    m = FENCE_OPEN_RE.match(lines[i])
    fence, info = m.group(2), m.group(3).strip().lower()
    close = re.compile(r"^\s{0,3}`{%d,}\s*$" % len(fence))
    j, body = i + 1, []
    while j < len(lines) and not close.match(lines[j]):
        body.append(lines[j])
        j += 1
    return info, body, min(j + 1, len(lines))


# Every fence that renders as a figure. Adding a figure type is adding a name
# here plus its parser — the scan below never changes shape again.
FIGURE_FENCES = ("flow", "flowchart", "state", "erd", "class")


def extract_figures(md, names=FIGURE_FENCES):
    """Lift top-level figure fences out of a body, keeping every other fence in
    place. They get their own section on the sheet, so leaving them here would
    print each figure twice. Returns ({name: [source, ...]}, remaining_md)."""
    lines = md.split("\n")
    kept, blocks, i = [], dict((n, []) for n in names), 0
    while i < len(lines):
        if not FENCE_OPEN_RE.match(lines[i]):
            kept.append(lines[i])
            i += 1
            continue
        info, body, nxt = scan_fence(lines, i)
        if info in blocks:
            blocks[info].append("\n".join(body))
        else:
            kept.extend(lines[i:nxt])
        i = nxt
    return blocks, "\n".join(kept)


def seq_figure(src, comps, figs, here):
    parsed = parse_sequence(src)
    if parsed is None:
        return None
    meta, steps = parsed
    lanes = {nd for st in steps for nd in st[:2]}
    fig_no = figs.next() if figs is not None else "—"
    title = meta.get("title", "")

    head = []
    if meta.get("trigger"):
        head.append('<div class="seqline"><span class="lbl">Trigger</span>%s</div>'
                    % inline_md(meta["trigger"], here))
    if meta.get("code"):
        head.append('<div class="seqline"><span class="lbl">Code</span><code>%s</code></div>'
                    % esc(meta["code"]))
    foot = ('<div class="seqline out"><span class="lbl">Outcome</span>%s</div>'
            % inline_md(meta["outcome"], here)) if meta.get("outcome") else ""

    # Past the budget a sequence stops being a picture and becomes a wall of
    # arrows; the numbered steps say the same thing and stay readable.
    if len(lanes) > SEQ_MAX_LANES or len(steps) > SEQ_MAX_STEPS:
        body = seq_steps_table(steps, here)
        style = "steps"
    else:
        body = svg_sequence(steps, comps)
        style = "sequence"

    caption = ("FIG %s · %s · %s%d step%s across %d participant%s"
               % (fig_no, style,
                  (esc(title) + " — ") if title else "",
                  len(steps), "" if len(steps) == 1 else "s",
                  len(lanes), "" if len(lanes) == 1 else "s"))
    return ('<div class="plot flowfig">%s%s%s<p class="figcap">%s</p></div>'
            % ("".join(head), body, foot, caption))


# ---------------------------------------------------------------- business logic

DECIDE_RE = re.compile(r"^decide\s*:\s*(.+)$", re.I)
TERMINAL_NAMES = ("start", "end")
DECL_SEPS = (" — ", " – ", " -- ")


def split_decl(body):
    """`<name> — <gloss>` → (name, gloss), gloss possibly empty. One helper, so
    `decide:` and `state:` cannot drift into two ideas of what separates a node
    name from the sentence explaining it."""
    for sep in DECL_SEPS:
        if sep in body:
            name, gloss = body.split(sep, 1)
            return name.strip(), gloss.strip()
    return body.strip(), ""



CHART_MAX_NODES = 20
CHART_MAX_EDGES = 28
CHART_MAX_DECIDES = 8


def parse_flowchart(src):
    """A ```flowchart fence: the ```flow headers, plus `decide:` lines naming the
    branch points, plus steps in the shared edge grammar. Returns
    (meta, questions, shapes, edges) or None when no edge parsed.

    A branch is an ordinary labelled edge out of a decide node — there is no
    separate branch syntax, because an indented one would be a third dialect in
    the same docs tree, and because edge labels already get placed in the gap
    after their source column without landing on anything."""
    meta, questions, edges = {}, {}, []
    for raw in src.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = SEQ_HEAD_RE.match(line)
        if m:  # before the arrow test: a trigger may itself contain '->'
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        m = DECIDE_RE.match(line)
        if m:
            name, question = split_decl(m.group(1).strip())
            if name:
                questions[name] = question
            continue
        edges.extend(parse_edge_line(line))
    if not edges:
        return None
    shapes = {}
    for a, b, _asyn, _lbl in edges:
        for nd in (a, b):
            # A terminal's own name says which end it is, and the two ends are not
            # the same thing — one is where you come in — so they are not one shape.
            shapes[nd] = ("decide" if nd in questions
                          else nd.lower() if nd.lower() in TERMINAL_NAMES else "step")
    return meta, questions, shapes, edges


def flowchart_figure(src, comps, figs, here):
    parsed = parse_flowchart(src)
    if parsed is None:
        return None
    meta, questions, shapes, edges = parsed
    nodes = {nd for e in edges for nd in e[:2]}
    fig_no = figs.next() if figs is not None else "—"
    title = meta.get("title", "")

    head = []
    if meta.get("trigger"):
        head.append('<div class="seqline"><span class="lbl">Trigger</span>%s</div>'
                    % inline_md(meta["trigger"], here))
    if meta.get("code"):
        head.append('<div class="seqline"><span class="lbl">Code</span><code>%s</code></div>'
                    % esc(meta["code"]))
    foot = ('<div class="seqline out"><span class="lbl">Outcome</span>%s</div>'
            % inline_md(meta["outcome"], here)) if meta.get("outcome") else ""

    svg = svg_dag(edges, comps, fig_no, shapes=shapes,
                  aria="business logic flowchart", wrap=False)
    if svg is None:
        return None
    caption = ('FIG %s · flowchart · %s'
               '<span style="color:%s;font-weight:700">◇ điểm rẽ</span> · ▭ bước · '
               '⬭ đầu/cuối · nhãn trên cạnh ra từ ◇ là tên nhánh'
               % (fig_no, (esc(title) + " — ") if title else "", L1))
    loops = len(feedback_arcs(edges))
    if loops:
        caption += ' · %d vòng lặp chạy dưới các hàng' % loops

    note = ""
    if (len(nodes) > CHART_MAX_NODES or len(edges) > CHART_MAX_EDGES
            or len(questions) > CHART_MAX_DECIDES):
        note = ('<div class="note"><span class="lbl">Dense</span>%d node · %d cạnh · %d điểm rẽ '
                "— quá ngưỡng đọc thoải mái (%d · %d · %d). Hình vẫn vẽ đủ và cuộn ngang; "
                "nếu khó theo dõi thì tách quy tắc này thành nhiều flowchart nhỏ.</div>"
                % (len(nodes), len(edges), len(questions),
                   CHART_MAX_NODES, CHART_MAX_EDGES, CHART_MAX_DECIDES))
    # One decision table, banded by source. It ships with every chart, not as a
    # rescue: it is the exact wording, the copyable record, and the figure's
    # accessible reading — and now also the answer to "how many ways out of here".
    tables = branch_table(edges, questions, here, "nhánh / bước")
    return (note + '<div class="plot flowfig">%s%s%s<p class="figcap">%s</p></div>'
            % ("".join(head), svg, foot, caption) + tables)


# ---------------------------------------------------------------- state machines

STATE_HEAD_RE = re.compile(r"^(title|entity|code|initial|final)\s*:\s*(.*)$", re.I)
STATE_DECL_RE = re.compile(r"^state\s*:\s*(.+)$", re.I)
# Lower than the flowchart's 20 · 28 on purpose: a flowchart legitimately runs to
# many steps, but a lifecycle with a dozen states is nearly always two machines
# composed, and splitting them reads better than drawing them at once.
STATE_MAX_STATES = 12
STATE_MAX_TRANSITIONS = 24


def parse_state_machine(src):
    """A ```state fence: `initial:` / `final:` naming REAL states, optional `state:`
    declarations, and transitions in the shared edge grammar. Returns
    (meta, marks, meanings, shapes, edges) or None when no transition parsed.

    initial/final mark real states instead of adding start/end pseudo-nodes: a
    six-state machine has to show six boxes, and an `end` sink would need a
    fabricated edge out of every terminal state, inflating the figure and the
    transition table alike. There is no guard syntax either — a condition worth
    drawing deserves a ```flowchart next to it, which is what §5 is for."""
    meta, meanings, edges = {}, {}, []
    for raw in src.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = STATE_DECL_RE.match(line)
        if m:
            name, meaning = split_decl(m.group(1).strip())
            if name:
                meanings[name] = meaning
            continue
        m = STATE_HEAD_RE.match(line)
        if m:  # before the arrow test: a title may itself contain '->'
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        edges.extend(parse_edge_line(line))
    if not edges:
        return None
    names = lambda key: [s.strip() for s in meta.get(key, "").split(",") if s.strip()]
    inits, finals = names("initial"), names("final")
    # A machine has one start. Naming more is a mistake worth showing rather than
    # guessing at, so the extras travel to the caller and end up in a note.
    marks = {"initial": inits[0] if inits else "",
             "extra_initial": inits[1:], "final": finals}
    shapes = {}
    for a, b, _asyn, _lbl in edges:
        for nd in (a, b):
            shapes[nd] = "final" if nd in finals else "state"
    return meta, marks, meanings, shapes, edges


def code_list(items):
    return ", ".join("<code>%s</code>" % esc(s) for s in items)


def state_figure(src, comps, figs, here):
    parsed = parse_state_machine(src)
    if parsed is None:
        return None
    meta, marks, meanings, shapes, edges = parsed
    states = {nd for e in edges for nd in e[:2]}
    fig_no = figs.next() if figs is not None else "—"
    title = meta.get("title", "")

    head = []
    if meta.get("entity"):
        head.append('<div class="seqline"><span class="lbl">Entity</span><code>%s</code></div>'
                    % esc(meta["entity"]))
    if meta.get("code"):
        head.append('<div class="seqline"><span class="lbl">Code</span><code>%s</code></div>'
                    % esc(meta["code"]))

    svg = svg_dag(edges, comps, fig_no, shapes=shapes, aria="entity state machine",
                  wrap=False, initial=marks["initial"])
    if svg is None:
        return None
    caption = ('FIG %s · state · %s'
               '<span style="color:%s;font-weight:700">▢ viền xanh = bắt đầu</span> · '
               '▣ viền đôi = kết thúc · nhãn cạnh là sự kiện'
               % (fig_no, (esc(title) + " — ") if title else "", L1))
    # A lifecycle loops by nature — a refund goes back, a retry comes round again.
    # The lanes under the rows come from the graph engine, not from anything here.
    loops = len(feedback_arcs(edges))
    if loops:
        caption += ' · %d transition quay ngược chạy dưới các hàng' % loops

    notes = []
    if len(states) > STATE_MAX_STATES or len(edges) > STATE_MAX_TRANSITIONS:
        notes.append('<div class="note"><span class="lbl">Dense</span>%d trạng thái · %d transition '
                     "— quá ngưỡng đọc thoải mái (%d · %d). Hình vẫn vẽ đủ và cuộn ngang; "
                     "nếu khó theo dõi thì tách thành nhiều máy trạng thái nhỏ hơn.</div>"
                     % (len(states), len(edges), STATE_MAX_STATES, STATE_MAX_TRANSITIONS))
    # Declaring one state opts the file into the typo check. It is worth having at
    # all because a mistyped state reads as plausible: a stray box in a flowchart
    # catches the eye, `shiped` sitting in a lifecycle does not.
    if meanings:
        missing = sorted(states - set(meanings), key=lambda s: s.lower())
        if missing:
            notes.append('<div class="note"><span class="lbl">Undeclared</span>%d trạng thái xuất '
                         "hiện trong transition nhưng chưa khai báo: %s. Thêm dòng "
                         "<code>state: &lt;tên&gt; — &lt;nghĩa&gt;</code>, hoặc kiểm tra lại "
                         "chính tả.</div>" % (len(missing), code_list(missing)))
    msgs = []
    if marks["extra_initial"]:
        msgs.append("<code>initial:</code> chỉ nhận một trạng thái — đang bỏ qua %s."
                    % code_list(marks["extra_initial"]))
    named = ([marks["initial"]] if marks["initial"] else []) + marks["final"]
    unknown = sorted({s for s in named if s not in states}, key=lambda s: s.lower())
    if unknown:
        # Not drawn as a lone box: svg_dag lays out edges, so an unreachable state
        # would need a fabricated transition, and a box nothing points at says
        # nothing about how you reach it. Naming it in a note is the honest fix.
        msgs.append("%s khai báo ở <code>initial:</code>/<code>final:</code> nhưng không xuất "
                    "hiện trong transition nào — kiểm tra lại chính tả." % code_list(unknown))
    if msgs:
        notes.append('<div class="note"><span class="lbl">Marks</span>%s</div>' % " ".join(msgs))

    tables = branch_table(edges, meanings, here, "sự kiện",
                          dead="trạng thái kết thúc — không có transition đi ra")
    return ("".join(notes) + '<div class="plot flowfig">%s%s<p class="figcap">%s</p></div>'
            % ("".join(head), svg, caption) + tables)


# ---------------------------------------------------------------- data model (ERD)

ERD_HEAD_RE = re.compile(r"^(title|code)\s*:\s*(.*)$", re.I)
ERD_TABLE_RE = re.compile(r"^table\s*:\s*(.+)$", re.I)
ERD_FK_RE = re.compile(r"\bfk\s*->\s*([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)", re.I)
ERD_FLAGS = ("pk", "unique", "null")
ERD_MAX_TABLES = 10
ERD_MAX_COLUMNS = 15   # in any one table


def erd_marker_defs():
    """Crow's-foot notation, in four variants because a marker at the start of a
    path and a marker at its end need different refX. `svg_dag` does not know any
    of this exists — it places markers by id, and this is where they are defined."""
    w, w15 = MARKER_W, MARKER_W * 1.5
    return (
        # child end: three toes at the box, converging into the line
        '<marker id="erd-many" viewBox="0 0 12 12" refX="0" refY="6" markerWidth="%g" '
        'markerHeight="%g" orient="auto"><path d="M0 6 H11 M0 1 L11 6 M0 11 L11 6" '
        'fill="none" stroke="%s" stroke-width="1.3"/></marker>'
        # child end, 1:1: one bar instead of the toes
        '<marker id="erd-one-s" viewBox="0 0 12 12" refX="0" refY="6" markerWidth="%g" '
        'markerHeight="%g" orient="auto"><path d="M0 6 H12 M4 1 V11" fill="none" '
        'stroke="%s" stroke-width="1.3"/></marker>'
        # parent end: exactly one
        '<marker id="erd-one-e" viewBox="0 0 12 12" refX="12" refY="6" markerWidth="%g" '
        'markerHeight="%g" orient="auto"><path d="M0 6 H12 M8 1 V11" fill="none" '
        'stroke="%s" stroke-width="1.3"/></marker>'
        # parent end, nullable: zero or one — the ring sits outside the bar. Its
        # viewBox is 18 wide against the others' 12, so it takes 1.5x the width to
        # come out at the same scale — the ring is extra length, not extra size.
        '<marker id="erd-zero-one" viewBox="0 0 18 12" refX="18" refY="6" markerWidth="%g" '
        'markerHeight="%g" orient="auto"><path d="M0 6 H18 M14 1 V11" fill="none" '
        'stroke="%s" stroke-width="1.3"/><circle cx="7" cy="6" r="2.6" fill="#ffffff" '
        'stroke="%s" stroke-width="1.3"/></marker>'
        % (w, w, INK, w, w, INK, w, w, INK, w15, w, INK, INK))


def parse_erd(src):
    """An ```erd fence: `table:` opens an entity and every following line is one of
    its columns. Returns (meta, order, tables, edges, marks) or None when no table
    parsed.

    There is no relationship syntax, deliberately. An `fk -> t.c` flag IS the
    relationship, and its cardinality follows from what a foreign key means — many
    child rows point at one parent row — so nothing is written twice and the
    picture cannot disagree with the column list beside it."""
    meta, tables, order, cur = {}, {}, [], None
    for raw in src.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = ERD_TABLE_RE.match(line)
        if m:
            cur = m.group(1).strip()
            if cur and cur not in tables:
                tables[cur] = []
                order.append(cur)
            continue
        m = ERD_HEAD_RE.match(line)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        if cur is None:
            continue          # a column before any table: has nowhere to live
        body, gloss = split_decl(line)
        ref = None
        m = ERD_FK_RE.search(body)
        if m:
            # Lift the fk clause out first — what is left is name, type and flags,
            # none of which can then be confused with the target it points at.
            ref = (m.group(1), m.group(2))
            body = body[:m.start()] + body[m.end():]
        parts = body.split()
        if not parts:
            continue
        cname, tags, ctype = parts[0], (["fk"] if ref else []), ""
        for tok in parts[1:]:
            if tok.lower() in ERD_FLAGS:
                tags.append(tok.lower())
            elif not ctype:
                ctype = tok
        tables[cur].append((cname, ctype, tuple(sorted(set(tags))), gloss, ref))
    if not order:
        return None
    # Table order, then column order — deterministic without a sort, and it keeps
    # the edge list reading the way the schema was written.
    edges, marks, anchor = [], {}, {}
    for t in order:
        for ri, row in enumerate(tables[t]):
            if row[4] is None:
                continue
            marks[len(edges)] = ("erd-one-s" if "unique" in row[2] else "erd-many",
                                 "erd-zero-one" if "null" in row[2] else "erd-one-e")
            # The relation leaves the foreign key's OWN column and lands on the
            # column it names. Both ends are rows the reader can see, which is the
            # whole difference between a picture of some boxes and a picture of a
            # schema: you can follow a key with your eye. A parent this block never
            # declared has no rows, so that end falls back to the header band.
            pt, pc = row[4]
            trow = next((j for j, prow in enumerate(tables.get(pt, []))
                         if prow[0] == pc), None)
            anchor[len(edges)] = (ri, trow)
            edges.append((t, row[4][0], False, ""))
    return meta, order, tables, edges, marks, anchor


def erd_columns_table(order, tables, here):
    rows = []
    for t in order:
        rows.append(band_row(t, "", 5, here))
        for cname, ctype, tags, gloss, ref in tables[t]:
            # `fk` belongs in the key column with the other key facts. It used to be
            # filtered out here and left implied by an arrow two columns further
            # right, which meant the column headed "khoá" was not the answer to
            # "what kind of key is this".
            keys = " ".join('<span class="tag">%s</span>' % k for k in tags) or NIL
            rel = ('→ <code>%s.%s</code>' % (esc(ref[0]), esc(ref[1]))) if ref else NIL
            rows.append('<tr><td class="mono zone">%s</td>'
                        '<td class="mono">%s</td><td>%s</td><td class="zone">%s</td>'
                        '<td>%s</td></tr>'
                        % (esc(cname), esc(ctype) if ctype else NIL, keys, rel,
                           inline_md(gloss, here) if gloss else NIL))
    return ('<table class="data"><tr><th class="zone" style="width:170px">cột</th>'
            '<th style="width:120px">kiểu</th><th style="width:130px">khoá</th>'
            '<th class="zone" style="width:180px">quan hệ</th>'
            "<th>ghi chú</th></tr>%s</table>" % "".join(rows))


def erd_figure(src, comps, figs, here):
    parsed = parse_erd(src)
    if parsed is None:
        return None
    meta, order, tables, edges, marks, anchor = parsed
    # Only a drawn figure spends a figure number, so a schema with no foreign key
    # does not leave a gap in the numbering of the sheet.
    fig_no = figs.next() if (edges and figs is not None) else "—"
    title = meta.get("title", "")

    head = []
    if meta.get("code"):
        head.append('<div class="seqline"><span class="lbl">Code</span><code>%s</code></div>'
                    % esc(meta["code"]))

    # An fk may point at a table this block never declared. Draw it anyway — the
    # relationship is real — as an empty box, and say so in a note.
    unknown = sorted({p for _c, p, _a, _l in edges if p not in tables},
                     key=lambda s: s.lower())
    rows_map = dict((t, tables[t]) for t in order)
    for t in unknown:
        rows_map[t] = []

    # No foreign key means no graph to lay out — svg_dag places boxes by their
    # edges, and a picture of unconnected boxes says nothing the table does not.
    svg = svg_dag(edges, comps, fig_no, aria="entity relationship diagram",
                  wrap=False, entity_rows=rows_map, marks=marks,
                  route="struct", anchor=anchor,
                  defs=erd_marker_defs()) if edges else None
    if edges and svg is None:
        return None

    caption = ('FIG %s · erd · %s%d bảng · %d quan hệ — '
               '<span style="color:%s;font-weight:700">▮ pk</span> · '
               'chân quạ = nhiều · gạch đơn = đúng một · ○ = không bắt buộc'
               % (fig_no, (esc(title) + " — ") if title else "",
                  len(order), len(edges), L1))
    loops = len(feedback_arcs(edges)) if edges else 0
    if loops:
        caption += ' · %d quan hệ tự trỏ chạy dưới các hàng' % loops

    notes = []
    widest = max([len(v) for v in tables.values()] or [0])
    if len(order) > ERD_MAX_TABLES or widest > ERD_MAX_COLUMNS:
        notes.append('<div class="note"><span class="lbl">Dense</span>%d bảng · bảng rộng nhất '
                     "%d cột — quá ngưỡng đọc thoải mái (%d · %d). Hình vẫn vẽ đủ và cuộn "
                     "ngang; nếu khó theo dõi thì tách lược đồ này theo bounded context.</div>"
                     % (len(order), widest, ERD_MAX_TABLES, ERD_MAX_COLUMNS))
    if unknown:
        notes.append('<div class="note"><span class="lbl">Unknown</span>%d bảng được fk trỏ tới '
                     "nhưng không khai báo trong khối này: %s. Vẽ thành hộp rỗng — thêm "
                     "<code>table:</code> cho nó, hoặc kiểm tra lại chính tả.</div>"
                     % (len(unknown), code_list(unknown)))

    body = ('<div class="plot flowfig">%s%s<p class="figcap">%s</p></div>'
            % ("".join(head), svg, caption)) if svg else ""
    return "".join(notes) + body + erd_columns_table(order, tables, here)


# ---------------------------------------------------------------- types (class)

CLASS_HEAD_RE = re.compile(r"^(title|code)\s*:\s*(.*)$", re.I)
CLASS_OPEN_RE = re.compile(r"^(class|interface)\s*:\s*(.+)$", re.I)
CLASS_REL_RE = re.compile(r"^(extends|implements)\s+([A-Za-z0-9_.]+)$", re.I)
CLASS_MAX_TYPES = 12
CLASS_MAX_MEMBERS = 15   # in any one type


def class_marker_defs():
    """One hollow triangle, used by both extends and implements — the line style
    is what tells them apart, exactly as UML has it. `svg_dag` never learns what
    this shape means; it places it by id."""
    return ('<marker id="cls-tri" viewBox="0 0 12 12" refX="12" refY="6" '
            'markerWidth="%g" markerHeight="%g" orient="auto">'
            '<path d="M0 1 L12 6 L0 11 Z" fill="#ffffff" stroke="%s" '
            'stroke-width="1.3"/></marker>' % (MARKER_W, MARKER_W, INK))


def short_sig(sig):
    """`(orderID string, cents int64) (Receipt, error)` → `(…)`.

    In the figure a method is a NAME. The full signature already has a column of
    its own in the table underneath, and printing it in the box made the same 46
    characters appear six times — once in the interface and once in each
    implementer, because an implementer repeats the contract verbatim. That is
    what drove every box to 467px and the canvas to 1012, past CONTENT_W, so the
    right-hand column came out clipped. A method that genuinely takes nothing
    keeps its empty parens rather than claiming arguments it does not have.
    Fields are untouched: a field's type is short, and it is the whole point."""
    return "()" if sig.replace(" ", "").startswith("()") else "(…)"


def bare_type(sig):
    """`*Foo`, `[]Foo`, `...Foo`, `map[string]Foo` → `Foo`. Anything qualified —
    `*http.Client` — keeps its dot and therefore matches no declared type, which
    is the point: a type from another package is not in this picture."""
    t = sig.strip()
    if t.startswith("map[") and "]" in t:
        t = t[t.index("]") + 1:]
    return t.lstrip("*[]. ").replace("[]", "").strip()


def parse_class(src):
    """A ```class fence: `class:` / `interface:` open a type, `extends` and
    `implements` are relation lines inside it, everything else is a member.
    Returns (meta, order, types, edges, marks) or None when no type parsed.

    A member whose type names another declared type draws an association, for the
    same reason `fk` draws an ERD relationship — one source per fact. Method
    signatures are deliberately NOT scanned: a signature naming every type in the
    package would draw a graph nobody can read."""
    meta, types, order, cur = {}, {}, [], None
    for raw in src.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = CLASS_OPEN_RE.match(line)
        if m:
            cur = m.group(2).strip()
            if cur and cur not in types:
                types[cur] = {"kind": m.group(1).lower(), "fields": [], "methods": [],
                              "rel": []}
                order.append(cur)
            continue
        m = CLASS_HEAD_RE.match(line)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        if cur is None:
            continue          # a member before any type: has nowhere to live
        m = CLASS_REL_RE.match(line)
        if m:
            types[cur]["rel"].append((m.group(1).lower(), m.group(2)))
            continue
        body, gloss = split_decl(line)
        vis = ""
        if body[:1] in ("+", "-"):
            vis, body = body[0], body[1:].strip()
        if "(" in body:
            # A method splits at its opening paren, not at whitespace: a signature
            # has spaces inside it, and splitting on the first one yields the
            # nonsense `Capture(orderID` / `string, cents int64) (Receipt, error)`.
            cut = body.index("(")
            name, sig = body[:cut].strip(), body[cut:].strip()
            bucket = "methods"
        else:
            parts = body.split(None, 1)
            if not parts:
                continue
            name, sig = parts[0], (parts[1].strip() if len(parts) > 1 else "")
            bucket = "fields"
        if not name:
            continue
        types[cur][bucket].append((vis, name, sig, gloss))
    if not order:
        return None

    edges, marks, dashed, anchor, seen = [], {}, set(), {}, set()

    def add(src_t, dst_t, kind, srow=None):
        if (src_t, dst_t, kind) in seen:
            return
        seen.add((src_t, dst_t, kind))
        marks[len(edges)] = (None, "cls-tri" if kind != "assoc" else "dag-a")
        # `extends` and `implements` belong to the TYPE, so they leave the header
        # band; an association exists because one field holds that type, so it
        # leaves that field's own row. Both land on the target's header band — a
        # relation points at a type, never at one of its members.
        anchor[len(edges)] = (srow, None)
        if kind == "implements":
            dashed.add(len(edges))
        edges.append((src_t, dst_t, False, ""))

    for t in order:
        for kind, target in types[t]["rel"]:
            add(t, target, kind)
        for fi, (_vis, _name, sig, _gloss) in enumerate(types[t]["fields"]):
            target = bare_type(sig)
            # An association is emitted once per pair: three fields of one type
            # would otherwise draw three parallel edges saying the same thing. The
            # first such field is the one the line comes out of.
            if target and target != t and target in types:
                add(t, target, "assoc", fi)
    return meta, order, types, edges, marks, dashed, anchor


def class_members_table(order, types, here):
    rows = []
    for t in order:
        spec = types[t]
        rows.append(band_row(t, "«interface»" if spec["kind"] == "interface" else "",
                             5, here))
        for bucket, label in (("fields", "field"), ("methods", "method")):
            for vis, name, sig, gloss in spec[bucket]:
                shown = {"+": "public", "-": "private"}.get(vis, "")
                # This is where the full signature lives, and why the figure is free
                # to draw a method as `name(…)` — nothing is lost from the page.
                rows.append('<tr><td class="mono zone">%s</td><td>%s</td>'
                            '<td>%s</td><td class="mono zone">%s</td><td>%s</td></tr>'
                            % (esc(name), label, shown or NIL,
                               esc(sig) if sig else NIL,
                               inline_md(gloss, here) if gloss else NIL))
    return ('<table class="data"><tr><th class="zone" style="width:190px">thành viên</th>'
            '<th style="width:80px">loại</th><th style="width:90px">hiển thị</th>'
            '<th class="zone" style="width:250px">kiểu / chữ ký</th>'
            "<th>ghi chú</th></tr>%s</table>" % "".join(rows))


def class_figure(src, comps, figs, here):
    parsed = parse_class(src)
    if parsed is None:
        return None
    meta, order, types, edges, marks, dashed, anchor = parsed
    fig_no = figs.next() if (edges and figs is not None) else "—"
    title = meta.get("title", "")

    head = []
    if meta.get("code"):
        head.append('<div class="seqline"><span class="lbl">Code</span><code>%s</code></div>'
                    % esc(meta["code"]))

    # A relation may name a type this block never declared. Draw it anyway — the
    # relation is real — as an empty box, and say so in a note.
    unknown = sorted({d for _s, d, _a, _l in edges if d not in types},
                     key=lambda s: s.lower())
    rows_map, tag_map = {}, {}
    for t in order + unknown:
        spec = types.get(t)
        rows = []
        if spec:
            rows = [(n, sig, ("private",) if v == "-" else ("public",) if v == "+" else ())
                    for v, n, sig, _g in spec["fields"]]
            for k, (v, n, sig, _g) in enumerate(spec["methods"]):
                tags = ("private",) if v == "-" else ("public",) if v == "+" else ()
                # The first method carries the separator, so the two compartments
                # cost one tag rather than a second kind of node.
                rows.append((n + short_sig(sig), "",
                             (tags + ("sep",)) if (k == 0 and spec["fields"])
                             else tags))
        rows_map[t] = rows
        if spec and spec["kind"] == "interface":
            tag_map[t] = "«interface»"

    svg = svg_dag(edges, comps, fig_no, aria="class diagram", wrap=False,
                  entity_rows=rows_map, entity_tag=tag_map, marks=marks,
                  dashed=dashed, route="struct", anchor=anchor,
                  defs=class_marker_defs()) if edges else None
    if edges and svg is None:
        return None

    caption = ('FIG %s · class · %s%d type · %d quan hệ — '
               '<span style="color:%s;font-weight:700">«interface»</span> · '
               'tam giác rỗng = implements/extends · nét đứt = implements · '
               'mũi tên thường = tham chiếu qua field'
               % (fig_no, (esc(title) + " — ") if title else "",
                  len(order), len(edges), L1))
    loops = len(feedback_arcs(edges)) if edges else 0
    if loops:
        caption += ' · %d quan hệ quay ngược chạy dưới các hàng' % loops

    notes = []
    widest = max([len(v["fields"]) + len(v["methods"]) for v in types.values()] or [0])
    if len(order) > CLASS_MAX_TYPES or widest > CLASS_MAX_MEMBERS:
        notes.append('<div class="note"><span class="lbl">Dense</span>%d type · type nhiều '
                     "thành viên nhất %d — quá ngưỡng đọc thoải mái (%d · %d). Hình vẫn vẽ "
                     "đủ và cuộn ngang; nếu khó theo dõi thì tách theo package.</div>"
                     % (len(order), widest, CLASS_MAX_TYPES, CLASS_MAX_MEMBERS))
    if unknown:
        notes.append('<div class="note"><span class="lbl">Unknown</span>%d type được nhắc '
                     "trong extends/implements nhưng không khai báo trong khối này: %s. Vẽ "
                     "thành hộp rỗng — thêm <code>class:</code> hoặc <code>interface:</code> "
                     "cho nó, hoặc kiểm tra lại chính tả.</div>"
                     % (len(unknown), code_list(unknown)))

    body = ('<div class="plot flowfig">%s%s<p class="figcap">%s</p></div>'
            % ("".join(head), svg, caption)) if svg else ""
    return "".join(notes) + body + class_members_table(order, types, here)


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
/* A table under a figure had six columns, horizontal rules only, and the leading
   name repeated four to six times down the page. Nothing held a column together
   for the eye. Three devices fix it without dropping a row — the table is still
   the figure's full reading. (1) The repeated name becomes a band, printed once.
   (2) Two vertical hairlines cut the row into what it IS, what it is SPECIFIED as,
   and what it MEANS. (3) An empty cell becomes a faint dot instead of an em-dash,
   so it stops competing with real text — about 40% of the cells were dashes. */
table.data td.zone, table.data th.zone { border-right: 1px solid var(--line); padding-right: 14px; }
table.data tr.band td { padding: 17px 12px 5px 0; border-bottom: 1.5px solid var(--line-2); color: var(--ink); }
table.data tr:first-child + tr.band td { padding-top: 6px; }  /* the band right under the header needs no air above it */
table.data tr.band:hover td { background: none; }
table.data tr.band code { font-size: 12.5px; font-weight: 700; background: none; border: 0; padding: 0; color: var(--ink); }
table.data tr.band .gloss { margin-left: 12px; font: 400 12.5px var(--sans); color: var(--ink-3); }
table.data .nil { color: var(--line-2); }
table.data tr.band + tr td { padding-top: 8px; }
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
.comps { display: grid; grid-template-columns: repeat(auto-fill, minmax(288px, 1fr)); gap: 12px; margin: 14px 0; }
.comp { border: 1px solid var(--line); border-radius: var(--r); padding: 11px 13px 9px; background: var(--paper); scroll-margin-top: 74px; }
.comp:target { border-color: var(--mark-2); box-shadow: inset 3px 0 0 var(--mark-2); }
.comp .cn { font: 650 13px var(--mono); color: var(--ink); display: flex; align-items: center; gap: 9px; }
.comp .cn .nm { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.comp .cn .kd { flex: none; font: 650 9.5px var(--mono); letter-spacing: .09em; text-transform: uppercase; color: var(--ink-3); border: 1px solid var(--line); border-radius: var(--r); padding: 1px 5px; }
.comp .cn .kd.k-db { color: var(--l1-deep); border-color: var(--l1-edge); background: var(--l1-wash); }
.comp .cn .kd.k-queue { color: var(--l2-deep); border-color: var(--l2-edge); background: var(--l2-wash); }
.comp .cr { font-size: 12.5px; color: var(--ink-2); margin-top: 6px; line-height: 1.5; }
table.spec.tight { margin-top: 9px; font-size: 12px; }
table.spec.tight th { width: 62px; padding: 5px 10px 5px 0; font-size: 9.5px; }
table.spec.tight td { padding: 5px 0; }
table.spec.tight td code { font-size: 11.5px; }
.tag.cref { padding: 0 6px; font-size: 10.5px; margin: 0 4px 3px 0; text-decoration: none; }
.seqline { display: flex; align-items: baseline; gap: 10px; font-size: 13px; color: var(--ink-2); padding: 0 0 12px; }
.seqline.out { padding: 12px 0 0; border-top: 1px dashed var(--line-2); margin-top: 4px; }
.seqline .lbl { flex: none; font: 700 9.5px var(--mono); letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3); }
.seqline.out .lbl { color: var(--l1); }
.plot.flowfig { background-image: none; background: var(--paper); }
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


def lane_tag(lane):
    if lane == "fast":
        return '<span class="tag lane-fast">fast</span>'
    if lane == "full":
        return '<span class="tag lane-full">full</span>'
    return ""


def slugify(text, seen=None):
    """Anchor slug built from a file name.

    File names are supposed to stay ASCII (STANDARD §11) — only the title is
    translated — so the diacritic folding here is a safety net, not the normal
    path. It matters because nothing enforces that rule: a plain [^a-z0-9]
    filter drops every diacritic-bearing letter outright, so 'phân-quyền' and
    'phần-quyền' would both collapse to 'ph-n-quy-n' — two products, one HTML
    id, and a sidebar link that jumps to the wrong card. Decomposing to NFD and
    dropping the combining marks keeps the base letters instead. 'đ' has no
    decomposition, so it is mapped by hand.

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


KIND_LABEL = {"svc": "service", "db": "datastore", "queue": "worker/queue",
              "ui": "interface", "ext": "external"}


def comp_slug(name):
    return "c-" + slugify(name)


def comp_ref(name):
    """A component chip that jumps to that component's own card."""
    return '<a class="tag cref" href="#%s">%s</a>' % (comp_slug(name), esc(name))


def body_sections(md, names):
    """Pull the '### <name>' body section for each named component. STANDARD §4
    already says the detail belongs in the body; this is what puts it on the card
    instead of leaving it somewhere nobody scrolls to."""
    want = {}
    for n in names:
        want[str(n).strip().lower()] = str(n).strip()
    out, cur, buf = {}, None, []
    for line in md.split("\n"):
        m = re.match(r"^(#{2,4})\s+(.*)$", line.strip())
        if m:
            if cur:
                out[cur] = "\n".join(buf).strip()
            cur = want.get(m.group(2).strip().strip("`").lower())
            buf = []
            continue
        if cur is not None:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


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
        "logic": load("03_business-logic"),
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
    figs = FigCounter()
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
    arch_figs, arch_body = extract_figures(arch_body)
    arch_flows, arch_charts = arch_figs["flow"], arch_figs["flowchart"]
    # (source label, anchor, blocks) — business flows collected from every Layer-1
    # doc and shown together, so they read as a set instead of one per card.
    flow_src, chart_src, state_src = [], [], []
    # Parsed once: the rail needs the count before the section needs the blocks.
    logic_figs = [(fm_str(d, "domain") or doc_title(d), extract_figures(d["body"])[0])
                  for d in data["logic"]]
    logic_charts = sum(len(f["flowchart"]) for _label, f in logic_figs)
    logic_states = sum(len(f["state"]) for _label, f in logic_figs)
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
            '<div class="trk"></div>'
            '<div class="st"><span class="c"></span><a href="#logic">Business logic</a><small>%s</small></div>'
            '<div class="trk"></div>'
            '<div class="st"><span class="c"></span><a href="#states">State machines</a><small>%s</small></div>'
            "</div>"
            % ("%d documented" % len(products),
               "%d now · %d next" % (now_count, next_count), arch_sub,
               "%d rule%s" % (logic_charts, "" if logic_charts == 1 else "s"),
               "%d machine%s" % (logic_states, "" if logic_states == 1 else "s")))

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
        prod_figs, prod_body = extract_figures(d["body"])
        if prod_figs["flow"]:
            flow_src.append((name, "#p-" + slug, prod_figs["flow"]))
        if prod_figs["flowchart"]:
            chart_src.append((name, "#p-" + slug, prod_figs["flowchart"]))
        if prod_figs["state"]:
            state_src.append((name, "#p-" + slug, prod_figs["state"]))
        body_html = md_to_html(prod_body, here, comps, figs)
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
                ids = ids_in(b)
                live = [x for x in ids if x.startswith("BACKLOG") and x in backlog_by_id]
                other_ids = [x for x in ids if x not in live]
                dot, badge, refs = "", "", ""
                if live:
                    st = fm_str(backlog_by_id[live[0]], "status")
                    dot_kind = {"open": "open", "in-progress": "progress", "done": "done"}.get(st, "open")
                    dot = '<span class="dot%s"></span>' % ("" if dot_kind == "open" else " d-" + dot_kind)
                    badge = id_tag(live[0], here)
                if other_ids:
                    refs = "".join(id_tag(x, here, "tag") for x in other_ids)
                # The remaining prose is still markdown — a bullet carrying an id
                # gets the same bold/code/link treatment as one that carries none.
                text = strip_ids(b) if ids else b
                head = ('<div class="im">%s%s</div>' % (dot, badge)) if (dot or badge) else ""
                tail = ('<div class="im" style="margin-top:5px">%s</div>' % refs) if refs else ""
                items.append('<div class="item%s">%s<div class="it"%s>%s</div>%s</div>'
                             % (" muted" if muted else "", head,
                                ' style="margin-top:0"' if not head else "",
                                inline_md(text, here), tail))
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
        parts.append(section_sub("Mỗi component: nó là gì và làm gì, đọc ở đâu trong source, "
                                 "ai bơm vào và nó bơm ra đâu. Hai dòng cuối suy ra từ "
                                 "data_flow — không ai phải chép tay lần thứ hai."))
        detail = body_sections(arch_body, comps.keys())
        cards = []
        for name, c in comps.items():
            kind = c["kind"]
            _b, _d, badge_bg, icon_color, icon, _lf = NODE_STYLE.get(kind, NODE_STYLE["svc"])
            icon_svg = ('<span class="ibadge" style="background:%s"><svg width="14" height="14" '
                        'viewBox="0 0 16 16" style="color:%s"><g fill="none" stroke="currentColor" '
                        'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">%s</g></svg></span>'
                        % (badge_bg, icon_color, ICONS[icon]))
            facts = component_facts(name, edges, comps)
            head = ('<div class="cn">%s<span class="nm">%s</span>'
                    '<span class="kd k-%s">%s</span></div>'
                    % (icon_svg, esc(name), esc(kind), esc(KIND_LABEL.get(kind, kind))))
            rows = []
            if c["code"]:
                rows.append('<tr><th>code</th><td><code>%s</code></td></tr>' % esc(c["code"]))
            rows.append('<tr><th>role</th><td>%s</td></tr>' % esc(facts["role"]))
            if facts["upstream"]:
                rows.append('<tr><th>in from</th><td>%s</td></tr>'
                            % "".join(comp_ref(x) for x in facts["upstream"]))
            if facts["downstream"]:
                rows.append('<tr><th>out to</th><td>%s</td></tr>'
                            % "".join(comp_ref(x) for x in facts["downstream"]))
            body = detail.get(name, "")
            more = ('<details class="more"><summary>Chi tiết</summary><div class="md">%s</div></details>'
                    % md_to_html(body, here, comps, figs)) if body.strip() else ""
            cards.append('<div class="comp" id="%s">%s<div class="cr">%s</div>'
                         '<table class="spec tight">%s</table>%s</div>'
                         % (comp_slug(name), head, inline_md(c["desc"], here) if c["desc"]
                            else '<span class="dim">chưa mô tả — đọc source rồi điền một câu '
                                 "nó là gì</span>",
                            "".join(rows), more))
        parts.append('<div class="comps">%s</div>' % "".join(cards))
    else:
        parts.append(empty_state("NO COMPONENTS — điền danh sách <code>components</code> trong "
                                 "<code>docs/02_architecture/architecture.md</code>"))

    parts.append('<h3 id="a-data">Data model</h3>')
    parts.append(section_sub("Lược đồ dữ liệu — bảng nào có cột gì, và cột nào trỏ sang bảng "
                             "nào. Components ở trên trả lời “có những gì” cho service; chỗ "
                             "này trả lời đúng câu đó cho dữ liệu"))
    if arch_figs["erd"]:
        for block in arch_figs["erd"]:
            fig = erd_figure(block, comps, figs, here)
            if fig:
                parts.append(fig)
            else:
                parts.append('<div class="note"><span class="lbl">Note</span>Một khối '
                             "<code>```erd</code> không đọc được bảng nào — mỗi bảng mở bằng "
                             "<code>table: &lt;tên&gt;</code>, rồi mỗi cột một dòng "
                             "<code>&lt;tên&gt; &lt;kiểu&gt; &lt;cờ&gt;</code>.</div>")
                parts.append("<pre><code>%s</code></pre>" % esc(block.strip()))
    else:
        parts.append(empty_state(
            "NO DATA MODEL — thêm một khối <code>```erd</code> vào "
            "<code>docs/02_architecture/</code>. Mở bằng <code>table: orders</code>, rồi "
            "mỗi cột một dòng: <code>merchant_id uuid fk -&gt; merchants.id</code>"))

    parts.append('<h3 id="a-types">Types &amp; contracts</h3>')
    parts.append(section_sub("Cấu trúc type — cái nào implement interface nào, cái nào giữ "
                             "tham chiếu tới cái nào. Data model ở trên là dữ liệu đã lưu; "
                             "chỗ này là code"))
    if arch_figs["class"]:
        for block in arch_figs["class"]:
            fig = class_figure(block, comps, figs, here)
            if fig:
                parts.append(fig)
            else:
                parts.append('<div class="note"><span class="lbl">Note</span>Một khối '
                             "<code>```class</code> không đọc được type nào — mỗi type mở bằng "
                             "<code>class: &lt;tên&gt;</code> hoặc <code>interface: &lt;tên&gt;</code>, "
                             "rồi mỗi thành viên một dòng.</div>")
                parts.append("<pre><code>%s</code></pre>" % esc(block.strip()))
    else:
        parts.append(empty_state(
            "NO TYPES — thêm một khối <code>```class</code> vào "
            "<code>docs/02_architecture/</code>. Mở bằng <code>interface: PSPClient</code> "
            "hoặc <code>class: PaymentAdapter</code>, rồi mỗi thành viên một dòng"))

    parts.append('<h3 id="a-flow">Data flow</h3>')
    if edges and flow_ok:
        # STANDARD §10: there is one style, the graph. Over budget it is still a
        # graph — drawn at natural size, scrolling inside its own frame — because
        # a flow the reader can follow one edge at a time beats a compact picture
        # that spells nothing out. The budget only decides whether to warn.
        dag = svg_dag(edges, comps, figs.next())
        if dag and not within_budget(edges):
            nodes = {n for e in edges for n in e[:2]}
            parts.append('<div class="note"><span class="lbl">Dense</span>%d component và %d cạnh '
                         "— quá ngưỡng đọc thoải mái (%d node · %d cạnh · %d hàng một cột). Hình "
                         "vẫn vẽ đủ ở kích thước thật và cuộn ngang; nếu khó theo dõi thì tách bớt "
                         "sang một doc Architecture khác thay vì rút gọn hình.</div>"
                         % (len(nodes), len(edges), FLOW_MAX_NODES, FLOW_MAX_EDGES, FLOW_MAX_ROWS))
        if dag:
            parts.append(dag)
        parts.append('<h4 id="a-edges">Mọi cạnh</h4>')
        parts.append(edge_table(edges, here))
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

    body_html = md_to_html(arch_body, here, comps, figs)
    if body_html.strip():
        parts.append('<details class="more" style="margin-top:20px"><summary>Full architecture document'
                     "</summary><div class=\"md\">%s</div></details>" % body_html)

    # --- business flows
    if arch_flows:
        flow_src.append(("Architecture", "#architecture", arch_flows))
    if arch_charts:
        chart_src.append(("Architecture", "#architecture", arch_charts))
    if arch_figs["state"]:
        state_src.append(("Architecture", "#architecture", arch_figs["state"]))
    # 03_business-logic is where branching rules and lifecycles live, so its figures
    # come last — after any a product or the architecture doc happened to carry.
    for label, d_figs in logic_figs:
        if d_figs["flow"]:
            flow_src.append((label, "#logic", d_figs["flow"]))
        if d_figs["flowchart"]:
            chart_src.append((label, "#logic", d_figs["flowchart"]))
        if d_figs["state"]:
            state_src.append((label, "#states", d_figs["state"]))
    parts.append('<h2 id="flows" class="s-l1"><span class="idx">§4</span>Business flows '
                 '<span class="src tag">```flow trong docs/01_products/ · 02_architecture/ · '
                 "03_business-logic/</span></h2>")
    parts.append(section_sub("Nghiệp vụ chạy ra sao, theo thứ tự thời gian — mỗi kịch bản một hình. "
                             "Đây là chỗ trả lời “đặt một lệnh thì chuyện gì xảy ra”, thứ mà sơ đồ "
                             "component tĩnh phía trên không nói được."))
    if flow_src:
        for label, anchor, blocks in flow_src:
            parts.append('<h3>%s <a class="tag" href="%s">nguồn</a></h3>' % (esc(label), anchor))
            for block in blocks:
                fig = seq_figure(block, comps, figs, here)
                if fig:
                    parts.append(fig)
                else:
                    parts.append('<div class="note"><span class="lbl">Note</span>Một khối '
                                 "<code>```flow</code> không đọc được bước nào — cú pháp mỗi bước là "
                                 "<code>a -&gt; b : việc gì</code>, <code>~&gt;</code> cho async.</div>")
                    parts.append("<pre><code>%s</code></pre>" % esc(block.strip()))
    else:
        parts.append(empty_state(
            "NO BUSINESS FLOWS — thêm một khối <code>```flow</code> vào thân file product "
            "hoặc architecture. Mỗi dòng là một bước: <code>api -&gt; engine : validate</code>; "
            "kèm <code>title:</code>, <code>trigger:</code>, <code>outcome:</code>, "
            "<code>code:</code> nếu có"))

    parts.append('<h2 id="logic" class="s-l1"><span class="idx">§5</span>Business logic '
                 '<span class="src tag">```flowchart trong docs/03_business-logic/</span></h2>')
    parts.append(section_sub("Quy tắc rẽ nhánh — điều gì xảy ra khi gặp điều kiện nào. "
                             "Sequence ở §4 kể thứ tự; chỗ này kể lựa chọn"))
    if chart_src:
        for label, anchor, blocks in chart_src:
            parts.append('<h3>%s <a class="tag" href="%s">nguồn</a></h3>' % (esc(label), anchor))
            for block in blocks:
                fig = flowchart_figure(block, comps, figs, here)
                if fig:
                    parts.append(fig)
                else:
                    parts.append('<div class="note"><span class="lbl">Note</span>Một khối '
                                 "<code>```flowchart</code> không đọc được cạnh nào — mỗi bước là "
                                 "<code>a -&gt; b</code>, nhánh là nhãn cạnh "
                                 "<code>a -&gt; b : yes</code>, điểm rẽ khai báo bằng "
                                 "<code>decide: a — câu hỏi?</code>.</div>")
                    parts.append("<pre><code>%s</code></pre>" % esc(block.strip()))
    else:
        parts.append(empty_state(
            "NO BUSINESS LOGIC — thêm một khối <code>```flowchart</code> vào "
            "<code>docs/03_business-logic/</code>. Khai báo điểm rẽ bằng "
            "<code>decide: check — câu hỏi?</code>, rồi nối các bước: "
            "<code>check -&gt; approve : yes</code>"))

    parts.append('<h2 id="states" class="s-l1"><span class="idx">§6</span>State machines '
                 '<span class="src tag">```state trong docs/03_business-logic/</span></h2>')
    parts.append(section_sub("Vòng đời của một entity — nó ở được những trạng thái nào, sự kiện "
                             "nào chuyển nó đi. §5 kể lựa chọn; chỗ này kể trạng thái"))
    if state_src:
        for label, anchor, blocks in state_src:
            parts.append('<h3>%s <a class="tag" href="%s">nguồn</a></h3>' % (esc(label), anchor))
            for block in blocks:
                fig = state_figure(block, comps, figs, here)
                if fig:
                    parts.append(fig)
                else:
                    parts.append('<div class="note"><span class="lbl">Note</span>Một khối '
                                 "<code>```state</code> không đọc được transition nào — mỗi chuyển "
                                 "trạng thái là <code>a -&gt; b : sự kiện</code>; trạng thái đầu và "
                                 "cuối khai báo bằng <code>initial:</code> và "
                                 "<code>final:</code>.</div>")
                    parts.append("<pre><code>%s</code></pre>" % esc(block.strip()))
    else:
        parts.append(empty_state(
            "NO STATE MACHINES — thêm một khối <code>```state</code> vào "
            "<code>docs/03_business-logic/</code>. Khai báo trạng thái đầu bằng "
            "<code>initial: pending</code>, rồi nối: "
            "<code>pending -&gt; paid : payment.succeeded</code>"))

    sidebar = ['<li><a href="#products">§1 Products</a></li>']
    for d in products:
        slug = slugs[d["path"]]
        sidebar.append('<li class="sub"><a href="#p-%s">%s</a></li>'
                       % (slug, esc(trim(fm_str(d, "name") or doc_title(d), 26))))
    sidebar.append('<li><a href="#roadmap">§2 Roadmap</a></li>')
    sidebar.append('<li><a href="#architecture">§3 Architecture</a></li>')
    for anchor, label in [("a-components", "Components"), ("a-data", "Data model"),
                          ("a-types", "Types &amp; contracts"), ("a-flow", "Data flow"),
                          ("a-stack", "Tech stack"), ("a-constraints", "Constraints"),
                          ("a-rev", "Revision block")]:
        sidebar.append('<li class="sub"><a href="#%s">%s</a></li>' % (anchor, label))
    sidebar.append('<li><a href="#flows">§4 Business flows</a></li>')
    sidebar.append('<li><a href="#logic">§5 Business logic</a></li>')
    sidebar.append('<li><a href="#states">§6 State machines</a></li>')

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
