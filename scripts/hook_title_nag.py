"""docs-kit Stop-hook worker: a crew session whose title no longer tells the truth.

WHY THIS EXISTS:
    The session title is the ONLY place the crew model is visible from outside a
    session — `crew status` derives every state from git, so the board is right
    whatever the title says, but the user's session list is not. An executor is
    born `processing` and moves to `finishing` the moment it writes the trailer
    (EXECUTION §3), and step 4b of the executor hat says to re-run
    `scripts/crew name executor` right there. Reported in practice: that step is
    the one most often skipped, so sessions end sitting at `processing` and the
    list reads as work still in flight.

WHY IT SHELLS OUT INSTEAD OF COMPUTING THE TITLE:
    The grammar is derived from git in exactly one place (`crew name`), and the
    CLI carries a comment forbidding anything else from spelling it out again.
    This asks that one place, with `--want`, and only compares strings.

WHY WARN-ONLY:
    Same doctrine as the other hooks (EXECUTION §12): a Stop hook that blocks
    teaches people to switch hooks off, which loses every warning. Never blocks,
    always exits 0, silent whenever anything is uncertain.

Silent when: the repo has no `scripts/crew`, the transcript has no title, the
title is not a crew title, `crew name --want` fails for any reason, or the title
already matches.
"""
import json
import os
import re
import subprocess
import sys

TITLE_RE = re.compile(r"·\s*crew/([a-z][a-z-]*)\s*$")
TICKET_RE = re.compile(r"·\s*b([0-9]{3,})\s*·")


def last_title(path):
    """The last custom-title record in the transcript, or ""."""
    title = ""
    try:
        with open(path, errors="replace") as f:
            for line in f:
                if '"custom-title"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("type") == "custom-title" and rec.get("customTitle"):
                    title = rec["customTitle"]
    except Exception:
        return ""
    return title.strip()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    cwd = data.get("cwd") or os.getcwd()
    transcript = data.get("transcript_path") or ""
    crew = os.path.join(cwd, "scripts", "crew")
    if not os.path.isfile(crew) or not transcript or not os.path.isfile(transcript):
        return

    got = last_title(transcript)
    role = TITLE_RE.search(got)
    if not role:
        return

    argv = ["bash", crew, "name", role.group(1)]
    # An executor session names its ticket; every other hat takes no number. A
    # wrong `processing`/`finishing` half still leaves the b<nnn> readable, which
    # is the part this needs.
    tick = TICKET_RE.search(got)
    if tick:
        argv.append(tick.group(1))
    argv.append("--want")

    try:
        r = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=20)
    except Exception:
        return
    if r.returncode != 0:
        return
    want = (r.stdout or "").strip()
    if not want or want == got:
        return

    print(json.dumps({"systemMessage": "\n".join([
        "crew: this session's title no longer matches what git says.",
        "  now  : %s" % got,
        "  true : %s" % want,
        "Retitle it — in the app the session can retitle itself; in a terminal:",
        "",
        "  /rename %s" % want,
    ])}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a hook must never break the user's session
    sys.exit(0)
