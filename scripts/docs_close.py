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
    about it requires reading prose. A move carries its relative links with it,
    in both directions, so a link that resolved before the run still resolves.

`plan()` decides all of it and writes nothing; `execute()` writes exactly that
plan. docs_archive.py prints the same plan as a chain-by-chain report.

WHAT THIS DELIBERATELY DOES NOT DO
    It never writes into layer 1, never creates an Issue, never invents an audit
    line for work no commit claims. Those are judgements, and they stay in the
    skill. This script only acts on statements the repo already contains — a
    link in layer 1 that pointed at a moved document is printed, not rewritten.

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
from datetime import date
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
    return set(audit_records(docs_root))


def audit_records(docs_root):
    """The same set as audit_ids, keyed to the line that records each completion.

    docs_archive prints *when* and *by what* a chain closed, and that is this
    line's date and its `why` column. Last line wins, so a hand-written
    correction appended later is the one reported.
    """
    seen = {}
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
                seen[subject.group(1)] = {"date": cols[0],
                                          "why": cols[4] if len(cols) > 4 else ""}
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


def archive_path(path):
    return path.parent / "_archive" / path.name


def today():
    # DOCS_KIT_NOW pins the date for tests, exactly as it pins the renderer's clock.
    now = os.environ.get("DOCS_KIT_NOW", "")
    return now[:10] if AUDIT_DATE_RE.match(now[:10]) else date.today().isoformat()


# ---- links -----------------------------------------------------------------
#
# Moving a file into `_archive/` adds a directory level, so every relative link
# out of it and every relative link into it shifts by one. Measured on a real
# repo before this existed: seven moves, 44 broken links, run green — the kit
# created the breakage and, until the validator's [link] check, could not see it.
# A move now carries its links with it.

LINK_RE = re.compile(r"\]\(([^)]*)\)")
# A script never writes here. Layer 1 changes only through a Decision (STANDARD
# §1) and the audit log only by appending (§4), so a link in either that pointed
# at a moved document is reported with its replacement instead of rewritten.
NO_WRITE = ("00_roadmap", "01_products", "02_architecture", "03_business-logic",
            "04_api", "92_audit")


def link_plan(docs_root, moves):
    """Every relative `.md` link a set of moves would shift, and its new target.

    `moves` maps a document's current path to its path under `_archive/`. Pure:
    it reads the tree as it stands and writes nothing, so a preview computes the
    same answer the apply writes.

    Only a link that resolves TODAY is touched. One that is already broken is
    somebody else's finding, and the validator's four-stage message says more
    about it than a guess made here could — so the promise is exactly "every
    link that worked before the run works after it", which is checkable.

    Returns (rewrites, left): rewrites = [(path, new_text, [(old, new)])] for
    files a script may write; left = [(path, old, new)] for NO_WRITE files.
    """
    moved = dict((os.path.normpath(str(a)), os.path.normpath(str(b)))
                 for a, b in moves.items())
    rewrites, left = [], []
    if not moved:
        return rewrites, left
    index = os.path.normpath(str(docs_root / "INDEX.md"))   # generated; re-rendered
    for f in sorted(docs_root.rglob("*.md")):
        here = os.path.normpath(str(f))
        if here == index:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        there = moved.get(here, here)
        changes = []

        def shift(m):
            raw = m.group(1)
            tgt, sep, anchor = raw.partition("#")
            # Same shapes the validator's check 7 skips: anchors, URLs, absolute
            # paths, angle-bracket targets, anything that is not a .md file.
            if (not tgt or not tgt.endswith(".md") or tgt.startswith(("/", "<"))
                    or "://" in tgt or tgt.startswith("mailto:") or " " in tgt):
                return m.group(0)
            old = os.path.normpath(os.path.join(os.path.dirname(here), tgt))
            if not os.path.isfile(old):
                return m.group(0)
            new = moved.get(old, old)
            if new == old and there == here:
                return m.group(0)
            rel = os.path.relpath(new, os.path.dirname(there))
            if os.path.normpath(os.path.join(os.path.dirname(there), tgt)) == new:
                return m.group(0)          # still resolves as written
            changes.append((raw, rel + sep + anchor))
            return "](" + rel + sep + anchor + ")"

        new_text = LINK_RE.sub(shift, text)
        if not changes:
            continue
        top = f.relative_to(docs_root).parts[0]
        if top in NO_WRITE:
            left.extend((f, a, b) for a, b in changes)
        else:
            rewrites.append((f, new_text, changes))
    return rewrites, left


# ---- plan: everything a run would do, decided before anything is written ----


