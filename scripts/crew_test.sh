#!/usr/bin/env bash
# docs-kit — deterministic tests for the crew layer.
#
# EXECUTION §8 rule 3 is the reason this file exists and the reason it looks
# the way it does: every enforcement path is run on a KNOWN-BAD case first,
# and the assertion is on the reason tag ([gate:no-draw], "check 1", …), not
# on the exit code — a check that fails for a shape error proves zero.
#
# Self-contained: builds its own scratch repos under mktemp, needs git,
# python3, and the kit checkout it lives in. Exit 0 = all green.
set -u

KIT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/crewtest.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "ok   - $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL - $1"; }
has() { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }

command -v python3 >/dev/null 2>&1 || { echo "crew_test: python3 required"; exit 2; }
command -v git >/dev/null 2>&1 || { echo "crew_test: git required"; exit 2; }

GATE="$KIT/scripts/hook_explain_gate.sh"
GUARD="$KIT/scripts/hook_resource_guard.sh"

run_gate() { # run_gate <cwd> <transcript>
  printf '{"session_id":"t1","cwd":"%s","transcript_path":"%s","tool_name":"AskUserQuestion","tool_input":{}}' \
    "$1" "$2" | bash "$GATE"
}
run_guard() { # run_guard <cwd> <command>
  printf '{"cwd":"%s","tool_name":"Bash","tool_input":{"command":"%s"}}' \
    "$1" "$2" | bash "$GUARD"
}

# ---------------------------------------------------------------- hook fixtures
HR="$TMP/hookrepo"
mkdir -p "$HR"
( cd "$HR" && git init -q && git checkout -q -b main \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init )
cat > "$HR/.docs-kit.json" <<'EOF'
{"owns": [], "crew": {"resources": {"e2e-harness": {"patterns": ["playwright"]}}}}
EOF

TS="$TMP/transcripts"
mkdir -p "$TS"
U='{"type":"user","message":{"role":"user","content":[{"type":"text","text":"please decide"}]}}'
TR='{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"x","content":"ok"}]}}'
A_PLAIN='{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I will ask the user now."}]}}'
A_DRAW='{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"d1","name":"mcp__visualize__show_widget","input":{}}]}}'
A_LANE='{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Nothing here is irreversible.\nLANE: fast — one config line, plain revert\nProceeding to the question."}]}}'
A_ECHO='{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"either show the decision or declare the fast lane with its one-line marker, says the gate"}]}}'

printf '%s\n%s\n' "$U" "$A_PLAIN" > "$TS/no_draw.jsonl"
printf '%s\n%s\n%s\n' "$U" "$A_DRAW" "$TR" > "$TS/draw.jsonl"
printf '%s\n%s\n' "$U" "$A_LANE" > "$TS/lane.jsonl"
printf '%s\n%s\n%s\n' "$A_DRAW" "$U" "$A_PLAIN" > "$TS/stale_draw.jsonl"
printf '%s\n%s\n' "$U" "$A_ECHO" > "$TS/echo_guidance.jsonl"

# THE known-bad case, first: a question with no drawing and no declared lane
# must warn, and must warn with the right tag.
OUT="$(run_gate "$HR" "$TS/no_draw.jsonl")"
has "$OUT" "[gate:no-draw]" && ok "gate: known-bad case is red, for the right reason" \
  || bad "gate: known-bad case (got: $OUT)"

# The self-unlock regression: text that merely DESCRIBES the marker (as the
# hook's own guidance does) must not open the gate. The origin repo's first
# gate died exactly here.
OUT="$(run_gate "$HR" "$TS/echo_guidance.jsonl")"
has "$OUT" "[gate:no-draw]" && ok "gate: guidance echo does not self-unlock" \
  || bad "gate: guidance echo self-unlocked (got: $OUT)"

# Evidence from BEFORE the last human turn is stale and does not count.
OUT="$(run_gate "$HR" "$TS/stale_draw.jsonl")"
has "$OUT" "[gate:no-draw]" && ok "gate: stale drawing does not count" \
  || bad "gate: stale drawing counted (got: $OUT)"

