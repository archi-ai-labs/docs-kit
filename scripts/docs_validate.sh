#!/usr/bin/env bash
# docs_validate.sh — deterministic validator for the docs-kit three-layer model.
#
# Read-only. No LLM, no network. Contract: STANDARD.md §7.
#
# Usage:  docs_validate.sh [--strict] [docs_dir]     (default: ./docs)
# Exit:   0 = clean · 1 = violations found · 2 = setup error
# Output: one "FAIL [tag] <file>: <message>" line per violation, then a count.
#         "NOTE [tag] ..." lines print the same way and never affect the exit code.
#
# TWO SEVERITIES, AND THE LINE BETWEEN THEM IS NAMES vs LINKS (0.28.0).
#   A wrong NAME silently merges two different things: a duplicate id makes every
#   reference to it ambiguous, an id in the wrong folder breaks the convention the
#   folder is read by. Those stay FAIL.
#   A wrong LINK is one broken edge, visible the moment you follow it and harmless
#   until you do. Those print as NOTE and pass — `--strict` turns every one of them
#   back into a FAIL, which is what CI should run.
#
# Hard checks — these FAIL (tags):
#   [ref]          a duplicate id:, and a component name declared twice with
#                  CONFLICTING backticked paths (edges and the rendered cards
#                  resolve components by name, so two different paths under one
#                  name are genuinely ambiguous). Repeating a name with no path of
#                  its own is a re-mention — a cross-cutting flows doc naming a
#                  participant it does not own — and is not reported.
#   [frontmatter]  a missing `id`, an id whose prefix does not match its folder,
#                  an empty or invalid enum value
#   [audit-append] 92_audit/ files are append-only vs git HEAD (skipped without git/HEAD)
#   [profile]      `owns` in .docs-kit.json holds only tokens the standard defines.
#                  A typo there silently drops a folder from the scaffold, and
#                  `owns` is a closed enum, so a value outside it cannot be
#                  "a judgment call I disagree with"
#
# Soft checks — these print and pass, and FAIL only under --strict:
#   [ref]          a *_ref: that is empty or resolves to no id: under docs/;
#                  an 04_api/ `service:` naming no declared component
#   [backlog]      a Backlog item with no source_ref:
#   [frontmatter]  a required field other than `id` missing; a Proposal with no
#                  "Alternatives considered" heading
#   [amended-by]   an amended_by / rejected entry citing a Decision that is not there
#   [anchor]       a path a doc names — a `backticked` components path, a fence
#                  `code:` header, a `generated_from` artifact — that no longer exists
#
# Informational always (never affect the exit code, even under --strict):
#   NOTE [layout]  a folder this repo's profile calls for is missing (STANDARD §9 —
#                  the profile is `owns` in .docs-kit.json; no declaration = all 17)
#   NOTE [stale]   a Layer 1 doc carries verified_at: <rev> and files it names have
#                  changed since that rev. Changed is not the same as wrong, which is
#                  why this warns instead of failing (same rationale as STANDARD §8).
#   NOTE [profile] .docs-kit.json declares `owns`, and the repo shows a surface it
#                  does not account for — a component tagged [db]/[ui]/[queue], or a
#                  folder holding real documents. Seeds identical to their shipped
#                  template count as neither.
#   NOTE [seed]    01_products/ holds nothing but the shipped example. It is the one
#                  folder no docs-init step fills from source — who the users are and
#                  what counts as success are not written down in any repo — and its
#                  seed satisfies every check above, so without this line a scaffold
#                  that documents no product reports "pass all checks".
#
# Layer 2 folders may hold an `_archive/` subfolder for terminal documents; it is
# validated exactly like the folder above it — archiving lowers read cost, never
# the standard a document is held to.
#
# Portability: bash 3.2 (macOS), BSD awk/grep. No associative arrays, no GNU-isms.

set -u

STRICT=0
DOCS=""
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    -*) echo "FAIL [setup] unknown flag '$arg' (only --strict)"; exit 2 ;;
    *) [ -z "$DOCS" ] && DOCS="$arg" ;;
  esac
