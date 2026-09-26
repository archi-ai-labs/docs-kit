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
# The suite's own cwd is scratch too. `cd ""` succeeds and stays put, so a helper
# whose target path came out empty runs right here — and measured 2026-09-24, a
# mutation run left no tree holding work/b102, `cowork` stayed in the kit
# checkout, and its `git add -A && git commit` swept the change in progress into
# two stray commits. Under $TMP the same slip meets "not a git repository".
cd "$TMP" || exit 2

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

# A picture file the host renders beside the chat is a drawing (0.40.4). The
# known-bad shapes go first: the same tool sending a file as an attachment, or
# sending text, has shown the user no picture.
send_file() { # send_file <files-json> [display]
  local disp=""
  [ -n "${2:-}" ] && disp=",\"display\":\"$2\""
  printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"f1","name":"SendUserFile","input":{"files":%s%s,"status":"normal"}}]}}' "$1" "$disp"
}
printf '%s\n%s\n%s\n' "$U" "$(send_file '["/s/why.html"]' attach)" "$TR" > "$TS/file_attach.jsonl"
printf '%s\n%s\n%s\n' "$U" "$(send_file '["/s/notes.md"]' render)" "$TR" > "$TS/file_text.jsonl"
printf '%s\n%s\n%s\n' "$U" "$(send_file '["/s/why.html"]' render)" "$TR" > "$TS/file.jsonl"
printf '%s\n%s\n%s\n' "$U" "$(send_file '["/s/notes.md","/s/flow.PNG"]')" "$TR" > "$TS/file_auto.jsonl"

OUT="$(run_gate "$HR" "$TS/file_attach.jsonl")"
has "$OUT" "[gate:no-draw]" && ok "gate: a picture sent as an attachment does not count" \
  || bad "gate: an attachment opened it (got: $OUT)"

OUT="$(run_gate "$HR" "$TS/file_text.jsonl")"
has "$OUT" "[gate:no-draw]" && ok "gate: a text file shown to the user does not count" \
  || bad "gate: a text file opened it (got: $OUT)"

OUT="$(run_gate "$HR" "$TS/file.jsonl")"
[ -z "$OUT" ] && ok "gate: a picture file sent to render satisfies the gate" \
  || bad "gate: rendered picture file not silent (got: $OUT)"

OUT="$(run_gate "$HR" "$TS/file_auto.jsonl")"
[ -z "$OUT" ] && ok "gate: a picture file with no display set satisfies the gate" \
  || bad "gate: default display not silent (got: $OUT)"

# crew-init writes the default draw_tools list into the config verbatim, so the
# file evidence must not depend on it: 3 of 4 real crew repos carry that list.
HRV="$TMP/hookrepo-verbatim"
mkdir -p "$HRV"
( cd "$HRV" && git init -q && git checkout -q -b main \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init )
printf '{"owns": [], "crew": {"draw_tools": ["mcp__visualize__show_widget", "Artifact"]}}\n' > "$HRV/.docs-kit.json"
OUT="$(run_gate "$HRV" "$TS/file.jsonl")"
[ -z "$OUT" ] && ok "gate: a verbatim draw_tools list does not hide the picture file" \
  || bad "gate: verbatim draw_tools hid the picture file (got: $OUT)"

# The stop scan reads <session>/subagents/ since 0.40.1; this gate must not copy
# it. A sub-agent's text never reached the user as a reply, so its marker line
# or its drawing opening the parent's question repeats rule 1's failure: text
# the user never saw, opening the gate.
mkdir -p "$TS/sub/subagents/workflows/wf_1"
printf '%s\n%s\n' "$U" "$A_PLAIN" > "$TS/sub.jsonl"
printf '%s\n%s\n' "$A_LANE" "$A_DRAW" > "$TS/sub/subagents/workflows/wf_1/agent-a1.jsonl"
OUT="$(run_gate "$HR" "$TS/sub.jsonl")"
has "$OUT" "[gate:no-draw]" && ok "gate: a sub-agent's marker or drawing does not open it" \
  || bad "gate: opened by a sub-agent's transcript (got: $OUT)"

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
  for n in 003 004 006; do
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

# Known-bad, and red for the right reason: with the trailer already written, one
# uncommitted file must pull the state back to `processing` and stop `crew done`
# at check 0. Measured 2026-09-09 — without this the merge went through, the
# ticket read `status: done` with an audit line citing a sha, and the file was
# still sitting in the executor when the run ended.
( cd "$WT" && echo stray > stray.txt )
[ "$(st)" = "processing" ] && ok "state: a trailer does not read finishing while the tree owns uncommitted work" \
  || bad "state: expected processing on a dirty tree, got '$(st)'"
OUT="$( (cd "$WR" && scripts/crew done 1) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "check 0" && has "$OUT" "stray.txt"; then
  ok "cli: check 0 is red on a dirty executor and names the file"
else
  bad "cli: check 0 (rc=$RC out: $OUT)"
fi
grep -q "^status: open" "$WR/docs/23_backlog/demo.md" \
  && ok "cli: check 0 stops before the merge, so the ticket is not closed" \
  || bad "cli: ticket closed despite check 0"
rm -f "$WT/stray.txt"
[ "$(st)" = "finishing" ] && ok "state: cleaning the tree restores finishing" \
  || bad "state: expected finishing after cleanup, got '$(st)'"
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

# Every close-out test above hands the path in through CREW_DOCS_CLOSE, so the
# FALLBACK lookup — the one a real terminal uses — was never run, and that is
# exactly how ISSUE-014 shipped. The marketplace cache nests a version between
# `docs-kit` and `scripts/`, so a search for the DIRECTORY finds a base that
# `scripts/docs_close.sh` never hangs off. Reproduce that shape and require the
# close-out to still land, with no env var and no CLAUDE_PLUGIN_ROOT.
FH="$TMP/fakehome"
FC="$FH/.claude/plugins/cache/archi-ai-labs/docs-kit/0.29.0"
mkdir -p "$FC"
cp -R "$KIT/scripts" "$FC/scripts"   # docs_close.sh shells out to siblings, so copy the dir
( cd "$WR" && scripts/crew new 6 >/dev/null 2>&1 ) || true
W6="$(git -C "$WR" worktree list --porcelain | awk '
  /^worktree /{ p = substr($0, 10) }
  /^branch .*work\/b006$/{ print p; exit }')"
( cd "$W6" && echo f6 > f6.txt && git add -A \
  && git -c user.email=t@t -c user.name=t commit -qm "add f6" -m "Closes: BACKLOG-006" )
OUT="$( (cd "$WR" && env -u CLAUDE_PLUGIN_ROOT -u CREW_DOCS_CLOSE HOME="$FH" scripts/crew done 6) 2>&1 )" || true
if ! has "$OUT" "docs_close is not reachable" && grep -q "^status: done" "$WR/docs/23_backlog/t006.md"; then
  ok "cli: the docs_close fallback resolves through the cache's version level"
else
  bad "cli: fallback lookup missed docs_close (ISSUE-014 shape) (out: $OUT)"
fi
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

# FREE is not the same as DETACHED, and this is the pool half of the same
# defect. Measured 2026-09-09: a tree parked by hand — which is exactly what
# `crew done` tells the operator to do when its own park refuses — still held
# the finished ticket's uncommitted file, read `idle`, and the next `crew new`
# checked a branch out on top of it. One ticket's work then sat on another
# ticket's branch, one `git add -A` away from being committed there.
printf -- '---\nid: BACKLOG-160\nstatus: open\nexecution: fast\n---\n' > "$RR/docs/23_backlog/b160.md"
( cd "$RR" && git add -A && git -c user.email=t@t -c user.name=t commit -qm "ticket 160" ) >/dev/null 2>&1
( cd "$R/app-e2" && git switch -q --detach dev ) 2>/dev/null || true
echo leftover > "$R/app-e2/stray.txt"
OUT="$( (cd "$RR" && scripts/crew status) 2>&1 )"
has "$OUT" "unclean" && ok "state: a detached tree that still owns files reads unclean, not idle" \
  || bad "state: unclean not reported (got: $OUT)"
OUT="$( (cd "$RR" && scripts/crew new 160) 2>&1 )"
E2H="$(git -C "$R/app-e2" symbolic-ref --short HEAD 2>/dev/null || echo -)"
if has "$OUT" "no executor was free" && [ "$E2H" = "-" ]; then
  ok "cli: an unclean tree is not handed to the next ticket — the pool grows instead"
else
  bad "cli: unclean tree handed out (head=$E2H out: $OUT)"
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
   && has "$OUT" "/rename $RNAME · steward"; then
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
  printf '{"type":"custom-title","customTitle":"%s · steward"}\n' "$RNAME"; } > "$PROJ/s1.jsonl"
OUT="$(run_name steward)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && has "$OUT" "name ok" && ok "name: the newest title is the title" \
  || bad "name: correct title rejected (rc=$RC, got: $OUT)"

# A fast-pair ticket skips the worktree and the branch, NOT the session — the
# origin repo really opened one (BACKLOG-010, titled `· b010 · crew/executor`).
# So it reads in the same shape as any executor session, with `main` as the
# place, and the token is zero-padded the way `crew new 42` pads it.
printf '{"type":"custom-title","customTitle":"%s · executor · b042 · main · processing"}\n' "$RNAME" > "$PROJ/s1.jsonl"
OUT="$(run_name executor 42)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && ok "name: a fast-pair session sits at main, padded token, born processing" \
  || bad "name: fast-pair grammar (rc=$RC, got: $OUT)"

# Its trailer lands on the dev branch and not on a work branch, so the state has
# to be read from there — same two words, a different place to look.
( cd "$WR" && echo p > pair.txt && git add pair.txt \
    && git -c user.email=t@t -c user.name=t commit -qm "fast-pair edit" -m "Closes: BACKLOG-042" )
OUT="$(run_name executor 42)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "b042 · main · finishing"; then
  ok "name: a fast-pair trailer on the dev branch flips the title to finishing"
else
  bad "name: fast-pair finishing (rc=$RC, got: $OUT)"
fi

# An executor session always belongs to one ticket; without a number there is
# nothing to name, and guessing would produce a title that means nothing.
OUT="$(run_name executor)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "belongs to one ticket"; then
  ok "name: an executor session with no ticket is refused, not guessed"
else
  bad "name: ticketless executor (rc=$RC, got: $OUT)"
fi

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
# title was derived. A FRESH number, not 042: the block above put 042's closer on
# the dev branch on purpose, and since 0.39.0 a closer already on dev is read as
# work that landed, so no session for that number can be born. One ticket lives
# in one place, which is what a real repo does anyway.
( cd "$E1" && git switch -q -c work/b045 2>/dev/null )
en_title() { printf '{"type":"custom-title","customTitle":"%s"}\n' "$1" > "$PROJ/s1.jsonl"; }
en_title "$RNAME · executor · b045 · e1 · processing"
OUT="$( (cd "$E1" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name executor) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && ok "name: a new executor session is born processing" \
  || bad "name: processing grammar (rc=$RC, got: $OUT)"

# ...and the SAME title goes red once the trailer lands, naming the new state.
( cd "$E1" && echo z > z.txt && git add z.txt \
    && git -c user.email=t@t -c user.name=t commit -qm "done" -m "Closes: BACKLOG-045" )
OUT="$( (cd "$E1" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name executor) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "b045 · e1 · finishing"; then
  ok "name: the trailer flips the title to finishing, and the old one is red"
else
  bad "name: finishing grammar (rc=$RC, got: $OUT)"
fi
en_title "$RNAME · executor · b045 · e1 · finishing"
OUT="$( (cd "$E1" && CREW_SESSIONS_DIR="$SESS" CREW_PROJECTS_DIR="$TMP/projects" scripts/crew name executor) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && ok "name: the retitled session matches again" \
  || bad "name: finishing match (rc=$RC, got: $OUT)"
( cd "$E1" && git switch -q --detach master 2>/dev/null || git switch -q --detach main 2>/dev/null )

# Blind checker must not make the role unrunnable (§8 fail-open doctrine).
OUT="$( (cd "$WR" && CREW_SESSIONS_DIR="$TMP/no-sessions" scripts/crew name steward) 2>&1 )" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && has "$OUT" "check skipped" \
   && has "$OUT" "$RNAME · steward"; then
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

# ---------------------------------------------------------------- main tree
# The board now answers `crew done`'s check 1 and check 2 before a merge is
# attempted, so the known-bad shapes come first: a main tree parked on the wrong
# branch, and a dirty one. Both used to be discoverable only by running the merge.
MT="$TMP/mainbranch"
mkdir -p "$MT/docs/23_backlog" "$MT/docs/92_audit" "$MT/scripts"
(
  cd "$MT"
  git init -q && git checkout -q -b dev
  git config user.email t@t && git config user.name t
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  printf '{"owns": [], "crew": {"dev_branch": "dev"}}\n' > .docs-kit.json
  printf '# Audit log\n' > docs/92_audit/LOG.md
  printf -- '---\nid: BACKLOG-001\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: open\n---\n' \
    > docs/23_backlog/t001.md
  git add -A && git commit -qm init
)
mt() { (cd "$MT" && scripts/crew status) 2>&1; }

# KNOWN-BAD 1: parked on a branch that is not dev. check 1 would refuse.
( cd "$MT" && git checkout -q -b sidequest && echo a > f && git add -A && git commit -qm side )
OUT="$(mt)"
if has "$OUT" "branch    : sidequest ≠ dev_branch 'dev'" \
   && has "$OUT" "check 1 wants 'dev' checked out"; then
  ok "main tree: a tree on the wrong branch is named, and cites check 1"
else
  bad "main tree: wrong branch (got: $(printf '%s' "$OUT" | sed -n '3,6p'))"
fi
# ...and it says how far that branch has drifted from dev, which is the whole
# reason the branch name alone is not enough.
has "$OUT" "vs dev    : 1 ahead, 0 behind" \
  && ok "main tree: distance from dev is counted, not just the branch name" \
  || bad "main tree: ahead/behind vs dev (got: $OUT)"

