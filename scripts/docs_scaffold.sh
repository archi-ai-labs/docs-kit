#!/usr/bin/env bash
# docs_scaffold.sh — create the three-layer docs skeleton from the plugin templates.
#
# Deterministic, no LLM. Called by the docs-init skill (or manually).
#
# Usage:  docs_scaffold.sh [target_root]    (default: current directory)
#         Creates <target_root>/docs from <plugin>/templates/docs.
#
# Exit:   0 = created · 2 = setup error (templates missing)
#         3 = <target_root>/docs already exists (NOTHING touched — the skill
#             must report the situation and ask the user; never auto-merge)
#
# Behavior on success:
#   - copies the full 15-folder template tree (every folder ships a seed file)
#   - substitutes {{DOCS_KIT_DATE}} with today's date in 92_audit/LOG.md
#   - prints the created file list, then "SCAFFOLD OK"

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES="$PLUGIN_ROOT/templates/docs"

TARGET_ROOT="${1:-.}"
if [ ! -d "$TARGET_ROOT" ]; then
  echo "SCAFFOLD ERROR: target root '$TARGET_ROOT' is not a directory"
  exit 2
fi
TARGET_ROOT="$(cd "$TARGET_ROOT" && pwd)"
TARGET="$TARGET_ROOT/docs"

if [ ! -d "$TEMPLATES" ]; then
  echo "SCAFFOLD ERROR: template tree not found at $TEMPLATES (broken plugin install)"
  exit 2
fi

if [ -e "$TARGET" ]; then
  echo "SCAFFOLD REFUSED: $TARGET already exists — nothing was touched."
  echo "Existing top-level entries:"
  ls -1 "$TARGET" | sed 's/^/  - /'
  echo "Standard folders present/missing:"
  for d in 00_roadmap 01_products 02_architecture 03_business-logic \
           20_issues 21_proposals 22_decisions 23_backlog 30_conventions \
           40_services 50_runbooks 60_fe-integration 70_deploy 92_audit 93_qa; do
    if [ -d "$TARGET/$d" ]; then echo "  present: $d"; else echo "  MISSING: $d"; fi
  done
  exit 3
fi

cp -R "$TEMPLATES" "$TARGET" || { echo "SCAFFOLD ERROR: copy failed"; exit 2; }

# Stamp the install date into the audit log baseline entries (portable sed: no -i).
TODAY="$(date +%Y-%m-%d)"
LOG="$TARGET/92_audit/LOG.md"
if [ -f "$LOG" ]; then
  sed "s/{{DOCS_KIT_DATE}}/$TODAY/g" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# Sanity: all 14 folders must exist after the copy (guards template drift).
for d in 00_roadmap 01_products 02_architecture 03_business-logic \
         20_issues 21_proposals 22_decisions 23_backlog 30_conventions \
         40_services 50_runbooks 60_fe-integration 70_deploy 92_audit 93_qa; do
  if [ ! -d "$TARGET/$d" ]; then
    echo "SCAFFOLD ERROR: expected folder $d missing after copy (broken template tree)"
    exit 2
  fi
done

echo "Created under $TARGET:"
find "$TARGET" -type f | LC_ALL=C sort | sed "s|^$TARGET_ROOT/|  |"
echo "SCAFFOLD OK"
exit 0