OUT="$(run_gate "$HR" "$TS/draw.jsonl")"
[ -z "$OUT" ] && ok "gate: drawing satisfies the gate" \
  || bad "gate: drawing case not silent (got: $OUT)"

OUT="$(run_gate "$HR" "$TS/lane.jsonl")"
[ -z "$OUT" ] && ok "gate: declared lane satisfies the gate" \
  || bad "gate: lane case not silent (got: $OUT)"

# Unreadable transcript → fail OPEN (allow) + one line in gate.log, so
# silence-from-broken never looks like silence-from-clean.
OUT="$(run_gate "$HR" "$TMP/no-such-transcript.jsonl")"
GLOG="$TMP/hookrepo-crew/gate.log"
if [ -z "$OUT" ] && [ -f "$GLOG" ] && grep -q "OPEN transcript unreadable" "$GLOG"; then
  ok "gate: fails open with a trail"
else
  bad "gate: fail-open trail missing (out: $OUT)"
fi

# enforce: true turns the same red case into a deny — same tag, harder verdict.
HR2="$TMP/hookrepo2"
mkdir -p "$HR2"
( cd "$HR2" && git init -q && git checkout -q -b main \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init )
printf '{"owns": [], "crew": {"enforce": true}}\n' > "$HR2/.docs-kit.json"
OUT="$(run_gate "$HR2" "$TS/no_draw.jsonl")"
if has "$OUT" '"permissionDecision": "deny"' && has "$OUT" "[gate:no-draw]"; then
  ok "gate: enforce flag promotes warn to deny"
else
  bad "gate: enforce promotion (got: $OUT)"
fi

# No crew key → the layer is off and the hook says nothing at all.
HR3="$TMP/hookrepo3"
mkdir -p "$HR3"
printf '{"owns": []}\n' > "$HR3/.docs-kit.json"
OUT="$(run_gate "$HR3" "$TS/no_draw.jsonl")"
[ -z "$OUT" ] && ok "gate: silent when crew is off" \
  || bad "gate: spoke while off (got: $OUT)"

# ---------------------------------------------------------------- resource-guard
OUT="$(run_guard "$HR" "npx playwright test --project=chromium")"
has "$OUT" "[resource:no-lock e2e-harness]" && ok "guard: unlocked resource warns, right tag" \
  || bad "guard: unlocked resource (got: $OUT)"

mkdir -p "$TMP/hookrepo-crew/locks"
printf 'BACKLOG-001\n1\n' > "$TMP/hookrepo-crew/locks/e2e-harness.lock"
OUT="$(run_guard "$HR" "npx playwright test")"
[ -z "$OUT" ] && ok "guard: held lock is silent" \
  || bad "guard: held lock spoke (got: $OUT)"

OUT="$(run_guard "$HR" "ls -la")"
[ -z "$OUT" ] && ok "guard: unrelated command is silent" \
  || bad "guard: unrelated command spoke (got: $OUT)"

# ---------------------------------------------------------------- crew CLI e2e
W="$TMP/work"
WR="$W/repo"
mkdir -p "$WR"
(
  cd "$WR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  echo hello > README.md
  # A checkout is not a working environment: gitignored payload (nested
  # harness repo, env file, shared cache) that crew new must put back.
  printf '.env\nharness/\nshared-cache/\n' > .gitignore
  mkdir -p harness shared-cache
  echo h > harness/h.txt
  echo c > shared-cache/c.txt
  echo SECRET > .env
  mkdir -p docs/23_backlog docs/92_audit scripts
  cat > docs/23_backlog/demo.md <<'EOF'
---
id: BACKLOG-001
description: "phiếu thử"
source_ref: ISSUE-001
status: open
scope_files: 1
---
Thân phiếu.
EOF
  cat > docs/23_backlog/pair.md <<'EOF'
---
id: BACKLOG-002
description: "phiếu fast-pair"
source_ref: ISSUE-002
status: open
execution: fast-pair
---
EOF
  for n in 003 004; do
    printf -- '---\nid: BACKLOG-%s\ndescription: "phiếu %s"\nsource_ref: ISSUE-%s\nstatus: open\n---\n' "$n" "$n" "$n" \
      > "docs/23_backlog/t$n.md"
  done
  echo lock-v1 > package-lock.json
  printf '# audit log\n' > docs/92_audit/LOG.md
  printf '{"owns": [], "crew": {"dev_branch": "main", "test_cmd": "", "typecheck_cmd": "", "copy": ["harness", ".env"], "link": ["shared-cache"], "setup_cmd": "printf x >> harness/.setup-done", "resetup_when": ["package-lock.json"], "roles_absent": ["devops"]}}\n' > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init
)