# KNOWN-BAD 2: on dev but dirty. check 2 would refuse. Plain porcelain, not
# own_files — check 2 counts the payload too, so a filtered board would promise
# a merge the merge refuses.
( cd "$MT" && git checkout -q dev && echo dirt > untracked.txt )
OUT="$(mt)"
if has "$OUT" "branch    : dev = dev_branch · 1 uncommitted" \
   && has "$OUT" "check 2 wants it clean" \
   && ! has "$OUT" "check 1"; then
  ok "main tree: a dirty tree cites check 2 alone"
else
  bad "main tree: dirty case (got: $(printf '%s' "$OUT" | sed -n '3,6p'))"
fi

# The count must be PLAIN porcelain, not own_files(). own_files filters the
# provisioned payload by name — `briefs` is in that list unconditionally — but
# check 2 counts every uncommitted file there is. A board that filtered would
# report a clean tree and then watch the merge refuse, which is worse than not
# reporting at all. `briefs/` is the realistic shape: a repo that runs
# /docs-kit:brief without gitignoring the folder has it untracked in the main
# tree, where own_dirty sees nothing and check 2 sees a blocker.
( cd "$MT" && git checkout -q dev && rm -f untracked.txt && mkdir -p briefs && echo b > briefs/x.md )
OUT="$(mt)"
if has "$OUT" "branch    : dev = dev_branch · 1 uncommitted" \
   && has "$OUT" "check 2 wants it clean"; then
  ok "main tree: the dirty count is check 2's, not the executor's filtered one"
else
  bad "main tree: payload-filtered count leaked in (got: $(printf '%s' "$OUT" | sed -n '3,6p'))"
fi
( cd "$MT" && rm -rf briefs && echo dirt > untracked.txt )

# Both wrong at once names both, in the order crew done hits them.
( cd "$MT" && git checkout -q sidequest )
OUT="$(mt)"
has "$OUT" "check 1 wants 'dev' checked out, check 2 wants it clean" \
  && ok "main tree: both refusals named together, in check order" \
  || bad "main tree: combined arrow (got: $OUT)"

# THE QUIET FORM: on dev, clean, nothing to act on — no arrow at all.
( cd "$MT" && git checkout -q dev && rm -f untracked.txt )
OUT="$(mt)"
if has "$OUT" "branch    : dev = dev_branch · clean" \
   && ! has "$OUT" "crew done refuses here"; then
  ok "main tree: a tree ready to merge draws no arrow"
else
  bad "main tree: quiet form (got: $(printf '%s' "$OUT" | sed -n '3,6p'))"
fi

# No remote is the common case in a fresh repo, and it must print the fact
# rather than a zero that reads as "in sync" (§8 fail open).
has "$OUT" "vs remote : 'dev' tracks nothing here" \
  && ok "main tree: no upstream states the fact instead of inventing a verdict" \
  || bad "main tree: no-upstream line (got: $OUT)"
# With no `origin` at all there is no origin/HEAD for any tool to read, so the
# default row has nothing to say.
has "$OUT" "default   :" \
  && bad "main tree: default row printed with no origin remote (got: $OUT)" \
  || ok "main tree: no origin remote, no default row"

# With an upstream, the comparison is against the remote — a different question
# wearing the same words, so it must name which one it answered.
(
  cd "$TMP" && git init -q --bare mainremote.git >/dev/null 2>&1
  cd "$MT" && git remote add origin "$TMP/mainremote.git" \
    && git push -q -u origin dev >/dev/null 2>&1
  echo b > g && git add -A && git commit -qm ahead
)
OUT="$(mt)"
has "$OUT" "vs remote : 1 ahead, 0 behind origin/dev" \
  && ok "main tree: on dev, the comparison is against the remote" \
  || bad "main tree: upstream compare (got: $OUT)"

# origin/HEAD is what Claude Code's diff pane and its "Main branch" line read.
# KNOWN-BAD first, in the shape the origin repo reported (FEEDBACK-007): the
# GitHub default is the prod branch, so a clone points origin/HEAD there, and
# every session between two releases diffs against prod.
( cd "$MT" && git push -q origin dev:master >/dev/null 2>&1 && git remote set-head origin master >/dev/null )
OUT="$(mt)"
has "$OUT" "default   : origin/HEAD is 'master', not dev_branch 'dev' · git remote set-head origin dev" \
  && ok "main tree: origin/HEAD on the prod branch is named, with the one-line fix" \
  || bad "main tree: origin/HEAD on master (got: $OUT)"

# `git remote add` + push never sets the ref, and then each tool guesses on its
# own — Claude Code picks origin/master whenever that exists.
( cd "$MT" && git remote set-head origin -d >/dev/null )
OUT="$(mt)"
has "$OUT" "default   : origin/HEAD is not set, so tools guess · git remote set-head origin dev" \
  && ok "main tree: an unset origin/HEAD is named, not read as fine" \
  || bad "main tree: unset origin/HEAD (got: $OUT)"

# set-head refuses a target with no remote-tracking ref, so a fix printed for an
# unpushed dev branch would just error; the push has to come first.
( cd "$MT" && git remote set-head origin master >/dev/null && git update-ref -d refs/remotes/origin/dev )
OUT="$(mt)"
has "$OUT" "· push 'dev' first, then git remote set-head origin dev" \
  && ok "main tree: an unpushed dev branch gets the push named before set-head" \
  || bad "main tree: unpushed dev fix (got: $OUT)"

# THE QUIET FORM: origin/HEAD already follows dev, nothing to act on, no row.
( cd "$MT" && git fetch -q origin && git remote set-head origin dev >/dev/null )
OUT="$(mt)"
has "$OUT" "default   :" \
  && bad "main tree: default row printed while origin/HEAD follows dev (got: $OUT)" \
  || ok "main tree: origin/HEAD on dev_branch draws no default row"

# A dev_branch naming a branch that does not exist must not be reported as a
# clean comparison against nothing.
printf '{"owns": [], "crew": {"dev_branch": "ghost"}}\n' > "$MT/.docs-kit.json"
OUT="$(mt)"
has "$OUT" "vs ghost  : that branch does not exist here" \
  && ok "main tree: a dev_branch that does not exist says so" \
  || bad "main tree: ghost dev_branch (got: $OUT)"
# ...and says it once: the default row would otherwise tell the user to push a
# branch that does not exist, on top of the note that already names it.
has "$OUT" "default   :" \
  && bad "main tree: a ghost dev_branch also drew a default row (got: $OUT)" \
  || ok "main tree: a ghost dev_branch is one fault, not a second default row"
printf '{"owns": [], "crew": {"dev_branch": "dev"}}\n' > "$MT/.docs-kit.json"

# ---------------------------------------------------------------- main is a place
# `main` is where every fast-pair ticket runs (EXECUTION §2), but exec_map matches
# `^<repo>-e[0-9]+$` only, so the main tree never appeared among the executors and
# the board called a working rig "pool empty". Worse, the in-progress sweep at the
# foot of the board looks a ticket up by its `work/b<nnn>` branch — which a
# fast-pair ticket has none of, by design — so it raised "no executor holds it"
# about the one state the design wants. Known-bad first, both shapes.
MP="$TMP/mainplace"
mkdir -p "$MP/docs/23_backlog" "$MP/docs/92_audit" "$MP/scripts"
(
  cd "$MP"
  git init -q && git checkout -q -b dev
  git config user.email t@t && git config user.name t
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  printf '{"owns": [], "crew": {"dev_branch": "dev"}}\n' > .docs-kit.json
  printf '# Audit log\n' > docs/92_audit/LOG.md
  git add -A && git commit -qm init
)
mkticket() { # mkticket <dir> <nnn> <status> <execution|->
  # mkdir first: git removes the folder when the last ticket in it is git rm'd,
  # and a printf into a missing folder fails silently enough to make a later
  # assertion pass for the wrong reason.
  mkdir -p "$1/docs/23_backlog"
  printf -- '---\nid: BACKLOG-%s\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: %s\n' "$2" "$3" \
    > "$1/docs/23_backlog/t$2.md"
  [ "$4" = "-" ] || printf 'execution: %s\n' "$4" >> "$1/docs/23_backlog/t$2.md"
  printf -- '---\n' >> "$1/docs/23_backlog/t$2.md"
  ( cd "$1" && git add -A && git commit -qm "ticket $2" >/dev/null )
}
mp() { (cd "$MP" && scripts/crew status) 2>&1; }

# KNOWN-BAD: one fast-pair ticket in progress. The rig is working; the board must
# not call it empty, and must not raise the orphan note about it.
mkticket "$MP" 042 in-progress fast-pair
OUT="$(mp)"
if has "$OUT" "  main  dev  BACKLOG-042  processing" \
   && has "$OUT" "ticket=in-progress"; then
  ok "main place: a fast-pair ticket puts main in the executors list"
else
  bad "main place: no main row (got: $(printf '%s' "$OUT" | sed -n '/executors:/,/^$/p'))"
fi
! has "$OUT" "BACKLOG-042 is in-progress but no executor holds it" \
  && ok "main place: the orphan note is not raised about a fast-pair ticket" \
  || bad "main place: false orphan note survived"
! has "$OUT" "(pool empty" \
  && ok "main place: a rig running one ticket is not reported empty" \
  || bad "main place: still says pool empty while main holds a ticket"

# The branch column stays the BRANCH. For main that is the dev branch, and the
# fact that it is not `work/b042` is itself what says fast-pair — no extra column.
has "$OUT" "  main  dev  " \
  && ok "main place: the branch column carries the dev branch, not the level" \
  || bad "main place: branch column (got: $OUT)"

# THE INVERSE, which is what stops the fix from silencing a real signal: a
# `full` ticket in progress with no executor holding it is still an orphan.
mkticket "$MP" 077 in-progress full
OUT="$(mp)"
has "$OUT" "BACKLOG-077 is in-progress but no executor holds it" \
  && ok "main place: a full ticket with no tree is still called an orphan" \
  || bad "main place: the orphan note was silenced for a full ticket too"

# A ticket with NO execution: field must behave as before — the field is optional
# (EXECUTION §3), so a repo that never wrote it cannot start losing the note.
( cd "$MP" && git rm -q docs/23_backlog/t077.md && git commit -qm rm >/dev/null )
mkticket "$MP" 099 in-progress -
OUT="$(mp)"
has "$OUT" "BACKLOG-099 is in-progress but no executor holds it" \
  && ok "main place: a ticket with no execution field keeps the old behaviour" \
  || bad "main place: missing execution field changed the verdict"

# Nothing in progress on main → main is idle, in the same shape an executor uses.
( cd "$MP" && git rm -q docs/23_backlog/t042.md docs/23_backlog/t099.md && git commit -qm rm >/dev/null )
OUT="$(mp)"
has "$OUT" "  main  idle" \
  && ok "main place: with no fast-pair ticket, main reads idle like any slot" \
  || bad "main place: idle form (got: $(printf '%s' "$OUT" | sed -n '/executors:/,/^$/p'))"

# Two fast-pair edits at once break the discipline that each is committed in the
# same bout (EXECUTION §2), so the board names both rather than picking one.
mkticket "$MP" 043 in-progress fast-pair
mkticket "$MP" 044 in-progress fast-pair
OUT="$(mp)"
if has "$OUT" "BACKLOG-043" && has "$OUT" "BACKLOG-044" \
   && has "$OUT" "two fast-pair tickets are open at once"; then
  ok "main place: two open fast-pair tickets are both listed and called out"
else
  bad "main place: second fast-pair ticket (got: $(printf '%s' "$OUT" | sed -n '/executors:/,/^$/p'))"
fi


# THE BRANCH COLUMN IS THE BRANCH, and 0.37.0 got that wrong: it printed the
# CONFIGURED dev branch instead of the one HEAD is actually on, so a main tree
# parked elsewhere made the board contradict itself four lines apart — the
# `main tree:` block reads symbolic-ref and said `sidequest ≠ dev_branch 'dev'`
# while this row still said `dev`. One tree, two branch names, one board.
( cd "$MP" && git checkout -q -b sidequest )
OUT="$(mp)"
if has "$OUT" "  main  sidequest  BACKLOG-043" && ! has "$OUT" "  main  dev  BACKLOG-043"; then
  ok "main place: the row names the branch HEAD is on, not the configured one"
else
  bad "main place: branch column off dev (got: $(printf '%s' "$OUT" | sed -n '/executors:/,/^$/p'))"
fi
# ...and it must agree with the block above it, which is the whole point.
if has "$OUT" "branch    : sidequest" && has "$OUT" "  main  sidequest  "; then
  ok "main place: both places on the board name the same branch"
else
  bad "main place: the two branch reports disagree (got: $OUT)"
fi
( cd "$MP" && git checkout -q dev )

# ---------------------------------------------------------------- name knows the level
# `crew name executor <nnn>` read only "which tree am I in", never "which tree
# should this ticket be in". Measured before the fix: from the main tree, a
# `full` ticket was blessed as `<repo> · main · b077 · processing · crew/executor`
# — so a session that skipped `crew new` got told its title was right and went on
# to edit the shared tree, where check 2 then blocks every crew done in flight.
NL="$TMP/namelevel"
mkdir -p "$NL/docs/23_backlog" "$NL/scripts"
(
  cd "$NL"
  git init -q && git checkout -q -b dev
  git config user.email t@t && git config user.name t
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  printf '{"owns": [], "crew": {"dev_branch": "dev"}}\n' > .docs-kit.json
  git add -A && git commit -qm init
)
nm() { (cd "$NL" && scripts/crew name executor "$1") 2>&1; }

# KNOWN-BAD: a full ticket named from the main tree.
mkticket "$NL" 077 open full
OUT="$(nm 077)"
if has "$OUT" "[name:place]" && has "$OUT" "BACKLOG-077 is full"; then
  ok "name level: a full ticket named from the main tree is refused, and says why"
else
  bad "name level: full ticket from main (got: $OUT)"
