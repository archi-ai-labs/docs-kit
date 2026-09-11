#!/usr/bin/env bash
# docs_feedback.sh — file a problem with docs-kit or crew, from inside the repo
# that hit it.
#
# Deterministic, no LLM, no network. Contract: STANDARD.md §12.
#
# Usage:  docs_feedback.sh new  <slug> [target_root]   (default root: .)
#         docs_feedback.sh list         [target_root]
#         docs_feedback.sh show <id>    [target_root]
#
#   new   allocates the next FEEDBACK id, copies the template, and fills in the
#         context a writer gets wrong: the kit version, this repo's profile, the
#         git rev, whether crew is stamped, and the platform. A report that
#         cannot be reproduced is nothing but its context, so the context is the
#         one part not left to recollection.
#   list  one line per report — id, status, severity, about, title.
#   show  prints one report verbatim, which is the whole delivery mechanism:
#         the file IS the prompt, so `show` piped to a clipboard is "send it".
#
# Template source: docs/99_feedback/TEMPLATE.md in the target repo when present
# (a repo may adapt the form), otherwise the copy shipped with the kit.
#
# Exit:   0 = done · 2 = setup error · 3 = docs/99_feedback/ missing (the repo
#         was scaffolded before this folder existed — /docs-kit:docs-upgrade)
#
# Portability: bash 3.2 (macOS), BSD sed/awk. No `sed -i`, no GNU-isms.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FOLDER="99_feedback"

usage() {
  echo "usage: docs_feedback.sh new <slug> [target_root]"
  echo "       docs_feedback.sh list [target_root]"
  echo "       docs_feedback.sh show <id|NNN> [target_root]"
}

CMD="${1:-}"
[ -n "$CMD" ] || { usage; exit 2; }
shift

case "$CMD" in
  new)
    SLUG_RAW="${1:-}"
    [ -n "$SLUG_RAW" ] || { echo "FEEDBACK ERROR: new needs a slug (e.g. crew-done-merge-order)"; exit 2; }
    shift
    ;;
  show)
    WANT_ID="${1:-}"
    [ -n "$WANT_ID" ] || { echo "FEEDBACK ERROR: show needs an id (003 or FEEDBACK-003)"; exit 2; }
    shift
    ;;
  list) ;;
  -h|--help|help) usage; exit 0 ;;
  *) echo "FEEDBACK ERROR: unknown command '$CMD'"; usage; exit 2 ;;
esac

ROOT="${1:-.}"
[ -d "$ROOT" ] || { echo "FEEDBACK ERROR: target root '$ROOT' is not a directory"; exit 2; }
ROOT="$(cd "$ROOT" && pwd)"
DIR="$ROOT/docs/$FOLDER"

if [ ! -d "$DIR" ]; then
  echo "FEEDBACK ERROR: $DIR does not exist."
  if [ -d "$ROOT/docs" ]; then
    echo "  This repo was scaffolded before the folder existed — run /docs-kit:docs-upgrade"
    echo "  (or: bash $SCRIPT_DIR/docs_scaffold.sh --sync $ROOT)."
  else
    echo "  There is no docs/ here at all — run /docs-kit:docs-init first."
  fi
  exit 3
fi

# report_files — every filed report, sorted. Never the template, never the README.
report_files() {
  find "$DIR" -maxdepth 1 -type f -name 'FEEDBACK-*.md' | LC_ALL=C sort
}