done
[ -z "$DOCS" ] && DOCS="docs"

if [ ! -d "$DOCS" ]; then
  echo "FAIL [setup] $DOCS: directory not found (run /docs-kit:docs-init first)"
  exit 2
fi

# Anchor paths are relative to the repo root, and checks 4 and 6 both need it,
# so it is resolved once here.
ROOT="$(cd "$DOCS/.." 2>/dev/null && pwd)"

# Which folders belong here is one question with one answer, and the scaffold has
# to ask it too — so the map lives in one file that both source (STANDARD §9). A
# broken install leaves the lib missing; degrade to "all 17", which is what every
# version before the profile existed did, rather than inventing findings.
VLIB="$(dirname "${BASH_SOURCE[0]:-$0}")/docs_profile.sh"
if [ -f "$VLIB" ]; then
  # shellcheck source=docs_profile.sh
  . "$VLIB"
  HAVE_PROFILE=1
else
  HAVE_PROFILE=0
fi

TMP="$(mktemp -d)" || exit 2
trap 'rm -rf "$TMP"' EXIT
FAILS="$TMP/fails"
NOTES="$TMP/notes"
SOFTS="$TMP/softs"
: > "$FAILS"
: > "$NOTES"
: > "$SOFTS"
TAB="$(printf '\t')"

fail() { # fail <tag> <file> <message>
  printf 'FAIL [%s] %s: %s\n' "$1" "$2" "$3" >> "$FAILS"
}

# NOTE lines print immediately and never touch the exit code. Used where
# "changed" cannot be distinguished from "wrong" without reading the code.
# Counted in a file, not a variable: several callers sit inside `... | while`
# pipelines, whose subshell would drop a counter increment on the floor.
note() { # note <tag> <file> <message>
  printf 'NOTE [%s] %s: %s\n' "$1" "$2" "$3"
  echo x >> "$NOTES"
}

# soft <tag> <file> <message> — a finding about a LINK, not about a name.
#
# A *_ref resolving to nothing, an amended_by citing a Decision that is not
# there, a documented path that moved: all still printed, none of them failing
# the run unless --strict is passed.
#
# WHY THE DEFAULT MOVED (0.28.0). Measured on this author's own repos before
# changing anything. BO-trading's 23_backlog/ is empty, and its README says why:
# `source_ref` must point at a Decision or an Issue, most of its workstreams had
# neither, so the work was written into the roadmap plan instead. A check people
# route around enforces nothing, while a check that prints without blocking is
# still read. (The 7 failures the old validator produced on that same repo were
# all false positives from the component check below, which is fixed rather than
# demoted — they are not evidence for this line.)
#
# Names stay hard, and that is the whole line: a duplicate id, an id in the
# wrong folder, an unknown `owns` token and a rewritten audit line remain FAIL,
# because those are the facts every link resolves *through*. A wrong link is one
# broken edge; a wrong name silently merges two different things.
soft() { # soft <tag> <file> <message>
  if [ "$STRICT" -eq 1 ]; then
    fail "$1" "$2" "$3"
  else
    note "$1" "$2" "$3"
    echo x >> "$SOFTS"   # the subset of NOTEs that --strict would have failed on
  fi
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
      soft ref "$f" "field '$key' is empty — every *_ref must point to an existing id"
    elif ! id_exists "$val"; then
      soft ref "$f" "field '$key' points to '$val' which matches no id: under $DOCS"
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
    soft backlog "$f" "missing or empty source_ref (Decision for full lane, Issue for fast lane)"
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
    fm_has "$rf_f" "$k" && continue
    # `id` is the name everything else resolves through, so its absence stays
    # hard. Every other missing field leaves a document that is merely thinner
    # than the contract asks for, and a thin document still resolves.
    if [ "$k" = "id" ]; then
      fail frontmatter "$rf_f" "missing required field 'id' — nothing can refer to this document"
    else
      soft frontmatter "$rf_f" "missing required field '$k'"
    fi
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

for dir in 01_products 02_architecture 03_business-logic 04_api 20_issues 21_proposals 22_decisions 23_backlog; do
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
      04_api)
        if require_fields "$f" service protocol amended_by; then
          fm_has "$f" protocol && check_enum "$f" protocol "$(fm_get "$f" protocol)" \
            http grpc graphql event
        fi
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
          soft frontmatter "$f" "missing 'Alternatives considered' heading (2-3 options with trade-offs required)"
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