class Plan(object):
    """What one run decides. `plan()` fills it and writes nothing; `execute()`
    writes exactly this and nothing else. The preview in report mode and the
    writes under --apply are therefore the same object, not two code paths that
    merely hope to agree.
    """

    def __init__(self):
        self.trailers = []   # dicts, in id order: skip | close
        self.moves = []      # (KIND, id, doc, how)  how: done|dropped|chain|settled
        self.verdicts = {}   # id -> verdict dict, for every HOT layer-2 document
        self.settled = []    # dicts: kind, id, doc, shape, line
        self.refused = []    # (id, reason) — a --settle the rule would not take
        self.docs = {}       # KIND -> loaded documents, hot and archived
        self.recorded = {}   # BACKLOG id -> {date, why}, as of after this run
        self.rewrites = []   # link_plan() output
        self.left = []


def verdict(state, shape, **kw):
    """state: moves · waits (on another document in the chain) · inflight (work
    in progress, closes by itself) · held (cannot close by itself — a person)."""
    kw.update(state=state, shape=shape)
    return kw


def mentions(p, ident):
    """Layer-2 documents whose BODY names `ident` — a hint, never a ref.

    Same distinction as audit_ids: mentioned is not cited. A promoted Issue that
    nothing cites is often one somebody folded into another ticket and named
    only in prose, and saying where it is named turns "broken chain" into a
    question a person can answer in one read.
    """
    out = []
    for kind in ("ISSUE", "PROPOSAL", "DECISION", "BACKLOG"):
        for d in p.docs.get(kind, []):
            did = fm_str(d, "id")
            if did and did != ident and cites(d["body"], ident):
                out.append(did)
    return out


def plan(root, archive=False, settle=(), why=None):
    docs_root = root / "docs"
    p = Plan()
    backlog = load(docs_root / "23_backlog")
    by_id = {}
    for d in backlog:
        bid = fm_str(d, "id")
        if bid:
            by_id[bid] = d
    p.recorded = audit_records(docs_root)
    log_ok = (docs_root / "92_audit" / "LOG.md").is_file()

    # ---- step 2: commits that declare a Backlog item finished ---------------
    for bid, c in sorted(trailers(root).items()):
        doc = by_id.get(bid)
        if doc is None:
            p.trailers.append({"skip": True, "id": bid, "commit": c})
            continue
        need_status = fm_str(doc, "status") != "done"
        need_audit = bid not in p.recorded
        if not need_status and not need_audit:
            continue
        src = fm_str(doc, "source_ref")
        ref = "%s (%s)" % (bid, src) if src else bid
        # date | what happened | ref | deviation | why  (STANDARD §4)
        # "why" cites the commit rather than the session: a sha is checkable years
        # later, and a chat transcript is not.
        line = (" %s " % AUDIT_SEP).join(
            [c["date"], c["subject"], ref, "-", "commit %s" % c["sha"]])
        p.trailers.append({"skip": False, "id": bid, "commit": c, "doc": doc,
                           "status": need_status, "audit": need_audit, "line": line})
        # The tree as this run will leave it, in BOTH modes. Before 0.40.0 report
        # mode skipped this, so a preview with --archive left out every item a
        # trailer was about to close — and --apply then moved it anyway.
        if need_status:
            doc["fm"]["status"] = "done"
        if need_audit and log_ok:
            p.recorded[bid] = {"date": c["date"], "why": "commit %s" % c["sha"]}

    if archive:
        judge(p, docs_root, backlog, list(settle), list(why or []))
        p.rewrites, p.left = link_plan(
            docs_root, dict((d["path"], archive_path(d["path"])) for _, _, d, _ in p.moves))
    return p