fi
has "$OUT" "scripts/crew new 077" \
  && ok "name level: the refusal names the command that fixes it" \
  || bad "name level: refusal has no next step (got: $OUT)"

# `fast` is the same shape and must be refused too — it is the level people reach
# for most, and it also takes a worktree.
mkticket "$NL" 078 open fast
has "$(nm 078)" "[name:place]" \
  && ok "name level: a fast ticket is refused from the main tree as well" \
  || bad "name level: fast ticket was allowed from the main tree"

# THE ALLOWED CASE: fast-pair belongs in the main tree, so it must still name.
mkticket "$NL" 042 in-progress fast-pair
OUT="$(nm 042)"
if ! has "$OUT" "[name:place]" && has "$OUT" "· b042 · i001 · main ·"; then
  ok "name level: a fast-pair ticket still names from the main tree"
else
  bad "name level: fast-pair was refused (got: $OUT)"
fi

# FAIL OPEN: no execution: field means the level was never recorded, and the kit
# does not guess. Refusing here would break every repo written before the field.
mkticket "$NL" 099 open -
OUT="$(nm 099)"
! has "$OUT" "[name:place]" \
  && ok "name level: a ticket with no execution field is not refused" \
  || bad "name level: missing field was treated as a violation"


# ---------------------------------------------------------------- navigator
# The sixth hat reads two documents nothing used to compare, so every check here
# starts from a KNOWN-BAD board and asserts the words a human acts on — not the
# exit code, which `crew status` never varies.
NV="$TMP/navrepo"
mkdir -p "$NV/docs/23_backlog" "$NV/docs/92_audit" "$NV/docs/00_roadmap" "$NV/scripts"
(
  cd "$NV"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  printf '{"owns": [], "crew": {"dev_branch": "main"}}\n' > .docs-kit.json
  printf '# Audit log\n\n2026-09-01 | init | - | - | mốc\n' > docs/92_audit/LOG.md
  for n in 002 004; do
    printf -- '---\nid: BACKLOG-%s\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: done\n---\n' "$n" \
      > "docs/23_backlog/t$n.md"
  done
  for n in 016 017; do
    printf -- '---\nid: BACKLOG-%s\ndescription: "y"\nsource_ref: ISSUE-002\nstatus: open\n---\n' "$n" \
      > "docs/23_backlog/t$n.md"
  done
  # The origin repo's real shape on 2026-09-10: the column names finished work
  # and neither open ticket appears anywhere.
  printf '# Roadmap\n\n## Now\n\n- A — `BACKLOG-002`.\n- B — `BACKLOG-004`.\n\n## Next\n\n- Không id.\n- C — `DECISION-008`.\n' \
    > docs/00_roadmap/roadmap.md
  git add -A && git commit -qm init
  echo a > f1 && git add -A && git commit -qm "a

Closes: BACKLOG-002"
  echo b > f2 && git add -A && git commit -qm "b

Closes: BACKLOG-004"
)
nav() { (cd "$NV" && scripts/crew "$@") 2>&1; }

OUT="$(nav status)"
# TWO ids on purpose: the first version of roadmap_stats read them through
# `IFS=<tab> read <<heredoc`, and the assignment was still in effect while the
# heredoc's command substitution ran, so the loop split on tabs and reported
# "1 listed · 1 done" for a two-ticket column. Counting one is the regression.
if has "$OUT" "roadmap Now : 2 listed · 2 done · 0 of 2 open present"; then
  ok "navigator: known-bad board counts the whole Now column"
else
  bad "navigator: stale Now (got: $(printf '%s' "$OUT" | grep 'roadmap Now'))"
fi
has "$OUT" "not listed  : BACKLOG-016 BACKLOG-017" \
  && ok "navigator: open tickets no column mentions are named" \
  || bad "navigator: not-listed line (got: $OUT)"
has "$OUT" "→ the Now column is not the Backlog" \
  && ok "navigator: the stale column gets the arrow that names its action" \
  || bad "navigator: sync arrow missing"
has "$OUT" "commit(s) closed a ticket in the last 7 days" \
  && ok "navigator: a week with landed work and no report says so" \
  || bad "navigator: report-due line (got: $OUT)"
has "$OUT" "→ a week has landed work and no report" \
  && ok "navigator: the missing report gets its own arrow" \
  || bad "navigator: report arrow missing"

# `crew report` measures the window from git, and names the ids it counted.
OUT="$(nav report)"
if has "$OUT" "landed      : 2 ticket(s) in 2 commit(s) — BACKLOG-002 BACKLOG-004" \
   && has "$OUT" "off-roadmap : 2 open ticket(s) named in no column" \
   && has "$OUT" "no-id lines : 1 bullet"; then
  ok "navigator: report measures landed work, off-roadmap tickets and id-less plan lines"
else
  bad "navigator: report numbers (got: $OUT)"
fi
has "$OUT" "not written — pass --write" \
  && ok "navigator: report prints without writing unless asked" \
  || bad "navigator: read-only default (got: $OUT)"

OUT="$(nav report 2026-Q1)" && RC=0 || RC=$?
[ "$RC" -ne 0 ] && has "$OUT" "a period is a week" \
  && ok "navigator: a period that is neither a week nor a month is red" \
  || bad "navigator: bad period accepted (rc=$RC, got: $OUT)"

WEEK="$(date -u +%G-W%V)"
OUT="$(nav report --write)"
if [ -f "$NV/docs/92_audit/reports/$WEEK.md" ] \
   && grep -q '^## 1. Số đo' "$NV/docs/92_audit/reports/$WEEK.md" \
   && grep -q '^## 5. Cần chủ dự án quyết' "$NV/docs/92_audit/reports/$WEEK.md"; then
  ok "navigator: --write lays down the report with the judgement sections empty"
else
  bad "navigator: --write output (got: $OUT)"
fi
# A report is append-only, so the command must never be the thing that rewrites one.
OUT="$(nav report --write)" && RC=0 || RC=$?
[ "$RC" -ne 0 ] && has "$OUT" "[report:exists]" \
  && ok "navigator: a second --write refuses, with the reason tag" \
  || bad "navigator: second write (rc=$RC, got: $OUT)"

( cd "$NV" && git add -A && git commit -qm "report" )
OUT="$(nav status)"
has "$OUT" "report      : reports/$WEEK.md" \
  && ok "navigator: an existing report closes the report line" \
  || bad "navigator: report line after write (got: $OUT)"

# The quiet form: a column that IS the Backlog draws no arrow at all.
(
  cd "$NV"
  printf '# Roadmap\n\n## Now\n\n- D — `BACKLOG-016`.\n- E — `BACKLOG-017`.\n\n## Next\n\n- C — `DECISION-008`.\n' \
    > docs/00_roadmap/roadmap.md
  git add -A && git commit -qm sync
)
OUT="$(nav status)"
if has "$OUT" "roadmap Now : 2 listed · 0 done · 2 of 2 open present" \
   && ! has "$OUT" "→ the Now column is not the Backlog" \
   && ! has "$OUT" "not listed"; then
  ok "navigator: a synced column is quiet — no arrow, no not-listed line"
else
  bad "navigator: quiet form (got: $OUT)"
fi

# A window with nothing landed owes nobody a report.
NV2="$TMP/navquiet"
mkdir -p "$NV2/docs/23_backlog" "$NV2/docs/92_audit" "$NV2/docs/00_roadmap" "$NV2/scripts"
(
  cd "$NV2"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  printf '{"owns": [], "crew": {"dev_branch": "main"}}\n' > .docs-kit.json
  printf '# Audit log\n' > docs/92_audit/LOG.md
  printf -- '---\nid: BACKLOG-001\ndescription: "z"\nsource_ref: ISSUE-001\nstatus: open\n---\n' \
    > docs/23_backlog/t001.md
  printf '# Roadmap\n\n## Now\n\n- Z — `BACKLOG-001`.\n' > docs/00_roadmap/roadmap.md
  git add -A && git commit -qm init
)
OUT="$( (cd "$NV2" && scripts/crew status) 2>&1 )"
has "$OUT" "report      : none due — nothing closed a ticket" \
  && ok "navigator: a week with nothing landed owes no report" \
  || bad "navigator: none-due line (got: $OUT)"

# Declared absent means silent, not quieter: the whole block goes away and the
# existing roles_absent note is the only trace. A board that nags for a hat
# nobody wears is a board that gets switched off.
printf '{"owns": [], "crew": {"dev_branch": "main", "roles_absent": ["navigator"]}}\n' > "$NV/.docs-kit.json"
OUT="$(nav status)"
if ! has "$OUT" "direction:" && has "$OUT" "role 'navigator' declared absent"; then
  ok "navigator: roles_absent removes the block and keeps the absent note"
else
  bad "navigator: absent handling (got: $OUT)"
fi
printf '{"owns": [], "crew": {"dev_branch": "main"}}\n' > "$NV/.docs-kit.json"

# THE REASON REPORTS LIVE IN A SUBFOLDER, proven both ways rather than asserted.
# docs_close::audit_ids reads every *.md DIRECTLY under 92_audit/, so a report
# beside LOG.md can make a ticket close with no audit line and no message.
# 0.35.0 narrowed what counts: only a line whose ref column LEADS with the id
# records a completion, so a prose mention no longer traps. The trap survives in
# the shape a report actually takes when it quotes the log — an audit-shaped row
# — which is why the subfolder still earns its keep. Reproduce the silent
# failure first, then the fix.
trap_repo() { # trap_repo <dir> <report-path-relative-to-docs>
  rm -rf "$1"; mkdir -p "$1/docs/23_backlog" "$1/docs/$(dirname "$2")"
  (
    cd "$1"
    git init -q && git checkout -q -b main
    git config user.email t@t && git config user.name t
    printf -- '---\nid: BACKLOG-016\ndescription: "y"\nsource_ref: ISSUE-002\nstatus: open\n---\n' \
      > docs/23_backlog/t016.md
    printf '# Audit log\n\n2026-09-01 | init | - | - | mốc\n' > docs/92_audit/LOG.md
    printf '# Báo cáo\n\nĐang mở: BACKLOG-016.\n\n2026-09-05 | trích lại từ log | BACKLOG-016 | - | dẫn chứng\n' > "docs/$2"
    git add -A && git commit -qm init
    echo x > f && git add -A && git commit -qm "x

Closes: BACKLOG-016"
    python3 "$KIT/scripts/docs_close.py" . --apply >/dev/null 2>&1
  )
  # `grep -c` prints 0 AND exits 1 when it matches nothing, so a `|| echo 0`
  # fallback would emit the count twice. Let the assignment carry the status.
  TR_N="$(grep -c 'BACKLOG-016' "$1/docs/92_audit/LOG.md" 2>/dev/null)" || TR_N=0
  echo "$TR_N"
}
FLAT="$(trap_repo "$TMP/trapflat" "92_audit/$WEEK.md")"
SUB="$(trap_repo "$TMP/trapsub" "92_audit/reports/$WEEK.md")"
if [ "$FLAT" -eq 0 ] && [ "$SUB" -eq 1 ]; then
  ok "navigator: a report beside LOG.md eats the audit line, one in reports/ does not"
else
  bad "navigator: audit_ids trap not reproduced (flat=$FLAT sub=$SUB — expected 0 and 1)"
fi

# Append-only really reaches into the subfolder: the check is on the folder, not
# on LOG.md, so a rewritten report is a FAIL like a rewritten log line.
printf 'rewritten\n' > "$NV/docs/92_audit/reports/$WEEK.md"
OUT="$(bash "$KIT/scripts/docs_validate.sh" "$NV/docs" 2>&1)"
if has "$OUT" "FAIL [audit-append]" && has "$OUT" "reports/$WEEK.md"; then
  ok "navigator: rewriting a committed report is red, and names the file"
else
  bad "navigator: append-only over reports/ (got: $OUT)"
fi
( cd "$NV" && git checkout -q -- "docs/92_audit/reports/$WEEK.md" )

# The scaffold needs no code change for a new role, but "needs none" is a claim
# with two halves and both are asserted.
NVS="$TMP/navstamp"
mkdir -p "$NVS"
( cd "$NVS" && git init -q && git checkout -q -b main \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init )
bash "$KIT/scripts/crew_scaffold.sh" "$NVS" >/dev/null 2>&1
[ -f "$NVS/.claude/commands/navigator.md" ] \
  && ok "navigator: the scaffold stamps the role file with no code change" \
  || bad "navigator: navigator.md not stamped"
NVS2="$TMP/navskip"
mkdir -p "$NVS2"
( cd "$NVS2" && git init -q && git checkout -q -b main \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init )
bash "$KIT/scripts/crew_scaffold.sh" --skip navigator "$NVS2" >/dev/null 2>&1
if [ ! -f "$NVS2/.claude/commands/navigator.md" ] \
   && [ -f "$NVS2/.claude/commands/planner.md" ]; then
  ok "navigator: --skip navigator leaves the hat unstamped"
else
  bad "navigator: --skip navigator"
fi

OUT="$( (cd "$NVS" && cp -R "$NVS/.claude" "$NV/" 2>/dev/null; cd "$NV" && scripts/crew role navigator) 2>&1 )" \
  && RC=0 || RC=$?
[ "$RC" -eq 0 ] && has "$OUT" "crew report" \
  && ok "navigator: crew role prints the stamped hat file" \
  || bad "navigator: crew role navigator (rc=$RC, got: $OUT)"

OUT="$( (cd "$NV" && CREW_SESSIONS_DIR="$TMP/no-sessions" scripts/crew name navigator) 2>&1 )" \
  && RC=0 || RC=$?
[ "$RC" -eq 0 ] && has "$OUT" "$(basename "$NV") · navigator" \
  && ok "navigator: the hat's session title follows the existing grammar" \
  || bad "navigator: crew name navigator (rc=$RC, got: $OUT)"

