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

# A drawing in this turn satisfies the gate — silent.
OUT="$(run_gate "$HR" "$TS/draw.jsonl")"
[ -z "$OUT" ] && ok "gate: drawing satisfies the gate" \
  || bad "gate: drawing case not silent (got: $OUT)"

# A declared fast lane satisfies the gate — silent.
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
  printf '# audit log\n' > docs/92_audit/LOG.md
  printf '{"owns": [], "crew": {"dev_branch": "main", "test_cmd": "", "typecheck_cmd": "", "copy": ["harness", ".env"], "link": ["shared-cache"], "setup_cmd": "touch harness/.setup-done", "roles_absent": ["devops"]}}\n' > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init
)

# Known-bad first: no ticket, no tree.
OUT="$( (cd "$WR" && scripts/crew new 5) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "no ticket, no tree"; then
  ok "cli: refuses a worktree for a missing ticket"
else
  bad "cli: missing-ticket refusal (rc=$RC out: $OUT)"
fi

# fast-pair refuses a worktree too.
OUT="$( (cd "$WR" && scripts/crew new 2) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "fast-pair"; then
  ok "cli: refuses a worktree for a fast-pair ticket"
else
  bad "cli: fast-pair refusal (rc=$RC out: $OUT)"
fi

# The real ticket gets a tree, on the right branch.
OUT="$( (cd "$WR" && scripts/crew new 1) 2>&1 )" || { bad "cli: crew new 1 failed: $OUT"; }
WT="$W/repo-b001"
if [ -d "$WT" ] && [ "$(git -C "$WT" rev-parse --abbrev-ref HEAD)" = "work/b001" ]; then
  ok "cli: worktree + branch follow the token"
else
  bad "cli: worktree/branch naming"
fi

# Provisioning: the gitignored payload arrives, the share is a link, the
# setup command ran, and the cost was logged.
if [ -f "$WT/harness/h.txt" ] && [ -f "$WT/.env" ]; then
  ok "cli: gitignored payload copied into the tree"
else
  bad "cli: copy list not provisioned"
fi
[ -L "$WT/shared-cache" ] && ok "cli: read-only share is a symlink" \
  || bad "cli: link list not provisioned"
[ -f "$WT/harness/.setup-done" ] && ok "cli: setup_cmd ran inside the tree" \
  || bad "cli: setup_cmd did not run"
grep -q "SETUP" "$W/repo-crew/log.tsv" 2>/dev/null \
  && ok "cli: provisioning time logged" \
  || bad "cli: SETUP line missing from log.tsv"

# check 1 red: the main tree holds the wrong branch.
( cd "$WR" && git checkout -q -b temp )
OUT="$( (cd "$WR" && scripts/crew done 1) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "check 1"; then
  ok "cli: check 1 is red on the wrong branch, for the right reason"
else
  bad "cli: check 1 (rc=$RC out: $OUT)"
fi
( cd "$WR" && git checkout -q main && git branch -q -D temp )

# check 2 red: dirty main tree, and the dirty file is NAMED.
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
OUT="$( (cd "$WR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew done 1) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] || bad "cli: crew done 1 failed (out: $OUT)"
[ -f "$WR/f.txt" ] && ok "cli: work is on the dev branch" || bad "cli: merge did not land"
[ ! -d "$WT" ] && ok "cli: worktree removed after done" || bad "cli: worktree still there"
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

# Locks: acquire → visible in status → second owner refused → release logged.
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
# Re-run is idempotent: nothing new to stamp.
OUT="$(bash "$KIT/scripts/crew_scaffold.sh" "$WR" 2>&1)"
has "$OUT" "0 stamped" && ok "scaffold: re-run stamps nothing" \
  || bad "scaffold: re-run not idempotent (got: $OUT)"
# A locally edited file is never clobbered — the new version lands as .new.
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

# A file the human edited keeps its hands-off treatment.
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
