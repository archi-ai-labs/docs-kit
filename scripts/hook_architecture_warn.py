"""docs-kit PostToolUse worker: warn on edits under the layer-1 folders
docs/02_architecture/ and docs/03_business-logic/.

WHY WARN-ONLY (do not "fix" this into a block):
    These enforcement rules have not been battle-tested across real projects yet.
    Blocking on a false positive teaches users to disable the hook entirely,
    which loses ALL enforcement. Warn now; promote to block only after the
    trigger rules have been tuned in practice. Deterministic — never calls an LLM.

Reads the hook JSON on stdin. If tool_input.file_path is under one of those
directories, emits hook JSON with:
  - systemMessage        → shown to the user
  - additionalContext    → injected for the agent so it can self-correct
Silent (no output) otherwise. Always exits 0.
"""
import json
import re
import sys

# The plugin's own template tree contains templates/docs/02_architecture/ — a
# path that ends in the very thing this hook looks for. Without this exemption
# the hook fires at anyone developing docs-kit itself, every time they touch a
# shipped template, which is exactly the false-positive class the warn-only
# note above says erodes the whole mechanism.
TEMPLATE_RE = re.compile(r"(^|/)templates/docs/")
LAYER1_RE = re.compile(r"(^|/)docs/(02_architecture|03_business-logic)/")

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool_input = data.get("tool_input") or {}
file_path = ""
if isinstance(tool_input, dict):
    file_path = str(tool_input.get("file_path") or "")

file_path = file_path.replace("\\", "/")
hit = LAYER1_RE.search(file_path)
if hit and not TEMPLATE_RE.search(file_path):
    folder = hit.group(2)
    subject = ("Architecture" if folder == "02_architecture" else "Business logic")
    warning = (
        "docs-kit: a file under docs/%s/ was just edited. "
        "%s is layer 1 — it may only be amended through the Decision "
        "workflow. Confirm an approved Decision covers this change and that its "
        "ref is recorded in the doc's amended_by list (- YYYY-MM-DD DECISION-NNN "
        "summary). If no Decision exists, revert the edit and create an Issue "
        "instead. This is a warning, not a block." % (folder, subject)
    )
    print(json.dumps({
        "systemMessage": warning,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": warning,
        },
    }))

sys.exit(0)
