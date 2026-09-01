#!/usr/bin/env bash
# docs-kit — stamp the crew layer into a target repo (the deterministic half of
# /docs-kit:crew-init; the interview and every write to CLAUDE.md or
# .docs-kit.json stay in the skill, behind AskUserQuestion).
#
# Usage: crew_scaffold.sh [--skip role,role] <target-repo-root>   (default: .)
#        --skip: role command files NOT to stamp (roles the interview found
#        absent in this repo — a stamped file for a ghost role is a wrong fact).
#
# Policy: never clobber a file a HUMAN wrote — but a file this script wrote and
# nobody touched since is this script's to replace, and replacing it is the whole
# point of re-running after a kit update.
#
# The two cases look identical on disk, so the script writes down what it put
# there: .claude/crew/.stamp holds a sha256 per stamped file. On a later run a
# file whose hash still matches the manifest is an untouched kit copy and gets
# UPDATED in place; anything else lands beside it as <name>.new for a human
# merge, exactly as before. A repo with no manifest yet (stamped by 0.26.2 or
# earlier) takes the conservative path once, and the manifest it writes on that
# run makes every later update automatic.
#
# Without sha256 on PATH the manifest is skipped and behaviour falls back to the
# old always-.new rule — degraded, never wrong.
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
UPDATED=0
KEPT=0
REVIEW=0

MAN="$TGT/.claude/crew/.stamp"
NEWMAN="$(mktemp "${TMPDIR:-/tmp}/crewstamp.XXXXXX")"
trap 'rm -f "$NEWMAN"' EXIT

if command -v shasum >/dev/null 2>&1; then
  sha() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; }
elif command -v sha256sum >/dev/null 2>&1; then
  sha() { sha256sum "$1" 2>/dev/null | awk '{print $1}'; }
else
  sha() { echo ""; }
fi

was_ours() { # was_ours <relpath> <file> — did this script write exactly this?
  [ -f "$MAN" ] || return 1
  want="$(awk -F'\t' -v r="$1" '$2 == r {print $1}' "$MAN" | tail -1)"
  [ -n "$want" ] || return 1
  got="$(sha "$2")"
  [ -n "$got" ] && [ "$want" = "$got" ]
}

record() { # record <relpath> <file>
  h="$(sha "$2")"
  [ -n "$h" ] && printf '%s\t%s\n' "$h" "$1" >> "$NEWMAN"
}

keep_old() { # keep_old <relpath> — carry a prior entry we did not rewrite
  [ -f "$MAN" ] || return 0
  awk -F'\t' -v r="$1" '$2 == r' "$MAN" | tail -1 >> "$NEWMAN"
}

put() { # put <src> <dst> [exec]
  src="$1"; dst="$2"; rel="${dst#"$TGT"/}"
  if [ ! -e "$dst" ]; then
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    [ "${3:-}" = "exec" ] && chmod +x "$dst"
    echo "stamped: $rel"
    STAMPED=$((STAMPED + 1))
    record "$rel" "$dst"
  elif cmp -s "$src" "$dst"; then
    KEPT=$((KEPT + 1))
    record "$rel" "$dst"
  elif was_ours "$rel" "$dst"; then
    cp "$src" "$dst"
    [ "${3:-}" = "exec" ] && chmod +x "$dst"
    echo "updated: $rel (this script's own copy, untouched since)"
    UPDATED=$((UPDATED + 1))
    record "$rel" "$dst"
  else
    cp "$src" "$dst.new"
    echo "review : $rel.new (local file differs — merge by hand)"
    REVIEW=$((REVIEW + 1))
    keep_old "$rel"
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

if [ -s "$NEWMAN" ]; then
  mkdir -p "$(dirname "$MAN")"
  sort -u "$NEWMAN" > "$MAN"
fi

echo "crew-scaffold: $STAMPED stamped, $UPDATED updated, $KEPT identical, $REVIEW to review"
if [ "$REVIEW" -gt 0 ]; then
  echo ""
  echo "next   : each line below replaces a file you edited — read the diff first"
  find "$TGT/.claude" "$TGT/scripts" -name '*.new' 2>/dev/null | while read -r n; do
    echo "  diff \"${n%.new}\" \"$n\" && mv \"$n\" \"${n%.new}\""
  done
fi
