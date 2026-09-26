"""docs-kit — the chain report behind /docs-kit:docs-archive.

docs_close.py decides what leaves the hot set one DOCUMENT at a time, and says so
in one line per move. That answers "what moved" and nothing else. A person
cleaning up Layer 2 asks about CHAINS — Issue → Proposal → Decision → Backlog —
and wants three things the flat list cannot say: which chains are finished end to
end, which ones will never close by themselves and why, and what a move does to
the links around it.

This script prints that, as one markdown report with a fixed shape, from the SAME
plan docs_close executes (`plan()`), so the report cannot disagree with the moves.
Nothing here decides anything: every verdict comes from docs_close.judge(), and
this file only groups and words them.

Usage:  docs_archive.py [--apply] [--settle ID [--why TEXT]]... [--all] [repo-root]

  --apply      write the plan: record unrecorded Closes: trailers, settle, move
               with `git mv`, rewrite the relative links the moves shift
  --settle ID  a person declares a chain finished that no predicate can close:
               an approved Decision no Backlog item cites, a rejected Decision,
               or a promoted Issue with no successor. Anything else is refused.
               Each settle appends one audit line; --why fills its reason column
               (the i-th --why pairs with the i-th --settle)
  --all        list every chain in flight (default: the first 25)

Exit:   0 = nothing moves, or applied · 1 = preview with moves pending
        2 = setup error, or a --settle the rule refused (nothing is written)
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docs_close import (ANY_ID_RE, execute, fm_str, plan)  # noqa: E402
from docs_render import project_name  # noqa: E402

KINDS = ("ISSUE", "PROPOSAL", "DECISION", "BACKLOG")
FOLDER = {"ISSUE": "20_issues", "PROPOSAL": "21_proposals",
          "DECISION": "22_decisions", "BACKLOG": "23_backlog"}
INFLIGHT_ROWS = 25

# Structure is English, explanation is Vietnamese (STANDARD §11): section
# headings and table headers are labels, every gloss and reason is prose.
INFLIGHT = {
    "open": "{id} còn open",
    "in-progress": "{id} đang in-progress",
    "exploring": "{id} còn exploring",
    "awaiting-decision": "{id} chưa có Decision",
}
HELD = {
    "no-audit": ("{id} đã done nhưng chưa có audit line",
                 "viết audit line cho {id} (tay, hoặc `/docs-kit:docs-sync`) rồi chạy lại"),
    "no-ticket": ("{id} approved nhưng không Backlog item nào cite",
                  "`--settle {id}` nếu chain đã xong mà không cần ticket (STANDARD §2)"),
    "rejected": ("{id} rejected; rule không tự archive vì rejected có thể là hoãn",
                 "`--settle {id}` nếu Decision không còn điều kiện mở lại"),
    "no-successor": ("{id} promoted nhưng không document nào cite",
                     "`--settle {id}` nếu việc đã gộp vào ticket khác; nếu chưa thì cắt Backlog item"),
    "enum": ("{id} có {field} `{value}` ngoài enum",
             "sửa frontmatter của {id} (`/docs-kit:docs-check` chỉ rõ)"),
    "stranded": ("{id} nằm trong _archive/ nhưng chưa done kèm audit line",
                 "ghi audit line cho {id}, hoặc đưa nó về hot set"),
}


def chains(p):
    """Connected components of the ref graph, over hot AND archived documents.

    Archived members are kept on purpose: a chain whose Backlog item moved last
    week and whose Decision moves today is one chain, and printing it as two
    would hide that it is now complete.
    """
    docs = {}
    for kind in KINDS:
        for d in p.docs.get(kind, []):
            did = fm_str(d, "id")
            if did:
                docs[did] = (kind, d)
    parent = dict((i, i) for i in docs)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for did, (kind, d) in docs.items():
        for key in ("source_ref", "proposal_ref", "issue_ref"):
            for ref in ANY_ID_RE.findall(fm_str(d, key)):
                if ref in docs:
                    parent[find(did)] = find(ref)
    groups = {}
    for did in docs:
        groups.setdefault(find(did), []).append(did)
    out = []
    for ids in groups.values():
        members = sorted(ids, key=lambda i: (KINDS.index(docs[i][0]), i))
        out.append([(i, docs[i][0], docs[i][1]) for i in members])
    return sorted(out, key=lambda c: c[0][0])


def label(chain):
    by = {}
    for did, kind, _ in chain:
        by.setdefault(kind, []).append(did)
    return " → ".join(", ".join(by[k]) for k in KINDS if k in by)


def lane(chain):
    kinds = set(k for _, k, _ in chain)
    fast = any(k == "BACKLOG" and fm_str(d, "source_ref").startswith("ISSUE-")
               for _, k, d in chain)
    full = "PROPOSAL" in kinds or "DECISION" in kinds
    if not full and not fast:     # an Issue with no successor yet: its own word
        return next((fm_str(d, "lane") for _, k, d in chain if k == "ISSUE"), "") or "—"
    return "full + fast" if full and fast else ("full" if full else "fast")


def leaves(p, chain):
    """The reasons a chain stays — only the ones at the bottom of a `waits`.

    A Decision waiting on a ticket that is waiting on nobody is one reason,
    the ticket's, not two. Printing every `waits` would repeat the same blocker
    once per link above it.
    """
    ids = set(i for i, _, _ in chain)
    archived = dict((i, d["archived"]) for i, _, d in chain)
    out = []
    for did, _, d in chain:
        v = p.verdicts.get(did)
        if v is None or v["state"] == "moves":
            continue
        if v["state"] in ("inflight", "held"):
            out.append((did, v))
        elif v["state"] == "waits":
            for on in v.get("on", []):
                # A blocker already in _archive/ has no verdict of its own —
                # somebody moved it by hand before it was terminal.
                if on in ids and archived.get(on) and not any(o == on for o, _ in out):
                    out.append((on, {"state": "held", "shape": "stranded"}))
    return out


def reason(did, v):
    if v["state"] == "inflight":
        return INFLIGHT.get(v["shape"], "{id} " + v["shape"]).format(id=did), ""
    text, release = HELD[v["shape"]]
    text = text.format(id=did, field=v.get("field", ""), value=v.get("value", ""))
    if v.get("via"):
        text += "; " + ", ".join("%s cite %s thay vì Decision" % b for b in v["via"])
    if v.get("named_in"):
        text += "; body của %s có nhắc tới" % ", ".join(v["named_in"])
    return text, release.format(id=did)


def chains_n(n):
    return "%d chain%s" % (n, "" if n == 1 else "s")


def closed_by(p, chain, moving):
    settled = [s for s in p.settled if s["id"] in moving]
    if settled:
        return "settle · %s" % settled[0]["line"].split(" | ")[-1]
    recs = [p.recorded[i] for i, k, _ in chain if k == "BACKLOG" and i in p.recorded]
    if recs:
        last = max(recs, key=lambda r: r["date"])
        why = last["why"]
        sha = why.split("commit ", 1)[1].split()[0] if "commit " in why else ""
        return "%s · %s" % (last["date"], "commit `%s`" % sha if sha else "audit line")
    if any(k == "ISSUE" and fm_str(d, "status") == "archived" for _, k, d in chain):
        return "status: archived (dropped)"
    return "—"


def table(head, rows, numeric=0):
    """A markdown table; the last `numeric` columns are right-aligned counts."""
    out = ["| " + " | ".join(head) + " |",
           "|" + "|".join("---:" if i >= len(head) - numeric else "---"
                          for i in range(len(head))) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |")
    return out


def report(root, p, applied, show_all):
    moving = set(mid for _, mid, _, _ in p.moves)
    groups = {"complete": [], "held": [], "inflight": []}
    for chain in chains(p):
        hot = [i for i, _, d in chain if not d["archived"]]
        if not hot:
            continue
        why = leaves(p, chain)
        moves = [i for i in hot if i in moving]
        if all(i in moving for i in hot):
            groups["complete"].append((chain, moves, why))
        elif any(v["state"] == "held" for _, v in why):
            groups["held"].append((chain, moves, why))
        else:
            groups["inflight"].append((chain, moves, why))

    n_moves = len(p.moves)
    n_links = sum(len(c) for _, _, c in p.rewrites)
    out = ["## docs-archive · %s · %s" % (project_name(root), "applied" if applied else "preview"), ""]
    if applied:
        out.append("Đã chuyển %d document vào `_archive/` bằng `git mv` và sửa %d link. "
                   "Chưa commit." % (n_moves, n_links) if n_moves
                   else "Không có document nào rời hot set lần này.")
    elif n_moves:
        out.append("Chưa ghi gì. Nếu áp dụng, %d document rời hot set (%d chain xong trọn) "
                   "và %d link được sửa theo." % (n_moves, len(groups["complete"]), n_links))
    else:
        out.append("Chưa ghi gì, và không có document nào rời hot set lần này.")
    out.append("")

    # ---- totals, per folder ------------------------------------------------
    rows, tot = [], [0, 0, 0, 0]
    for kind in KINDS:
        ds = p.docs.get(kind, [])
        hot = sum(1 for d in ds if not d["archived"])
        mv = sum(1 for k, _, _, _ in p.moves if k == kind)
        arch = sum(1 for d in ds if d["archived"])
        # p.docs was loaded before execute() ran, so these are "before" counts
        # in both modes and the arithmetic below is the same promise either way.
        row = [hot, mv, hot - mv, arch + mv]
        tot = [a + b for a, b in zip(tot, row)]
        rows.append(["`%s`" % FOLDER[kind]] + row)
    rows.append(["total"] + tot)
    out += table(["Folder", "Hot", "Moves", "Hot after", "_archive/ after"], rows, 4) + [""]

    if p.refused:
        out += ["### Settle refused", "Không settle được, nên lần chạy này không ghi gì", ""]
        out += table(["Id", "Why"], [[i, r] for i, r in p.refused]) + [""]

    closes = [t for t in p.trailers if not t["skip"]]
    skips = [t for t in p.trailers if t["skip"]]
    if closes or skips:
        out += ["### Recorded from commits",
                "Closes: trailer chưa được ghi; script ghi trước rồi mới xét archive", ""]
        rows = []
        for t in closes:
            w = [x for x, on in (("status → done", t["status"]), ("audit line", t["audit"])) if on]
            rows.append([t["id"], ", ".join(w), "`%s` %s" % (t["commit"]["sha"], t["commit"]["date"])])
        for t in skips:
            rows.append([t["id"], "bỏ qua: không Backlog item nào có id này",
                         "`%s` %s" % (t["commit"]["sha"], t["commit"]["date"])])
        out += table(["Backlog", "Writes", "Commit"], rows) + [""]

    out += ["### Complete · %s" % chains_n(len(groups["complete"])),
            "Mọi document trong chain đã terminal nên cả chain rời hot set", ""]
    if groups["complete"]:
        out += table(["Chain", "Lane", "Closed by", "Moves"],
                     [[label(c), lane(c), closed_by(p, c, moving), len(m)]
                      for c, m, _ in groups["complete"]], 1) + [""]
    else:
        out += ["Không có chain nào xong trọn lần này.", ""]

    out += ["### Needs a decision · %s" % chains_n(len(groups["held"])),
            "Chain không tự đóng được; cần một người quyết", ""]
    if groups["held"]:
        rows = []
        for c, m, why in groups["held"]:
            for did, v in why:
                if v["state"] != "held":
                    continue
                text, release = reason(did, v)
                rows.append([label(c), ", ".join(m) or "—", text, release])
        out += table(["Chain", "Moves", "Held by", "To release"], rows) + [""]
    else:
        out += ["Không có chain nào bị kẹt.", ""]

    fl = sorted(groups["inflight"], key=lambda g: (not g[1], g[0][0][0]))
    shown = fl if show_all else fl[:INFLIGHT_ROWS]
    out += ["### In flight · %s" % chains_n(len(fl)),
            "Việc đang làm dở; chain tự đóng khi việc xong, không cần làm gì", ""]
    if shown:
        out += table(["Chain", "Moves", "Waiting on"],
                     [[label(c), ", ".join(m) or "—",
                       "; ".join(reason(i, v)[0] for i, v in why)] for c, m, why in shown])
        if len(fl) > len(shown):
            out.append("")
            out.append("… và %d chain nữa (`--all` để liệt kê hết)." % (len(fl) - len(shown)))
        out.append("")
    else:
        out += ["Không có chain nào đang làm dở.", ""]

    if p.rewrites or p.left:
        out += ["### Links", "Đường dẫn tương đối lệch đi khi file chuyển vào `_archive/`", ""]
        if p.rewrites:
            out.append("- %d link trong %d file %s để vẫn trỏ đúng document."
                       % (n_links, len(p.rewrites), "đã được sửa" if applied else "sẽ được sửa"))
        if p.left:
            out.append("- %d link nằm ở layer 1 hoặc audit log; script không ghi vào đó:"
                       % len(p.left))
            out.append("")
            out += table(["File", "Link", "Sửa thành"],
                         [["`%s`" % f.relative_to(root), "`%s`" % a, "`%s`" % b]
                          for f, a, b in p.left])
        out.append("")

    if applied:
        out.append("Tiếp theo: chạy `docs_render.sh` vì `INDEX.md` và `MAP.tsv` đã cũ, "
                   "rồi commit các lần `git mv`.")
    elif n_moves or closes or p.settled:
        out.append("Tiếp theo: chạy lại với `--apply` để ghi đúng những gì liệt kê ở trên.")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(prog="docs_archive.py", add_help=True)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--settle", action="append", default=[])
    ap.add_argument("--why", action="append", default=[])
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if not (root / "docs").is_dir():
        print("docs-archive: no docs/ under %s" % root, file=sys.stderr)
        return 2
    p = plan(root, archive=True, settle=a.settle, why=a.why)
    # A refused settle writes nothing at all, not "everything except the settle":
    # the person approved one plan, and a partial apply is a different plan.
    if p.refused:
        sys.stdout.write(report(root, p, False, a.all))
        return 2
    if a.apply:
        execute(root, p)
        sys.stdout.write(report(root, p, True, a.all))
        return 0
    sys.stdout.write(report(root, p, False, a.all))
    return 1 if p.moves or p.settled or any(not t["skip"] for t in p.trailers) else 0


if __name__ == "__main__":
    sys.exit(main())