# Known-bad first: no ticket, no branch.
OUT="$( (cd "$WR" && scripts/crew new 5) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "no ticket, no branch"; then
  ok "cli: refuses a branch for a missing ticket"
else
  bad "cli: missing-ticket refusal (rc=$RC out: $OUT)"
fi

OUT="$( (cd "$WR" && scripts/crew new 2) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "fast-pair"; then
  ok "cli: refuses an executor for a fast-pair ticket"
else
  bad "cli: fast-pair refusal (rc=$RC out: $OUT)"
fi

OUT="$( (cd "$WR" && scripts/crew executor add) 2>&1 )" || bad "cli: executor add failed: $OUT"
E1="$W/repo-e1"
if [ -d "$E1" ] && [ "$(git -C "$E1" rev-parse --abbrev-ref HEAD)" = "HEAD" ]; then
  ok "cli: a fresh executor parks at a detached HEAD, which is how free is encoded"
else
  bad "cli: executor add did not park detached"
fi
if [ -f "$E1/harness/h.txt" ] && [ -f "$E1/.env" ]; then
  ok "cli: gitignored payload copied into the executor"
else
  bad "cli: copy list not provisioned"
fi
[ -L "$E1/shared-cache" ] && ok "cli: read-only share is a symlink" \
  || bad "cli: link list not provisioned"
[ "$(cat "$E1/harness/.setup-done" 2>/dev/null)" = "x" ] \
  && ok "cli: setup_cmd ran once when the executor was built" \
  || bad "cli: setup_cmd did not run at add"
grep -q "SETUP" "$W/repo-crew/log.tsv" 2>/dev/null \
  && ok "cli: provisioning time logged against the executor" \
  || bad "cli: SETUP line missing from log.tsv"

OUT="$( (cd "$WR" && scripts/crew new 1) 2>&1 )" || bad "cli: crew new 1 failed: $OUT"
WT="$E1"
if [ "$(git -C "$WT" rev-parse --abbrev-ref HEAD)" = "work/b001" ]; then
  ok "cli: the ticket branch opens inside a free executor"
else
  bad "cli: branch did not open in the executor"
fi
# The pin is the branch, so a second claim on the same ticket must be refused by
# reading git, not by consulting a file that could disagree with it.
OUT="$( (cd "$WR" && scripts/crew new 1) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "already open in e1"; then
  ok "cli: the branch an executor holds is the pin, and it is read back"
else
  bad "cli: double-assignment not refused (rc=$RC out: $OUT)"
fi
[ "$(cat "$WT/harness/.setup-done" 2>/dev/null)" = "x" ] \
  && ok "cli: setup_cmd skipped when no lockfile moved" \
  || bad "cli: setup_cmd re-ran with an unchanged lockfile"

# Executor state is derived from the branch, so walk the lifecycle and assert
# each shape. A state that never changes proves nothing — all four are checked.
st() { (cd "$WR" && scripts/crew status) 2>&1 | awk '$1 == "e1" { print $4; exit }'; }
[ "$(st)" = "processing" ] && ok "state: an executor holding a branch reads processing" \
  || bad "state: expected processing, got '$(st)'"
( cd "$WT" && echo half > f.txt && git add f.txt \
    && git -c user.email=t@t -c user.name=t commit -qm "wip" )
[ "$(st)" = "processing" ] && ok "state: a commit does not change it — only the trailer does" \
  || bad "state: expected processing after a plain commit, got '$(st)'"

