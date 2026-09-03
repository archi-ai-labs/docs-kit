#!/usr/bin/env bash
# docs_profile.sh — which folders belong in THIS repo's docs/.
#
# SOURCED, never executed. `docs_scaffold.sh` and `docs_validate.sh` both need
# the answer, and two copies of it would be the one thing this kit refuses
# everywhere else: one fact with two sources. The map below is the single source.
#
# The whole answer comes from one declared field, `owns` in `.docs-kit.json`
# (STANDARD §9). There is deliberately no second axis: an earlier design had a
# `scope` enum beside it, and its only remaining job after D landed was "is this
# thing deployed?" — which is one token, not an enum, and one token is one less
# piece of state that can drift.
#
#   owns token   folders it justifies
#   ----------   --------------------
#   endpoints    04_api
#   screens      60_fe-integration
#   deploys      40_services · 50_runbooks · 70_deploy
#   data         (none — the erd lives in 02_architecture, which is core)
#   jobs         (none — a [queue] component lives in 02_architecture too)
#
# `data` and `jobs` unlock no folder on purpose. They still earn their place:
# both are evidence for `NOTE [profile]`, and both are read by anyone deciding
# what a repo is. A token is not required to open a folder to be worth declaring.
#
# **A repo that does not declare `owns` gets all 17 folders** — exactly what
# every version before this one did. That is the migration guarantee: no repo
# scaffolded by an older docs-kit changes shape, ever, without someone declaring
# something first.
#
# Portability: bash 3.2, BSD sed/grep. No associative arrays.

# Core — every repo, every profile. These answer the questions no repo escapes:
# what are we building, what is it made of, how does it change, what happened —
# and, since 0.27.0, what the kit itself got wrong here (99_feedback). That last
# one is core for the same reason 92_audit is: a repo that cannot record the
# problem records nothing, and the problem then reaches nobody.
DK_CORE="00_roadmap 01_products 02_architecture 03_business-logic
20_issues 21_proposals 22_decisions 23_backlog 30_conventions
92_audit 93_qa 99_feedback"

# Conditional — "<folder>:<the owns token that justifies it>".
DK_CONDITIONAL="04_api:endpoints
60_fe-integration:screens
40_services:deploys
50_runbooks:deploys
70_deploy:deploys"

# The closed enum. A token outside it is a typo, and a typo here silently drops a
# folder — which is why the validator fails on it rather than shrugging.
DK_TOKENS="data endpoints screens jobs deploys"

# DK_OWNS_OVERRIDE — when set (even to the empty string) it *is* the declaration
# and `.docs-kit.json` is not consulted. This is how `docs_scaffold.sh --owns`
# resolves a profile for a repo that has not recorded one yet, without growing a
# second copy of the map to do it.

# dk_owns_declared <root> — is there an `owns` key at all?
#
# Present-but-empty (`"owns": []`) is a declaration: a library that owns nothing
# conditional. Only an absent key means "this repo never said", which is the case
# that falls back to all 17.
dk_owns_declared() {
  [ "${DK_OWNS_OVERRIDE+set}" = set ] && return 0
  [ -f "$1/.docs-kit.json" ] || return 1
  tr -d '\n' < "$1/.docs-kit.json" | grep -q '"owns"[[:space:]]*:[[:space:]]*\['
}

# dk_owns <root> — one declared token per line. Prints nothing for `owns: []`.
# Handles a flat JSON array of strings, which is all the field is; the Python
# side uses a real parser.
dk_owns() {
  if [ "${DK_OWNS_OVERRIDE+set}" = set ]; then
    printf '%s\n' "$DK_OWNS_OVERRIDE" | tr ', ' '\n\n' | grep -v '^$'
    return 0
  fi
  [ -f "$1/.docs-kit.json" ] || return 0
  tr -d '\n' < "$1/.docs-kit.json" \
    | sed -n 's/.*"owns"[[:space:]]*:[[:space:]]*\[\([^]]*\)\].*/\1/p' \
    | tr ',' '\n' | tr -d ' "' | grep -v '^$'
}

# dk_owns_has <root> <token>
dk_owns_has() {
  dk_owns "$1" | grep -Fxq "$2"
}

# dk_owns_unknown <root> — one unrecognised token per line (empty when clean).
dk_owns_unknown() {
  dk_owns "$1" | while IFS= read -r t; do
    printf '%s\n' $DK_TOKENS | grep -Fxq "$t" || printf '%s\n' "$t"
  done
}

# dk_folders <root> — the folders this repo's profile requires.
dk_folders() {
  printf '%s\n' $DK_CORE
  if dk_owns_declared "$1"; then
    printf '%s\n' "$DK_CONDITIONAL" | while IFS=: read -r folder token; do
      [ -n "$folder" ] || continue
      dk_owns_has "$1" "$token" && printf '%s\n' "$folder"
    done
  else
    printf '%s\n' "$DK_CONDITIONAL" | sed 's/:.*//'
  fi
  return 0
}

# dk_folders_all — all 17. The union of every profile; nothing may fall
# outside it or the template tree ships a folder no repo can ever receive.
dk_folders_all() {
  printf '%s\n' $DK_CORE
  printf '%s\n' "$DK_CONDITIONAL" | sed 's/:.*//'
}

# dk_profile_label <root> — one line naming the profile, for a human reading a
# script's output. "all 17 folders (no owns declared)" or "owns: a, b".
dk_profile_label() {
  if dk_owns_declared "$1"; then
    set -- "$(dk_owns "$1" | LC_ALL=C sort | tr '\n' ',' | sed 's/,$//; s/,/, /g')"
    if [ -z "$1" ]; then
      printf 'owns: nothing conditional — core folders only\n'
    else
      printf 'owns: %s\n' "$1"
    fi
  else
    printf 'no owns declared in .docs-kit.json — all 17 folders\n'
  fi
}
