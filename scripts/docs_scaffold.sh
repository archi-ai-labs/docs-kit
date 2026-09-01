#!/usr/bin/env bash
# docs_scaffold.sh — create the three-layer docs skeleton from the plugin templates.
#
# Deterministic, no LLM. Called by the docs-init skill (or manually).
#
# Usage:  docs_scaffold.sh [--sync] [--owns a,b,c] [target_root]   (default: .)
#         Creates <target_root>/docs from <plugin>/templates/docs.
#
#         --sync reconciles an EXISTING docs/ with the template tree: it creates
#         only what is missing and never overwrites, edits, or deletes a single
#         existing file. That is how a repo scaffolded by an older docs-kit picks
#         up a folder a later version added (04_api arrived in 0.20.0), and it
#         replaces the hand-rolled `cp -Rn` docs-init used to ask an agent to
#         perform — a careful file operation belongs in a script, not in a prompt.
#
#         --owns names what this repo holds title to (STANDARD §9), and that is
#         what decides which folders it gets: `--owns data,endpoints` scaffolds
#         13 folders, not 17 — 12 core plus 04_api, since `data` unlocks nothing
#         (see docs_profile.sh for the map). Tokens: data · endpoints · screens
#         · jobs · deploys.
#         `--owns ""` is legal and means "nothing conditional" — a library.
#
#         WITHOUT --owns the profile is read from `.docs-kit.json`, and a repo
#         that declares nothing there gets all 17 folders, exactly as before this
#         flag existed. Nothing changes shape until somebody declares something.
#
# Exit:   0 = created / synced · 2 = setup error (templates missing, bad --owns)
#         3 = plain mode and <target_root>/docs already exists (NOTHING touched —
#             the skill must report the situation and ask the user; never
#             auto-merge), or --sync and docs/ does not exist yet
#
# Behavior on success:
#   - copies the folders this repo's profile calls for (every folder ships a seed)
#   - substitutes {{DOCS_KIT_DATE}} with today's date in 92_audit/LOG.md
#   - writes .docs-kit.json with the declared `owns` when --owns was given and no
#     such file exists yet; never edits an existing one
#   - prints the created file list, then "SCAFFOLD OK"

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATES="$PLUGIN_ROOT/templates/docs"

if [ ! -f "$SCRIPT_DIR/docs_profile.sh" ]; then
  echo "SCAFFOLD ERROR: $SCRIPT_DIR/docs_profile.sh not found (broken plugin install)"
  exit 2
fi
# shellcheck source=docs_profile.sh
. "$SCRIPT_DIR/docs_profile.sh"

SYNC=0
OWNS_SET=0
OWNS_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sync)   SYNC=1; shift ;;
    --owns=*) OWNS_ARG="${1#--owns=}"; OWNS_SET=1; shift ;;
    --owns)
      shift
      if [ $# -eq 0 ]; then
        echo "SCAFFOLD ERROR: --owns needs a value (use --owns '' for a repo that owns nothing conditional)"
        exit 2
      fi
      OWNS_ARG="$1"; OWNS_SET=1; shift ;;
    --) shift; break ;;
    -*) echo "SCAFFOLD ERROR: unknown flag '$1'"; exit 2 ;;
    *)  break ;;
  esac
done

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

# ---------------------------------------------------------------- profile ----
#
# Resolve it once, here, so every path below asks the same question of the same
# answer. --owns wins for this run; otherwise .docs-kit.json speaks; otherwise
# nobody has declared anything and the answer is all 17.
if [ "$OWNS_SET" -eq 1 ]; then
  OWNS_NORM="$(printf '%s\n' "$OWNS_ARG" | tr ', ' '\n\n' | grep -v '^$' | LC_ALL=C sort -u || true)"
  BAD=""
  for tok in $OWNS_NORM; do
    printf '%s\n' $DK_TOKENS | grep -Fxq "$tok" || BAD="$BAD $tok"
  done
  if [ -n "$BAD" ]; then
    echo "SCAFFOLD ERROR: unknown owns token(s):$BAD"
    echo "  valid tokens: $(printf '%s ' $DK_TOKENS)"
    exit 2
  fi
  DK_OWNS_OVERRIDE="$(printf '%s' "$OWNS_NORM" | tr '\n' ',')"
  export DK_OWNS_OVERRIDE
fi

WANT="$(dk_folders "$TARGET_ROOT" | LC_ALL=C sort -u)"
echo "Profile: $(dk_profile_label "$TARGET_ROOT")"

# want_folder <name> — is this folder part of this repo's profile?
want_folder() {
  printf '%s\n' "$WANT" | grep -Fxq "$1"
}

