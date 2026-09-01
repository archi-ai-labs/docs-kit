#!/usr/bin/env bash
# docs-kit — stamp the crew layer into a target repo (the deterministic half of
# /docs-kit:crew-init; the interview and every write to CLAUDE.md or
# .docs-kit.json stay in the skill, behind AskUserQuestion).
#
# Usage: crew_scaffold.sh [--skip role,role] <target-repo-root>   (default: .)
#        --skip: role command files NOT to stamp (roles the interview found
#        absent in this repo — a stamped file for a ghost role is a wrong fact).
#
# Policy, same spirit as docs_scaffold.sh: ADD, never clobber. A file that
# already exists and differs from its template is left untouched and the new
# version lands beside it as <name>.new for a human merge; an identical file is
# skipped silently. This is also how /docs-kit:docs-upgrade re-stamps after a
# kit update without eating local edits.
#
# Exit: 0 = stamped/nothing to do · 2 = setup error
set -u

KIT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
SRC="$KIT/templates/crew"
SKIP=""
if [ "${1:-}" = "--skip" ]; then
  SKIP="${2:-}"
  shift 2
fi
TGT="${1:-.}"

[ -d "$SRC" ] || { echo "crew-scaffold: templates/crew missing in the kit" >&2; exit 2; }
[ -d "$TGT" ] || { echo "crew-scaffold: no such directory: $TGT" >&2; exit 2; }
TGT="$(cd "$TGT" && pwd)"
git -C "$TGT" rev-parse --show-toplevel >/dev/null 2>&1 \
  || { echo "crew-scaffold: $TGT is not a git repository" >&2; exit 2; }

STAMPED=0
KEPT=0
REVIEW=0

put() { # put <src> <dst> [exec]
  src="$1"; dst="$2"
  if [ ! -e "$dst" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    [ "${3:-}" = "exec" ] && chmod +x "$dst"
    echo "stamped: ${dst#"$TGT"/}"
    STAMPED=$((STAMPED + 1))
  elif cmp -s "$src" "$dst"; then
    KEPT=$((KEPT + 1))
  else
    cp "$src" "$dst.new"
    echo "review : ${dst#"$TGT"/}.new (local file differs — merge by hand)"
    REVIEW=$((REVIEW + 1))
  fi
}

put "$SRC/crew" "$TGT/scripts/crew" exec
for f in "$SRC"/commands/*.md; do
  b="$(basename "$f" .md)"
  case ",$SKIP," in
    *",$b,"*) echo "skipped: .claude/commands/$b.md (role declared absent)"; continue ;;
  esac
  put "$f" "$TGT/.claude/commands/$(basename "$f")"
done
for f in "$SRC"/docs/*.md; do
  put "$f" "$TGT/.claude/crew/$(basename "$f")"
done

# crew rides the Backlog (EXECUTION §1) — a repo without one has nothing to run.
[ -d "$TGT/docs/23_backlog" ] \
  || echo "note   : docs/23_backlog/ missing — run /docs-kit:docs-init first; crew rides the Backlog"

echo "crew-scaffold: $STAMPED stamped, $KEPT identical, $REVIEW to review"
