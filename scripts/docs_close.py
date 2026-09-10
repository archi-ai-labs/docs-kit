"""docs-kit — the deterministic half of docs-sync.

Two of docs-sync's seven steps never needed a model. Both are decided entirely by
facts already written down, and both were being done by re-reading a session's
own history and inferring:

  Step 2 — "which Backlog items did this session finish?" Inferred from context,
    then written as an audit line that cites the session rather than the work. The
    commit already knows: `Closes: BACKLOG-012` in the message is the author saying
    it, at the moment they said it, in something that outlives the chat.

  Step 6 — "what can leave the hot set?" A pure predicate over frontmatter: a
    Backlog item at `status: done` whose audit line is written, a Decision whose
    Backlog items are all done, and an Issue that was either dropped
    (`status: archived`) or has outlived every successor it produced. Nothing
    about it requires reading prose.

WHAT THIS DELIBERATELY DOES NOT DO
    It never writes into layer 1, never creates an Issue, never invents an audit
    line for work no commit claims. Those are judgements, and they stay in the
    skill. This script only acts on statements the repo already contains.

Usage:  docs_close.py [--apply] [--archive] [repo-root]
        (default: report only, current directory)

Exit:   0 = nothing to do, or applied cleanly
        1 = something to do (report mode) — usable as a CI gate
        2 = setup error
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# One frontmatter parser for the whole kit. Re-implementing the YAML subset here
# would drift from the renderer's, and the inline-comment handling in particular
# has already caused one phantom-component bug.
from docs_render import parse_frontmatter  # noqa: E402

TRAILER_RE = re.compile(r"^\s*closes:\s*(.+)$", re.I | re.M)
ID_RE = re.compile(r"\b(BACKLOG-[0-9]{3,})\b")
# Any layer-2 id, whatever its prefix (STANDARD §3). Needed to find which id an
# audit line is *about*, which is the first one in its ref column regardless of
# kind — a line led by DECISION-008 is not a Backlog item's completion.
ANY_ID_RE = re.compile(r"\b([A-Z]+-[0-9]{3,})\b")
# An audit line leads with its date (STANDARD §4). Prose in the same file — the
# header, the format reminder, a paragraph naming an id — must not be read as a
# record of anything.
AUDIT_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
AUDIT_SEP = "|"


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root)] + list(args),
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=30)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode("utf-8", "replace")


def md_files(folder):
    if not folder.is_dir():
        return []
    out = [p for p in sorted(folder.glob("*.md")) if p.name != "README.md"]
    arch = folder / "_archive"
    if arch.is_dir():
        out += [p for p in sorted(arch.glob("*.md")) if p.name != "README.md"]
    return out


def load(folder):
    docs = []
    for p in md_files(folder):
        fm, body = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        docs.append({"path": p, "fm": fm, "body": body,
                     "archived": p.parent.name == "_archive"})
    return docs


def cites(value, ident):
    """True when `value` names `ident` as a whole id, not as a prefix of a longer one.

    Ids are a prefix plus three digits *or more* (STANDARD §3), so a plain `in`
    test makes DECISION-001 a match inside DECISION-0012 — silently archiving a
    chain on the strength of a different chain's completion. Every ref read in
    step 6 goes through here.
    """
    return re.search(r"\b%s\b" % re.escape(ident), value or "") is not None


def fm_str(doc, key):
    v = doc["fm"].get(key, "")
    if isinstance(v, list):
        v = v[0] if v else ""
    return str(v).strip()


def trailers(root):
    """Every `Closes: BACKLOG-NNN` in the repo's history → id -> commit facts.

    The whole history is scanned, not a range since some marker. Scanning a range
    needs state about where the last run stopped, and state that can be wrong is
    worse than a scan that costs a second: the write below is idempotent, so
    re-reading a commit that was already applied changes nothing.

    First commit wins per id. A later commit mentioning the same id is a follow-up
    fix, not a second completion, and the audit line should name the moment the
    work landed.
    """
    log = git(root, "log", "--reverse", "--format=%H%x1f%h%x1f%ad%x1f%s%x1f%b%x1e",
              "--date=short")
    if log is None:
        return {}
    found = {}
    for rec in log.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        parts = rec.split("\x1f")
        if len(parts) < 5:
            continue
        short, date, subject, body = parts[1], parts[2], parts[3], parts[4]
        for m in TRAILER_RE.finditer(body):
            for bid in ID_RE.findall(m.group(1)):
                found.setdefault(bid, {"sha": short, "date": date, "subject": subject})
    return found


def audit_columns(line):
    """Split one audit-log line into its columns, or [] if it is not one.

    Two shapes are in the wild and both are honoured. STANDARD §4 writes the bare
    form, `date | what | ref | deviation | why`, which is what this script appends.
    People also write the same five fields as a markdown table row, wrapped in
    pipes, because it renders — so the leading and trailing separator is stripped
    before splitting rather than treated as an empty first column. Getting that
    wrong shifts every column by one, which is a silent misread of the ref.
    """
    t = line.strip()
    if not t or AUDIT_SEP not in t:
        return []
    if t.startswith(AUDIT_SEP):
        t = t[1:]
    if t.endswith(AUDIT_SEP):
        t = t[:-1]
    return [c.strip() for c in t.split(AUDIT_SEP)]


def audit_ids(docs_root):
    """Backlog ids whose COMPLETION the audit log already records.

    This used to be cheap containment — any `BACKLOG-nnn` anywhere in any file
    here counted. That conflates *mentioned* with *recorded*, and the difference
    is not academic. Measured 2026-09-10 on a real repo: an audit line for a
    Decision approval named the two tickets that Decision OPENED, in its ref
    column, months before either finished. From then on `need_audit` was False
    for both, so the next `Closes:` trailer flipped `status: done` and appended
    nothing, reporting `CLOSE BACKLOG-nnn — status -> done` — a close-out that
    reads exactly like a correct one while STANDARD §6's completion trigger goes
    unmet. Silent, which EXECUTION §12 ranks above a refusal.

    So a line records a completion only when the id is the line's SUBJECT: the
    first id of any kind in the ref column (STANDARD §4). That is the shape this
    script writes — `BACKLOG-001 (DECISION-000)` — and the shape people already
    write by hand.

    Why not "ref column plus a commit sha in the why column": hand-written audit
    lines are explicitly valid (§6.1) and carry no sha. On the repo above that
    rule matched 2 of 16 finished items, so the next run would have appended
    fourteen duplicate lines. The subject rule matched 16 of 16, and neither of
    the two open tickets — including the poisoned one.

    Two ceilings, stated rather than papered over. A line whose *what happened*
    column contains a literal `|` shifts the columns, so the wrong field is read
    as the ref; that can only lose a record, never invent the old bug back, and
    losing one costs a visible extra line rather than a silent missing one. And
    an id recorded in some other shape — `DECISION-009 (BACKLOG-020)` for a line
    that really is that Backlog item's completion — is not seen, so this script
    appends its own line naming the commit. Both failure directions are now
    loud: the old one was quiet.

    The glob stays non-recursive and stays a glob. Non-recursive because a crew
    repo keeps its periodic reports in `92_audit/reports/` precisely so prose
    full of ids cannot reach this function; a glob rather than `LOG.md` alone
    because a repo that splits a long log by year still has real records in the
    older file.
    """
    seen = set()
    folder = docs_root / "92_audit"
    if not folder.is_dir():
        return seen
    for p in sorted(folder.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line in text.split("\n"):
            cols = audit_columns(line)
            # date, what happened, ref — everything after the ref is irrelevant
            # here, and some repos write the line as a four-column markdown table
            # without the `why`, so do not insist on all five.
            if len(cols) < 3 or not AUDIT_DATE_RE.match(cols[0]):
                continue
            subject = ANY_ID_RE.search(cols[2])
            if subject and subject.group(1).startswith("BACKLOG-"):
                seen.add(subject.group(1))
    return seen


def set_status(path, value):
    """Rewrite one frontmatter scalar in place, touching nothing else.

    A line edit rather than a re-serialise: these files are hand-written, and a
    round-trip through a YAML dumper would reflow comments, quoting and key order
    that the author chose.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return False
    for i, raw in enumerate(lines[1:], start=1):
        if raw.strip() == "---":
            break
        if re.match(r"^status:\s*", raw):
            lines[i] = "status: %s" % value
            path.write_text("\n".join(lines), encoding="utf-8")
            return True
    return False


