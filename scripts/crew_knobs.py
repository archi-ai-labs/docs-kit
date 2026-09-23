"""docs-kit: the crew tuning knobs a repo carries at exactly the kit's default.

WHY THIS EXISTS: every reader of `.docs-kit.json` falls back to the kit's
default only when a key is ABSENT. crew-init used to copy EXECUTION §9's whole
block into the config, so a knob nobody tuned sat there as a frozen copy and
outranked every later change to the default. Measured 2026-09-24 on the four
crew repos of one machine: three carried reader_cap, wait_budget_min and
draw_tools, all nine entries equal to the default, none tuned; and 0.40.4 could
not move draw_tools' default for them.

A knob is a value the crew-init interview never asks for. The asked fields are
not knobs even when an answer equals the reader's fallback: `dev_branch: "main"`
in a repo whose dev branch IS main is a fact about the repo, and dropping it
would let a future default move it. `enforce` is not a knob here either:
STANDARD §8 fixes its default at false, so a written false can never stand in
the way of a kit change, and setup.md tells people to flip it in place.

Equality follows each reader, not JSON: scripts/crew's cfg() prints a list
space-joined and anything else with str(), and the explain-gate uses
`draw_tools or DEFAULT_DRAW` as a membership list. So `reader_cap: "4"` is
frozen, `reader_cap: 4.0` is not, and `draw_tools: []` is. Dropping a key this
reports therefore changes no behaviour at the moment it is dropped.
crew_test.sh asserts that KNOBS still matches the fallbacks in scripts/crew and
DEFAULT_DRAW in the hook, so the table cannot drift away from the readers.

Usage:
  crew_knobs.py [REPO]          report; writes nothing
  crew_knobs.py --drop [REPO]   remove exactly the keys the report names
Output:
  [knob:frozen] <key> = <json>  one line per knob at exactly the default
  [knob:dropped] <key>          --drop, one line per key removed
  KNOBS none | KNOBS off        nothing frozen | no crew key in the config
Exit 0, 1 when --drop could not write, 2 on usage.
"""
import json
import os
import sys

KNOBS = {
    "reader_cap": "4",
    "wait_budget_min": "30",
    "resetup_when": "package-lock.json yarn.lock pnpm-lock.yaml "
                    "requirements.txt go.sum Gemfile.lock Cargo.lock",
    "draw_tools": ["mcp__visualize__show_widget", "Artifact"],
}


def printed(v):
    # scripts/crew cfg(): what the shell receives for a present key.
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def frozen(key, value):
    if key == "draw_tools":
        if not isinstance(value, list):
            return False
        return set(value or KNOBS[key]) == set(KNOBS[key])
    return printed(value) == KNOBS[key]


def load(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return text, json.loads(text)


def main(argv):
    drop = "--drop" in argv
    rest = [a for a in argv if a != "--drop"]
    if len(rest) > 1 or any(a.startswith("-") for a in rest):
        print("usage: crew_knobs.py [--drop] [REPO]")
        return 2
    path = os.path.join(rest[0] if rest else ".", ".docs-kit.json")
    try:
        text, data = load(path)
    except Exception:
        print("KNOBS off")
        return 0
    crew = data.get("crew") if isinstance(data, dict) else None
    if not isinstance(crew, dict):
        print("KNOBS off")
        return 0

    hits = [k for k in KNOBS if k in crew and frozen(k, crew[k])]
    if not hits:
        print("KNOBS none")
        return 0
    if not drop:
        for k in hits:
            print("[knob:frozen] %s = %s" % (k, json.dumps(crew[k], ensure_ascii=False)))
        return 0

    # Same serialisation the configs were written with (crew-init's python3
    # json read-modify-write), so the diff is the dropped lines and nothing else.
    canonical = json.dumps(data, indent=2, ensure_ascii=False) + "\n" == text
    for k in hits:
        del crew[k]
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    except Exception as e:
        print("KNOBS write failed: %s" % e)
        return 1
    for k in hits:
        print("[knob:dropped] %s" % k)
    if not canonical:
        print("note: the file was not in 2-space JSON form, so other lines "
              "were re-indented too — read git diff before committing")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