for amdir in 02_architecture 03_business-logic 04_api; do
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
          soft amended-by "$f" "$key entry lacks a DECISION-NNN ref: '$entry'"
          continue
        fi
        while IFS= read -r r; do
          [ -z "$r" ] && continue
          id_exists "$r" || soft amended-by "$f" "$key cites '$r' which matches no Decision id: under $DOCS"
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
# opinion, so it is reported every run — a NOTE by default and a FAIL under
# --strict, because a moved path is a broken link, not a wrong name; a path that
# merely *changed* since verified_at is a NOTE in every mode, because changed is
# not the same as wrong.
#
# Placeholder values — anything containing < or > — are the templates' own
# "<file to read>" markers and are skipped, so a fresh scaffold passes clean.

# component_names <file> → the name of each components: entry, one per line.
# The name half of component_sig() — parsed once, so the two cannot disagree.
# Mirrors parse_components() in the renderer: split off the description at the
# first " — " / " – " / " -- " / ": ", then drop the [kind] tag and the `path`.
component_names() {
  component_sig "$1" | cut -f1
}

anchor_paths() { # anchor_paths <file> → one repo-relative path per line
  # 1. the backticked path inside each components: entry
  fm_list "$1" components | awk '
    { n = split($0, part, "`"); if (n >= 3 && part[2] != "") print part[2] }'
  # 1b. the generated artifact an API contract defers its volatile half to. It is
  #     an anchor like any other: if it moves, the contract can no longer be
  #     checked against reality, and the check going quiet is the danger.
  fm_get "$1" generated_from
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
      sub(/^"/, "", v); sub(/"$/, "", v)
      # A scenario rarely lives in one file, so the header takes a comma-separated
      # list. Reading the whole string as one path is what made every multi-path
      # header a FAIL — the check reporting a doc unverifiable for the way it was
      # punctuated, which is worse than not checking at all.
      n = split(v, ps, ",")
      for (j = 1; j <= n; j++) {
        p = ps[j]
        sub(/^[ \t]+/, "", p); sub(/[ \t\r]+$/, "", p)
        if (p != "") print p
      }
    }
  ' "$1"
}

# anchor_exists <root> <path> — does this anchor resolve to at least one file?
#
# Literal test first, and only then a glob. The order matters: a Next.js route
# segment like `app/students/[id]/page.tsx` is a real directory whose name happens
# to be a bracket expression, so expanding it as a pattern would report a file that
# is sitting right there as missing. `-e` does not glob, so the literal test settles
# every such path before the pattern branch is reached.
anchor_exists() {
  [ -e "$1/$2" ] && return 0
  case "$2" in
    *"*"*|*"?"*) ;;
    *) return 1 ;;
  esac
  # A path may legitimately name a family — `lib/validators/*.schema.ts` is one
  # fact about fourteen files, not fourteen facts. It resolves if anything matches.
  ( cd "$1" 2>/dev/null || exit 1
    for m in $2; do [ -e "$m" ] && exit 0; done
    exit 1 )
}

# anchor_prefix <path> — the form used to compare against changed files.
#
# `git diff --name-only` prints real filenames, which no pattern will ever equal,
# so a glob is reduced to its longest literal directory prefix. Coarser than the
# glob, and deliberately so: a NOTE that fires slightly too often costs one re-read,
# while one that never fires costs the whole check. `[` is not treated as a
# metacharacter here for the same reason as above.
anchor_prefix() {
  case "$1" in
    *"*"*|*"?"*) printf '%s\n' "${1%%[*?]*}" | sed 's|[^/]*$||' ;;
    *) printf '%s\n' "$1" ;;
  esac
}