def judge(p, docs_root, backlog, settle, why):
    """Step 6 — what can leave the hot set. A pure predicate over frontmatter.

    Every hot document gets a verdict, not only the ones that move: the chain
    report prints why each of the others stays, and a reason computed anywhere
    else would be a second predicate free to disagree with this one.
    """
    issues = load(docs_root / "20_issues")
    proposals = load(docs_root / "21_proposals")
    decisions = load(docs_root / "22_decisions")
    p.docs = {"ISSUE": issues, "PROPOSAL": proposals, "DECISION": decisions,
              "BACKLOG": backlog}
    V = p.verdicts
    moving = set()
    wanted = dict(zip(settle, why + [""] * len(settle)))

    def move(kind, d, how):
        did = fm_str(d, "id")
        if did in moving:
            return
        moving.add(did)
        p.moves.append((kind, did, d, how))
        V[did] = verdict("moves", how)

    def terminal(d):
        # Never archive a done item whose audit line is missing: the folder
        # that gets read least is the worst place to lose a trace.
        return fm_str(d, "status") == "done" and fm_str(d, "id") in p.recorded

    def settle_line(did, what, members):
        ref = "%s (%s)" % (did, ", ".join(members)) if members else did
        return (" %s " % AUDIT_SEP).join(
            [today(), what, ref, "-", wanted.get(did) or "xác nhận trong docs-archive"])

    for d in backlog:
        bid = fm_str(d, "id")
        if d["archived"] or not bid:
            continue
        st = fm_str(d, "status")
        if terminal(d):
            move("BACKLOG", d, "done")
        elif st == "done":
            V[bid] = verdict("held", "no-audit")
        elif st in ("open", "in-progress"):
            V[bid] = verdict("inflight", st)
        else:
            V[bid] = verdict("held", "enum", field="status", value=st)

    for d in issues:
        if not d["archived"] and fm_str(d, "status") == "archived" and fm_str(d, "id"):
            move("ISSUE", d, "dropped")

    # A Decision (and the Proposal behind it) is terminal once every Backlog
    # item that cites it is done and audited. Derived from source_ref, never
    # declared — a "chain complete" field would be a second thing to keep true.
    #
    # Two shapes never become terminal by themselves, and --settle is how a person
    # says they are: an approved Decision no Backlog item cites (STANDARD §2 has
    # its three shapes — none is a broken chain, and none can be told apart from
    # the frontmatter), and a rejected one. Rejected is not finished by rule
    # either: measured on a real repo, the one rejected Decision meant "deferred,
    # reopen when a second process is needed", and archiving that on a predicate
    # would file a live condition in the folder nobody reads.
    for dec in decisions:
        did = fm_str(dec, "id")
        if dec["archived"] or not did:
            continue
        out = fm_str(dec, "outcome")
        pref = fm_str(dec, "proposal_ref")
        items = [d for d in backlog if cites(fm_str(d, "source_ref"), did)]
        members = []
        if out == "approved" and items and all(terminal(d) for d in items):
            how = "chain"
        elif did in wanted and (out == "rejected" or (out == "approved" and not items)):
            how = "settled"
            shape = "rejected" if out == "rejected" else "no-ticket"
            members = [pref] if pref else []
            for pr in proposals:
                if pref and fm_str(pr, "id") == pref and fm_str(pr, "issue_ref"):
                    members.append(fm_str(pr, "issue_ref"))
            what = ("đóng tay: Decision rejected, chain không còn việc" if shape == "rejected"
                    else "đóng tay: chain xong mà không sinh Backlog item")
            p.settled.append({"kind": "DECISION", "id": did, "doc": dec, "shape": shape,
                              "line": settle_line(did, what, members)})
        else:
            if out == "approved" and not items:
                # The three-route lookup STANDARD §2 asks for: a ticket that cites
                # the Issue behind this Decision's Proposal is the "recording
                # shipped work" shape, and reads as no ticket at all otherwise.
                via = []
                for pr in proposals:
                    if pref and fm_str(pr, "id") == pref:
                        iref = fm_str(pr, "issue_ref")
                        via = [(fm_str(d, "id"), iref) for d in backlog
                               if iref and cites(fm_str(d, "source_ref"), iref)]
                V[did] = verdict("held", "no-ticket", via=via)
            elif out == "approved":
                V[did] = verdict("waits", "items",
                                 on=[fm_str(d, "id") for d in items if not terminal(d)])
            elif out == "rejected":
                V[did] = verdict("held", "rejected")
            else:
                V[did] = verdict("held", "enum", field="outcome", value=out)
            continue
        move("DECISION", dec, how)
        for pr in proposals:
            if not pr["archived"] and pref and fm_str(pr, "id") == pref:
                move("PROPOSAL", pr, how)

    # A Proposal nothing has decided on is simply waiting. One whose Decision is
    # already in _archive/ follows it — terminal for the reason its Decision is,
    # and otherwise stranded forever, since the pass above only ever moves a
    # Proposal together with a Decision that is still hot.
    for pr in proposals:
        prid = fm_str(pr, "id")
        if pr["archived"] or not prid or prid in moving:
            continue
        decs = [dec for dec in decisions if cites(fm_str(dec, "proposal_ref"), prid)]
        if not decs:
            V[prid] = verdict("inflight", "awaiting-decision")
        elif any(dec["archived"] for dec in decs):
            move("PROPOSAL", pr, "chain")
        else:
            V[prid] = verdict("waits", "decision", on=[fm_str(dec, "id") for dec in decs])

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
    # Read this run's own `moving`, never the filesystem. Under --apply the
    # Proposal above has not moved yet at the moment its Issue is judged here.
    for iss in issues:
        iid = fm_str(iss, "id")
        if iss["archived"] or not iid or iid in moving:
            continue
        st = fm_str(iss, "status")
        if st in ("exploring", "open"):
            V[iid] = verdict("inflight", st)
            continue
        if st != "promoted":
            V[iid] = verdict("held", "enum", field="status", value=st)
            continue
        props = [x for x in proposals if cites(fm_str(x, "issue_ref"), iid)]
        items = [d for d in backlog if cites(fm_str(d, "source_ref"), iid)]
        # No successor at all is a broken chain, not a finished one, and the
        # least-read folder is the worst place to put it. The validator's
        # [ref] check owns that case — unless a person says the work went
        # elsewhere, which is what `status: archived` has always declared.
        if not props and not items:
            if iid in wanted:
                iss["fm"]["status"] = "archived"
                p.settled.append({"kind": "ISSUE", "id": iid, "doc": iss,
                                  "shape": "no-successor",
                                  "line": settle_line(iid, "đóng tay: Issue promoted không có "
                                                      "successor, đặt status: archived", [])})
                move("ISSUE", iss, "settled")
            else:
                V[iid] = verdict("held", "no-successor", named_in=mentions(p, iid))
            continue
        wait = [fm_str(x, "id") for x in props
                if not (x["archived"] or fm_str(x, "id") in moving)]
        wait += [fm_str(d, "id") for d in items if not terminal(d)]
        if wait:
            V[iid] = verdict("waits", "successors", on=wait)
            continue
        move("ISSUE", iss, "chain")

    # --settle is a declaration about exactly three shapes. Anything else named
    # is refused with the reason, never stretched to fit: a settle that moved an
    # open ticket would be the one way this script could hide unfinished work.
    for sid in settle:
        if any(s["id"] == sid for s in p.settled):
            continue
        v = V.get(sid)
        if sid in moving:
            p.refused.append((sid, "moves anyway — its chain is complete"))
        elif v is None:
            known = any(fm_str(d, "id") == sid for ds in p.docs.values() for d in ds)
            p.refused.append((sid, "already in _archive/" if known
                              else "no Issue or Decision has this id"))
        else:
            p.refused.append((sid, "settle takes an approved Decision no Backlog item "
                              "cites, a rejected Decision, or a promoted Issue with no "
                              "successor — this one is %s: %s" % (v["state"], v["shape"])))