# A pool size is a guess, so a full pool GROWS rather than blocking the ticket.
OUT="$( (cd "$WR" && scripts/crew new 3) 2>&1 )" || bad "cli: crew new 3 failed: $OUT"
if has "$OUT" "no executor was free" && [ -d "$W/repo-e2" ] \
   && [ "$(git -C "$W/repo-e2" rev-parse --abbrev-ref HEAD)" = "work/b003" ]; then
  ok "cli: a full pool grows by one instead of blocking the ticket"
else
  bad "cli: full-pool growth (out: $OUT)"
fi
[ -f "$W/repo-e2/harness/h.txt" ] && [ -L "$W/repo-e2/shared-cache" ] \
  && ok "cli: the grown executor is provisioned like any other" \
  || bad "cli: grown executor not provisioned"
grep -q "GROW" "$W/repo-crew/log.tsv" 2>/dev/null \
  && ok "cli: growth is logged, so a pool that only grows is visible later" \
  || bad "cli: GROW line missing from log.tsv"
OUT="$( (cd "$WR" && scripts/crew executor rm 2) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "still holds work/b003"; then
  ok "cli: a busy executor cannot be removed"
else
  bad "cli: busy-executor removal (rc=$RC out: $OUT)"
fi

( cd "$WR" && git checkout -q -b temp )
OUT="$( (cd "$WR" && scripts/crew done 1) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "check 1"; then
  ok "cli: check 1 is red on the wrong branch, for the right reason"
else
  bad "cli: check 1 (rc=$RC out: $OUT)"
fi
( cd "$WR" && git checkout -q main && git branch -q -D temp )

echo dirty >> "$WR/README.md"
OUT="$( (cd "$WR" && scripts/crew done 1) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "check 2" && has "$OUT" "README.md"; then
  ok "cli: check 2 is red on a dirty tree and names the file"
else
  bad "cli: check 2 (rc=$RC out: $OUT)"
fi
( cd "$WR" && git checkout -q -- README.md )

# Happy path: commit with the Closes: trailer, then done → merged, closed, cleaned.
(
  cd "$WT"
  echo change > f.txt
  git add f.txt
  git -c user.email=t@t -c user.name=t commit -qm "add f" -m "Closes: BACKLOG-001"
)
[ "$(st)" = "finishing" ] && ok "state: a Closes: trailer reads finishing, before any merge" \
  || bad "state: expected finishing, got '$(st)'"
OUT="$( (cd "$WR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew done 1) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] || bad "cli: crew done 1 failed (out: $OUT)"
[ -z "$(st)" ] && ok "state: a parked executor is back to idle" \
  || bad "state: expected idle, got '$(st)'"
[ -f "$WR/f.txt" ] && ok "cli: work is on the dev branch" || bad "cli: merge did not land"
if [ -d "$WT" ] && [ "$(git -C "$WT" rev-parse --abbrev-ref HEAD)" = "HEAD" ]; then
  ok "cli: done parks the executor instead of destroying it"
else
  bad "cli: executor not parked after done"
fi
[ -f "$WT/harness/h.txt" ] && [ -L "$WT/shared-cache" ] \
  && ok "cli: the payload survives the ticket, which is the whole saving" \
  || bad "cli: payload lost on park"

# Keeping the payload is the saving AND the hazard: the next ticket would test
# against the last one's dependencies. The guard is not "it usually re-runs" —
# it must re-run exactly when a resetup_when file moved, so prove that branch.
( cd "$WR" && echo lock-v2 > package-lock.json \
    && git -c user.email=t@t -c user.name=t commit -qam "bump lock" )
OUT="$( (cd "$WR" && scripts/crew new 4) 2>&1 )" || bad "cli: crew new 4 failed: $OUT"
if [ "$(cat "$WT/harness/.setup-done" 2>/dev/null)" = "xx" ] && ! has "$OUT" "skipped"; then
  ok "cli: a moved lockfile re-runs setup_cmd in the reused executor"
else
  bad "cli: lockfile drift did not re-provision (out: $OUT)"
