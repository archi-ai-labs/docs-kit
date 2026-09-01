# Design notes

`STANDARD.md` says what the model **is**. `CHANGELOG.md` says what **changed** and why.
Neither has a place for the third thing: reasoning that shaped the standard and
deliberately did not become code — a limitation we accepted, or a road we measured and
did not take.

That reasoning is the most expensive kind to reproduce and the easiest to lose. It lived
in a gitignored proposal until 0.23.0; this file is where it lives now. Two sections:
what the model still cannot do, and why documentation is text in git rather than rows in
a database.

Paths here are cited by **check name or function name**, never by line number — a design
note that names a line is a doc with an anchor nothing validates, which is the exact
failure mode the rest of this repo exists to prevent.

---

## 1. Where the cost actually is

Split the lifetime cost of a docs set into four. This table is the finding that reordered
the entire 0.18–0.23 series:

| Cost | Incurred | Scales with docs size | Addressed |
|---|---|---|---|
| **Write** — authoring an Issue / Decision / Backlog item | per change | no | not needed |
| **Read** — an agent consulting docs to do work | per session | **yes** | `INDEX.md`, `_archive/`, `rejected:`, per-service architecture |
| **Verify** — is the doc still true of the code | per session that changes code | **yes** | `[anchor]`, `NOTE [stale]`, `--check-api` |
| **Repair** — fixing what drifted | per drift found | yes | **partially** — only the generated half |

The original proposal contained items A–F, every one of which optimised **Read**. Read is
the cheap half. Verify and Repair dominate, because they recur on every session that
touches code, and at the time both were handled by a single non-deterministic step: Step 5
of `skills/docs-sync/SKILL.md` has an LLM re-read Architecture and compare it against the
session diff. That step is expensive, only runs when someone remembers, and *reports*
rather than blocks — and a false positive there costs a whole session spent on a document
that never drifted.

Items G (deterministic anchors) and H (generated half / intent half) were added because of
this table, and G was ranked second overall. The lesson generalises past this repo: **an
optimisation that only touches the cost you can see is not obviously net positive.**

Repair is still only half-addressed, and that is deliberate. H removes the volatile content
from the document entirely — an endpoint list is regenerated, never repaired. What remains
is prose about intent, and nothing can repair that automatically, because nothing can tell
whether a sentence about a component is still true.

---

## 2. Limitations that survive 0.23.0

Recorded so they are chosen rather than discovered.

1. **The validator checks form, not truth.** `STANDARD.md` says so outright and nothing has
   changed it. A fully valid Architecture document can describe a system that does not
   exist. `[anchor]` narrows this — it catches a file that *moved* — but not a wrong
   sentence about a file that is still there.

2. **The most valuable sentence in the model is the one nothing can check.** `docs-init`
   demands a component description stating *what it is*, written after reading the source.
   That is the highest-value fact in Layer 1, it drifts silently, and no anchor detects it:
   the path still existing says nothing about whether the sentence is still true. Every
   deterministic check in this repo is a check on the *scaffolding around* that sentence.

3. **Nothing handles deletion.** When a service is retired, its Architecture document, its
   API document and its tables all need removing. Layer 1 changes only through a Decision,
   and a Decision can approve the removal — but no step in the model performs it, and no
   check notices it was skipped. Dead documents are worse than absent ones. This is the
   sharpest remaining gap, and it got sharper in 0.23.0: `owns` **shrinking** is not
   detectable either, for the same reason (see 5).

4. **Cross-service edge ownership is a rule, tested once.** "Caller owns the edge, callee
   owns the contract" resolves the duplication that splitting Architecture would otherwise
   create. It has been exercised against exactly one real multi-deployable repo. One repo
   is evidence; it is not a sample.

5. **Only the growth direction of `owns` is checked.** A repo that grows a `[db]` component
   without declaring `data` gets `NOTE [profile]`. A repo that declares `screens` and no
   longer has any cannot be told apart from one where nobody has written the screens down
   yet — so guessing there would cry wolf, and we do not guess. The consequence is that
   `owns` decays in one direction only, silently.

