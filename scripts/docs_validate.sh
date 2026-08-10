#!/usr/bin/env bash
# docs_validate.sh — deterministic validator for the docs-kit three-layer model.
#
# Read-only. No LLM, no network. Contract: STANDARD.md §7.
#
# Usage:  docs_validate.sh [docs_dir]     (default: ./docs)
# Exit:   0 = clean · 1 = violations found · 2 = setup error
# Output: one "FAIL [tag] <file>: <message>" line per violation, then a count.
#         "NOTE [layout] ..." lines are informational only (never affect exit code).
#
# Checks (tags):
#   [ref]          every *_ref: resolves to an existing id: under docs/. Keys that must
#                  be unique and are not are reported here too: a duplicate id:, and a
#                  component name declared in two 02_architecture/ docs (edges and the
#                  rendered cards resolve components by name, so a clash is ambiguous)
#   [backlog]      every Backlog item has a non-empty source_ref:
#   [frontmatter]  required fields per type, valid enums, id prefix per folder,
#                  Proposals contain an "Alternatives considered" heading
#   [audit-append] 92_audit/ files are append-only vs git HEAD (skipped without git/HEAD)
#   [amended-by]   every amended_by / rejected entry cites an existing DECISION id
#   [anchor]       every path a doc names — a `backticked` components path, a fence
#                  `code:` header — still exists in the repo
#
# Informational only (never affect the exit code):
#   NOTE [layout]  a standard folder is missing
#   NOTE [stale]   a Layer 1 doc carries verified_at: <rev> and files it names have
#                  changed since that rev. Changed is not the same as wrong, which is
#                  why this warns instead of failing (same rationale as STANDARD §8).
#
# Layer 2 folders may hold an `_archive/` subfolder for terminal documents; it is
# validated exactly like the folder above it — archiving lowers read cost, never
# the standard a document is held to.
#
# Portability: bash 3.2 (macOS), BSD awk/grep. No associative arrays, no GNU-isms.

set -u

DOCS="${1:-docs}"
if [ ! -d "$DOCS" ]; then
  echo "FAIL [setup] $DOCS: directory not found (run /docs-kit:docs-init first)"
  exit 2
fi

# The repo root is the parent of docs/. Anchor paths are relative to it, and
# checks 4 and 6 both need it, so it is resolved once here.
ROOT="$(cd "$DOCS/.." 2>/dev/null && pwd)"

TMP="$(mktemp -d)" || exit 2
trap 'rm -rf "$TMP"' EXIT
FAILS="$TMP/fails"
: > "$FAILS"
TAB="$(printf '\t')"

fail() { # fail <tag> <file> <message>
  printf 'FAIL [%s] %s: %s\n' "$1" "$2" "$3" >> "$FAILS"
}

# NOTE lines print immediately and never touch the exit code. Used where
# "changed" cannot be distinguished from "wrong" without reading the code.
note() { # note <tag> <file> <message>
  printf 'NOTE [%s] %s: %s\n' "$1" "$2" "$3"
}

# ---------------------------------------------------------------- helpers ----

# Print the frontmatter body of a file (between the first two `---` lines).
# Prints nothing if the file does not start with `---`.
frontmatter() {
  awk 'NR==1 { if ($0 ~ /^---[ \t\r]*$/) next; else exit }
       /^---[ \t\r]*$/ { exit }
       { print }' "$1"
}

# Trim a raw frontmatter value: strip inline " # comment", surrounding
# whitespace, and surrounding double quotes.
clean_value() {
  printf '%s' "$1" | awk '{
    sub(/[ \t]#.*$/, "")
    sub(/^[ \t]+/, ""); sub(/[ \t\r]+$/, "")
    sub(/^"/, ""); sub(/"$/, "")
    print
  }'
}

# fm_get <file> <key> → cleaned value of the first top-level `key:` line.
fm_get() {
  raw="$(frontmatter "$1" | awk -v k="$2" '
    index($0, k ":") == 1 { print substr($0, length(k) + 2); exit }')"
  clean_value "$raw"
}

fm_has() { # fm_has <file> <key>
  frontmatter "$1" | grep -q "^$2:"
}

