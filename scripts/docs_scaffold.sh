#!/usr/bin/env bash
# docs_scaffold.sh — create the three-layer docs skeleton from the plugin templates.
#
# Deterministic, no LLM. Called by the docs-init skill (or manually).
#
# Usage:  docs_scaffold.sh [--sync] [target_root]   (default: current directory)
#         Creates <target_root>/docs from <plugin>/templates/docs.
#
#         --sync reconciles an EXISTING docs/ with the template tree: it creates
#         only what is missing and never overwrites, edits, or deletes a single
#         existing file. That is how a repo scaffolded by an older docs-kit picks
#         up a folder a later version added (04_api arrived in 0.20.0), and it
#         replaces the hand-rolled `cp -Rn` docs-init used to ask an agent to
#         perform — a careful file operation belongs in a script, not in a prompt.
#
# Exit:   0 = created / synced · 2 = setup error (templates missing)
#         3 = plain mode and <target_root>/docs already exists (NOTHING touched —
#             the skill must report the situation and ask the user; never
#             auto-merge), or --sync and docs/ does not exist yet
#
# Behavior on success:
#   - copies the full 16-folder template tree (every folder ships a seed file)
#   - substitutes {{DOCS_KIT_DATE}} with today's date in 92_audit/LOG.md
#   - prints the created file list, then "SCAFFOLD OK"

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES="$PLUGIN_ROOT/templates/docs"

SYNC=0
case "${1:-}" in
  --sync) SYNC=1; shift ;;
esac

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

if [ "$SYNC" -eq 1 ]; then
  if [ ! -d "$TARGET" ]; then
    echo "SYNC REFUSED: $TARGET does not exist — run docs_scaffold.sh without --sync first."
    exit 3
  fi
  # Copy only what is absent. Never overwrite: an existing file is the repo's
  # content, and this script has no way to tell an edited template from a
  # deliberate rewrite — so it does not get to guess.
  created=0
  ( cd "$TEMPLATES" && find . -type f ) | sed 's|^\./||' | LC_ALL=C sort > "$TARGET_ROOT/.docs-kit-sync.$$"
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    if [ ! -e "$TARGET/$rel" ]; then
      mkdir -p "$TARGET/$(dirname "$rel")"
      cp "$TEMPLATES/$rel" "$TARGET/$rel" || { echo "SYNC ERROR: copy failed for $rel"; exit 2; }
      echo "  added docs/$rel"
      created=$((created + 1))
    fi
  done < "$TARGET_ROOT/.docs-kit-sync.$$"
  rm -f "$TARGET_ROOT/.docs-kit-sync.$$"

  # A folder the template ships but that holds no seed file would be invisible to
  # the loop above, so assert the shape separately.
  for d in 00_roadmap 01_products 02_architecture 03_business-logic 04_api \
           20_issues 21_proposals 22_decisions 23_backlog 30_conventions \
           40_services 50_runbooks 60_fe-integration 70_deploy 92_audit 93_qa; do
    if [ ! -d "$TARGET/$d" ]; then
      mkdir -p "$TARGET/$d"
      echo "  added docs/$d/"
      created=$((created + 1))
    fi
  done

  if [ "$created" -eq 0 ]; then
    echo "SYNC OK — nothing to add; docs/ already has every folder this version ships"
  else
    echo "SYNC OK — $created item(s) added, nothing overwritten"
  fi
  exit 0
fi

if [ -e "$TARGET" ]; then
  echo "SCAFFOLD REFUSED: $TARGET already exists — nothing was touched."
  echo "Existing top-level entries:"
  ls -1 "$TARGET" | sed 's/^/  - /'
  echo "Standard folders present/missing:"
  for d in 00_roadmap 01_products 02_architecture 03_business-logic 04_api \
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

# Sanity: every standard folder must exist after the copy (guards template drift).
for d in 00_roadmap 01_products 02_architecture 03_business-logic 04_api \
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