def append_audit(docs_root, line):
    """Append one line to the audit log. Append is the only legal write here —
    the validator diffs this file against git HEAD and reports any rewritten line.
    """
    target = docs_root / "92_audit" / "LOG.md"
    if not target.is_file():
        return False
    text = target.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    target.write_text(text + line + "\n", encoding="utf-8")
    return True


def move_to_archive(root, path):
    dest = path.parent / "_archive"
    dest.mkdir(exist_ok=True)
    target = dest / path.name
    # git mv so history follows the document. An untracked file has no history to
    # keep, so a plain rename is the honest fallback rather than an error.
    if git(root, "mv", str(path.relative_to(root)),
           str(target.relative_to(root))) is None:
        path.rename(target)
    return target


def main():
    flags = set(a for a in sys.argv[1:] if a.startswith("-"))
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    apply_ = "--apply" in flags
    do_archive = "--archive" in flags
    root = Path(argv[0] if argv else ".").resolve()
    docs_root = root / "docs"
    if not docs_root.is_dir():
        print("docs-close: no docs/ under %s" % root, file=sys.stderr)
        return 2

    backlog = load(docs_root / "23_backlog")
    by_id = {}
    for d in backlog:
        bid = fm_str(d, "id")
        if bid:
            by_id[bid] = d

    pending, actions = [], 0

    # ---- step 2: commits that declare a Backlog item finished ---------------
    recorded = audit_ids(docs_root)
    for bid, c in sorted(trailers(root).items()):
        doc = by_id.get(bid)
        if doc is None:
            pending.append("SKIP  %s — commit %s claims it, but no Backlog item has that id"
                           % (bid, c["sha"]))
            continue
        need_status = fm_str(doc, "status") != "done"
        need_audit = bid not in recorded
        if not need_status and not need_audit:
            continue
        src = fm_str(doc, "source_ref")
        ref = "%s (%s)" % (bid, src) if src else bid
        # date | what happened | ref | deviation | why  (STANDARD §4)
        # "why" cites the commit rather than the session: a sha is checkable years
        # later, and a chat transcript is not.
        line = (" %s " % AUDIT_SEP).join(
            [c["date"], c["subject"], ref, "-", "commit %s" % c["sha"]])
        what = []
        if need_status:
            what.append("status -> done")
        if need_audit:
            what.append("audit line")
        pending.append("CLOSE %s — %s  [%s]" % (bid, ", ".join(what), c["sha"]))
        if apply_:
            if need_status:
                set_status(doc["path"], "done")
                doc["fm"]["status"] = "done"
            if need_audit and append_audit(docs_root, line):
                recorded.add(bid)
            actions += 1

    # ---- step 6: what can leave the hot set --------------------------------
    if do_archive:
        movable = []
        for d in backlog:
            if d["archived"]:
                continue
            bid = fm_str(d, "id")
            # Never archive a done item whose audit line is missing: the folder
            # that gets read least is the worst place to lose a trace.
            if fm_str(d, "status") == "done" and bid in recorded:
                movable.append(("BACKLOG", bid, d))

        issues = load(docs_root / "20_issues")
        for d in issues:
            if not d["archived"] and fm_str(d, "status") == "archived":
                movable.append(("ISSUE", fm_str(d, "id"), d))

        # A Decision (and the Proposal behind it) is terminal once every Backlog
        # item that cites it is done and audited. Derived from source_ref, never
        # declared — a "chain complete" field would be a second thing to keep true.
        decisions = load(docs_root / "22_decisions")
        proposals = load(docs_root / "21_proposals")
        for dec in decisions:
            if dec["archived"]:
                continue
            did = fm_str(dec, "id")
            if not did or fm_str(dec, "outcome") != "approved":
                continue
            items = [d for d in backlog if cites(fm_str(d, "source_ref"), did)]
            if not items or not all(fm_str(d, "status") == "done"
                                    and fm_str(d, "id") in recorded for d in items):
                continue
            movable.append(("DECISION", did, dec))
            pref = fm_str(dec, "proposal_ref")
            for p in proposals:
                if not p["archived"] and pref and fm_str(p, "id") == pref:
                    movable.append(("PROPOSAL", pref, p))

        # An Issue at `promoted` is terminal for the same reason, one link earlier:
        # every successor it produced has finished. Full lane that is the Proposal
        # citing it, fast lane the Backlog items citing it, and an Issue that fed
        # both needs both. `archived` keeps meaning exactly what it meant — dropped
        # or superseded — so this is a second way out of the hot folder, not a
        # redefinition of the first.
        #
        # Without this the folder only ever shrinks when work is abandoned: every
        # other document in a completed chain leaves, and its Issue does not.
        #
        # Read this run's own `movable`, never the filesystem. Under --apply the
        # Proposal above has not moved yet at the moment its Issue is judged here.
        moving = set(mid for _, mid, _ in movable)
        for iss in issues:
            iid = fm_str(iss, "id")
            if iss["archived"] or not iid or fm_str(iss, "status") != "promoted":
                continue
            props = [p for p in proposals if cites(fm_str(p, "issue_ref"), iid)]
            items = [d for d in backlog if cites(fm_str(d, "source_ref"), iid)]
            # No successor at all is a broken chain, not a finished one, and the
            # least-read folder is the worst place to put it. The validator's
            # [ref] check owns that case.
            if not props and not items:
                continue
            if not all(p["archived"] or fm_str(p, "id") in moving for p in props):
                continue
            if not all(fm_str(d, "status") == "done" and fm_str(d, "id") in recorded
                       for d in items):
                continue
            movable.append(("ISSUE", iid, iss))

        for kind, did, d in movable:
            pending.append("ARCHIVE %s %s — %s" % (kind, did, d["path"].name))
            if apply_:
                move_to_archive(root, d["path"])
                actions += 1

    if not pending:
        print("docs-close: nothing to do — no unrecorded Closes: trailer, "
              "nothing terminal to archive")
        return 0

    for line in pending:
        print(line)
    if apply_:
        print("docs-close: applied %d change(s). Re-run docs_render.sh — "
              "docs/INDEX.md and docs/MAP.tsv are now stale." % actions)
        return 0
    print("docs-close: %d pending change(s). Re-run with --apply to write them."
          % len(pending))
    return 1


if __name__ == "__main__":
    sys.exit(main())