# ---------------------------------------------------------------- title nag
# Step 4b of the executor hat — re-run `crew name` after the trailer, because the
# state just moved from processing to finishing — is the step most often skipped,
# so sessions end sitting at a title the session list then reports as work still
# in flight. The board is unaffected (it derives state from git); the LIST is what
# goes wrong, and nothing looked at it. Known-bad first.
NG="$TMP/titlenag"
mkdir -p "$NG/docs/23_backlog" "$NG/scripts"
(
  cd "$NG"
  git init -q && git checkout -q -b dev
  git config user.email t@t && git config user.name t
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  # Since 0.42.0 a title with no `crew/` marker is a crew title only when its
  # second field names a role this repo stamped.
  mkdir -p .claude/commands && echo executor > .claude/commands/executor.md
  printf '{"owns": [], "crew": {"dev_branch": "dev"}}\n' > .docs-kit.json
  git add -A && git commit -qm init >/dev/null
)
mkticket "$NG" 043 in-progress fast-pair
# The trailer is what moves the state, so write one: pair_state now reads finishing.
( cd "$NG" && echo x > f && git add -A && git commit -qm "work

Closes: BACKLOG-043" >/dev/null )

NGT="$TMP/nagtranscripts"; mkdir -p "$NGT"
mktitle() { printf '{"type":"custom-title","customTitle":"%s"}\n' "$1" > "$NGT/$2.jsonl"; }
run_nag() { # run_nag <cwd> <transcript> → the systemMessage, decoded
  # json.dumps escapes the title separator (U+00B7) to \u00b7, so asserting on
  # the raw wire form would test the encoder, not the message a reader sees.
  # Silence stays silence: no output in, empty string out.
  printf '{"session_id":"t1","cwd":"%s","transcript_path":"%s"}' "$1" "$2" \
    | bash "$KIT/scripts/hook_title_nag.sh" \
    | python3 -c 'import json,sys
raw = sys.stdin.read().strip()
print(json.loads(raw).get("systemMessage", "") if raw else "", end="")'
}

# KNOWN-BAD: the trailer is written, so git says finishing; the title still says
# processing. This is the exact shape that was reported as forgotten.
mktitle "titlenag · executor · b043 · i001 · main · processing" stale
OUT="$(run_nag "$NG" "$NGT/stale.jsonl")"
if has "$OUT" "b043 · i001 · main · finishing" && has "$OUT" "/rename"; then
  ok "title nag: a stale processing title is caught, with the /rename line"
else
  bad "title nag: stale title (got: $OUT)"
fi
# It must show BOTH halves — a nag that prints only the right answer leaves the
# reader guessing what was wrong with theirs.
has "$OUT" "now  : titlenag · executor · b043 · i001 · main · processing" \
  && ok "title nag: it prints the wrong title beside the right one" \
  || bad "title nag: only one half shown (got: $OUT)"

# THE QUIET FORM: the title already matches, so there is nothing to say.
mktitle "titlenag · executor · b043 · i001 · main · finishing" fresh
[ -z "$(run_nag "$NG" "$NGT/fresh.jsonl")" ] \
  && ok "title nag: a correct title is silent" \
  || bad "title nag: fired on a correct title"

# Not a crew session at all — every other session in the machine passes through
# this hook, and none of them may be nagged.
mktitle "just some session about billing" plain
[ -z "$(run_nag "$NG" "$NGT/plain.jsonl")" ] \
  && ok "title nag: a non-crew title is silent" \
  || bad "title nag: fired on a non-crew session"

# A repo with no scripts/crew is not a crew repo, whatever its title says.
NOC="$TMP/nocrew"; mkdir -p "$NOC"
( cd "$NOC" && git init -q && git config user.email t@t && git config user.name t \
  && git commit -q --allow-empty -m init >/dev/null )
[ -z "$(run_nag "$NOC" "$NGT/stale.jsonl")" ] \
  && ok "title nag: a repo without scripts/crew is silent" \
  || bad "title nag: fired in a repo that does not run crew"

# 0.39.0: the same hook has to catch the OTHER end of the lifecycle. Once the
# ticket is closed out, a session still titled `finishing` is naming work that
# has nothing left to do — and for a fast-pair ticket the trailer never moves,
# so the close-out is the only thing that can tell the two apart.
mkticket "$NG" 043 done fast-pair
mktitle "titlenag · executor · b043 · i001 · main · finishing" landed
OUT="$(run_nag "$NG" "$NGT/landed.jsonl")"
if has "$OUT" "b043 · i001 · main · finished"; then
  ok "title nag: a closed-out ticket moves the title from finishing to finished"
else
  bad "title nag: finished not caught (got: $OUT)"
fi

# FAIL OPEN, and this is the case the guard added earlier makes reachable: a
# `full` ticket named from the main tree makes `crew name --want` refuse. The
# hook must go quiet, not relay a refusal it cannot act on.
mkticket "$NG" 077 in-progress full
mktitle "titlenag · executor · b077 · i001 · main · processing" refused
[ -z "$(run_nag "$NG" "$NGT/refused.jsonl")" ] \
  && ok "title nag: a title crew name refuses to compute is silent, not relayed" \
  || bad "title nag: relayed a refusal (got: $(run_nag "$NG" "$NGT/refused.jsonl"))"

# ---------------------------------------------------------------- subjects (0.42.0)
# From `b<nnn>` alone the user could not tell which planner to go back to (four
# repos, 2026-09-24). The link was already in every ticket — `source_ref` — and
# nothing showed it. Since 0.42.0 the executor title carries the source as a
# token, a subject planner carries the same token plus the words its document's
# file name already holds, and `--group` hands the desktop the two sidebar groups.
mkdir -p "$NG/docs/10_issues" "$NG/docs/22_decisions/_archive"
printf -- '---\nid: ISSUE-001\n---\n' > "$NG/docs/10_issues/ISSUE-001-nut-luu-khong-chep.md"
printf -- '---\nid: DECISION-009\n---\n' > "$NG/docs/22_decisions/DECISION-009-co-vi-the.md"
printf -- '---\nid: DECISION-010\n---\n' > "$NG/docs/22_decisions/_archive/DECISION-010.md"
( cd "$NG" && git add -A && git commit -qm "subjects" >/dev/null )
ngn() { (cd "$NG" && scripts/crew name "$@") 2>&1; }

OUT="$(ngn planner d009 --want)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && [ "$OUT" = "titlenag · planner · d009 co-vi-the" ] \
  && ok "subject: a subject planner is named by its document, words read from the file name" \
  || bad "subject: planner title (rc=$RC, got: $OUT)"
[ "$(ngn planner DECISION-009 --want)" = "$(ngn planner D9 --want)" ] \
  && [ "$(ngn planner D9 --want)" = "titlenag · planner · d009 co-vi-the" ] \
  && ok "subject: d009, D9 and DECISION-009 name the same subject" \
  || bad "subject: id forms disagree ($(ngn planner D9 --want))"
[ "$(ngn planner d010 --want)" = "titlenag · planner · d010" ] \
  && ok "subject: an archived document with no slug still names its subject, as the bare token" \
  || bad "subject: bare token (got: $(ngn planner d010 --want))"

# KNOWN-BAD: an id with no document behind it. The words come from a file name,
# so there is nothing to read — and a subject nobody wrote down is not a subject.
OUT="$(ngn planner d999 --want)" && RC=0 || RC=$?
[ "$RC" -ne 0 ] && has "$OUT" "[name:subject]" \
  && ok "subject: an id with no document is refused, not titled" \
  || bad "subject: missing doc (rc=$RC, got: $OUT)"
OUT="$(ngn executor d009 --want)" && RC=0 || RC=$?
[ "$RC" -ne 0 ] && has "$OUT" "named by its ticket" \
  && ok "subject: an executor takes no subject argument — its ticket's source_ref is the subject" \
  || bad "subject: executor subject arg (rc=$RC, got: $OUT)"

# A hat working one ticket keeps the ticket as its task; a hat with nothing is the hat.
[ "$(ngn tester 157 --want)" = "titlenag · tester · b157" ] \
  && [ "$(ngn steward --want)" = "titlenag · steward" ] \
  && ok "subject: a hat is <repo> · <role>, with its ticket after it when it has one" \
  || bad "subject: hat grammar ($(ngn tester 157 --want) / $(ngn steward --want))"

# A ticket with no source_ref keeps the rest of its title (fail open).
printf -- '---\nid: BACKLOG-044\ndescription: "x"\nstatus: in-progress\nexecution: fast-pair\n---\n' \
  > "$NG/docs/23_backlog/t044.md"
( cd "$NG" && git add -A && git commit -qm "t044" >/dev/null )
[ "$(ngn executor 44 --want)" = "titlenag · executor · b044 · main · processing" ] \
  && ok "subject: a ticket with no source_ref is titled without a subject, not refused" \
  || bad "subject: no source_ref (got: $(ngn executor 44 --want))"

# --group: the subject's group first, then the project's — and only the project's
# when the subject has no document to take its words from.
OUT="$(ngn planner d009 --group)"
[ "$OUT" = "$(printf 'titlenag · d009 co-vi-the\ntitlenag')" ] \
  && ok "group: a subject planner belongs in its subject's group, then the project's" \
  || bad "group: planner groups (got: $OUT)"
OUT="$(ngn executor 43 --group)"
[ "$OUT" = "$(printf 'titlenag · i001 nut-luu-khong-chep\ntitlenag')" ] \
  && ok "group: an executor's first group is the subject its ticket's source_ref names" \
  || bad "group: executor groups (got: $OUT)"
[ "$(ngn executor 44 --group)" = "titlenag" ] && [ "$(ngn steward --group)" = "titlenag" ] \
  && ok "group: no subject, one group — the project's" \
  || bad "group: project only ($(ngn executor 44 --group) / $(ngn steward --group))"

# The hook follows the same grammar. A title in the pre-0.42 grammar is still a
# crew title by its `crew/` marker, and is nagged once into the new one.
mktitle "titlenag · main · b043 · finishing · crew/executor" legacy
OUT="$(run_nag "$NG" "$NGT/legacy.jsonl")"
has "$OUT" "grammar before 0.42.0" \
  && has "$OUT" "true : titlenag · executor · b043 · i001 · main · finished" \
  && ok "title nag: a pre-0.42 title is carried into the new grammar" \
  || bad "title nag: legacy title (got: $OUT)"

# With no marker, the second field is only a candidate: it counts when the repo
# stamped a role file for it. A plain session named like a project is left alone.
mktitle "titlenag · notes · họp tuần với khách" notes
[ -z "$(run_nag "$NG" "$NGT/notes.jsonl")" ] \
  && ok "title nag: a second field that is no stamped role is silent" \
  || bad "title nag: nagged a non-role title"
mktitle "titlenag · planner · d009" nslug
[ -z "$(run_nag "$NG" "$NGT/nslug.jsonl")" ] \
  && ok "title nag: a role this repo never stamped is silent" \
  || bad "title nag: nagged an unstamped role"
echo planner > "$NG/.claude/commands/planner.md"
OUT="$(run_nag "$NG" "$NGT/nslug.jsonl")"
has "$OUT" "true : titlenag · planner · d009 co-vi-the" \
  && ok "title nag: a subject planner missing its words is given them" \
  || bad "title nag: subject planner (got: $OUT)"


# ---------------------------------------------------------------- finished (0.39.0)
# Before this state existed a session whose work had LANDED read exactly like one
# still waiting for its merge — the distinction `finishing` was invented to make.
# Measured 2026-09-12 on a fixture like this one: after the merge the board and
# the title fell BACK from `finishing` to `processing`, because the only test was
# the range `main..work/b<nnn>` and a fast-forward merge empties it; after the
# park `crew name` exited 1, and the Stop hook — silent on any non-zero exit —
# left the session at `finishing` for the rest of its life. Both ends are walked
# here, on two tickets: 001 straight through the real `crew done`, 002 stopped in
# the gap between the merge and the close-out.
FN="$TMP/finished"
FNR="$FN/repo"
mkdir -p "$FNR/scripts" "$FNR/docs/92_audit"
(
  cd "$FNR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  printf '# audit log\n' > docs/92_audit/LOG.md
  printf '{"owns": [], "crew": {"dev_branch": "main", "copy": [], "link": []}}\n' > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init >/dev/null
)
mkticket "$FNR" 001 open -
mkticket "$FNR" 002 open -
fst() { # fst <e<k>> → the state column of that executor's row, empty when idle
  (cd "$FNR" && scripts/crew status) 2>&1 | awk -v e="$1" '$1 == e { print $4; exit }'
}
fwant() { # fwant <e<k>> <nnn> → the title crew name computes inside that tree
  (cd "$FN/repo-$1" && "$FNR/scripts/crew" name executor "$2" --want) 2>&1
}
( cd "$FNR" && scripts/crew executor add >/dev/null 2>&1 && scripts/crew new 1 >/dev/null 2>&1 )
( cd "$FN/repo-e1" && echo a > a.txt && git add a.txt \
    && git -c user.email=t@t -c user.name=t commit -qm "work" -m "Closes: BACKLOG-001" )
[ "$(fst e1)" = "finishing" ] && ok "finished: the trailer alone is still finishing" \
  || bad "finished: expected finishing before the merge, got '$(fst e1)'"

OUT="$( (cd "$FNR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew done 1) 2>&1 )" && RC=0 || RC=$?
[ "$RC" -eq 0 ] || bad "finished: crew done 1 failed (out: $OUT)"
grep -q "^status: done" "$FNR/docs/23_backlog/t001.md" \
  && ok "finished: crew done writes the close-out half the state reads" \
  || bad "finished: ticket 001 was not closed out (done said: $OUT)"
# The tree is free while the SESSION is finished. Two different subjects, and the
# board must keep answering about the tree.
[ -z "$(fst e1)" ] && ok "finished: the parked tree still reads idle on the board" \
  || bad "finished: expected an idle row, got '$(fst e1)'"
OUT="$(fwant e1 1)" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && has "$OUT" "executor · b001 · i001 · e1 · finished"; then
  ok "finished: a parked executor whose ticket is closed out is named, and the word is finished"
else
  bad "finished: parked title (rc=$RC, got: $OUT)"