# fm_list <file> <key> → one line per entry of a list-valued frontmatter field.
# Accepts both YAML shapes the templates allow:
#   key: [A, B]      flow style  → printed as the single line "[A, B]"
#   key:             block style → one line per "- entry"
#     - entry
# An empty list (`key: []`) prints nothing. Shared by the amended-by and anchor
# checks so the two cannot disagree about what an entry is.
fm_list() {
  frontmatter "$1" | awk -v k="$2" '
    index($0, k ":") == 1 {
      blk = 1
      rest = substr($0, length(k) + 2)
      sub(/[ \t]#.*$/, "", rest); sub(/^[ \t]+/, "", rest); sub(/[ \t\r]+$/, "", rest)
      if (rest != "" && rest !~ /^\[[ \t]*\]$/) print rest
      next
    }
    blk && /^[^ \t]/ { blk = 0 }
    blk && /^[ \t]*-/ { print }
  '
}

id_exists() { # id_exists <ID>
  cut -f1 "$TMP/ids" | grep -Fxq "$1"
}

check_enum() { # check_enum <file> <key> <value> <allowed...>
  ce_f="$1"; ce_k="$2"; ce_v="$3"; shift 3
  if [ -z "$ce_v" ]; then
    fail frontmatter "$ce_f" "field '$ce_k' is empty (allowed: $*)"
    return
  fi
  for a in "$@"; do
    [ "$ce_v" = "$a" ] && return
  done
  fail frontmatter "$ce_f" "field '$ce_k' has invalid value '$ce_v' (allowed: $*)"
}

# ------------------------------------------------- collect ids (+ check 1a) --

find "$DOCS" -type f -name '*.md' | LC_ALL=C sort > "$TMP/files"
: > "$TMP/ids"
while IFS= read -r f; do
  fid="$(fm_get "$f" id)"
  [ -n "$fid" ] && printf '%s\t%s\n' "$fid" "$f" >> "$TMP/ids"
done < "$TMP/files"

# Duplicate ids make refs ambiguous → reported under [ref].
cut -f1 "$TMP/ids" | LC_ALL=C sort | uniq -d > "$TMP/dups"
while IFS= read -r dup; do
  [ -z "$dup" ] && continue
  where="$(awk -F"$TAB" -v d="$dup" '$1==d { print $2 }' "$TMP/ids" | tr '\n' ' ')"
  first="$(awk -F"$TAB" -v d="$dup" '$1==d { print $2; exit }' "$TMP/ids")"
  fail ref "$first" "duplicate id '$dup' defined in: $where"
done < "$TMP/dups"

# ------------------------------------------ check 1: *_ref: fields resolve ---

while IFS= read -r f; do
  frontmatter "$f" | awk '
    /^[A-Za-z0-9_]+_ref:/ {
      i = index($0, ":")
      print substr($0, 1, i - 1) "\t" substr($0, i + 1)
    }' > "$TMP/refs"
  while IFS="$TAB" read -r key rawval; do
    [ -z "$key" ] && continue
    val="$(clean_value "$rawval")"
    if [ -z "$val" ]; then
      # Empty source_ref in the backlog folder is check 2's finding — skip here.
      case "$f" in
        */23_backlog/*) [ "$key" = "source_ref" ] && continue ;;
      esac
      fail ref "$f" "field '$key' is empty — every *_ref must point to an existing id"
    elif ! id_exists "$val"; then
      fail ref "$f" "field '$key' points to '$val' which matches no id: under $DOCS"
    fi
  done < "$TMP/refs"
done < "$TMP/files"

# --------------------------------- check 2: Backlog has non-empty source_ref --

for f in "$DOCS"/23_backlog/*.md "$DOCS"/23_backlog/_archive/*.md; do
  [ -f "$f" ] || continue
  case "$(basename "$f")" in README.md) continue ;; esac
  if ! frontmatter "$f" | grep -q .; then
    continue   # missing frontmatter entirely → reported by check 3
  fi
  src="$(fm_get "$f" source_ref)"
  if [ -z "$src" ]; then
    fail backlog "$f" "missing or empty source_ref (Decision for full lane, Issue for fast lane)"
  fi
done

# ------------------------- check 3: required fields, enums, id prefixes ------

require_fields() { # require_fields <file> <key...>  → 0 if frontmatter present
  rf_f="$1"; shift
  if ! frontmatter "$rf_f" | grep -q .; then
    fail frontmatter "$rf_f" "missing frontmatter (--- block) — required fields: $*"
    return 1
  fi
  for k in "$@"; do
    fm_has "$rf_f" "$k" || fail frontmatter "$rf_f" "missing required field '$k'"
  done
  return 0
}

check_id_prefix() { # check_id_prefix <file> <PREFIX>
  cip_id="$(fm_get "$1" id)"
  [ -z "$cip_id" ] && return   # missing id already reported by require_fields
  if ! printf '%s' "$cip_id" | grep -Eq "^$2-[0-9]{3,}$"; then
    fail frontmatter "$1" "id '$cip_id' does not match convention '$2-NNN' for this folder"
  fi
}

for dir in 01_products 02_architecture 03_business-logic 20_issues 21_proposals 22_decisions 23_backlog; do
  [ -d "$DOCS/$dir" ] || continue
  # _archive/ holds terminal documents. They are read less, never validated less.
  for f in "$DOCS/$dir"/*.md "$DOCS/$dir"/_archive/*.md; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in README.md) continue ;; esac
    case "$dir" in
      01_products)
        require_fields "$f" name users problem scope_in scope_out success_metric
        ;;
      02_architecture)
        require_fields "$f" components data_flow tech_stack constraints amended_by
        ;;
      03_business-logic)
        require_fields "$f" domain amended_by
        ;;
      20_issues)
        if require_fields "$f" id description why lane status; then
          check_id_prefix "$f" ISSUE
          fm_has "$f" lane   && check_enum "$f" lane   "$(fm_get "$f" lane)"   fast full
          fm_has "$f" status && check_enum "$f" status "$(fm_get "$f" status)" exploring open promoted archived
        fi
        ;;
      21_proposals)
        if require_fields "$f" id issue_ref problem proposed impact; then
          check_id_prefix "$f" PROPOSAL
        fi
        if ! grep -Eiq '^#{1,6}[[:space:]]+.*alternatives considered' "$f"; then
          fail frontmatter "$f" "missing 'Alternatives considered' heading (2-3 options with trade-offs required)"
        fi
        ;;
      22_decisions)
        if require_fields "$f" id proposal_ref outcome reason decided_by; then
          check_id_prefix "$f" DECISION
          fm_has "$f" outcome && check_enum "$f" outcome "$(fm_get "$f" outcome)" approved rejected
        fi
        ;;
      23_backlog)
        if require_fields "$f" id description source_ref status; then
          check_id_prefix "$f" BACKLOG
          fm_has "$f" status && check_enum "$f" status "$(fm_get "$f" status)" open in-progress done
        fi
        ;;
    esac
  done
done

# ------------------------- check 4: 92_audit/ append-only (vs git HEAD) ------

AUDIT_DIR="$DOCS/92_audit"
if [ -d "$AUDIT_DIR" ] && [ -n "$ROOT" ] && command -v git >/dev/null 2>&1 \
   && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
   && git -C "$ROOT" rev-parse -q --verify HEAD >/dev/null 2>&1; then
  AUDIT_ABS="$(cd "$AUDIT_DIR" && pwd)"
  git -C "$ROOT" diff HEAD --numstat -- "$AUDIT_ABS" > "$TMP/numstat" 2>/dev/null
  while IFS="$TAB" read -r added deleted path; do
    [ -z "$path" ] && continue
    [ "$deleted" = "-" ] && continue      # binary file — nothing to assert
    if [ "$deleted" != "0" ]; then
      fail audit-append "$path" "append-only violated: $deleted line(s) deleted or rewritten since git HEAD (audit entries may only be appended)"
    fi
  done < "$TMP/numstat"
fi

# ------- check 5: amended_by / rejected entries cite existing Decisions ------
#
# Both fields record the same kind of event from opposite sides: a Decision that
# changed layer 1, and a Decision that ruled something out. `rejected:` exists so
# that "what was already considered and dropped" is answerable from layer 1 alone
# — without it, every reader has to scan all of 22_decisions to find out.
# It is optional: a repo scaffolded before it existed stays valid.

for amdir in 02_architecture 03_business-logic; do
  [ -d "$DOCS/$amdir" ] || continue
  for f in "$DOCS/$amdir"/*.md; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in README.md) continue ;; esac
    for key in amended_by rejected; do
      fm_list "$f" "$key" > "$TMP/amended"
      while IFS= read -r entry; do
        [ -z "$entry" ] && continue
        refs="$(printf '%s' "$entry" | grep -oE 'DECISION-[0-9]+' || true)"
        if [ -z "$refs" ]; then
          fail amended-by "$f" "$key entry lacks a DECISION-NNN ref: '$entry'"
          continue
        fi
        while IFS= read -r r; do
          [ -z "$r" ] && continue
          id_exists "$r" || fail amended-by "$f" "$key cites '$r' which matches no Decision id: under $DOCS"
        done <<EOF
$refs
EOF
      done < "$TMP/amended"
    done
  done
done

# ------------- check 6: anchors still exist (+ verified_at staleness) --------
#
# Every load-bearing fact in layer 1 already carries an anchor into the source:
# a component names its `path/in/repo`, and every figure fence takes a `code:`
# header. Nothing used them. A path that no longer exists is not a matter of
# opinion, so it FAILs; a path that merely *changed* since verified_at is a NOTE,
# because changed is not the same as wrong.
#
# Placeholder values — anything containing < or > — are the templates' own
# "<file to read>" markers and are skipped, so a fresh scaffold passes clean.

# component_names <file> → the name of each components: entry, one per line.
# Mirrors parse_components() in the renderer: split off the description at the
# first " — " / " – " / " -- " / ": ", then drop the [kind] tag and the `path`.
component_names() {
  fm_list "$1" components | awk '
    {
      s = $0
      sub(/^[ \t]*-[ \t]*/, "", s)
      sub(/^"/, "", s); sub(/"$/, "", s)
      for (i = 1; i <= 4; i++) {
        sep = (i == 1) ? " — " : (i == 2) ? " – " : (i == 3) ? " -- " : ": "
        p = index(s, sep)
        if (p > 0) { s = substr(s, 1, p - 1); break }
      }
      gsub(/\[[a-z]+\]/, "", s)
      gsub(/`[^`]*`/, "", s)
      gsub(/^[ \t]+|[ \t\r]+$/, "", s)
      if (s != "") print s
    }'
}

anchor_paths() { # anchor_paths <file> → one repo-relative path per line
  # 1. the backticked path inside each components: entry
  fm_list "$1" components | awk '
    { n = split($0, part, "`"); if (n >= 3 && part[2] != "") print part[2] }'
  # 2. the code: header of each figure fence in the body. Only a bare
  #    ```<type> line opens one, so a ```flow shown inside a ````markdown
  #    block is not a fence — same rule the renderer applies.
  awk '
    NR == 1 && /^---[ \t\r]*$/ { fm = 1; next }
    fm && /^---[ \t\r]*$/       { fm = 0; next }
    fm { next }
    !fence && /^```(flow|flowchart|state|erd|class)[ \t]*\r?$/ { fence = 1; next }
    fence && /^```[ \t]*\r?$/ { fence = 0; next }
    fence && index($0, "code:") == 1 {
      v = substr($0, 6)
      sub(/^[ \t]+/, "", v); sub(/[ \t\r]+$/, "", v)
      sub(/^"/, "", v); sub(/"$/, "", v)
      if (v != "") print v
    }
  ' "$1"
}

