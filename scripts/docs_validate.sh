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
#   [ref]          every *_ref: resolves to an existing id: under docs/ (+ duplicate ids)
#   [backlog]      every Backlog item has a non-empty source_ref:
#   [frontmatter]  required fields per type, valid enums, id prefix per folder,
#                  Proposals contain an "Alternatives considered" heading
#   [audit-append] 92_audit/ files are append-only vs git HEAD (skipped without git/HEAD)
#   [amended-by]   every amended_by entry in Architecture cites an existing DECISION id
#
# Portability: bash 3.2 (macOS), BSD awk/grep. No associative arrays, no GNU-isms.

set -u

DOCS="${1:-docs}"
if [ ! -d "$DOCS" ]; then
  echo "FAIL [setup] $DOCS: directory not found (run /docs-kit:docs-init first)"
  exit 2
fi

TMP="$(mktemp -d)" || exit 2
trap 'rm -rf "$TMP"' EXIT
FAILS="$TMP/fails"
: > "$FAILS"
TAB="$(printf '\t')"

fail() { # fail <tag> <file> <message>
  printf 'FAIL [%s] %s: %s\n' "$1" "$2" "$3" >> "$FAILS"
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

for f in "$DOCS"/23_backlog/*.md; do
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
  for f in "$DOCS/$dir"/*.md; do
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
ROOT="$(cd "$DOCS/.." 2>/dev/null && pwd)"
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

# ---------------- check 5: amended_by entries cite existing Decisions --------

for amdir in 02_architecture 03_business-logic; do
  [ -d "$DOCS/$amdir" ] || continue
  for f in "$DOCS/$amdir"/*.md; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in README.md) continue ;; esac
    frontmatter "$f" | awk '
      index($0, "amended_by:") == 1 {
        blk = 1
        rest = substr($0, 12)
        sub(/[ \t]#.*$/, "", rest); sub(/^[ \t]+/, "", rest); sub(/[ \t\r]+$/, "", rest)
        if (rest != "" && rest !~ /^\[[ \t]*\]$/) print rest   # flow-style, e.g. [DECISION-001]
        next
      }
      blk && /^[^ \t]/ { blk = 0 }
      blk && /^[ \t]*-/ { print }
    ' > "$TMP/amended"
    while IFS= read -r entry; do
      [ -z "$entry" ] && continue
      refs="$(printf '%s' "$entry" | grep -oE 'DECISION-[0-9]+' || true)"
      if [ -z "$refs" ]; then
        fail amended-by "$f" "amended_by entry lacks a DECISION-NNN ref: '$entry'"
        continue
      fi
      while IFS= read -r r; do
        [ -z "$r" ] && continue
        id_exists "$r" || fail amended-by "$f" "amended_by cites '$r' which matches no Decision id: under $DOCS"
      done <<EOF
$refs
EOF
    done < "$TMP/amended"
  done
done

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
echo "docs-validate: OK — $SCANNED markdown file(s) in $DOCS pass all checks (ref, backlog, frontmatter, audit-append, amended-by)"
exit 0