# Every path in the template tree that this profile does not call for. A file
# under a skipped folder must not be copied, or --sync would quietly reintroduce
# the folder the profile just excluded.
wanted_path() { # wanted_path <path-relative-to-templates/docs>
  case "$1" in
    */*) want_folder "${1%%/*}" ;;
    *)   return 0 ;;          # a top-level file (docs/README.md) always belongs
  esac
}

# ------------------------------------------------------------------- sync ----

if [ "$SYNC" -eq 1 ]; then
  if [ ! -d "$TARGET" ]; then
    echo "SYNC REFUSED: $TARGET does not exist — run docs_scaffold.sh without --sync first."
    exit 3
  fi
  # Copy only what is absent. Never overwrite: an existing file is the repo's
  # content, and this script has no way to tell an edited template from a
  # deliberate rewrite — so it does not get to guess.
  #
  # Never remove either, including a folder this profile does not call for. A
  # repo that declares `owns` after the fact keeps every folder it already has:
  # deleting documentation because a config line changed is not a trade anyone
  # agreed to, and "extra folder" is never a finding anywhere else in the kit.
  #
  # **A seed arrives with its folder, never alone.** This used to copy any template
  # file the repo lacked, which meant deleting a seed — the documented thing to do
  # once you have written the real document — got it resurrected on the next sync.
  # Found by running this on a real repo. An existing folder is the repo's, and the
  # only thing sync may put in one is nothing.
  created=0
  NEWDIRS=""
  for d in $WANT; do
    if [ ! -d "$TARGET/$d" ]; then
      mkdir -p "$TARGET/$d" || { echo "SYNC ERROR: cannot create $d"; exit 2; }
      NEWDIRS="$NEWDIRS $d"
      echo "  added docs/$d/"
      created=$((created + 1))
    fi
  done

  ( cd "$TEMPLATES" && find . -type f ) | sed 's|^\./||' | LC_ALL=C sort > "$TARGET_ROOT/.docs-kit-sync.$$"
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    wanted_path "$rel" || continue
    case "$rel" in
      */*) # a seed: only when this run is the one creating its folder
        case " $NEWDIRS " in *" ${rel%%/*} "*) ;; *) continue ;; esac ;;
    esac
    if [ ! -e "$TARGET/$rel" ]; then
      mkdir -p "$TARGET/$(dirname "$rel")"
      cp "$TEMPLATES/$rel" "$TARGET/$rel" || { echo "SYNC ERROR: copy failed for $rel"; exit 2; }
      echo "  added docs/$rel"
      created=$((created + 1))
    fi
  done < "$TARGET_ROOT/.docs-kit-sync.$$"
  rm -f "$TARGET_ROOT/.docs-kit-sync.$$"

  if [ "$created" -eq 0 ]; then
    echo "SYNC OK — nothing to add; docs/ already has every folder this profile calls for"
  else
    echo "SYNC OK — $created item(s) added, nothing overwritten"
  fi
  exit 0
fi

# ------------------------------------------------------------------ fresh ----

if [ -e "$TARGET" ]; then
  echo "SCAFFOLD REFUSED: $TARGET already exists — nothing was touched."
  echo "Existing top-level entries:"
  ls -1 "$TARGET" | sed 's/^/  - /'
  echo "Folders this profile calls for, present/missing:"
  for d in $WANT; do
    if [ -d "$TARGET/$d" ]; then echo "  present: $d"; else echo "  MISSING: $d"; fi
  done
  exit 3
fi

mkdir -p "$TARGET" || { echo "SCAFFOLD ERROR: cannot create $TARGET"; exit 2; }
for f in "$TEMPLATES"/*; do
  [ -e "$f" ] || continue
  base="$(basename "$f")"
  if [ -d "$f" ]; then
    want_folder "$base" || continue
  fi
  cp -R "$f" "$TARGET/$base" || { echo "SCAFFOLD ERROR: copy failed for $base"; exit 2; }
done

# Stamp the install date into the audit log baseline entries (portable sed: no -i).
TODAY="$(date +%Y-%m-%d)"
LOG="$TARGET/92_audit/LOG.md"
if [ -f "$LOG" ]; then
  sed "s/{{DOCS_KIT_DATE}}/$TODAY/g" "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# Sanity: every folder this profile calls for must exist after the copy, and no
# folder outside it may. The first guards template drift; the second guards the
# map — a conditional folder that leaks in anyway makes --owns a lie.
for d in $WANT; do
  if [ ! -d "$TARGET/$d" ]; then
    echo "SCAFFOLD ERROR: expected folder $d missing after copy (broken template tree)"
    exit 2
  fi
done
for d in $(dk_folders_all); do
  if [ -d "$TARGET/$d" ] && ! want_folder "$d"; then
    echo "SCAFFOLD ERROR: $d was copied but this profile does not call for it"
    exit 2
  fi
done

# Record the declaration, so the next run of anything — validator, --sync, the
# next agent — reads the same profile this run used. Create-only: merging into an
# existing JSON file is not something to attempt in bash, and guessing wrong there
# would corrupt a config the repo already depends on.
CONFIG="$TARGET_ROOT/.docs-kit.json"
if [ "$OWNS_SET" -eq 1 ]; then
  if [ ! -e "$CONFIG" ]; then
    {
      echo '{'
      printf '  "owns": ['
      first=1
      for tok in $OWNS_NORM; do
        [ "$first" -eq 1 ] || printf ', '
        printf '"%s"' "$tok"
        first=0
      done
      echo ']'
      echo '}'
    } > "$CONFIG"
    echo "Wrote $CONFIG"
  else
    echo "PROFILE NOTE: $CONFIG already exists and was not touched."
    echo "  Add this key yourself so the declaration matches what was scaffolded:"
    printf '    "owns": [%s]\n' "$(printf '%s\n' $OWNS_NORM | sed 's/^/"/; s/$/"/' | tr '\n' ',' | sed 's/,$//; s/,/, /g')"
  fi
fi

echo "Created under $TARGET:"
find "$TARGET" -type f | LC_ALL=C sort | sed "s|^$TARGET_ROOT/|  |"
echo "SCAFFOLD OK"
exit 0
