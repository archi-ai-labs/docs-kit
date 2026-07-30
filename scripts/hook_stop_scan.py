"""docs-kit Stop-hook worker: detect sensitive edits without docs traceability.

WHY WARN-ONLY (do not "fix" this into a block):
    These enforcement rules have not been battle-tested across real projects yet.
    Blocking on a false positive teaches users to disable the hook entirely,
    which loses ALL enforcement. Warn now; promote to block only after the
    trigger rules have been tuned in practice. Deterministic — never calls an LLM.

Logic:
  1. Read hook JSON from stdin (needs `cwd` and `transcript_path`).
  2. Guard: only act in repos that actually use docs-kit (docs/ skeleton present).
  3. Load sensitive path patterns from <cwd>/.docs-kit.json (`sensitive_paths`),
     falling back to **/schema/**, **/api/**, **/migrations/**.
  4. Scan the session transcript (JSONL):
       - collect Edit/Write file paths matching a sensitive pattern
         (paths under docs/ are never sensitive-zone code);
       - mark the session "engaged" with the docs workflow if it edited files
         under docs/20_issues|21_proposals|22_decisions, or if any transcript
         line mentions a concrete ISSUE-NNN / DECISION-NNN id.
         Known trade-off, accepted for a warn-only hook: merely READING a doc
         that contains a numbered id also counts as engaged (false negative,
         never a false positive). Tune after real-world use.
  5. Sensitive edits + no engagement → emit a systemMessage reminder to run
     /docs-kit:docs-sync. Otherwise stay silent. Always exit 0.
"""
import fnmatch
import json
import os
import re
import sys

DEFAULT_PATTERNS = ["**/schema/**", "**/api/**", "**/migrations/**"]
ID_RE = re.compile(r"\b(?:ISSUE|DECISION)-[0-9]{3,}\b")
DOCS_ENGAGE_RE = re.compile(r"(^|/)docs/(20_issues|21_proposals|22_decisions)/")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    cwd = data.get("cwd") or os.getcwd()
    transcript_path = data.get("transcript_path") or ""
    docs_root = os.path.join(cwd, "docs")

    # Repo doesn't use docs-kit → never nag.
    if not (
        os.path.isdir(os.path.join(docs_root, "22_decisions"))
        or os.path.isfile(os.path.join(docs_root, "README.md"))
    ):
        return
    if not transcript_path or not os.path.isfile(transcript_path):
        return

    patterns = list(DEFAULT_PATTERNS)
    cfg_path = os.path.join(cwd, ".docs-kit.json")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as fh:
                cfg = json.load(fh)
            loaded = cfg.get("sensitive_paths")
            if isinstance(loaded, list) and all(isinstance(p, str) for p in loaded):
                patterns = loaded
        except Exception:
            pass  # malformed config → keep defaults

    def is_sensitive(path):
        rel = path
        if os.path.isabs(path):
            try:
                rel = os.path.relpath(path, cwd)
            except ValueError:
                rel = path
        rel = rel.replace(os.sep, "/").lstrip("./")
        for pat in patterns:
            if fnmatch.fnmatch(rel, pat):
                return True
            # "**/x/**" should also match at the repo root ("x/file").
            if pat.startswith("**/") and fnmatch.fnmatch(rel, pat[3:]):
                return True
        return False

    sensitive_edits = set()
    engaged = [False]

    def note_edit(path):
        rel = path.replace("\\", "/")
        if DOCS_ENGAGE_RE.search(rel):
            engaged[0] = True
            return
        if re.search(r"(^|/)docs/", rel):
            return  # docs content itself is never sensitive-zone code
        if is_sensitive(rel):
            try:
                shown = os.path.relpath(rel, cwd) if os.path.isabs(rel) else rel
            except ValueError:
                shown = rel
            sensitive_edits.add(shown.replace(os.sep, "/"))

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
                # Any concrete id mention anywhere (text, tool input, file
                # content, tool result) counts as referencing the docs workflow.
                if not engaged[0] and ID_RE.search(line):
                    engaged[0] = True
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                walk(obj)
    except Exception:
        return

    if sensitive_edits and not engaged[0]:
        shown = sorted(sensitive_edits)
        listed = ", ".join(shown[:3]) + (" …" if len(shown) > 3 else "")
        print(json.dumps({
            "systemMessage": (
                "docs-kit: this session edited sensitive paths ({}) but never "
                "created or referenced an Issue/Decision. Per the trigger rules "
                "(docs/README.md), schema/API/boundary changes need a Decision "
                "and finished work needs Backlog + audit updates. Run "
                "/docs-kit:docs-sync to reconcile docs/."
            ).format(listed),
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a hook must never break the user's session
    sys.exit(0)