fi

# KNOWN-BAD, and this is the regression itself: the closer is on the dev branch,
# so the work HAS landed, but the close-out never ran. It must read `finishing`,
# whose action is "finish closing it out", and must never fall back to
# `processing`, which claims a session is still editing.
( cd "$FNR" && scripts/crew new 2 >/dev/null 2>&1 )
( cd "$FN/repo-e1" && echo b > b.txt && git add b.txt \
    && git -c user.email=t@t -c user.name=t commit -qm "work" -m "Closes: BACKLOG-002" )
( cd "$FNR" && git merge -q --ff-only work/b002 )
[ "$(fst e1)" = "finishing" ] \
  && ok "finished: a merge with no close-out holds at finishing instead of falling back" \
  || bad "finished: merged-but-unclosed read '$(fst e1)' — the 0.39.0 regression is back"
OUT="$(fwant e1 2)" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && has "$OUT" "b002 · i001 · e1 · finishing"; then
  ok "finished: the title agrees with the board inside that gap"
else
  bad "finished: gap title (rc=$RC, got: $OUT)"
fi
# Parked inside the gap there is NO title, because `finishing` is still the
# honest word and somebody has to write the close-out. The refusal must name
# that missing half rather than repeat the take-a-ticket line.
git -C "$FN/repo-e1" switch -q --detach main
OUT="$(fwant e1 2)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "[name:unclosed]"; then
  ok "finished: a parked ticket nobody closed out is red, and names the half that is missing"
else
  bad "finished: unclosed refusal (rc=$RC, got: $OUT)"
fi
# A genuinely free tree still refuses the old way, which is what keeps the new
# branch narrow: a ticket argument alone must not conjure a title.
OUT="$(fwant e1 6)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "holds no ticket"; then
  ok "finished: a free tree is still refused, so the ticket argument buys nothing on its own"
else
  bad "finished: free-tree refusal (rc=$RC, got: $OUT)"
fi

# ---------------------------------------------------------------- frozen knobs (0.40.5)
# A present key outranks the kit's default forever, and crew-init used to copy
# the knobs in verbatim. The known-bad case is the shape 3 of 4 real crew repos
# carried: every knob at exactly the default, beside asked answers that also
# equal their fallbacks and must NOT be reported.
KN="$KIT/scripts/crew_knobs.py"
KD="$TMP/knobs"
mkdir -p "$KD/verbatim" "$KD/tuned" "$KD/off"
python3 - "$KD" <<'PY'
import json, os, sys
d = sys.argv[1]
def put(sub, obj):
    with open(os.path.join(d, sub, ".docs-kit.json"), "w") as f:
        f.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
put("verbatim", {"owns": ["screens"], "crew": {
    "test_cmd": "npm test", "typecheck_cmd": "", "dev_branch": "main",
    "prod_branch": "production", "copy": [], "link": [], "setup_cmd": "",
    "roles_absent": [], "resources": {}, "reader_cap": 4, "wait_budget_min": 30,
    "draw_tools": ["mcp__visualize__show_widget", "Artifact"], "enforce": False}})
put("tuned", {"crew": {"reader_cap": 6, "draw_tools": ["mcp__visualize__show_widget"]}})
put("off", {"owns": []})
PY

OUT="$(python3 "$KN" "$KD/verbatim")"
if has "$OUT" "[knob:frozen] reader_cap" && has "$OUT" "[knob:frozen] wait_budget_min" \
   && has "$OUT" "[knob:frozen] draw_tools"; then
  ok "knobs: a verbatim default is reported, by key"
else
  bad "knobs: verbatim defaults not reported (got: $OUT)"
fi

N="$(printf '%s\n' "$OUT" | grep -c '^\[knob:frozen\]')"
[ "$N" -eq 3 ] && ok "knobs: an asked answer equal to its fallback is not a knob, nor is enforce" \
  || bad "knobs: reported more than the three knobs (got: $OUT)"

OUT="$(python3 "$KN" "$KD/tuned")"
[ "$OUT" = "KNOBS none" ] && ok "knobs: a tuned value is left alone" \
  || bad "knobs: tuned value reported (got: $OUT)"

OUT="$(python3 "$KN" "$KD/off")"
[ "$OUT" = "KNOBS off" ] && ok "knobs: silent about a repo with crew off" \
  || bad "knobs: crew-off repo (got: $OUT)"

cp "$KD/verbatim/.docs-kit.json" "$KD/before.json"
python3 "$KN" --drop "$KD/verbatim" >/dev/null
OUT="$(python3 - "$KD/before.json" "$KD/verbatim/.docs-kit.json" <<'PY'
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:])
gone = sorted(set(a["crew"]) - set(b["crew"]))
kept = all(b["crew"][k] == v for k, v in a["crew"].items() if k not in gone)
print("gone=%s kept=%s owns=%s" % (",".join(gone), kept, b.get("owns") == a.get("owns")))
PY
)"
AGAIN="$(python3 "$KN" "$KD/verbatim")"
if [ "$OUT" = "gone=draw_tools,reader_cap,wait_budget_min kept=True owns=True" ] \
   && [ "$AGAIN" = "KNOBS none" ]; then
  ok "knobs: --drop removes exactly what was reported and nothing else"
else
  bad "knobs: --drop (got: $OUT / again: $AGAIN)"
fi

# Dropping is only a no-op if the table IS what the readers fall back to. Read
# the fallbacks out of the stamped CLI and the hook, so a retuned default that
# forgets the table goes red here instead of dropping a live value.
OUT="$(python3 - "$KIT" <<'PY'
import ast, re, sys
kit = sys.argv[1]
sys.dont_write_bytecode = True  # no cache tree beside the kit scripts
sys.path.insert(0, kit + "/scripts")
import crew_knobs
bad = []
cli = open(kit + "/templates/crew/crew").read()
for key, want in crew_knobs.KNOBS.items():
    if key == "draw_tools":
        tree = ast.parse(open(kit + "/scripts/hook_explain_gate.py").read())
        got = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(getattr(t, "id", "") == "DEFAULT_DRAW" for t in n.targets)]
        if got != [want]:
            bad.append("%s hook=%s" % (key, got))
        continue
    seen = {m.group(1) if m.group(1) is not None else m.group(2)
            for m in re.finditer(r'cfg %s (?:"([^"]*)"|([^\s)"]+))' % key, cli)}
    if seen != {want}:
        bad.append("%s cli=%s" % (key, sorted(seen)))
print("drift: " + "; ".join(bad) if bad else "same")
PY
)"
[ "$OUT" = "same" ] && ok "knobs: the table matches every reader's fallback" \
  || bad "knobs: table drifted from the readers ($OUT)"