def execute(root, p):
    """Write exactly what `plan()` decided. Returns the number of actions."""
    docs_root = root / "docs"
    actions = 0
    for t in p.trailers:
        if t["skip"]:
            continue
        if t["status"]:
            set_status(t["doc"]["path"], "done")
        if t["audit"]:
            append_audit(docs_root, t["line"])
        actions += 1
    for s in p.settled:
        if s["kind"] == "ISSUE":
            set_status(s["doc"]["path"], "archived")
        append_audit(docs_root, s["line"])
    if not p.moves:
        return actions
    # Re-plan the links now: the status writes above changed the text of the
    # very files whose links are about to be rewritten, and writing the
    # preview's copy back would undo them.
    moves = dict((d["path"], archive_path(d["path"])) for _, _, d, _ in p.moves)
    p.rewrites, p.left = link_plan(docs_root, moves)
    for _, _, d, _ in p.moves:
        move_to_archive(root, d["path"])
        actions += 1
    for f, text, _ in p.rewrites:
        moves.get(f, f).write_text(text, encoding="utf-8")
    return actions


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

    p = plan(root, archive=do_archive)
    pending = []
    for t in p.trailers:
        c = t["commit"]
        if t["skip"]:
            pending.append("SKIP  %s — commit %s claims it, but no Backlog item has that id"
                           % (t["id"], c["sha"]))
            continue
        what = []
        if t["status"]:
            what.append("status -> done")
        if t["audit"]:
            what.append("audit line")
        pending.append("CLOSE %s — %s  [%s]" % (t["id"], ", ".join(what), c["sha"]))
    for kind, did, d, _ in p.moves:
        pending.append("ARCHIVE %s %s — %s" % (kind, did, d["path"].name))

    if not pending:
        print("docs-close: nothing to do — no unrecorded Closes: trailer, "
              "nothing terminal to archive")
        return 0

    actions = execute(root, p) if apply_ else 0
    for line in pending:
        print(line)
    for f, old, new in p.left:
        print("LINK  %s: `%s` -> `%s` — layer 1 or audit log, not rewritten"
              % (f.relative_to(root), old, new))
    n = sum(len(c) for _, _, c in p.rewrites)
    if apply_:
        if n:
            print("docs-close: rewrote %d relative link(s) in %d file(s) so they still "
                  "resolve after the move." % (n, len(p.rewrites)))
        print("docs-close: applied %d change(s). Re-run docs_render.sh — "
              "docs/INDEX.md and docs/MAP.tsv are now stale." % actions)
        return 0
    if n:
        print("docs-close: the moves above also rewrite %d relative link(s) in %d file(s)."
              % (n, len(p.rewrites)))
    print("docs-close: %d pending change(s). Re-run with --apply to write them."
          % len(pending))
    return 1


if __name__ == "__main__":
    sys.exit(main())