# fm <file> <key> — first top-level `key:` value, quotes and inline comment stripped.
fm() {
  awk -v k="$2" '
    NR == 1 && $0 !~ /^---[ \t\r]*$/ { exit }
    NR > 1 && /^---[ \t\r]*$/ { exit }
    index($0, k ":") == 1 {
      v = substr($0, length(k) + 2)
      sub(/[ \t]#.*$/, "", v)
      sub(/^[ \t]+/, "", v); sub(/[ \t\r]+$/, "", v)
      sub(/^"/, "", v); sub(/"$/, "", v)
      print v; exit
    }' "$1"
}

# The first ATX heading in the BODY. The frontmatter is skipped first: it carries
# `#` comment lines of its own, and one of them read as every report's title.
title_of() {
  awk '
    NR == 1 && $0 ~ /^---[ \t\r]*$/ { fm = 1; next }
    fm && /^---[ \t\r]*$/ { fm = 0; next }
    fm { next }
    /^#[ \t]/ { sub(/^#[ \t]+/, ""); sub(/[ \t\r]+$/, ""); print; exit }' "$1"
}

# ------------------------------------------------------------------- list ----

if [ "$CMD" = "list" ]; then
  report_files | while IFS= read -r f; do
    [ -n "$f" ] || continue
    printf '%-15s %-7s %-9s %-9s %s\n' \
      "$(fm "$f" id)" "$(fm "$f" status)" "$(fm "$f" severity)" \
      "$(fm "$f" about)" "$(title_of "$f")"
  done
  n="$(report_files | wc -l | tr -d ' ')"
  if [ "$n" -eq 0 ]; then
    echo "No reports filed in docs/$FOLDER/ yet."
  else
    echo "-- $n report(s) in docs/$FOLDER/ · send one with: docs_feedback.sh show <id>"
  fi
  exit 0
fi

# ------------------------------------------------------------------- show ----

if [ "$CMD" = "show" ]; then
  # Accept 003, 3, or FEEDBACK-003 — the id is what matters, not how it is typed.
  num="$(printf '%s' "$WANT_ID" | sed 's/^[Ff][Ee][Ee][Dd][Bb][Aa][Cc][Kk]-//')"
  case "$num" in
    ''|*[!0-9]*) echo "FEEDBACK ERROR: '$WANT_ID' is not an id (003 or FEEDBACK-003)"; exit 2 ;;
  esac
  # `10#` or printf reads 077 as octal and hunts for FEEDBACK-063. The id loop
  # below already guards this; the lookup has no excuse not to.
  padded="$(printf '%03d' "$((10#$num))")"
  hit=""
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ "$(fm "$f" id)" = "FEEDBACK-$padded" ] && { hit="$f"; break; }
  done <<EOF
$(report_files)
EOF
  if [ -z "$hit" ]; then
    echo "FEEDBACK ERROR: no report with id FEEDBACK-$padded in docs/$FOLDER/"
    echo "  filed ids: $(report_files | while IFS= read -r f; do printf '%s ' "$(fm "$f" id)"; done)"
    exit 2
  fi
  cat "$hit"
  exit 0
fi

# -------------------------------------------------------------------- new ----

# Slug: lowercase, [a-z0-9-] only, no leading/trailing or doubled dashes, 48 max.
# It is a filename hint, not an identifier — `ls` is how a writer checks whether
# the thing they just hit is already filed, and that only works if names read.
SLUG="$(printf '%s' "$SLUG_RAW" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9]/-/g; s/--*/-/g; s/^-//; s/-$//' \
  | cut -c1-48 | sed 's/-$//')"
if [ -z "$SLUG" ]; then
  echo "FEEDBACK ERROR: slug '$SLUG_RAW' has nothing usable in it (a-z, 0-9, dashes)"
  exit 2
fi

# Id allocation is read-then-write, so two sessions that both read before either
# writes pick the same number — and the filenames differ by slug, so the
# `already exists` check below never sees the collision. Measured in a real repo:
# two FEEDBACK-002 files written the same day by two executor sessions, 08:33 and
# 10:11. It landed in the tool people use to REPORT bugs, which is why it earns a
# lock rather than a warning.
#
# `mkdir` is the atomic primitive, the same one `crew new` uses for its claim: it
# works on every filesystem in the portability floor, unlike flock. The lock lives
# OUTSIDE the repo so one left behind by a hard kill can never turn up in
# `git status` or, worse, get committed.
FB_LOCK="${TMPDIR:-/tmp}/docs-kit-fb-$(printf '%s' "$ROOT" | tr -c 'A-Za-z0-9' '-').lock"
fb_i=0
while ! mkdir "$FB_LOCK" 2>/dev/null; do
  fb_i=$((fb_i + 1))
  if [ "$fb_i" -ge 15 ]; then
    echo "FEEDBACK ERROR: another 'docs_feedback new' has held the id claim for 15s"
    echo "  if none is running, remove $FB_LOCK"
    exit 2
  fi
  sleep 1
done
trap 'rmdir "$FB_LOCK" 2>/dev/null || true' EXIT INT TERM

# Next id = highest filed + 1. Read from `id:`, not from the filename: §3 says a
# file name is never a reference key, and this script does not get an exception.
NEXT=1
while IFS= read -r f; do
  [ -n "$f" ] || continue
  cur="$(fm "$f" id)"; cur="${cur#FEEDBACK-}"
  case "$cur" in
    ''|*[!0-9]*) continue ;;
  esac
  cur=$((10#$cur))
  [ "$cur" -ge "$NEXT" ] && NEXT=$((cur + 1))
done <<EOF
$(report_files)
EOF
ID="FEEDBACK-$(printf '%03d' "$NEXT")"
OUT="$DIR/$ID-$SLUG.md"
[ -e "$OUT" ] && { echo "FEEDBACK ERROR: $OUT already exists — nothing written"; exit 2; }

TPL="$DIR/TEMPLATE.md"
[ -f "$TPL" ] || TPL="$PLUGIN_ROOT/templates/docs/$FOLDER/TEMPLATE.md"
[ -f "$TPL" ] || { echo "FEEDBACK ERROR: no TEMPLATE.md in docs/$FOLDER/ or in the kit"; exit 2; }

# ---- the context a writer gets wrong ----------------------------------------

KIT_VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  "$PLUGIN_ROOT/.claude-plugin/plugin.json" 2>/dev/null | head -1)"
[ -n "$KIT_VERSION" ] || KIT_VERSION="unknown"

REPO_NAME="$(basename "$ROOT")"

REPO_REV="unknown"
if command -v git >/dev/null 2>&1 \
   && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REPO_REV="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo uncommitted)"
  if [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]; then
    REPO_REV="$REPO_REV+dirty"
  fi
fi

REPO_PROFILE="unknown"
if [ -f "$SCRIPT_DIR/docs_profile.sh" ]; then
  # shellcheck source=docs_profile.sh
  . "$SCRIPT_DIR/docs_profile.sh"
  REPO_PROFILE="$(dk_profile_label "$ROOT")"
fi

CREW_STATE="absent"
[ -f "$ROOT/.claude/crew/.stamp" ] && CREW_STATE="stamped"

PLATFORM="$(uname -sr 2>/dev/null || echo unknown)"
PLATFORM="$PLATFORM · bash ${BASH_VERSION%%(*}"
if command -v python3 >/dev/null 2>&1; then
  PLATFORM="$PLATFORM · python $(python3 -c 'import platform;print(platform.python_version())' 2>/dev/null || echo '?')"
fi

TODAY="$(date +%Y-%m-%d)"

# `|` is the sed delimiter below, and a value carrying one would rewrite the
# command instead of landing in the file. None of these fields needs the
# character, so it is dropped rather than escaped.
strip_pipe() { printf '%s' "$1" | tr -d '|'; }

sed -e "s|{{FEEDBACK_DATE}}|$(strip_pipe "$TODAY")|g" \
    -e "s|{{KIT_VERSION}}|$(strip_pipe "$KIT_VERSION")|g" \
    -e "s|{{CREW_STATE}}|$(strip_pipe "$CREW_STATE")|g" \
    -e "s|{{REPO_NAME}}|$(strip_pipe "$REPO_NAME")|g" \
    -e "s|{{REPO_PROFILE}}|$(strip_pipe "$REPO_PROFILE")|g" \
    -e "s|{{REPO_REV}}|$(strip_pipe "$REPO_REV")|g" \
    -e "s|{{PLATFORM}}|$(strip_pipe "$PLATFORM")|g" \
    -e "s|^id: FEEDBACK-NNN|id: $ID|" \
    "$TPL" > "$OUT" || { echo "FEEDBACK ERROR: could not write $OUT"; exit 2; }

# The claim covers read-through-write and nothing further: released the moment the
# file exists on disk, because everything after this point is only reporting.
trap - EXIT INT TERM
rmdir "$FB_LOCK" 2>/dev/null || true

echo "Created docs/$FOLDER/$(basename "$OUT")"
echo "  id        : $ID"
echo "  kit       : $KIT_VERSION · crew $CREW_STATE"
echo "  profile   : $REPO_PROFILE"
echo "  rev       : $REPO_REV"
echo ""
echo "next: fill in the body, then send it as-is —"
echo "  bash \"$SCRIPT_DIR/docs_feedback.sh\" show $ID $ROOT"
echo "and set 'status: sent' once it has been handed over."
exit 0