fi
( cd "$WR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew done 4 >/dev/null 2>&1 ) || true
grep -q "^status: done" "$WR/docs/23_backlog/demo.md" \
  && ok "cli: docs_close flipped status via the trailer" \
  || bad "cli: status not flipped"
grep -q "BACKLOG-001" "$WR/docs/92_audit/LOG.md" \
  && ok "cli: audit line cites the completion" \
  || bad "cli: audit line missing"
LOGT="$W/repo-crew/log.tsv"
if [ -f "$LOGT" ] && grep -q "SIZE" "$LOGT" && grep -q "declared=1 actual=1" "$LOGT"; then
  ok "cli: size calibration logged (declared vs actual)"
else
  bad "cli: size calibration missing"
fi

OUT="$( (cd "$WR" && scripts/crew lock acquire e2e-harness 7) 2>&1 )" \
  && ok "cli: lock acquired" || bad "cli: lock acquire ($OUT)"
OUT="$( (cd "$WR" && scripts/crew lock acquire e2e-harness 8) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "held by BACKLOG-007"; then
  ok "cli: second owner queues, holder named"
else
  bad "cli: lock contention (rc=$RC out: $OUT)"
fi
OUT="$( (cd "$WR" && scripts/crew status) 2>&1 )"
if has "$OUT" "e2e-harness" && has "$OUT" "pacing:"; then
  ok "cli: status shows locks and pacing"
else
  bad "cli: status output (got: $OUT)"
fi
has "$OUT" "prod_branch 'production' does not exist" \
  && ok "cli: status surfaces the missing prod branch" \
  || bad "cli: missing prod branch not surfaced (got: $OUT)"
has "$OUT" "role 'devops' declared absent" \
  && ok "cli: status surfaces the absent role" \
  || bad "cli: absent role not surfaced (got: $OUT)"
OUT="$( (cd "$WR" && scripts/crew lock release e2e-harness 7) 2>&1 )" \
  && ok "cli: lock released" || bad "cli: lock release ($OUT)"
grep -q "RELEASE" "$LOGT" && ok "cli: release logged with held time" \
  || bad "cli: release not logged"

# ---------------------------------------------------------------- concurrency
# Two commands read shared state and then write it, which is the same defect
# twice, and BOTH were real (measured 2026-09-08 before the fix): three
# concurrent `crew new` against a pool of two landed one ticket in 4 runs of 5
# and left the second executor idle with a branch nobody held, and two
# concurrent `crew lock acquire` on one resource BOTH reported success in 5 of
# 5. Neither is provable by reading the code, so both are raced here.
R="$TMP/race"; RR="$R/app"
mkdir -p "$RR"
(
  cd "$RR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  mkdir -p scripts docs/23_backlog
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  printf '{"crew":{"dev_branch":"dev","copy":[],"link":[],"setup_cmd":""}}\n' > .docs-kit.json
  for n in 157 158 159; do
    printf -- '---\nid: BACKLOG-%s\nstatus: open\nexecution: fast\n---\n' "$n" > "docs/23_backlog/b$n.md"
  done
  echo x > README.md
  git add -A && git commit -qm init && git branch dev
  scripts/crew executor add >/dev/null 2>&1
  scripts/crew executor add >/dev/null 2>&1
) >/dev/null 2>&1
( cd "$RR" && scripts/crew new 157 >"$R/o1" 2>&1 ) &
( cd "$RR" && scripts/crew new 158 >"$R/o2" 2>&1 ) &
( cd "$RR" && scripts/crew new 159 >"$R/o3" 2>&1 ) &
wait
TOOK="$(cat "$R"/o1 "$R"/o2 "$R"/o3 2>/dev/null | grep -c 'executor :' || true)"
BRN="$(git -C "$RR" branch --list 'work/*' 2>/dev/null | wc -l | tr -d ' ')"
POOLN="$(ls -d "$R"/app-e[0-9]* 2>/dev/null | wc -l | tr -d ' ')"
if [ "$TOOK" -eq 3 ] && [ "$BRN" -eq 3 ] && [ "$POOLN" -eq 3 ]; then
  ok "race: 3 concurrent claims on a pool of 2 all land, growing it to exactly 3"
else
  bad "race: crew new (took=$TOOK branches=$BRN pool=$POOLN)"
fi
# Distinct trees, distinct branches: growth under contention must not hand two
# tickets the same index or the same checkout.
HEADS="$(for d in "$R"/app-e[0-9]*; do git -C "$d" symbolic-ref --short HEAD 2>/dev/null || echo -; done | sort)"
if [ "$(echo "$HEADS" | wc -l | tr -d ' ')" -eq 3 ] \
   && [ "$(echo "$HEADS" | sort -u | wc -l | tr -d ' ')" -eq 3 ] \
   && ! echo "$HEADS" | grep -qx -- '-'; then
  ok "race: every executor holds a different branch, and none was left empty"
else
  bad "race: executor assignment ($(echo "$HEADS" | tr '\n' ' '))"
fi

# Growth is automatic, so shrinking must be one command — otherwise the pool
# only ratchets up. Prune takes idle trees only, and stops at the floor.
( cd "$R/app-e3" && git switch -q --detach dev 2>/dev/null ) || true
OUT="$( (cd "$RR" && scripts/crew executor prune 1) 2>&1 )"
POOLN="$(ls -d "$R"/app-e[0-9]* 2>/dev/null | wc -l | tr -d ' ')"
if [ "$POOLN" -eq 2 ] && has "$OUT" "removed e3" && has "$OUT" "kept e1"; then
  ok "prune: idle executors go, busy ones are kept and named"
else
  bad "prune: (pool=$POOLN out: $OUT)"
fi

( cd "$RR" && scripts/crew lock acquire rig 157 >"$R/l1" 2>&1 ) &
( cd "$RR" && scripts/crew lock acquire rig 158 >"$R/l2" 2>&1 ) &
wait
HELD="$(cat "$R/l1" "$R/l2" 2>/dev/null | grep -c 'acquired by' || true)"
QUEUED="$(cat "$R/l1" "$R/l2" 2>/dev/null | grep -c 'is held by' || true)"
if [ "$HELD" -eq 1 ] && [ "$QUEUED" -eq 1 ]; then
  ok "race: one resource, two acquires — exactly one holder, the loser is told who"
else
  bad "race: lock acquire (held=$HELD queued=$QUEUED)"
fi

# ---------------------------------------------------------------- session name
# The title is the last custom-title record in the session transcript, reached
# from the sessionId in the live session entry — which the check finds by walking
# up the process tree. Planting the entry under this harness's own pid exercises
# that walk for real instead of stubbing it.
SESS="$TMP/sessions"
PROJ="$TMP/projects/slug"
mkdir -p "$SESS" "$PROJ"
RNAME="$(basename "$WR")"
printf '{"pid":%s,"sessionId":"s1"}\n' "$$" > "$SESS/$$.json"
run_name() { # run_name <args...>
  (cd "$WR" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name "$@") 2>&1
}

# Known-bad first: an auto-generated title is not a hat name.
printf '{"type":"custom-title","customTitle":"Diagram explanations"}\n' > "$PROJ/s1.jsonl"
OUT="$(run_name steward)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "[name:wrong]" \
   && has "$OUT" "/rename $RNAME · crew/steward"; then
  ok "name: wrong title is red, and prints the line the human must type"
else
  bad "name: wrong title (rc=$RC, got: $OUT)"
fi

# A session nobody has retitled reads as unnamed, not as a match on empty.
printf '{"type":"ai-title","aiTitle":"Diagram explanations"}\n' > "$PROJ/s1.jsonl"
OUT="$(run_name steward)" && RC=0 || RC=$?
[ "$RC" -ne 0 ] && has "$OUT" "no set title" && ok "name: an auto title is not a name" \
  || bad "name: auto title (rc=$RC, got: $OUT)"

# The LAST custom-title wins — a rename lands as another record, not an edit.
{ printf '{"type":"custom-title","customTitle":"old name"}\n'
  printf '{"type":"custom-title","customTitle":"%s · crew/steward"}\n' "$RNAME"; } > "$PROJ/s1.jsonl"
OUT="$(run_name steward)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && has "$OUT" "name ok" && ok "name: the newest title is the title" \
  || bad "name: correct title rejected (rc=$RC, got: $OUT)"

# A ticket session carries the §1 token in the middle, zero-padded the way
# `crew new 42` pads it — an unpadded expectation would disagree with the branch.
printf '{"type":"custom-title","customTitle":"%s · b042 · crew/executor"}\n' "$RNAME" > "$PROJ/s1.jsonl"
OUT="$(run_name executor 42)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && ok "name: ticket grammar carries the padded token" \
  || bad "name: ticket grammar (rc=$RC, got: $OUT)"

# An executor is titled by its TREE, not its ticket: the pool is persistent, so
# one session spans many tickets and is named once. Running the check from
# inside e1 is what selects that grammar, so run it from there for real.
# A session is one per ticket, so a parked executor has NO session to name and
# the command must say that rather than invent an idle title.
OUT="$( (cd "$E1" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name executor) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "holds no ticket"; then
  ok "name: a parked executor has no session to name, and the command says so"
else
  bad "name: idle executor should refuse (rc=$RC, got: $OUT)"
fi

# All three parts come from git — no argument is passed, so a pass proves the
# title was derived. Born processing:
( cd "$E1" && git switch -q -c work/b042 2>/dev/null )
en_title() { printf '{"type":"custom-title","customTitle":"%s"}\n' "$1" > "$PROJ/s1.jsonl"; }
en_title "$RNAME · e1 · b042 · processing · crew/executor"
OUT="$( (cd "$E1" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name executor) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && ok "name: a new executor session is born processing" \
  || bad "name: processing grammar (rc=$RC, got: $OUT)"

# ...and the SAME title goes red once the trailer lands, naming the new state.
( cd "$E1" && echo z > z.txt && git add z.txt \
    && git -c user.email=t@t -c user.name=t commit -qm "done" -m "Closes: BACKLOG-042" )
OUT="$( (cd "$E1" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name executor) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "b042 · finishing"; then
  ok "name: the trailer flips the title to finishing, and the old one is red"
else
  bad "name: finishing grammar (rc=$RC, got: $OUT)"
fi
en_title "$RNAME · e1 · b042 · finishing · crew/executor"
OUT="$( (cd "$E1" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name executor) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && ok "name: the retitled session matches again" \
  || bad "name: finishing match (rc=$RC, got: $OUT)"
( cd "$E1" && git switch -q --detach master 2>/dev/null || git switch -q --detach main 2>/dev/null )

# Blind checker must not make the role unrunnable (§8 fail-open doctrine).
OUT="$( (cd "$WR" && CREW_SESSIONS_DIR="$TMP/no-sessions" scripts/crew name steward) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && has "$OUT" "check skipped" \
   && has "$OUT" "$RNAME · crew/steward"; then
  ok "name: fails open with no session entry, and still states the name"
else
  bad "name: fail-open on session entry (rc=$RC, got: $OUT)"
fi

OUT="$( (cd "$WR" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/no-projects" \
  scripts/crew name steward) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && has "$OUT" "check skipped" \
  && ok "name: fails open with no transcript" \
  || bad "name: fail-open on transcript (rc=$RC, got: $OUT)"