# A component name IS a reference key: data_flow edges name components, and the
# rendered cards resolve upstream/downstream by name. Once 02_architecture/ holds
# one doc per service, two docs can declare the same name — and the renderer takes
# the first, silently. Reported here for the same reason a duplicate id: is.
: > "$TMP/compnames"
for f in "$DOCS"/02_architecture/*.md; do
  [ -f "$f" ] || continue
  case "$(basename "$f")" in README.md) continue ;; esac
  component_names "$f" | while IFS= read -r n; do
    [ -n "$n" ] && printf '%s\t%s\n' "$n" "$f" >> "$TMP/compnames"
  done
done
if [ -s "$TMP/compnames" ]; then
  cut -f1 "$TMP/compnames" | LC_ALL=C sort | uniq -d > "$TMP/compdups"
  while IFS= read -r dup; do
    [ -z "$dup" ] && continue
    where="$(awk -F"$TAB" -v d="$dup" '$1==d { print $2 }' "$TMP/compnames" | tr '\n' ' ')"
    first="$(awk -F"$TAB" -v d="$dup" '$1==d { print $2; exit }' "$TMP/compnames")"
    fail ref "$first" "component '$dup' is declared in more than one architecture doc: $where"
  done < "$TMP/compdups"
fi

if [ -n "$ROOT" ]; then
  # Files changed since each doc's verified_at rev, resolved lazily per rev.
  HAVE_GIT=0
  if command -v git >/dev/null 2>&1 \
     && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    HAVE_GIT=1
  fi

  for andir in 01_products 02_architecture 03_business-logic; do
    [ -d "$DOCS/$andir" ] || continue
    for f in "$DOCS/$andir"/*.md; do
      [ -f "$f" ] || continue
      case "$(basename "$f")" in README.md) continue ;; esac

      anchor_paths "$f" | LC_ALL=C sort -u > "$TMP/anchors"
      [ -s "$TMP/anchors" ] || continue

      while IFS= read -r p; do
        [ -z "$p" ] && continue
        case "$p" in *"<"*|*">"*) continue ;; esac   # template placeholder
        [ -e "$ROOT/$p" ] || \
          fail anchor "$f" "names '$p', which does not exist in the repo (a moved or deleted path makes this doc unverifiable)"
      done < "$TMP/anchors"

      # verified_at: <rev> — warn when the code under those anchors has moved on.
      rev="$(fm_get "$f" verified_at)"
      [ -z "$rev" ] && continue
      case "$rev" in *"<"*|*">"*) continue ;; esac
      if [ "$HAVE_GIT" -eq 0 ]; then continue; fi
      if ! git -C "$ROOT" rev-parse -q --verify "$rev^{commit}" >/dev/null 2>&1; then
        note stale "$f" "verified_at: '$rev' is not a commit in this repo"
        continue
      fi
      # rev vs the WORKING TREE, not vs HEAD: docs-sync runs at the end of a
      # session, before the work is committed. Comparing against HEAD would make
      # exactly the changes that session just made invisible to this check.
      git -C "$ROOT" diff --name-only "$rev" > "$TMP/changed" 2>/dev/null || continue
      hits=0
      while IFS= read -r p; do
        [ -z "$p" ] && continue
        case "$p" in *"<"*|*">"*) continue ;; esac
        if awk -v p="$p" 'index($0, p) == 1 { found = 1; exit } END { exit !found }' "$TMP/changed"; then
          hits=$((hits + 1))
        fi
      done < "$TMP/anchors"
      if [ "$hits" -gt 0 ]; then
        note stale "$f" "verified_at $rev — $hits of the paths this doc names changed since then; re-read them and move verified_at forward"
      fi
    done
  done
fi

# ----------------------------- layout notes (informational, never failing) ---

for dir in 00_roadmap 01_products 02_architecture 03_business-logic \
           20_issues 21_proposals 22_decisions 23_backlog 30_conventions \
           40_services 50_runbooks 60_fe-integration 70_deploy 92_audit 93_qa; do
  [ -d "$DOCS/$dir" ] || echo "NOTE [layout] $DOCS/$dir: standard folder missing (docs-init creates all 15)"
done

# -------------------------------------------------------------------- report -

SCANNED="$(wc -l < "$TMP/files" | tr -d ' ')"
if [ -s "$FAILS" ]; then
  cat "$FAILS"
  echo "docs-validate: $(wc -l < "$FAILS" | tr -d ' ') violation(s) across $SCANNED markdown file(s) in $DOCS"
  exit 1
fi
echo "docs-validate: OK — $SCANNED markdown file(s) in $DOCS pass all checks (ref, backlog, frontmatter, audit-append, amended-by, anchor)"
exit 0