# A component name IS a reference key: data_flow edges name components, and the
# rendered cards resolve upstream/downstream by name. Once 02_architecture/ holds
# one doc per service, two docs can declare the same name — and the renderer takes
# the first, silently.
#
# But repeating a name is not the same as disagreeing about it. A cross-cutting
# document — a flows.md drawing a sequence across services — has to NAME the
# participants that live in other documents, and the grammar has no way to say
# "reference, do not declare". Measured on BO-trading: 7 failures, every one a
# bare `- api` re-listed beside a bare `- api`, nothing in conflict, and the
# renderer's "takes the first" losing exactly nothing.
#
# So the conflict is what fails: two declarations of one name that give DIFFERENT
# backticked paths. Same path, or a path on only one side, is a re-mention.
# Mirrors parse_components() in the renderer: split off the description at the
# first " — " / " – " / " -- " / ": ", then drop the [kind] tag and the `path`.
# component_names() is the name half of this.
component_sig() { # component_sig <file> → "name<TAB>path" per entry ("" path if none)
  fm_list "$1" components | awk -F'`' '
    {
      s = $0
      sub(/^[ \t]*-[ \t]*/, "", s)
      sub(/^"/, "", s); sub(/"$/, "", s)
      path = (NF >= 3) ? $2 : ""
      for (i = 1; i <= 4; i++) {
        sep = (i == 1) ? " — " : (i == 2) ? " – " : (i == 3) ? " -- " : ": "
        p = index(s, sep)
        if (p > 0) { s = substr(s, 1, p - 1); break }
      }
      gsub(/\[[a-z]+\]/, "", s)
      gsub(/`[^`]*`/, "", s)
      gsub(/^[ \t]+|[ \t\r]+$/, "", s)
      if (s != "") print s "\t" path
    }'
}

: > "$TMP/compnames"
: > "$TMP/compsig"
for f in "$DOCS"/02_architecture/*.md; do
  [ -f "$f" ] || continue
  case "$(basename "$f")" in README.md) continue ;; esac
  component_names "$f" | while IFS= read -r n; do
    [ -n "$n" ] && printf '%s\n' "$n" >> "$TMP/compnames"
  done
  component_sig "$f" | while IFS="$TAB" read -r n path; do
    [ -n "$n" ] && printf '%s\t%s\t%s\n' "$n" "$path" "$f" >> "$TMP/compsig"
  done
done
if [ -s "$TMP/compsig" ]; then
  # Only names carrying two or more DISTINCT non-empty paths are conflicts.
  awk -F"$TAB" '$2 != "" { key = $1 SUBSEP $2; if (!(key in seen)) { seen[key] = 1; n[$1]++ } }
                END { for (k in n) if (n[k] > 1) print k }' "$TMP/compsig" \
    | LC_ALL=C sort > "$TMP/compdups"
  while IFS= read -r dup; do
    [ -z "$dup" ] && continue
    where="$(awk -F"$TAB" -v d="$dup" '$1==d && $2!="" { print $3 " (" $2 ")" }' "$TMP/compsig" | tr '\n' ' ')"
    first="$(awk -F"$TAB" -v d="$dup" '$1==d { print $3; exit }' "$TMP/compsig")"
    fail ref "$first" "component '$dup' is declared with conflicting paths: $where"
  done < "$TMP/compdups"
fi

# An API doc's `service:` is the one join between 04_api/ and 02_architecture/:
# it says which component publishes the contract. A name that matches nothing
# leaves the contract attached to no service at all, which is worse than having
# no API doc — the boundary looks documented and is not.
#
# Skipped when the architecture declares no components: a fresh scaffold has none,
# and there is nothing for a name to be wrong about.
if [ -s "$TMP/compnames" ] && [ -d "$DOCS/04_api" ]; then
  for f in "$DOCS"/04_api/*.md; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in README.md) continue ;; esac
    svc="$(fm_get "$f" service)"
    [ -z "$svc" ] && continue      # emptiness is check 3's finding, not this one
    cut -f1 "$TMP/compnames" | grep -Fxq "$svc" || \
      soft ref "$f" "service '$svc' matches no component declared in $DOCS/02_architecture/"
  done
fi

if [ -n "$ROOT" ]; then
  # Files changed since each doc's verified_at rev, resolved lazily per rev.
  HAVE_GIT=0
  if command -v git >/dev/null 2>&1 \
     && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    HAVE_GIT=1
  fi

  for andir in 01_products 02_architecture 03_business-logic 04_api; do
    [ -d "$DOCS/$andir" ] || continue
    for f in "$DOCS/$andir"/*.md; do
      [ -f "$f" ] || continue
      case "$(basename "$f")" in README.md) continue ;; esac

      anchor_paths "$f" | LC_ALL=C sort -u > "$TMP/anchors"
      [ -s "$TMP/anchors" ] || continue

      while IFS= read -r p; do
        [ -z "$p" ] && continue
        case "$p" in *"<"*|*">"*) continue ;; esac   # template placeholder
        anchor_exists "$ROOT" "$p" || \
          soft anchor "$f" "names '$p', which does not exist in the repo (a moved or deleted path makes this doc unverifiable)"
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
        p="$(anchor_prefix "$p")"
        [ -z "$p" ] && continue
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

# ------------- profile notes: does `owns` still describe this repo? ----------
#
# A project changes. A repo that owned no API grows one; a backend grows a
# frontend. `owns` in .docs-kit.json is a declared fact, and a declared fact
# drifts — so it gets the same treatment as verified_at and generated_from:
# declare it, and let something deterministic notice when reality disagrees.
#
# The evidence used here is the docs themselves, which needs no knowledge of any
# framework: a folder holding real documents that `owns` does not account for
# means the repo grew something nobody declared. It is a NOTE, not a FAIL —
# `owns` is optional and this rule has not been used in anger yet (STANDARD §8).
#
# Only the growth direction is checked. `owns` claiming something the repo no
# longer has cannot be told apart from "nobody has written it yet", and guessing
# there would cry wolf.
#
# `owns` is read by docs_profile.sh — the same reader the scaffold uses to decide
# which folders to create. Two readers would be one fact with two sources, which
# is the thing this kit refuses everywhere else.
#
# A file byte-identical to the template it was scaffolded from is a SEED, not
# something somebody wrote. Without this the check fires on a fresh scaffold —
# `04_api/example-api.md` ships with the plugin — and a warn-only rule that cries
# wolf on day one is a rule people switch off. Compared by bytes rather than by
# name because `60_fe-integration/overview.md` carries no "example" in its name.
VTEMPLATES="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../templates/docs" 2>/dev/null && pwd || true)"

folder_has_docs() { # folder_has_docs <dir-name-under-docs>
  fhd="$DOCS/$1"
  [ -d "$fhd" ] || return 1
  for fh in "$fhd"/*.md; do
    [ -f "$fh" ] || continue
    case "$(basename "$fh")" in README.md) continue ;; esac
    seed="$VTEMPLATES/$1/$(basename "$fh")"
    if [ -n "$VTEMPLATES" ] && [ -f "$seed" ] && cmp -s "$fh" "$seed"; then
      continue    # untouched template seed
    fi
    return 0
  done
  return 1
}

# No template tree to compare against means every seed would read as content, so
# the check would invent findings. Skipping is the honest failure mode.
# The strongest evidence is not a folder having files — it is a component's own
# [kind] tag. `components` already declares `mongo [db]`, `mini-app [ui]`,
# `jobs [queue]`, each with a path inside this repo, which is a repo saying in its
# own architecture doc what it holds. Found by running this on a real repo: it
# owned screens obviously (a [ui] component right there) and the folder-only rule
# stayed silent, because 60_fe-integration/ held nothing but its seed.
component_kinds() { # → one [kind] per component entry, deduped
  for ck in "$DOCS"/02_architecture/*.md; do
    [ -f "$ck" ] || continue
    case "$(basename "$ck")" in README.md) continue ;; esac
    fm_list "$ck" components | grep -oE '\[(db|queue|ui|svc)\]'
  done | tr -d '[]' | LC_ALL=C sort -u
}

if [ -n "$ROOT" ] && [ "$HAVE_PROFILE" -eq 1 ] && dk_owns_declared "$ROOT"; then
  # A token outside the enum is not an opinion, it is a typo — and this one has
  # teeth now: `owns` decides which folders the scaffold creates, so "endpoint"
  # for "endpoints" silently costs the repo its 04_api/. Fail, do not shrug.
  for bad in $(dk_owns_unknown "$ROOT"); do
    fail profile "$ROOT/.docs-kit.json" "unknown owns token '$bad' — valid: $(printf '%s ' $DK_TOKENS)"
  done
fi

if [ -n "$ROOT" ] && [ "$HAVE_PROFILE" -eq 1 ] && [ -n "$VTEMPLATES" ] && dk_owns_declared "$ROOT"; then
  KINDS="$(component_kinds)"
  has_kind() { printf '%s\n' "$KINDS" | grep -Fxq "$1"; }

  if folder_has_docs 04_api && ! dk_owns_has "$ROOT" endpoints; then
    note profile "$DOCS/04_api" "holds contracts but .docs-kit.json 'owns' does not list 'endpoints' — this repo grew an API surface; update owns (that is a layer 1 change, so it goes through a Decision)"
  fi
  if { folder_has_docs 60_fe-integration || has_kind ui; } && ! dk_owns_has "$ROOT" screens; then
    note profile "$DOCS" "declares a [ui] component or fe-integration docs, but .docs-kit.json 'owns' does not list 'screens' — update owns"
  fi
  if has_kind db && ! dk_owns_has "$ROOT" data; then
    note profile "$DOCS" "declares a [db] component, but .docs-kit.json 'owns' does not list 'data' — update owns"
  fi
  if has_kind queue && ! dk_owns_has "$ROOT" jobs; then
    note profile "$DOCS" "declares a [queue] component, but .docs-kit.json 'owns' does not list 'jobs' — update owns"
  fi
  # `deploys` decides three folders at once (40_services · 50_runbooks · 70_deploy),
  # so it is the token whose absence costs the most. Its evidence is the same shape
  # as the rest: those folders holding something somebody wrote.
  if { folder_has_docs 40_services || folder_has_docs 50_runbooks \
       || folder_has_docs 70_deploy; } && ! dk_owns_has "$ROOT" deploys; then
    note profile "$DOCS" "holds operational docs (40_services / 50_runbooks / 70_deploy) but .docs-kit.json 'owns' does not list 'deploys' — update owns"
  fi
fi

# ----------------------- no product described yet (informational, never failing) ---
#
# `01_products/` is the one folder in the tree that is present under every profile,
# is never written by any step of docs-init, and whose seed passes every check
# above. It passes because the six required fields are all *present* in it —
# filled with the sentence describing what to write there. Measured on a fresh
# scaffold before this check existed: validate printed "pass all checks",
# current.html listed "Example product" under Products, and INDEX.md told the next
# agent this repo documents one product.
#
# Why docs-init cannot just fill it like the rest of layer 1: `components` and
# `data_flow` are read out of the source, but no repo writes down who its users
# are or what counts as success. That is an answer only a person has, so the step
# that gets it has to ask — and until someone answers, this line is the reminder.
#
# Informational, never failing, not even under --strict: on day one the seed IS
# the correct state, and a check that fails a fresh scaffold is a check people
# switch off.
product_described() {
  pdt="$VTEMPLATES/01_products"
  pd_name=""
  [ -n "$VTEMPLATES" ] && [ -f "$pdt/example-product.md" ] \
    && pd_name="$(fm_get "$pdt/example-product.md" name)"
  for pf in "$DOCS"/01_products/*.md "$DOCS"/01_products/_archive/*.md; do
    [ -f "$pf" ] || continue
    case "$(basename "$pf")" in README.md) continue ;; esac
    # Two ways to still be the shipped example. Byte-identical is the same test
    # folder_has_docs uses, and it is not folded into that function because the
    # two ask different questions: that one asks whether a folder holds content,
    # this one asks whether anyone has described a product.
    if [ -n "$VTEMPLATES" ] && [ -f "$pdt/$(basename "$pf")" ] \
       && cmp -s "$pf" "$pdt/$(basename "$pf")"; then
      continue
    fi
    # Renamed and lightly edited, frontmatter untouched: the file is a different
    # name and different bytes, and `name:` still says "Example product". A
    # product doc whose own name is the placeholder describes nothing.
    if [ -n "$pd_name" ] && [ "$(fm_get "$pf" name)" = "$pd_name" ]; then
      continue
    fi
    return 0
  done
  return 1
}

if [ -d "$DOCS/01_products" ] && ! product_described; then
  note seed "$DOCS/01_products" "no product is described here yet — only the shipped example, whose six fields are placeholders that satisfy every check above. current.html and INDEX.md report it as a real product. Fill name/users/problem/scope_in/scope_out/success_metric, or re-run /docs-kit:docs-init, whose Step 3.5 drafts it and asks for the two fields no source read can answer"
fi

# ----------------------------- layout notes (informational, never failing) ---
#
# What counts as missing depends on the profile: a repo that declares
# `owns: ["data"]` is not missing 04_api/, it never asked for one. A repo that
# declares nothing is held to all 17, exactly as before profiles existed.
#
# A folder present but *outside* the profile is never reported. Repos grow, docs
# are not deleted for a config change, and "extra folder" is not a finding
# anywhere else in this kit.
if [ "$HAVE_PROFILE" -eq 1 ]; then
  LAYOUT_WANT="$(dk_folders "$ROOT" | LC_ALL=C sort -u)"
  LAYOUT_WHY="$(dk_profile_label "$ROOT")"
else
  LAYOUT_WANT="$(printf '%s\n' 00_roadmap 01_products 02_architecture 03_business-logic 04_api \
    20_issues 21_proposals 22_decisions 23_backlog 30_conventions \
    40_services 50_runbooks 60_fe-integration 70_deploy 92_audit 93_qa 99_feedback)"
  LAYOUT_WHY="docs_profile.sh not found — held to all 17"
fi
for dir in $LAYOUT_WANT; do
  [ -d "$DOCS/$dir" ] || note layout "$DOCS/$dir" "folder missing — this repo's profile calls for it ($LAYOUT_WHY)"
done

# -------------------------------------------------------------------- report -

SCANNED="$(wc -l < "$TMP/files" | tr -d ' ')"
if [ -s "$FAILS" ]; then
  cat "$FAILS"
  echo "docs-validate: $(wc -l < "$FAILS" | tr -d ' ') violation(s) across $SCANNED markdown file(s) in $DOCS"
  exit 1
fi
NOTED="$(wc -l < "$NOTES" | tr -d ' ')"
SOFTED="$(wc -l < "$SOFTS" | tr -d ' ')"
if [ "$SOFTED" -gt 0 ]; then
  # No failures, so this run passes — but "pass all checks" would read as
  # "nothing was found", and the NOTE lines above found something.
  echo "docs-validate: OK — $SCANNED markdown file(s) in $DOCS, no failures · $NOTED note(s) above, $SOFTED of them fail under --strict"
elif [ "$NOTED" -gt 0 ]; then
  # Layout/profile/stale notes only: nothing here fails in any mode.
  echo "docs-validate: OK — $SCANNED markdown file(s) in $DOCS pass all checks · $NOTED informational note(s) above"
else
  echo "docs-validate: OK — $SCANNED markdown file(s) in $DOCS pass all checks (ref, backlog, frontmatter, audit-append, amended-by, anchor, profile)"
fi
exit 0
