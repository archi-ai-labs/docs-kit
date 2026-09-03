"""docs-kit Stop-hook worker: report edits to code a document claims to describe.

WHY WARN-ONLY (do not "fix" this into a block):
    These enforcement rules have not been battle-tested across real projects yet.
    Blocking on a false positive teaches users to disable the hook entirely,
    which loses ALL enforcement. Warn now; promote to block only after the
    trigger rules have been tuned in practice. Deterministic — never calls an LLM.

WHY THIS ASKS A DIFFERENT QUESTION THAN IT USED TO (0.25.0):
    It used to ask "does this path look sensitive", matching `**/schema/**`,
    `**/api/**`, `**/migrations/**` against every edit. Measured on a real
    monorepo whose service directory is named `apps/api/`, that glob matched 57
    of 57 edited files — every test, every changelog — because "a directory
    called api" and "an API boundary" are not the same thing and a pattern cannot
    tell them apart. The warning fired in 15 of 36 sessions and, in that repo,
    could not be silenced at all: the engagement check looked for
    `docs/22_decisions/` while the repo used `docs/20_decisions/`.

    It now asks "does any document claim to describe this file", which is a fact
    the docs already state — a component names its `path/in/repo`, a figure fence
    takes a `code:` header — collected into `docs/MAP.tsv` by docs-render. A file
    nobody documents produces silence, however sensitive its path looks.

Logic:
  1. Read hook JSON from stdin (needs `cwd` and `transcript_path`).
  2. Guard: the repo declares itself a docs-kit repo (`.docs-kit.json` or
     `docs/22_decisions/`). `docs/README.md` alone is NOT enough — that is what
     made this fire in a repo using a different folder scheme entirely.
  3. Load `docs/MAP.tsv` (path → doc, claim, verified_at).
  4. Scan the transcript for Edit/Write paths, split into code edits and edits to
     documents under docs/.
  5. Report, grouped by DOCUMENT rather than by file:
       - a document whose claimed paths this session edited, unless the session
         also edited that document (it was already being kept up to date);
       - a file sitting beside a claimed file in the same directory that nothing
         claims — the "you added something next to a documented thing" signal.
  6. Silence in every other case. Always exit 0.
"""
import fnmatch
import json
import os
import subprocess
import sys

EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
MAX_DOCS_LISTED = 3
MAX_FILES_PER_DOC = 3


def load_map(docs_root):
    """docs/MAP.tsv → [(path, doc, claim, verified_at)].

    Comment lines carry the format; they are not data. A malformed line is
    skipped rather than raising, because a hook that crashes on a stray line is
    a hook the user turns off.
    """
    path = os.path.join(docs_root, "MAP.tsv")
    if not os.path.isfile(path):
        return None
    rows = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) == 4:
                    rows.append(tuple(parts))
    except Exception:
        return None
    return rows


def claims(rel, entry_path):
    """Does this map entry claim this edited file?

    Three shapes, all of them things authors actually write (STANDARD §7):
    an exact path, a directory prefix (`lib/data/`), and a glob
    (`lib/validators/*.schema.ts`).
    """
    if entry_path == rel:
        return True
    if entry_path.endswith("/") and rel.startswith(entry_path):
        return True
    if ("*" in entry_path or "?" in entry_path) and fnmatch.fnmatch(rel, entry_path):
        return True
    return False