# ---------------------------------------------------------------- scaffold
OUT="$(bash "$KIT/scripts/crew_scaffold.sh" "$WR" 2>&1)"
if has "$OUT" "stamped: .claude/crew/README.md" && [ -f "$WR/.claude/commands/executor.md" ]; then
  ok "scaffold: templates land in commands/ and crew/"
else
  bad "scaffold: first stamp (got: $OUT)"
fi
# scripts/crew was already present and identical → kept, not clobbered.
has "$OUT" "review : scripts/crew" && bad "scaffold: flagged an identical file" \
  || ok "scaffold: identical file skipped silently"
OUT="$(bash "$KIT/scripts/crew_scaffold.sh" "$WR" 2>&1)"
has "$OUT" "0 stamped" && ok "scaffold: re-run stamps nothing" \
  || bad "scaffold: re-run not idempotent (got: $OUT)"
echo "local note" >> "$WR/.claude/crew/README.md"
OUT="$(bash "$KIT/scripts/crew_scaffold.sh" "$WR" 2>&1)"
if has "$OUT" "review : .claude/crew/README.md.new" \
   && grep -q "local note" "$WR/.claude/crew/README.md"; then
  ok "scaffold: local edit survives, .new laid beside it"
else
  bad "scaffold: clobber policy (got: $OUT)"
