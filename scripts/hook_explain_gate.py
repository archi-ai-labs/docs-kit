"""docs-kit PreToolUse worker (AskUserQuestion): the crew explain-gate.

Gate 1 of EXECUTION §7 wants an explanation on the table before a session asks
the user to decide: a drawing-tool call, a picture file sent to render, or a
declared fast lane. This worker looks for any of them in this turn's replies,
and warns when none is there.

WHY WARN-ONLY BY DEFAULT (promote per repo, never here):
    STANDARD §8 doctrine: blocking on a false positive teaches users to disable
    the hook, which loses all enforcement. `.docs-kit.json` "crew":
    {"enforce": true} turns the warning into a deny for THAT repo once the
    rules are tuned in practice (EXECUTION §8).

Three rules this file must never lose (each learned from a hook that failed):
 1. Read transcript EVENTS, never the transcript as one string. The origin
    repo's first gate string-matched the whole text; its own refusal message
    contained both strings it hunted, so it blocked exactly once and then held
    the door open forever. Corollary: no output below ever contains the
    literal marker line this worker scans for.
 2. Fail open, with a trail: transcript unreadable -> allow, plus one line in
    the crew state dir's gate.log, so silence-from-broken never looks like
    silence-from-clean.
 3. The shipped test (scripts/crew_test.sh) asserts the reason TAG
    ([gate:no-draw]), not the exit code — red for the right reason.

Evidence accepted, scanning backwards to the last human turn:
  - an assistant tool_use whose name is in crew.draw_tools
    (default: mcp__visualize__show_widget, Artifact)
  - an assistant SendUserFile tool_use that shows a picture file: at least
    one path with a picture extension, and a display other than "attach".
    It is matched on its payload and is NOT read through draw_tools, because
    crew-init writes the default list into .docs-kit.json verbatim (3 of the
    4 crew repos measured for 0.40.4 carry it), so a new default entry would
    never reach them. A name match alone would also count a changelog sent
    as an attachment.
  - an assistant TEXT block carrying the one-line fast-lane marker of
    EXECUTION §7 — matched at line start, in assistant-authored text only.
    A tool_result event also has type "user" but carries no text block, so it
    never terminates the scan; only a human turn does.

Only the main transcript counts. A sub-agent's events live in
`<session>/subagents/`, which the Stop scan reads since 0.40.1; this worker
must not follow it there. Nothing a sub-agent writes reaches the user as a
reply, so its marker or its drawing unlocking the parent's question would
repeat rule 1's failure: text the user never saw, opening the gate
(crew_test.sh asserts it).
"""
import datetime
import json
import os
import re
import subprocess
import sys

DEFAULT_DRAW = ["mcp__visualize__show_widget", "Artifact"]
MARKER_RE = re.compile(r"^LANE:\s*fast\b", re.M)
FILE_TOOL = "SendUserFile"
PICTURE_EXT = (".html", ".htm", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp")


def find_root(start):
    d = os.path.abspath(start or ".")
    for _ in range(12):
        if os.path.isfile(os.path.join(d, ".docs-kit.json")):
            return d
        nxt = os.path.dirname(d)
        if nxt == d:
            return None
        d = nxt
    return None


def state_dir(root):
    # Sibling of the MAIN worktree (EXECUTION §4), resolved via git so the
    # answer is identical from the main tree and from any -b worktree.
    try:
        out = subprocess.run(
            ["git", "-C", root, "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        for line in out.splitlines():
            if line.startswith("worktree "):
                main = line[len("worktree "):]
                return os.path.join(
                    os.path.dirname(main), os.path.basename(main) + "-crew")
    except Exception:
        pass
    return None


def log_open(root, why):
    # Best-effort: the trail must never become a new way to crash the gate.
    try:
        sd = state_dir(root)
        if not sd:
            return
        os.makedirs(sd, exist_ok=True)
        with open(os.path.join(sd, "gate.log"), "a") as f:
            ts = datetime.datetime.now().isoformat(timespec="seconds")
            f.write("%s OPEN %s\n" % (ts, why))
    except Exception:
        pass


def blocks(msg):
    c = (msg or {}).get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def shows_picture(block):
    # An omitted display lets the host decide by file type, and it renders
    # HTML and images, so only an explicit "attach" rules the send out.
    inp = block.get("input") or {}
    if inp.get("display") == "attach":
        return False
    files = inp.get("files") or []
    if isinstance(files, str):
        files = [files]
    return any(isinstance(p, str) and p.lower().endswith(PICTURE_EXT)
               for p in files)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    root = find_root(data.get("cwd"))
    if not root:
        return
    try:
        with open(os.path.join(root, ".docs-kit.json")) as f:
            conf = json.load(f)
    except Exception:
        return
    crew = (conf or {}).get("crew")
    if not isinstance(crew, dict):
        return
    draw = crew.get("draw_tools") or DEFAULT_DRAW
    enforce = bool(crew.get("enforce"))

    events = []
    try:
        with open(data.get("transcript_path") or "") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        log_open(root, "transcript unreadable session=%s"
                 % data.get("session_id", "?"))
        return  # rule 2: fail open

    evidence = None
    for ev in reversed(events):
        etype = ev.get("type")
        msg = ev.get("message") or {}
        if etype == "user":
            if any(b.get("type") == "text" for b in blocks(msg)):
                break  # the last human turn — scan no further back
            continue  # a tool_result event, not a human turn
        if etype != "assistant":
            continue
        for b in blocks(msg):
            if b.get("type") == "tool_use" and b.get("name") in draw:
                evidence = "draw"
                break
            if (b.get("type") == "tool_use" and b.get("name") == FILE_TOOL
                    and shows_picture(b)):
                evidence = "file"
                break
            if b.get("type") == "text" and MARKER_RE.search(b.get("text") or ""):
                evidence = "lane"
                break
        if evidence:
            break

    if evidence:
        return  # gate satisfied — stay silent

    # Rule 1 corollary: describe the marker, never quote it.
    guidance = (
        "docs-kit crew [gate:no-draw]: this question is about to reach the "
        "user without a gate-1 explanation in this turn's replies. Before "
        "asking, either show the decision (a BEFORE/AFTER diagram via a "
        "drawing tool, or a picture file sent to render) or declare the "
        "fast lane with its one-line marker — "
        "the marker format and the three lane questions are in "
        ".claude/crew/gates.md (EXECUTION §7)."
    )
    if enforce:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason":
                    guidance + " crew.enforce is on for this repo.",
            }
        }))
    else:
        # Warn-only: a systemMessage and no permission decision, so the
        # question still goes through and nothing about approval flow changes.
        print(json.dumps({
            "systemMessage": guidance + " This is a warning, not a block."
        }))


main()
sys.exit(0)