# ---------------------------------------------------------------- chains (0.41.0)
# GitHub issue #4, from a repo with ~330 backlog items and 6 executors: a run of
# dependent tickets (each one edits a file the one before it creates) cost one
# hand-off per ticket, and the order of the chain lived only in a chat message.
# The planner now records it as `after_ref:` on the later ticket, one session
# carries the whole chain, and — the property the owner asked to be most careful
# about — the executor carrying a chain stays BUSY through every `crew done`: a
# parked tree is a free tree, and a free tree is what another session's
# `crew new` takes. Known-bad first.
CH="$TMP/chain"
CHR="$CH/repo"
mkdir -p "$CHR/scripts" "$CHR/docs/92_audit"
(
  cd "$CHR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  printf '# audit log\n' > docs/92_audit/LOG.md
  printf '{"owns": [], "crew": {"dev_branch": "main", "copy": [], "link": []}}\n' > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init >/dev/null
)
chticket() { # chticket <nnn> <after nnn|-> [execution] — a Backlog item, committed
  mkdir -p "$CHR/docs/23_backlog"
  printf -- '---\nid: BACKLOG-%s\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: open\n' "$1" \
    > "$CHR/docs/23_backlog/t$1.md"
  [ "$2" = "-" ] || printf 'after_ref: BACKLOG-%s\n' "$2" >> "$CHR/docs/23_backlog/t$1.md"
  [ -z "${3:-}" ] || printf 'execution: %s\n' "$3" >> "$CHR/docs/23_backlog/t$1.md"
  printf -- '---\n' >> "$CHR/docs/23_backlog/t$1.md"
  ( cd "$CHR" && git add -A && git commit -qm "ticket $1" >/dev/null )
}
chcrew() { (cd "$CHR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew "$@") 2>&1; }
chwork() { # chwork <e<k>> <nnn> — the ticket's work, committed with its closer
  ( cd "$CH/repo-$1" && echo "$2" >> routes.txt && git add -A \
      && git -c user.email=t@t -c user.name=t commit -qm "work $2" -m "Closes: BACKLOG-$2" )
}
chclose() { ( cd "$CHR" && git add -A && git commit -qm "docs: close-out" >/dev/null ); }
chrow() { chcrew status | awk -v e="$1" '$1 == e { print $2; exit }'; }
chwant() { (cd "$CH/repo-$1" && "$CHR/scripts/crew" name executor "$2" --want) 2>&1; }
chticket 101 -
chticket 102 101
chticket 103 102
chticket 200 -
( cd "$CHR" && scripts/crew executor add >/dev/null 2>&1 )

# KNOWN-BAD: 102 edits what 101 builds, and 101 has not landed.
OUT="$(chcrew new 102)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "[new:after]" && has "$OUT" "BACKLOG-101"; then
  ok "chain: a ticket whose predecessor has not landed is refused, and the refusal names it"
else
  bad "chain: after_ref gate (rc=$RC out: $OUT)"
fi
[ -z "$(git -C "$CHR" branch --list 'work/b102')" ] \
  && ok "chain: the refusal leaves no branch behind" \
  || bad "chain: a refused ticket still got a branch"

OUT="$(chcrew new 101 --chain)" || bad "chain: crew new 101 failed: $OUT"
has "$OUT" "101→103" && ok "chain: crew new says which chain the session now carries" \
  || bad "chain: crew new did not name the chain (out: $OUT)"
# Still refused while 101 is in flight, and now the refusal says WHO carries it,
# so a second session does not go looking for a tree of its own.
OUT="$(chcrew new 102)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "open in e1"; then
  ok "chain: while the predecessor is in flight the refusal names the session carrying it"
else
  bad "chain: in-flight refusal (rc=$RC out: $OUT)"
fi

OUT="$(chwant e1 101)"
has "$OUT" "b101 · i001 · 101→103 · e1 · processing" \
  && ok "chain: the title names one ticket and the chain it belongs to" \
  || bad "chain: chained title (got: $OUT)"
OUT="$(chcrew status)"
if has "$OUT" "chains:" && has "$OUT" "101→103  e1 on 101 · queued 102 103"; then
  ok "chain: the board shows what is queued behind the session"
else
  bad "chain: chains block (got: $OUT)"
fi

# THE PROPERTY THE OWNER ASKED FOR. crew done 101 must leave e1 holding 102's
# branch — busy — and must get there without ever detaching: a detached, clean
# tree is exactly what exec_free hands to the next `crew new`, so even an instant
# spent parked is a window in which another session takes the chain's tree. The
# end state cannot prove "never parked" (park-then-switch ends in the same place),
# so the check reads e1's own reflog for the move itself.
chwork e1 101
OUT="$(chcrew done 101)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] || bad "chain: crew done 101 failed (out: $OUT)"
[ "$(git -C "$CH/repo-e1" symbolic-ref --short HEAD 2>/dev/null)" = "work/b102" ] \
  && ok "chain: crew done hands the tree straight to the next ticket in the chain" \
  || bad "chain: e1 is not on work/b102 after crew done 101 (out: $OUT)"
[ "$(chrow e1)" = "work/b102" ] \
  && ok "chain: the board reads the chain's executor as busy, never idle" \
  || bad "chain: board row for e1 is '$(chrow e1)'"
MOVE="$(git -C "$CH/repo-e1" reflog -1 --format=%gs HEAD)"
has "$MOVE" "moving from work/b101 to work/b102" \
  && ok "chain: the tree went from one branch to the next with no detached HEAD in between" \
  || bad "chain: the handoff passed through another state (reflog: $MOVE)"
[ -f "$CH/repo-e1/routes.txt" ] && grep -q "^101$" "$CH/repo-e1/routes.txt" \
  && ok "chain: the next ticket starts from a dev branch that already holds the last one" \
  || bad "chain: work/b102 was not cut from the merged dev branch"
grep -q "NEW	e1	BACKLOG-102	.*after=BACKLOG-101" "$CH/repo-crew/log.tsv" \
  && ok "chain: the handoff is logged as a NEW that says which ticket it followed" \
  || bad "chain: no NEW line for the handoff"

# Another session asking for a tree right now must NOT get e1.
chclose
OUT="$(chcrew new 200)" || bad "chain: crew new 200 failed: $OUT"
if [ "$(git -C "$CH/repo-e1" symbolic-ref --short HEAD 2>/dev/null)" = "work/b102" ] \
   && [ "$(git -C "$CH/repo-e2" symbolic-ref --short HEAD 2>/dev/null)" = "work/b200" ]; then
  ok "chain: an unrelated crew new grows the pool instead of taking the chain's tree"
else
  bad "chain: unrelated ticket landed in the wrong tree (out: $OUT)"
fi

# The session's old title still reads 101; the nag must move it to 102, not to
# `finished` — the chain is not over. Written in the pre-0.42 grammar on purpose:
# a chain session titled before the upgrade must be carried over too.
mktitle "repo · e1 · b101 · 101→103 · finishing · crew/executor" chainstale
OUT="$(run_nag "$CH/repo-e1" "$NGT/chainstale.jsonl")"
has "$OUT" "true : repo · executor · b102 · i001 · 101→103 · e1 · processing" \
  && ok "chain: the title nag moves a chain session on to its next ticket" \
  || bad "chain: nag after handoff (got: $OUT)"

# --park ends the chain session here: the tree is free, the board points at the
# ticket that is now ready, and whoever resumes gets the tree they stand in.
chwork e1 102
OUT="$(chcrew done 102 --park)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && [ -z "$(git -C "$CH/repo-e1" symbolic-ref --short HEAD 2>/dev/null)" ] \
  && ok "chain: --park lands the ticket and frees the tree instead of handing it on" \
  || bad "chain: --park (rc=$RC out: $OUT)"
chclose
OUT="$(chcrew status)"
has "$OUT" "← no session carries this chain — next: scripts/crew new 103" \
  && ok "chain: a chain nobody carries is flagged with the ticket that is ready" \
  || bad "chain: uncarried chain not flagged (got: $OUT)"
( cd "$CHR" && scripts/crew executor add >/dev/null 2>&1 )   # e3, free, listed after e1
OUT="$( (cd "$CH/repo-e3" && "$CHR/scripts/crew" new 103) 2>&1 )" || bad "chain: crew new 103 failed: $OUT"
if [ "$(git -C "$CH/repo-e3" symbolic-ref --short HEAD 2>/dev/null)" = "work/b103" ] \
   && [ -z "$(git -C "$CH/repo-e1" symbolic-ref --short HEAD 2>/dev/null)" ]; then
  ok "chain: crew new takes the free executor the session stands in, not the first free one"
else
  bad "chain: cwd preference (e1=$(git -C "$CH/repo-e1" symbolic-ref --short HEAD 2>/dev/null) out: $OUT)"
fi

# The last ticket has nothing after it, so it parks exactly as before, and the
# session ends `finished` with the chain still in its title.
chwork e3 103
OUT="$(chcrew done 103)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] && [ -z "$(git -C "$CH/repo-e3" symbolic-ref --short HEAD 2>/dev/null)" ] \
  && ok "chain: the last ticket of a chain parks the tree" \
  || bad "chain: last ticket did not park (rc=$RC out: $OUT)"
chclose
OUT="$(chwant e3 103)"
has "$OUT" "b103 · i001 · 101→103 · e3 · finished" \
  && ok "chain: the session carrying a chain ends finished on its last ticket" \
  || bad "chain: finished title (got: $OUT)"
has "$(chcrew status)" "chains:" \
  && bad "chain: a chain with every ticket done is still on the board" \
  || ok "chain: a chain whose tickets are all done drops off the board"
OUT="$(chwant e2 200)"
has "$OUT" "b200 · i001 · e2 · processing" \
  && ok "chain: a ticket nobody chained keeps exactly the title it had" \
  || bad "chain: unchained title changed (got: $OUT)"

# A fork: two tickets after one. crew done continues into the lowest and names
# the other; a fast-pair link is never held for, because it runs in main.
chticket 300 -
chticket 302 300
chticket 301 300
chticket 400 -
chticket 401 400 fast-pair
OUT="$(chcrew status)"
has "$OUT" "fork: 300 is followed by 301 302" \
  && ok "chain: the board names a fork and which lane crew done continues into" \
  || bad "chain: fork line (got: $OUT)"
( cd "$CH/repo-e1" && "$CHR/scripts/crew" new 300 --chain >/dev/null 2>&1 )
chwork e1 300
OUT="$(chcrew done 300)"
if [ "$(git -C "$CH/repo-e1" symbolic-ref --short HEAD 2>/dev/null)" = "work/b301" ] \
   && has "$OUT" "also after BACKLOG-300: 302"; then
  ok "chain: at a fork crew done continues into the lowest ticket and names the other lane"
else
  bad "chain: fork handoff (out: $OUT)"
fi
chclose
( cd "$CH/repo-e3" && "$CHR/scripts/crew" new 400 >/dev/null 2>&1 )
chwork e3 400
OUT="$(chcrew done 400)"
if [ -z "$(git -C "$CH/repo-e3" symbolic-ref --short HEAD 2>/dev/null)" ] && has "$OUT" "fast-pair"; then
  ok "chain: a fast-pair next ticket runs in main, so the tree is parked, with the reason"
else
  bad "chain: fast-pair link (out: $OUT)"
fi
chclose

# after_ref names a Backlog item, never an Issue; and a loop cannot hang the board.
printf -- '---\nid: BACKLOG-500\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: open\nafter_ref: ISSUE-001\n---\n' \
  > "$CHR/docs/23_backlog/t500.md"
chclose
OUT="$(chcrew new 500)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "links Backlog items only"; then
  ok "chain: an after_ref that names an Issue is refused with the reason"
else
  bad "chain: non-Backlog after_ref (rc=$RC out: $OUT)"
fi
chticket 601 602
chticket 602 601
OUT="$(chcrew status)"
has "$OUT" "loops back on itself through" \
  && ok "chain: an after_ref loop is named on the board instead of hanging it" \
  || bad "chain: loop not reported (got: $OUT)"
OUT="$( (cd "$CHR" && scripts/crew name executor 601 --want) 2>&1 )"
if has "$OUT" "b601 · i001 · main · processing" && ! has "$OUT" "→"; then
  ok "chain: a ticket inside a loop gets no chain in its title, since no ticket there is first"
else
  bad "chain: looped title (got: $OUT)"
fi

# ---------------------------------------------------------------- close-out is committed (0.41.1)
# `crew done` ran docs_close on the main tree and left what it wrote there —
# the Backlog doc's `status: done` and the audit line — uncommitted. The very
# next `crew done` then died at check 2, naming exactly those two files and
# guessing "an open fast-pair edit?". Reproduced 2026-09-24 on 0.40.3 with two
# tickets back to back. Two parallel executors met it already; a chain session
# (0.41.0) met it on every ticket after the first. And because the push ran
# BEFORE the close-out, even a hand-committed close-out reached the remote one
# ticket late, riding the next push, and the last ticket's not at all.
CO="$TMP/closeout"
COR="$CO/repo"
COB="$CO/origin.git"
mkdir -p "$COR/scripts" "$COR/docs/92_audit"
git init -q --bare "$COB"
(
  cd "$COR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  echo hello > README.md
  printf '# audit log\n' > docs/92_audit/LOG.md
  printf '{"owns": [], "crew": {"dev_branch": "main", "copy": [], "link": []}}\n' > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init >/dev/null
  git remote add origin "$COB" && git push -q origin main 2>/dev/null
)
coticket() { # coticket <nnn> [<after nnn>]
  mkdir -p "$COR/docs/23_backlog"
  printf -- '---\nid: BACKLOG-%s\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: open\n' "$1" \
    > "$COR/docs/23_backlog/t$1.md"
  [ -z "${2:-}" ] || printf 'after_ref: BACKLOG-%s\n' "$2" >> "$COR/docs/23_backlog/t$1.md"
  printf -- '---\n' >> "$COR/docs/23_backlog/t$1.md"
  ( cd "$COR" && git add -A && git commit -qm "ticket $1" >/dev/null )
}
cowork() { # cowork <nnn> — commit the ticket's work, with its closer, in whichever tree holds it
  CT="$(git -C "$COR" worktree list --porcelain | awk -v b="branch refs/heads/work/b$1" '
    /^worktree /{ p = substr($0, 10) } $0 == b { print p; exit }')"
  [ -n "$CT" ] || { echo "cowork: no tree holds work/b$1" >&2; return 1; }
  ( cd "$CT" && echo "$1" >> "w$1.txt" && git add -A \
      && git -c user.email=t@t -c user.name=t commit -qm "work $1" -m "Closes: BACKLOG-$1" )
}
codone() { (cd "$COR" && CREW_DOCS_CLOSE="${CODC:-$KIT/scripts/docs_close.sh}" scripts/crew done "$@") 2>&1; }
coticket 001
coticket 002
( cd "$COR" && scripts/crew executor add >/dev/null 2>&1 \
    && scripts/crew new 1 >/dev/null 2>&1 && scripts/crew new 2 >/dev/null 2>&1 )
cowork 001
cowork 002

OUT="$(codone 1)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] || bad "close-out: crew done 1 failed (out: $OUT)"
# KNOWN-BAD, the reported shape: the second crew done in a row.
OUT="$(codone 2)" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && ! has "$OUT" "check 2"; then
  ok "close-out: a second crew done in a row is not refused by the first one's close-out"
else
  bad "close-out: back-to-back crew done (rc=$RC out: $OUT)"
fi
[ -z "$(git -C "$COR" status --porcelain)" ] \
  && ok "close-out: crew done leaves the main tree clean" \
  || bad "close-out: main tree left dirty: $(git -C "$COR" status --porcelain | tr '\n' ' ')"
SUBJ="$(git -C "$COR" log -1 --format=%s main)"
FILES="$(git -C "$COR" show --name-only --format= main | sort | tr '\n' ' ')"
if [ "$SUBJ" = "docs: close-out BACKLOG-002" ] \
   && [ "$FILES" = "docs/23_backlog/t002.md docs/92_audit/LOG.md " ]; then
  ok "close-out: it is one commit on the dev branch, holding exactly what docs_close wrote"
else
  bad "close-out: commit shape (subject: $SUBJ · files: $FILES)"
fi
# A close-out commit that carried the trailer would be a second closer for the
# same ticket, and every reader of closers would have to know which one counts.
[ "$(git -C "$COR" log -1 --format=%B main | grep -c '^Closes:')" -eq 0 ] \
  && ok "close-out: the close-out commit carries no Closes: trailer of its own" \
  || bad "close-out: the close-out commit repeats the trailer"
[ "$(git --git-dir="$COB" log -1 --format=%s main 2>/dev/null)" = "docs: close-out BACKLOG-002" ] \
  && ok "close-out: the push goes after the close-out, so the remote has status: done" \
  || bad "close-out: remote main is not the local close-out ($(git --git-dir="$COB" log -1 --format=%s main 2>/dev/null))"

# Only what docs_close wrote. The main tree is shared, and between check 2 and
# the close-out a fast-pair session can start an edit; sweeping it into a commit
# titled "close-out" would land half-typed work on the dev branch under the
# wrong name. The wrapper makes that race deterministic.
coticket 003
( cd "$COR" && scripts/crew new 3 >/dev/null 2>&1 )
cowork 003
printf '#!/bin/bash\necho half-typed >> "%s/README.md"\nexec bash "%s/scripts/docs_close.sh" "$@"\n' \
  "$COR" "$KIT" > "$CO/dc-race.sh"
OUT="$(CODC="$CO/dc-race.sh" codone 3)" && RC=0 || RC=$?
FILES="$(git -C "$COR" show --name-only --format= main | sort | tr '\n' ' ')"
if [ "$FILES" = "docs/23_backlog/t003.md docs/92_audit/LOG.md " ] \
   && [ "$(git -C "$COR" status --porcelain)" = " M README.md" ]; then
  ok "close-out: an edit another session starts meanwhile stays out of the commit, and stays put"
else
  bad "close-out: race (files: $FILES · left: $(git -C "$COR" status --porcelain | tr '\n' ' ') · out: $OUT)"
fi
git -C "$COR" checkout -q -- README.md

# A file that was ALREADY dirty when the close-out started holds somebody's edit
# and docs_close's line together. It is left for its owner and named, with the
# tag. The edit lands between check 2 and docs_close through a post-merge hook —
# git runs it on the main tree's --ff-only merge, which is exactly that window —
# and only in the main tree, since every executor shares the hooks directory.
coticket 004
( cd "$COR" && scripts/crew new 4 >/dev/null 2>&1 )
cowork 004
printf '#!/bin/sh\n[ "$(basename "$PWD")" = repo ] || exit 0\necho "hand note" >> docs/92_audit/LOG.md\n' \
  > "$COR/.git/hooks/post-merge" && chmod +x "$COR/.git/hooks/post-merge"
OUT="$(codone 4)" && RC=0 || RC=$?
rm -f "$COR/.git/hooks/post-merge"
FILES="$(git -C "$COR" show --name-only --format= main | sort | tr '\n' ' ')"
if has "$OUT" "[done:closeout]" && has "$OUT" "docs/92_audit/LOG.md" \
   && [ "$FILES" = "docs/23_backlog/t004.md " ] && grep -q "hand note" "$COR/docs/92_audit/LOG.md" \
   && [ "$(git -C "$COR" status --porcelain)" = " M docs/92_audit/LOG.md" ]; then
  ok "close-out: a file that was already dirty is left for its owner and named, with [done:closeout]"
else
  bad "close-out: pre-dirty file (rc=$RC · files: $FILES · left: $(git -C "$COR" status --porcelain | tr '\n' ' ') · out: $OUT)"
fi
( cd "$COR" && git commit -qam "hand note" >/dev/null )

# A refused commit (a repo's own pre-commit hook) must not fail a merge that has
# already landed. It is reported with the tag and the files, and never bypassed.
coticket 005
( cd "$COR" && scripts/crew new 5 >/dev/null 2>&1 )
cowork 005
printf '#!/bin/sh\nexit 1\n' > "$COR/.git/hooks/pre-commit" && chmod +x "$COR/.git/hooks/pre-commit"
OUT="$(codone 5)" && RC=0 || RC=$?
rm -f "$COR/.git/hooks/pre-commit"
if [ "$RC" -eq 0 ] && has "$OUT" "[done:closeout]" && has "$OUT" "docs/23_backlog/t005.md" \
   && [ "$(git -C "$COR" log -1 --format=%s main)" = "work 005" ]; then
  ok "close-out: a refused commit is reported with [done:closeout] and the files, not bypassed"
else
  bad "close-out: refused commit (rc=$RC · head: $(git -C "$COR" log -1 --format=%s main) · out: $OUT)"
fi
( cd "$COR" && git commit -qam "close-out by hand" >/dev/null )

# An executor may flip `status: done` inside its own ticket and forget the audit
# line; docs_close then writes LOG.md alone, and no Backlog doc names the ticket.
# The commit must still be titled after the ticket crew done closed, and say which
# crew done wrote it — found by explaining this very mechanism, when the subject
# came out as `BACKLOG-docs/92_audit/LOG.md`.
coticket 007
( cd "$COR" && scripts/crew new 7 >/dev/null 2>&1 )
CT7="$(git -C "$COR" worktree list --porcelain | awk '/^worktree /{ p = substr($0, 10) } $0 == "branch refs/heads/work/b007" { print p; exit }')"
( cd "$CT7" && sed 's/^status: open$/status: done/' docs/23_backlog/t007.md > t7.tmp && mv t7.tmp docs/23_backlog/t007.md \
    && echo 7 > w007.txt && git add -A \
    && git -c user.email=t@t -c user.name=t commit -qm "work 007" -m "Closes: BACKLOG-007" )
OUT="$(codone 7)" && RC=0 || RC=$?
SUBJ="$(git -C "$COR" log -1 --format=%s main)"
BODY="$(git -C "$COR" log -1 --format=%b main)"
FILES="$(git -C "$COR" show --name-only --format= main | sort | tr '\n' ' ')"
if [ "$SUBJ" = "docs: close-out BACKLOG-007" ] && has "$BODY" "crew done 007 " \
   && [ "$FILES" = "docs/92_audit/LOG.md " ]; then
  ok "close-out: an audit-only close-out is still titled after its ticket, and names its crew done"
else
  bad "close-out: audit-only close-out (subject: $SUBJ · body: $BODY · files: $FILES)"
fi

# No docs_close reachable (a plain terminal, ISSUE-014): nothing was written, so
# nothing is committed — never an empty close-out commit.
coticket 006
( cd "$COR" && scripts/crew new 6 >/dev/null 2>&1 )
cowork 006
mkdir -p "$CO/emptyhome"
OUT="$( (cd "$COR" && env -u CLAUDE_PLUGIN_ROOT -u CREW_DOCS_CLOSE HOME="$CO/emptyhome" scripts/crew done 6) 2>&1 )" || true
if [ "$(git -C "$COR" log -1 --format=%s main)" = "work 006" ] && has "$OUT" "docs_close is not reachable"; then
  ok "close-out: with docs_close unreachable nothing is written and nothing is committed"
else
  bad "close-out: unreachable path (head: $(git -C "$COR" log -1 --format=%s main) · out: $OUT)"
fi

# The chain case, end to end with no hand commit anywhere: this is the run a
# chain session meets on every ticket after the first.
coticket 101
coticket 102 101
( cd "$COR" && scripts/crew new 101 --chain >/dev/null 2>&1 )
cowork 101
OUT1="$(codone 101)"
cowork 102
OUT="$(codone 102)" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && has "$OUT1" "stays busy" && ! has "$OUT" "check 2" \
   && grep -q "^status: done" "$COR/docs/23_backlog/t102.md"; then
  ok "close-out: a chain runs ticket after ticket with no close-out committed by hand"
else
  bad "close-out: chain run (rc=$RC out: $OUT)"
fi

# ---------------------------------------------------------------- a chain is carried by choice (0.41.2)
# Measured 2026-09-24 with three real executor sessions on one 332→333→334
# chain: the two given the chain prompt carried it end to end, but the one given
# the ordinary one-ticket prompt for 332 stopped after `crew done 332` — rightly,
# its prompt put 333 out of scope — and left e1 holding work/b333 with nobody on
# it. The board read `e1 on 333 · processing`, word for word what a live session
# looks like. crew done had handed the tree on because of an after_ref line,
# while whether a session carries the chain is decided by the prompt it got. The
# session now says so once, `crew new <first> --chain`, and without it crew done
# parks exactly as it does for a lone ticket. Known-bad first.
OP="$TMP/optin"
OPR="$OP/repo"
mkdir -p "$OPR/scripts" "$OPR/docs/92_audit"
(
  cd "$OPR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  printf '# audit log\n' > docs/92_audit/LOG.md
  printf '{"owns": [], "crew": {"dev_branch": "main", "copy": [], "link": []}}\n' > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init >/dev/null
)
opticket() { # opticket <nnn> <after nnn|-> — a Backlog item, committed
  mkdir -p "$OPR/docs/23_backlog"
  printf -- '---\nid: BACKLOG-%s\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: open\n' "$1" \
    > "$OPR/docs/23_backlog/t$1.md"
  [ "$2" = "-" ] || printf 'after_ref: BACKLOG-%s\n' "$2" >> "$OPR/docs/23_backlog/t$1.md"
  printf -- '---\n' >> "$OPR/docs/23_backlog/t$1.md"
  ( cd "$OPR" && git add -A && git commit -qm "ticket $1" >/dev/null )
}
opcrew() { (cd "$OPR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew "$@") 2>&1; }
opin() { # opin <e<k>> <crew args…> — crew run from inside that executor tree
  opin_e="$1"; shift
  (cd "$OP/repo-$opin_e" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" "$OPR/scripts/crew" "$@") 2>&1
}
opwork() { # opwork <e<k>> <nnn> — the ticket's work, committed with its closer
  ( cd "$OP/repo-$1" && echo "$2" >> routes.txt && git add -A \
      && git -c user.email=t@t -c user.name=t commit -qm "work $2" -m "Closes: BACKLOG-$2" )
}
ophead() { git -C "$OP/repo-$1" symbolic-ref --short HEAD 2>/dev/null; }
opticket 101 -
opticket 102 101
opticket 103 102
opticket 104 103
opticket 900 -
( cd "$OPR" && scripts/crew executor add >/dev/null 2>&1 )

# The one-ticket session of the measurement: 101 opened without --chain.
OUT="$(opcrew new 101)" || bad "chain-optin: crew new 101 failed: $OUT"
has "$OUT" "without --chain" \
  && ok "chain-optin: crew new without --chain says crew done will park, not hand on" \
  || bad "chain-optin: crew new 101 note (out: $OUT)"
has "$(opcrew status)" "e1 on 101 (this ticket only)" \
  && ok "chain-optin: the board marks a chain ticket whose session does not carry the chain" \
  || bad "chain-optin: board holder mark (got: $(opcrew status))"
OUT="$(opcrew new 102)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "[new:after]" && has "$OUT" "for that ticket alone"; then
  ok "chain-optin: a refused next ticket is not promised to a session that will not open it"
else
  bad "chain-optin: in-flight refusal (rc=$RC out: $OUT)"
fi

# KNOWN-BAD: before 0.41.2 this handed e1 to work/b102, and nobody was on it.
opwork e1 101
OUT="$(opcrew done 101)" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && [ -z "$(ophead e1)" ] && has "$OUT" "[done:alone]"; then
  ok "chain-optin: crew done parks a tree whose session was not given the chain, tagged [done:alone]"
else
  bad "chain-optin: uncarried handoff (rc=$RC e1=$(ophead e1) out: $OUT)"
fi
has "$OUT" "scripts/crew new 102 --chain" \
  && ok "chain-optin: the park names the command that carries the rest of the chain" \
  || bad "chain-optin: no --chain command in the park note (out: $OUT)"
has "$(opcrew status)" "← no session carries this chain — next: scripts/crew new 102 --chain" \
  && ok "chain-optin: the board's arrow asks for --chain while more than one ticket is left" \
  || bad "chain-optin: board arrow (got: $(opcrew status))"

# The chain session: 102 opened with --chain, from inside the parked e1.
OUT="$(opin e1 new 102 --chain)" || bad "chain-optin: crew new 102 --chain failed: $OUT"
[ "$(ophead e1)" = "work/b102" ] && has "$OUT" "this session carries it" \
  && ok "chain-optin: crew new --chain says the session carries the chain" \
  || bad "chain-optin: crew new --chain (e1=$(ophead e1) out: $OUT)"
tail -1 "$OP/repo-crew/log.tsv" | grep -q "NEW	e1	BACKLOG-102	.* chain$" \
  && ok "chain-optin: the choice is logged on the NEW line crew done reads it back from" \
  || bad "chain-optin: NEW line (got: $(tail -1 "$OP/repo-crew/log.tsv"))"
opwork e1 102
OUT="$(opcrew done 102)"
[ "$(ophead e1)" = "work/b103" ] \
  && ok "chain-optin: a session given the chain still has its tree handed on" \
  || bad "chain-optin: carried handoff (e1=$(ophead e1) out: $OUT)"
has "$OUT" "chain    : 101→104  landed 101 102 · e1 on 103 · queued 104" \
  && ok "chain-optin: each handoff prints the chain's progress in the board's own words" \
  || bad "chain-optin: progress line (out: $OUT)"
# The flag is given once: the handoff's own NEW line carries it forward.
opwork e1 103
OUT="$(opcrew done 103)"
[ "$(ophead e1)" = "work/b104" ] \
  && ok "chain-optin: carrying passes through a handoff without --chain being given again" \
  || bad "chain-optin: second handoff (e1=$(ophead e1) out: $OUT)"
opwork e1 104
OUT="$(opcrew done 104)"
S102="$(git -C "$OPR" log -1 --format=%h --grep='^Closes: BACKLOG-102' main)"
if [ -z "$(ophead e1)" ] && has "$OUT" "carried  : BACKLOG-102 → BACKLOG-104" \
   && has "$OUT" "BACKLOG-102  $S102" && ! has "$OUT" "BACKLOG-101  "; then
  ok "chain-optin: the chain's last crew done lists what THIS session carried, with each sha"
else
  bad "chain-optin: carried summary (e1=$(ophead e1) out: $OUT)"
fi
ORD="$(printf '%s\n' "$OUT" | awk '/^  BACKLOG-[0-9]+  /{ printf "%s ", $1 }')"
[ "$ORD" = "BACKLOG-102 BACKLOG-103 BACKLOG-104 " ] \
  && ok "chain-optin: the summary lists the carried tickets in the order they ran" \
  || bad "chain-optin: summary order '$ORD'"

# --chain on a ticket nothing runs after changes nothing, and says so.
OUT="$(opcrew new 900 --chain)"
has "$OUT" "--chain changes nothing" \
  && ok "chain-optin: --chain on a lone ticket says it changes nothing" \
  || bad "chain-optin: lone --chain (out: $OUT)"

# ---------------------------------------------------------------- a closer that skipped its branch (0.42.2)
# Measured 2026-09-24, twice, with a real executor session (Haiku): it ran
# `crew new 332` and got e1 on work/b332, then committed the ticket's work —
# trailer and all — straight onto main in the MAIN tree, redid it in e1 and ran
# `crew done 332`. Nothing said a word: check 2 sees only uncommitted files,
# log.tsv got `SIZE declared=1 actual=0`, and from the moment of the stray commit
# the board read e1 as `finishing` while e1 had no commit at all. The signature
# is a commit carrying the ticket's closer that is not on work/b<nnn>'s own
# (first-parent) line. Known-bad first.
BP="$TMP/bypass"
BPR="$BP/repo"
mkdir -p "$BPR/scripts" "$BPR/docs/92_audit"
(
  cd "$BPR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  printf '# audit log\n' > docs/92_audit/LOG.md
  # The test fails while the flag file exists, so a crew done can be made to die
  # AFTER it has merged the dev branch into the work branch.
  printf '{"owns": [], "crew": {"dev_branch": "main", "copy": [], "link": [], "test_cmd": "test ! -f %s/redtest"}}\n' "$BP" > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init >/dev/null
)
bpticket() { # bpticket <nnn> — a Backlog item, committed
  mkdir -p "$BPR/docs/23_backlog"
  printf -- '---\nid: BACKLOG-%s\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: open\nscope_files: 1\n---\n' "$1" \
    > "$BPR/docs/23_backlog/t$1.md"
  ( cd "$BPR" && git add -A && git commit -qm "ticket $1" >/dev/null )
}
bpcrew() { (cd "$BPR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew "$@") 2>&1; }
bpcommit() { # bpcommit <dir> <nnn> — the ticket's work with its closer, committed in <dir>
  # Same file, same content in both trees, as measured — but the message names the
  # tree: two commits with one tree, one parent, one author and one second ARE one
  # commit to git, and the stray one would vanish into the executor's own.
  ( cd "$1" && echo "$2" >> "w$2.txt" && git add "w$2.txt" \
      && git -c user.email=t@t -c user.name=t commit -qm "work $2" -m "in $(basename "$1")" -m "Closes: BACKLOG-$2" )
}
bprow() { bpcrew status | awk -v e="$1" '$1 == e'; }
bpticket 001
bpticket 002
bpticket 005
bpticket 100
( cd "$BPR" && scripts/crew executor add >/dev/null 2>&1 )

# KNOWN-BAD, the measured shape: e1 holds 001, the work lands on main from the main tree.
bpcrew new 1 >/dev/null
bpcommit "$BPR" 001
STRAY="$(git -C "$BPR" rev-parse --short HEAD)"
ROW="$(bprow e1)"
if has "$ROW" "processing" && has "$ROW" "bypass=$STRAY"; then
  ok "bypass: the board stops reading a tree with no commit as finishing, and names the stray closer"
else
  bad "bypass: board row after a main-tree closer (got: $ROW)"
fi
OUT="$( (cd "$BP/repo-e1" && "$BPR/scripts/crew" name executor --want) 2>&1 )"
has "$OUT" "b001 · i001 · e1 · processing" \
  && ok "bypass: the title agrees with the board — the tree's own work is not done" \
  || bad "bypass: title after a main-tree closer (got: $OUT)"

# The session redoes the work in e1, as measured. First run dies on a red test
# AFTER merging main into work/b001; the stray closer is then a second parent of
# the branch, and a range test (work/b001..main) would read clean on the rerun.
bpcommit "$BP/repo-e1" 001
: > "$BP/redtest"
OUT="$(bpcrew done 1)" && RC=0 || RC=$?
[ "$RC" -ne 0 ] && has "$OUT" "tests failed" \
  || bad "bypass: the red-test run did not die where it should (rc=$RC out: $OUT)"
rm -f "$BP/redtest"
OUT="$(bpcrew done 1)" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && has "$OUT" "[done:bypass]" && has "$OUT" "$STRAY"; then
  ok "bypass: crew done names the closer that skipped the branch, tagged [done:bypass], even on a rerun"
else
  bad "bypass: crew done rerun (rc=$RC out: $OUT)"
fi
grep -q "^status: done" "$BPR/docs/23_backlog/t001.md" \
  && ok "bypass: the ticket still lands and closes out — the stray commit is already on the shared branch" \
  || bad "bypass: the ticket did not close out"
grep -q "BYPASS	-	BACKLOG-001	$STRAY" "$BP/repo-crew/log.tsv" \
  && ok "bypass: the stray closer is logged as a BYPASS line" \
  || bad "bypass: no BYPASS line (log: $(grep BACKLOG-001 "$BP/repo-crew/log.tsv" | tr '\n' '|'))"

# Silent where nothing skipped the branch: the executor merges main into its own
# branch by hand (legitimate), and main already holds 001's stray closer.
bpcrew new 2 >/dev/null
( cd "$BP/repo-e1" && git -c user.email=t@t -c user.name=t merge -q --no-edit main >/dev/null 2>&1 )
bpcommit "$BP/repo-e1" 002
ROW="$(bprow e1)"
OUT="$(bpcrew done 2)" && RC=0 || RC=$?
if ! has "$ROW" "bypass=" && [ "$RC" -eq 0 ] && ! has "$OUT" "[done:bypass]"; then
  ok "bypass: a ticket whose closer was made on its own branch never reads as a bypass"
else
  bad "bypass: false positive (row: $ROW · out: $OUT)"
fi
# A four-digit id is not a three-digit one: BACKLOG-1000 on main is not 100's.
bpcrew new 100 >/dev/null
( cd "$BPR" && echo x > w1000.txt && git add w1000.txt \
    && git -c user.email=t@t -c user.name=t commit -qm "work 1000" -m "Closes: BACKLOG-1000" )
has "$(bprow e1)" "bypass=" \
  && bad "bypass: BACKLOG-1000's closer was read as BACKLOG-100's (row: $(bprow e1))" \
  || ok "bypass: a closer for BACKLOG-1000 is not read as one for BACKLOG-100"
bpcommit "$BP/repo-e1" 100
bpcrew done 100 >/dev/null

# The carrying session's summary rows carry the flag into the chain report.
bpcrew new 5 --chain >/dev/null
bpcommit "$BPR" 005
STRAY5="$(git -C "$BPR" rev-parse --short HEAD)"
bpcommit "$BP/repo-e1" 005
OUT="$(bpcrew done 5)"
printf '%s\n' "$OUT" | grep -q "^  BACKLOG-005  .*bypass=$STRAY5" \
  && ok "bypass: the carried summary row names the stray closer, so the final report does" \
  || bad "bypass: summary row (out: $OUT)"

# ---------------------------------------------------------------- the check question guides (0.42.3)
# The owner, 2026-09-25: the check question is asked with AskUserQuestion and
# leads the reader to the right answer instead of setting a puzzle, and the
# explanation file carries the answer, shown only on a click. In the session
# that asked, two check questions typed at the end of the chat were both left
# unanswered. Known-bad first: the template had no check card at all.
EXT="$KIT/skills/explain/template.html"
CHK="$(awk '/<section class="card check">/,/<\/section>/' "$EXT")"
if has "$CHK" "<details" && has "$CHK" "<summary>"; then
  ok "explain: the template ends with a check card whose answer folds under a click"
else
  bad "explain: no folded check card in template.html"
fi
OPEN="$(printf '%s\n' "$CHK" | awk '/<details/ { exit } { print }')"
if [ -n "$CHK" ] && ! has "$OPEN" "[The right answer"; then
  ok "explain: the answer sits inside the fold, never beside the question"
else
  bad "explain: the check card shows its answer before the fold"
fi
S3="$(awk '/^## Step 3/,0' "$KIT/skills/explain/SKILL.md")"
if has "$S3" "AskUserQuestion" && has "$S3" "Not sure" && has "$S3" "one to three"; then
  ok "explain: step 3 asks one to three questions with AskUserQuestion, each with a way back to the page"
else
  bad "explain: step 3 does not name AskUserQuestion, one to three questions and a not-sure option"
fi
# The owner, same day: the answer says where a reader goes wrong and why, not
# only which option was right.
FOLD="$(printf '%s\n' "$CHK" | awk '/<details/,/<\/details>/')"
if has "$FOLD" "goes wrong" && has "$S3" "goes wrong"; then
  ok "explain: the folded answer names where a reader goes wrong, and why"
else
  bad "explain: the folded answer gives the right option only"
fi

# ---------------------------------------------------------------- quiet gates, fresh index (0.42.4)
# Two things a crew done left behind, both measured 2026-09-26 on real executor
# sessions. Its gates streamed the repo's own output: one green run put 10,539
# characters of passing tests above the line that decided it, and executors took
# to piping crew done through `tail -40`, which drops crew's own notes too. And
# its close-out committed the ticket's status and audit line but left
# docs/INDEX.md and docs/MAP.tsv describing the tree before them: 8 of 50
# "Re-run docs_render.sh" reminders ended the session unrendered, and a render in
# the shared main tree would have left files that check 2 refuses the next merge on.
QG="$TMP/quiet"
QGR="$QG/repo"
mkdir -p "$QGR/scripts" "$QGR/docs/92_audit" "$QGR/docs/23_backlog"
# A runner shaped like node --test: a line per case, then its counts. Red when
# $QG/red exists, with the failing case near the end, where runners put it.
cat > "$QG/run-tests.sh" <<QEOF
i=1; while [ \$i -le 300 ]; do echo "✔ case \$i passes"; i=\$((i + 1)); done
if [ -f "$QG/red" ]; then echo "✖ case 301 failed: expected 1, got 2"; echo "ℹ tests 301"; echo "ℹ fail 1"; exit 1; fi
echo "ℹ tests 300"; echo "ℹ pass 300"; echo "ℹ fail 0"
QEOF
(
  cd "$QGR"
  git init -q && git checkout -q -b main
  git config user.email t@t && git config user.name t
  printf '# audit log\n' > docs/92_audit/LOG.md
  printf '{"owns": [], "crew": {"dev_branch": "main", "copy": [], "link": [], "test_cmd": "bash %s/run-tests.sh", "typecheck_cmd": "echo typecheck-noise", "setup_cmd": "i=0; while [ $i -lt 200 ]; do echo setup-noise-$i; i=$((i + 1)); done"}}\n' "$QG" > .docs-kit.json
  cp "$KIT/templates/crew/crew" scripts/crew && chmod +x scripts/crew
  git add -A && git commit -qm init >/dev/null
)
qticket() { # qticket <nnn> — a Backlog doc, then a render, both committed
  printf -- '---\nid: BACKLOG-%s\ndescription: "x"\nsource_ref: ISSUE-001\nstatus: open\n---\n' "$1" \
    > "$QGR/docs/23_backlog/t$1.md"
  ( cd "$QGR" && python3 "$KIT/scripts/docs_render.py" . >/dev/null 2>&1 \
      && git add -A && git commit -qm "ticket $1" >/dev/null )
}
qwork() { # qwork <nnn> — the ticket's work, with its closer, in the tree holding it
  QT="$(git -C "$QGR" worktree list --porcelain | awk -v b="branch refs/heads/work/b$1" '
    /^worktree /{ p = substr($0, 10) } $0 == b { print p; exit }')"
  [ -n "$QT" ] || { echo "qwork: no tree holds work/b$1" >&2; return 1; }
  ( cd "$QT" && echo "$1" >> "w$1.txt" && git add -A \
      && git -c user.email=t@t -c user.name=t commit -qm "work $1" -m "Closes: BACKLOG-$1" )
}
qdone() { (cd "$QGR" && CREW_DOCS_CLOSE="$KIT/scripts/docs_close.sh" scripts/crew done "$@") 2>&1; }
qticket 001
qticket 002
OUT="$( (cd "$QGR" && scripts/crew executor add) 2>&1 )"
QLOG="$QG/repo-crew/logs"
if ! has "$OUT" "setup-noise-0" && has "$OUT" "setup_cmd passed" \
   && grep -q "setup-noise-199" "$QLOG/setup-repo-e1.log" 2>/dev/null; then
  ok "quiet: setup_cmd's output goes to its log, and the terminal gets one line for it"
else
  bad "quiet: setup_cmd output (out: $OUT)"
fi
( cd "$QGR" && scripts/crew new 1 >/dev/null 2>&1 )
qwork 001
OUT="$(qdone 1)" && RC=0 || RC=$?
if [ "$RC" -eq 0 ] && ! has "$OUT" "case 1 passes" && ! has "$OUT" "typecheck-noise" \
   && has "$OUT" "ℹ pass 300" && has "$OUT" "b001-test.log"; then
  ok "quiet: a green crew done shows the runner's counts and the log path, not every passing case"
else
  bad "quiet: green crew done output (rc=$RC out: $OUT)"
fi
[ "$(grep -c 'passes$' "$QLOG/b001-test.log" 2>/dev/null)" = "300" ] \
  && ok "quiet: the log keeps the whole run" \
  || bad "quiet: the test log is missing or cut short"
# The index half. --check is the gate STANDARD §10 names for "does the index
# match the markdown"; on 0.42.3 it said stale here, because the close-out
# flipped t001.md to done and nothing rewrote INDEX.md.
OUT="$(python3 "$KIT/scripts/docs_render.py" --check "$QGR" 2>&1)" && RC=0 || RC=$?
FILES="$(git -C "$QGR" show --name-only --format= main | sort | tr '\n' ' ')"
if [ "$RC" -eq 0 ] && [ "$FILES" = "docs/23_backlog/t001.md docs/92_audit/LOG.md docs/INDEX.md " ]; then
  ok "fresh index: the close-out commit carries the regenerated INDEX.md, and --check agrees with it"
else
  bad "fresh index: after crew done (check rc=$RC: $OUT · close-out files: $FILES)"
fi
[ -z "$(git -C "$QGR" status --porcelain)" ] \
  && ok "fresh index: nothing is left in the main tree for check 2 to refuse" \
  || bad "fresh index: main tree left dirty: $(git -C "$QGR" status --porcelain | tr '\n' ' ')"
# KNOWN-BAD for the gates: a red run must still show what failed and where the
# rest is, without the three hundred lines that passed.
( cd "$QGR" && scripts/crew new 2 >/dev/null 2>&1 )
qwork 002
: > "$QG/red"
OUT="$(qdone 2)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "tests failed in" && has "$OUT" "✖ case 301 failed" \
   && has "$OUT" "b002-test.log" && ! has "$OUT" "case 1 passes" \
   && [ "$(printf '%s\n' "$OUT" | wc -l | tr -d ' ')" -lt 60 ]; then
  ok "quiet: a red crew done shows the failing lines and the log path, and stops"
else
  bad "quiet: red crew done output (rc=$RC out: $OUT)"
fi
rm -f "$QG/red"

# ---------------------------------------------------------------- a preview config in the main tree (0.42.5)
# The Browser pane reads .claude/launch.json only from the main tree, so an
# executor previewing its own tree adds a config there. Measured 2026-09-26: one
# such edit kept a main tree dirty for over three hours, and another executor's
# crew done waited behind it for 1h33 with the file listed and nothing more.
# Check 2 still refuses (it counts every file); the refusal now says what the
# file is and how to put it back. Ticket 002 is still on e1 from the red run.
mkdir -p "$QGR/.claude"
printf '{"version": "0.0.1", "configurations": [{"name": "app", "runtimeExecutable": "npm", "runtimeArgs": ["run", "dev"], "port": 3000}]}\n' \
  > "$QGR/.claude/launch.json"
( cd "$QGR" && git add .claude/launch.json && git commit -qm "preview config" )
printf '{"version": "0.0.1", "configurations": [{"name": "app", "port": 3000}, {"name": "repo-e1-b002", "runtimeExecutable": "sh", "runtimeArgs": ["-c", "cd ../repo-e1 && npm run dev -- -p 3002"], "port": 3002}]}\n' \
  > "$QGR/.claude/launch.json"
OUT="$(qdone 2)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "check 2: main tree is dirty" && has "$OUT" "[done:preview]" \
   && has "$OUT" "checkout -- .claude/launch.json"; then
  ok "preview: a tracked launch.json edit still stops check 2, and the refusal says what it is and how to put it back"
else
  bad "preview: tracked launch.json at check 2 (rc=$RC out: $OUT)"
fi
git -C "$QGR" checkout -q -- .claude/launch.json
OUT="$(qdone 2)" && RC=0 || RC=$?
[ "$RC" -eq 0 ] \
  && ok "preview: the remedy the refusal prints is enough for the rerun to land" \
  || bad "preview: crew done after putting launch.json back (rc=$RC out: $OUT)"
# The other two shapes. A dirty file that is NOT launch.json must not get the
# tag, or the hint teaches the wrong fix. And a launch.json in a .claude/ git
# has never seen shows up in plain porcelain as `?? .claude/`, name hidden.
( cd "$QGR" && git rm -q -r .claude && git commit -qm "drop preview config" )
qticket 003
( cd "$QGR" && scripts/crew new 3 >/dev/null 2>&1 )
qwork 003
echo "draft" > "$QGR/notes.txt"
OUT="$(qdone 3)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "check 2: main tree is dirty" && ! has "$OUT" "[done:preview]"; then
  ok "preview: any other dirty file is refused without the preview hint"
else
  bad "preview: a non-launch.json dirty file (rc=$RC out: $OUT)"
fi
rm -f "$QGR/notes.txt"
mkdir -p "$QGR/.claude"
printf '{"version": "0.0.1", "configurations": []}\n' > "$QGR/.claude/launch.json"
OUT="$(qdone 3)" && RC=0 || RC=$?
if [ "$RC" -ne 0 ] && has "$OUT" "?? .claude/" && has "$OUT" "[done:preview]" \
   && has "$OUT" "new and untracked"; then
  ok "preview: an untracked launch.json is named even when porcelain shows only its folder"
else
  bad "preview: untracked launch.json at check 2 (rc=$RC out: $OUT)"
fi
rm -rf "$QGR/.claude"

# ---------------------------------------------------------------- summary
echo ""
echo "crew_test: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