6. **Two repos on the same version can have different trees.** This is the price of item F,
   paid knowingly. Only `.docs-kit.json` explains the difference, and `owns` is
   user-declared, so a mis-declaration produces a tree that is wrong in a way nothing can
   detect — a missing folder looks exactly like a folder the profile never wanted. The
   mitigations are that the branch is opt-in (no `owns` → all 17 folders, the pre-0.23
   behaviour), an unknown token is refused rather than ignored, and `--sync` never shrinks
   a tree. None of that helps a plausible-but-wrong declaration.

7. **`04_api` will drift harder than anything else in the model.** API contracts change more
   often than architecture does. Behind a Decision gate, either people route around the gate
   or the gate becomes a rubber stamp — both are failure modes. H is the mitigation: the
   endpoint list is generated, so only the intent half sits behind the gate. Whether that is
   *sufficient* is still unknown; the evidence is one repo where `--check-api` matched 13/13
   real operations.

8. **The figure budgets cap "complete".** 20 nodes / 32 edges per figure. In a 40-service
   system, splitting per service means the whole is never visible in one picture. The
   requirement "visual and complete" is therefore met at the service level and not at the
   system level. A cross-repo aggregate view would fix it and does not exist.

---

## 3. Storage — markdown, or SQLite once it grows

**Verdict: markdown stays the source of truth. SQLite only as a derived, gitignored cache.**
Three reasons, in order of weight.

### 3.1 Git *is* the version-synchronisation mechanism

A documentation change committed **in the same commit as the code change** is the only thing
that binds the two to one version. That is what "synchronised to a specific version" means
operationally, and it is a property of text in git, not of a database.

A SQLite file in git is a binary blob: no diff, no blame, no reviewable change in a pull
request, and a merge conflict that cannot be resolved without a custom merge driver.

The hard evidence is inside this repo. The `[audit-append]` check in
`scripts/docs_validate.sh` enforces append-only audit logs by diffing the log **line by line
against `git HEAD`**. That check cannot exist over a binary blob. The model already contains
a structural invariant that requires text in git.

### 3.2 The scale argument does not hold — the read pattern was the problem, not the format

Estimated from file shape (a Layer 2 document is ~25 lines ≈ 300 tokens; an index line
≈ 15 tokens):

| Read pattern | Cost at N Layer 2 documents | Exceeds a 30k-token budget at |
|---|---|---|
| glob the folder (pre-0.18) | ~300 × N | **N ≈ 100** |
| `INDEX.md` | ~15 × N | **N ≈ 2 000** |
| SQL query | only matching rows | effectively never |

At five records a week, N = 2 000 is roughly seven to eight years. Markdown was not failing
at scale; it was being read in the worst possible way. Fixing the read pattern moved the
ceiling out ~20×, far enough that scale stopped being a reason to change stores.

### 3.3 SQLite optimises the cheap half too

Layer 2 is relational records — SQL genuinely wins there. But the dominant read cost is
**Layer 1: prose an agent must actually read to write correct code.** That cannot be indexed
or partially queried; the content *is* the answer. SQLite lowers that floor by nothing. It
is section 1's mistake in a different costume.

And `INDEX.md` is already a materialised view. Every common query can become its own
generated index — `load_docs()` in `scripts/docs_render.py` loads the whole model into
memory as it is.

### 3.4 The middle path, if query power is ever wanted

Have `docs_render.py` also emit `docs/.cache/docs.sqlite`, gitignored, rebuilt from markdown
on every render. Tooling gets SQL; no second source of truth is created; the marginal cost is
near zero because the data is already in memory. Python 3.9 ships `sqlite3` in the standard
library, so the portability floor (bash 3.2 / BSD awk / python 3.9) is unaffected.

### 3.5 What would change this verdict

Stated now, so the decision can be revisited on evidence rather than on feel:

- Layer 2 passes ~2 000 documents **and** `INDEX.md` is measurably the bottleneck;
- or the docs stop being edited by humans and by agents in a working tree — at which point
  the git properties in 3.1 are no longer being used, and their cost has no return.