fi
# The manifest is what makes a re-stamp after a kit update automatic: a file the
# script itself wrote and nobody touched is replaced in place, and only a file a
# human edited still needs hands. The kit is COPIED first — a test that edits the
# checkout it runs from leaves the repo dirty the moment it fails.
[ -f "$WR/.claude/crew/.stamp" ] && ok "scaffold: writes the stamp manifest" \
  || bad "scaffold: no manifest at .claude/crew/.stamp"

KC="$TMP/kitcopy"
mkdir -p "$KC"
cp -R "$KIT/scripts" "$KIT/templates" "$KC/"
echo "a line the next kit version adds" >> "$KC/templates/crew/docs/tickets.md"

OUT="$(bash "$KC/scripts/crew_scaffold.sh" "$WR" 2>&1)"
if has "$OUT" "updated: .claude/crew/tickets.md" \
   && [ ! -f "$WR/.claude/crew/tickets.md.new" ] \
   && grep -q "a line the next kit version adds" "$WR/.claude/crew/tickets.md"; then
  ok "scaffold: an untouched kit file is updated in place, no .new"
else
  bad "scaffold: untouched file not updated (got: $OUT)"
fi

echo "steward wrote a rule here" >> "$WR/.claude/crew/tickets.md"
echo "and the kit moved again" >> "$KC/templates/crew/docs/tickets.md"
OUT="$(bash "$KC/scripts/crew_scaffold.sh" "$WR" 2>&1)"
if has "$OUT" "review : .claude/crew/tickets.md.new" \
   && has "$OUT" "next   :" \
   && grep -q "steward wrote a rule here" "$WR/.claude/crew/tickets.md"; then
  ok "scaffold: an edited file still gets .new, with the command to finish it"