def changed_since(cwd, rev):
    """Files changed between a rev and the WORKING TREE.

    Against the working tree, not HEAD: this runs at the end of a session, before
    the work is committed, and comparing against HEAD would hide exactly the
    changes that session just made. Same rule as the validator's [stale] check.
    """
    try:
        out = subprocess.run(["git", "-C", cwd, "diff", "--name-only", rev],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=10)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return set(out.stdout.decode("utf-8", "replace").split("\n"))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    cwd = data.get("cwd") or os.getcwd()
    transcript_path = data.get("transcript_path") or ""
    docs_root = os.path.join(cwd, "docs")

    # A repo that has not declared itself a docs-kit repo is never nagged. The old
    # guard accepted a bare docs/README.md, which every documented project has.
    if not (os.path.isfile(os.path.join(cwd, ".docs-kit.json"))
            or os.path.isdir(os.path.join(docs_root, "22_decisions"))):
        return
    if not transcript_path or not os.path.isfile(transcript_path):
        return

    rows = load_map(docs_root)

    code_edits = set()
    doc_edits = set()

    def note_edit(path):
        rel = path.replace("\\", "/")
        if os.path.isabs(rel):
            try:
                rel = os.path.relpath(rel, cwd)
            except ValueError:
                return
        rel = rel.replace(os.sep, "/").lstrip("./")
        if rel.startswith("../"):
            return  # an edit outside this repo is not this repo's business
        if rel.startswith("docs/"):
            doc_edits.add(rel)
        else:
            code_edits.add(rel)

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "tool_use" and node.get("name") in EDIT_TOOLS:
                tool_input = node.get("input") or {}
                if isinstance(tool_input, dict):
                    fp = tool_input.get("file_path") or tool_input.get("notebook_path")
                    if fp:
                        note_edit(str(fp))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                walk(obj)
    except Exception:
        return

    if not code_edits:
        return  # a docs-only session has nothing to reconcile

    if rows is None:
        # Said once, and only in a session that actually touched code: without the
        # map this hook cannot tell a documented file from any other, and guessing
        # from the path shape is the behaviour that was removed.
        print(json.dumps({
            "systemMessage": (
                "docs-kit: docs/MAP.tsv is missing, so edits cannot be matched to the "
                "documents that describe them. Run /docs-kit:docs-render to generate it."
            ),
        }))
        return

    # doc → {"files": set, "rev": verified_at}
    hit = {}
    claimed_files = set()
    for rel in sorted(code_edits):
        for entry_path, doc, claim, rev in rows:
            if not claims(rel, entry_path):
                continue
            claimed_files.add(rel)
            slot = hit.setdefault(doc, {"files": set(), "rev": rev})
            slot["files"].add(rel)

    # A document the session also edited was already being kept current; saying so
    # would be telling the user about work they just did. This replaces the old
    # "any ISSUE-NNN mentioned anywhere counts as engaged" heuristic, which
    # silenced the wrong sessions and could not be satisfied at all in a repo whose
    # decisions are not numbered that way.
    for doc in list(hit):
        if ("docs/" + doc) in doc_edits:
            del hit[doc]

    # Of the documents left, keep those the code has actually moved out from under.
    # An unverified document (no verified_at) cannot be proven stale — it is
    # reported as never-checked instead, which is a different and honest claim.
    stale, unverified = [], []
    for doc in sorted(hit):
        slot = hit[doc]
        rev = slot["rev"]
        files = sorted(slot["files"])
        if rev and rev != "-" and "<" not in rev:
            changed = changed_since(cwd, rev)
            if changed is None:
                unverified.append((doc, files, "verified_at '%s' is not a commit here" % rev))
            elif any(f in changed for f in files):
                stale.append((doc, files, "verified_at %s" % rev))
        else:
            unverified.append((doc, files, "no verified_at"))

    # A file with no claim at all, sitting in a directory where something else IS
    # claimed by name. That is the "added a sibling to a documented thing" case;
    # a directory nothing documents stays silent, and so does a directory claimed
    # as a whole (`lib/data/`), which already covers everything inside it.
    named_dirs = set()
    for entry_path, _doc, _claim, _rev in rows:
        if not entry_path.endswith("/") and "*" not in entry_path and "?" not in entry_path:
            named_dirs.add(os.path.dirname(entry_path))
    gaps = sorted(f for f in code_edits
                  if f not in claimed_files and os.path.dirname(f) in named_dirs)

    if not stale and not unverified and not gaps:
        return

    def fmt(entries, headline):
        out = []
        for doc, files, why in entries[:MAX_DOCS_LISTED]:
            shown = ", ".join(files[:MAX_FILES_PER_DOC])
            if len(files) > MAX_FILES_PER_DOC:
                shown += " (+%d more)" % (len(files) - MAX_FILES_PER_DOC)
            out.append("  docs/%s — %s [%s]" % (doc, shown, why))
        if len(entries) > MAX_DOCS_LISTED:
            out.append("  … and %d more document(s)" % (len(entries) - MAX_DOCS_LISTED))
        return [headline] + out

    lines = ["docs-kit: this session edited code that documents claim to describe."]
    if stale:
        lines += fmt(stale, "Changed since the document was last verified:")
    if unverified:
        lines += fmt(unverified, "Claimed by a document that has never been verified:")
    if gaps:
        shown = ", ".join(gaps[:MAX_FILES_PER_DOC])
        if len(gaps) > MAX_FILES_PER_DOC:
            shown += " (+%d more)" % (len(gaps) - MAX_FILES_PER_DOC)
        lines.append("Not claimed by any document, but beside files that are: " + shown)
    lines.append("Run /docs-kit:docs-sync to reconcile — it re-reads only these documents.")

    print(json.dumps({"systemMessage": "\n".join(lines)}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a hook must never break the user's session
    sys.exit(0)
