---
name: explain
description: "Explain a docs-kit layer-2 document or its chain — an Issue, Backlog item, Proposal, or Decision — or a mechanism this repo runs on, such as a script, a hook, a skill, a command or a config key, to the four-gates standard: at least one drawing, BEFORE/AFTER, trade-offs with numbers, ids as links, level-2 check questions to close. Trigger when the user asks what or why about an ISSUE-/BACKLOG-/PROPOSAL-/DECISION- id, a lane choice, the workflow between them, or how a piece of this repo's own tooling actually works; every other topic waits to be typed explicitly."
arguments: topic
argument-hint: "<điều chưa hiểu — một id, một tệp, một quyết định>"
---

# explain — the gate-1 explanation, on demand

The problem this skill exists for: a user nods at a decision they have not
understood, and that nod looks identical to an informed nod — even to them.
Your job is to explain ONE thing well enough that the nod means something.

This is a **deliberate exception to "keep answers short"**: brevity applies to
reports, never to the explanation standing before a decision. There, the more
visual the better, and bare prose does not pass.

**Every run of this skill leaves at least one picture on the table.** The two
lanes below differ in how MUCH you draw, never in whether you draw: a reader
who asks "what does this change?" is asking to be shown, and a paragraph that
answers in words has answered a different question.

## Step 0 — Ground the topic

`$ARGUMENTS` names the thing. Before explaining anything:

- If it names ids (`BACKLOG-`, `DECISION-`, `PROPOSAL-`, `ISSUE-`): open
  exactly those documents via `docs/INDEX.md` — never glob whole folders.
- If it names code, a file, or an error: read that code first.
- If it names a mechanism this repo runs on — a script, a hook, a skill, a
  command, a config key: open the file and read the part that answers the
  question, then say where you read it. A mechanism explained from memory is
  how one confident wrong sentence ends up drawn four times; this skill has its
  own case, a claim that the CLI refuses a session name another session holds,
  when it quietly hands out a different name instead.
- If you genuinely cannot tell WHICH thing is meant, ask one short clarifying
  question and stop. Do not explain a guess.

## Step 1 — Pick the depth: the three lane questions (STANDARD §5)

1. Does it touch layer 1 — Architecture, Business logic, an API contract?
2. If it turns out wrong, does reverting cost more than a day?
3. Any irreversible side effect — deleted data, an outside publish, a one-way
   flag, something sent to a person? This one outranks the other two.

All "no" → **shallow form**: one small diagram plus a few sentences — what
shrinks in this lane is the prose, not the drawing — and write the marker line
`LANE: fast — <reason>` at line start so the reader sees which lane you chose
(in a crew repo the explain-gate hook looks for exactly that line in the chat,
or for a drawing: a drawing-tool call, or a picture file sent to render).

Any "yes" → **deep form**, everything below.

## Where the picture goes — both lanes

A drawing counts once the reader has it, and a tool call that returned success
does not prove that: in one reported session the visualize widget answered
"rendered and shown" and the user saw no picture. Pick the surface from what
this session can do, top row first:

| The session has | The surface | The chat carries |
|---|---|---|
| `SendUserFile` (the Claude desktop app's Code tab) | one standalone HTML file: copy `template.html` from this skill's folder into the scratchpad, fill it, send it with `display: "render"`. Every picture, the short prose and the trade-off numbers go in the file | 2–4 lines that lead into the file, then the check questions, asked with AskUserQuestion (Step 3) |
| no file send | the visualize widget, an Artifact page, or a mermaid block | the explanation itself, then the check questions with AskUserQuestion |

The file comes first because readers asked for it by name. In the repo that
reported it, three explanations sent this way were each read, and the check
question after the first was answered right on the first try; the same content
written into the chat was called rambling twice in one session. The widget is
not broken in that app: of 68 widget calls measured on another machine, none
drew a report of a missing picture, and several drew replies about what the
picture showed. It just leaves the prose in the chat, where it scrolls away.

Three rules for the file surface:

- **Ids go in both places.** The file names each id with its one sentence;
  the chat lines carry the clickable links, repo-relative, because a file in
  the scratchpad cannot resolve a repo-relative path.
- **The fast-lane marker stays in the chat.** The hook reads the chat, never
  the file.
- **Believe the reader over the tool result.** A reader who says there is no
  picture is right: move to the next surface in the table instead of drawing
  again on the same one.

## Step 2 — The explanation (deep form)

- **BEFORE vs AFTER, side by side, as a real drawing,** on the surface chosen
  above. A table supplements the drawing, it never replaces it. If every
  surface fails, name WHICH one failed and how, then draw the fallback in a
  fenced ASCII block; a turn that explains a decision and shows no picture has
  not run this skill.
- **Trade-offs cut both ways, each side with its number.** A trade-off
  without a number is an opinion wearing a table.
- **Every id you mention is a clickable link** to its file (repo-relative
  path) plus one sentence saying what it is; several ids → gather the links
  at the TOP of the message. A bare id forces the reader to go digging, and
  nobody remembers hundreds of tickets.
- **The expensive rule — two measurements.** Any number that supports an
  irreversible action needs TWO independent measurements, and the second must
  be one that could prove the number WRONG — a deliberate attempt to break
  it, not another reading of the same gauge. Born from a real case: a count
  of `1`, pasted onto four diagrams, justified a permanent deletion — the
  single record was a marker planted by a startup probe, the true count was
  `0`, and a 5-second query had pointed the other way the whole time. Right
  number, wrong reading, and four good-looking diagrams laundered it. If you
  cannot run the falsifying measurement, say so inside the explanation — a
  labelled hole beats a confident one.

## The three shapes — both lanes, no fourth invented on the spot

The fast lane draws one of these small and the deep lane draws it full size;
neither gets to skip the step. Pick the shape from the question, not from the
topic:

| The question is | The drawing is |
|---|---|
| what changed? | two columns, before on the left, after on the right, one row per change |
| one input, several outcomes | the source at the left, each outcome its own box at the right |
| what happens, in order? | stations stacked downward, with the command that moves between two of them in a box of its own |

Four rules keep them readable, and each is here because breaking it cost a
redraw:

- **Prose lives outside the picture.** Inside: labels only — one claim per box,
  a subtitle of five words or fewer. A paragraph inside a diagram is a paragraph
  nobody reads sitting in a box nobody can scan.
- **Evidence is the real output.** Paste the actual lines a command printed,
  including the ugly ones. A described output and a real one look identical to
  the reader and only one of them can be checked.
- **Colour carries meaning, not sequence.** Neutral for ordinary steps, one
  colour for the outcome that is fine, one for the outcome that needs a human.
  Three families is the ceiling; a rainbow encodes nothing.
- **One picture answers one question.** A second question earns a second
  picture, never a second panel bolted onto the first.

## Step 3 — Close with one to three level-2 check questions, asked with AskUserQuestion

Each check question can only be answered correctly by someone holding the
model. Not "does this make sense?" — level 0 catches nobody, a real nod and a
polite nod look identical. Not "can you repeat it back?" — level 1 catches only
the reader, while the usual error belongs to the drawer. A good level-2
question makes the reader RUN the model ("if X happened here, what breaks
first?"), and a wrong answer teaches you which part to redraw.

**How many: one to three, one per core change.** A question is about one change
the explanation carries, to the workflow or to the code, and the most
important change is asked first. One change gets one question; an explanation
that carries several gets up to three, picked by importance, and never a
fourth, which tests stamina rather than the model. Stay on the core of the
explanation: a question about a side detail confirms nothing the decision
rests on. The owner's rule, 2026-09-25, after a single question left two of an
explanation's three main changes unchecked.

**Ask them with AskUserQuestion, and make them guide, not trap.** The owner's
rule of the same day, after two check questions typed at the end of the chat
in one session were both left unanswered: the questions go in ONE
AskUserQuestion call (it takes up to four), the reader answers each with one
click, and their job is to find what the drawing failed to carry, not to grade
the reader.

- **The options are real readings of the model**: the right one, and one or
  two misreadings the drawing could actually produce. No near-identical
  wording, no "all of the above", nothing marked recommended, and the right
  answer is not always first.
- **Each question has a "Not sure" option**, written in the reader's language,
  whose description names the section to re-read: "re-read ② in the page, then
  open the answer at the bottom".
- **Each question text ends with the same pointer**, so a reader who is unsure
  knows where to look before choosing.
- **The file carries every answer, folded.** `template.html` ends with one card
  per question: the question word for word, where to look, and inside
  `<details>`, shown only on a click, the answer with why and the section that
  shows it. An Artifact page or the widget folds them the same way; a mermaid
  block cannot, so there the answers come in the reply.
- **An answer says where a reader goes wrong, and why.** For every wrong
  option: the reading behind it, why that reading is tempting, and the fact in
  the explanation that rules it out. A reader who picked it learns what to
  unlearn, which a bare "B is right" never teaches.

The replies decide what happens next. A right answer is confirmed in one
sentence that says why. A wrong answer is met with where it goes wrong and
why, the section is redrawn, and that question is asked once more. "Not
sure", silence, or a vague answer under "Other" reads as NOT understood:
re-explain that section more simply. Gate 2 closes only when every question is
answered right; never move on to offering choices past an open one. If a
decision follows, record WHICH level the confirmation reached and what each
answer was (a "confirmed" that was really level 0 makes the decision harder to
challenge later than no record at all), and only then present the options —
gate 3, a separate AskUserQuestion call, never earlier, and the gates do not
merge.
