"""docs-kit: the crew block of CLAUDE.md, held against the one this kit ships.

WHY THIS EXISTS: crew-init appends templates/crew/claude-md-crew-snippet.md to
CLAUDE.md once, and before 0.44.1 nothing refreshed it: crew-update re-stamped
scripts/crew, the role files and .claude/crew/, and never read CLAUDE.md. The
block is loaded into every session of the repo, so a stale one teaches every
session an old rule. Measured 2026-09-27 on the four crew repos of one machine:
all four carried the pre-0.42.0 block, whose title grammar ends in
`· crew/executor` and which says one session per ticket, three releases after
both rules changed.

WHY A SCRIPT AND NOT AN EDIT: CLAUDE.md is the user's file, and everything
outside the two markers is theirs. Replacing by byte offsets leaves every other
byte of the file as it was, which a free-hand edit cannot promise. The skill
asks first; this only does what the answer allows.

A repo without the markers declined the block at crew-init, so --apply never
adds one. A start marker without its end, or two blocks, is left alone: there is
no way to tell which text the user meant to keep.

Usage:
  crew_snippet.py [REPO]           report; writes nothing
  crew_snippet.py --apply [REPO]   replace the block with the kit's, nothing else
Output:
  SNIPPET current                  the block equals the kit's
  SNIPPET stale <now> <kit>        it differs; sizes in bytes
  SNIPPET absent                   no CLAUDE.md, or no crew markers in it
  SNIPPET broken                   markers unpaired or repeated: never touched
  SNIPPET replaced <now> <kit>     --apply wrote the kit's block
Exit 0, 1 when --apply could not write, 2 on usage.
"""
import os
import sys

START = "<!-- docs-kit:crew:start"
END = "<!-- docs-kit:crew:end -->"
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(KIT, "templates", "crew", "claude-md-crew-snippet.md")


def span(text):
    """(start, end) of the block, end just past the end marker; None if absent;
    "broken" if the markers are not exactly one ordered pair."""
    ns, ne = text.count(START), text.count(END)
    if ns == 0 and ne == 0:
        return None
    if ns != 1 or ne != 1:
        return "broken"
    s = text.rfind("\n", 0, text.index(START)) + 1   # the marker's line start
    e = text.index(END) + len(END)
    return (s, e) if e > s else "broken"


def main(argv):
    apply = "--apply" in argv
    rest = [a for a in argv if a != "--apply"]
    if len(rest) > 1 or any(a.startswith("-") for a in rest):
        print("usage: crew_snippet.py [--apply] [REPO]")
        return 2
    path = os.path.join(rest[0] if rest else ".", "CLAUDE.md")
    try:
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
    except OSError:
        print("SNIPPET absent")
        return 0
    with open(TEMPLATE, encoding="utf-8") as f:
        kit = f.read().rstrip("\n")
    if "\r\n" in text:
        kit = kit.replace("\n", "\r\n")

    where = span(text)
    if where is None:
        print("SNIPPET absent")
        return 0
    if where == "broken":
        print("SNIPPET broken")
        return 0
    s, e = where
    now = text[s:e]
    if now == kit:
        print("SNIPPET current")
        return 0
    sizes = "%d %d" % (len(now.encode("utf-8")), len(kit.encode("utf-8")))
    if not apply:
        print("SNIPPET stale " + sizes)
        return 0
    try:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text[:s] + kit + text[e:])
    except OSError as err:
        print("SNIPPET write failed: %s" % err)
        return 1
    print("SNIPPET replaced " + sizes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
