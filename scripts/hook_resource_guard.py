"""docs-kit PreToolUse worker (Bash): the crew resource-guard.

A shared rig (e2e harness, stable local env) is a lock with a queue, not a
role (EXECUTION §5). This worker notices a Bash command that looks like it
touches a declared resource while nobody holds that resource's lock, and says
so — to the user, once, before the command runs.

WHY WARN-ONLY (always, in 0.26.0 — no enforce path for this hook):
    Substring patterns over one command string measure the cooperative and
    miss the forgetful: a wrapper script slips through unlogged. That ceiling
    is declared in EXECUTION §8 rather than papered over, and a deny built on
    such evidence would punish exactly the sessions that cooperate. The real
    fence is `crew lock` and the role files; this is the auxiliary net.

Fail open everywhere: a config or state dir this worker cannot read yields
silence, never a crash — same doctrine as the explain-gate.
"""
import json
import os
import subprocess
import sys


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
    # Sibling of the MAIN worktree (EXECUTION §4) — same resolution as the
    # crew CLI, so both look at the same lock files.
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


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    tool_input = data.get("tool_input") or {}
    command = ""
    if isinstance(tool_input, dict):
        command = str(tool_input.get("command") or "")
    if not command:
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
    resources = crew.get("resources")
    if not isinstance(resources, dict) or not resources:
        return

    low = command.lower()
    unlocked = []
    sd = state_dir(root)
    for name, spec in resources.items():
        pats = (spec or {}).get("patterns") if isinstance(spec, dict) else None
        if not isinstance(pats, list):
            continue
        if not any(str(p).lower() in low for p in pats):
            continue
        lock = os.path.join(sd, "locks", "%s.lock" % name) if sd else None
        if lock and os.path.isfile(lock):
            continue  # held by someone — the queue is working
        unlocked.append(name)

    if not unlocked:
        return
    names = ", ".join(sorted(unlocked))
    print(json.dumps({
        "systemMessage": (
            "docs-kit crew [resource:no-lock %s]: this command matches the "
            "patterns of a declared shared resource and no session holds its "
            "lock. Acquire first — scripts/crew lock acquire <resource> <nnn> "
            "(EXECUTION §5). This is a warning, not a block." % names
        )
    }))


main()
sys.exit(0)