else
  bad "scaffold: edited file mishandled (got: $OUT)"
fi

# A role the interview found absent is never stamped — a command file for a
# ghost role is a wrong fact in the repo.
SK="$TMP/skiprepo"
mkdir -p "$SK"
( cd "$SK" && git init -q && git checkout -q -b main \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init )
OUT="$(bash "$KIT/scripts/crew_scaffold.sh" --skip devops,release "$SK" 2>&1)"
if [ -f "$SK/.claude/commands/planner.md" ] \
   && [ ! -f "$SK/.claude/commands/devops.md" ] \
   && [ ! -f "$SK/.claude/commands/release.md" ]; then
  ok "scaffold: --skip leaves ghost roles unstamped"
else
  bad "scaffold: --skip (got: $OUT)"
fi

# ---------------------------------------------------------------- role file
# A session opened from a task reads its role through `crew role`, not through a
# path. The worktree below is the reason: .claude/ was stamped after the initial
# commit, so it is untracked and a fresh worktree has no copy — which is exactly
# what a repo that gitignores .claude/ looks like from inside a worktree.
OUT="$( (cd "$WR" && scripts/crew role executor) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && has "$OUT" "crew new" && ok "role: prints the stamped role file" \
  || bad "role: main tree (rc=$RC, got: $OUT)"

git -C "$WR" worktree add -q "$W/probe" -b probe/x >/dev/null 2>&1
if [ ! -f "$W/probe/.claude/commands/executor.md" ]; then
  ok "role: the probe worktree really has no role file of its own"
else
  bad "role: probe worktree already carries .claude — the check below proves nothing"
fi
OUT="$( (cd "$W/probe" && scripts/crew role executor) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && has "$OUT" "crew new" && ok "role: reaches the main tree from a worktree" \
  || bad "role: from worktree (rc=$RC, got: $OUT)"

OUT="$( (cd "$WR" && scripts/crew role ghost) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -ne 0 ] && has "$OUT" "no role file" && ok "role: an unstamped role is red, and says so" \
  || bad "role: unstamped (rc=$RC, got: $OUT)"

# ---------------------------------------------------------------- summary
echo ""
echo "crew_test: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
