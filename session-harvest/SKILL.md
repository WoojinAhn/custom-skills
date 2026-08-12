---
name: session-harvest
description: Use when a work session is wrapping up — the user says "세션 마무리", "챙길 거 있나", "얻어낼 거 뽑아줘", "harvest", or a major deliverable just shipped and the session will close soon. Extracts durable value (tooling issues, docs, memory) and flags leftovers before context is lost.
---

# Session Harvest

## Overview

Before a session closes, sweep it once for durable value. **The gate decides, not the
request wording**: "최대한 다 뽑아줘" means sweep every lane, NOT lower the bar.
0건 also counts as a valid result — report skips explicitly.

## The Effectiveness Gate (실효성 게이트)

Before creating or keeping anything (an issue, a doc section, a memory), check all
three — failing any one means don't do it:

1. **흡수 (absorption)** — is it already implemented or superseded? Compare against
   the *current* state, not your memory of it.
2. **근거 (evidence)** — is the demand demonstrated *now*? Only real occurrences
   count as signal; speculation and "it might help later" do not.
3. **사용패턴 (usage pattern)** — is it valid under how things are *actually* used
   today?

Record the verdict where the artifact lives. A fail means discard, not backlog —
revive with evidence if the demand recurs.

## Two-Phase Flow: Propose, Then Execute

The harvest is two separate phases. Phase 1 produces a proposal list; Phase 2 runs
only on the approved subset.

**Phase 1 — Harvest & propose (read-only).** Sweep the four lanes, apply the
effectiveness gate, dup-check trackers, open docs to verify staleness. Then present
one numbered candidate list: per item, the lane, the destination (issue/doc/memory/
deletion target), and a one-line rationale — plus the 의도적 스킵 list. Inspection is
fine in this phase; creating issues, editing docs/CLAUDE.md, saving memories, and
deleting files are not.

**Approval.** Ask which items to run (AskUserQuestion with multiSelect when
available, otherwise a numbered list and wait). The user may approve all, a subset,
or none — "none" is a valid harvest outcome.

**Phase 2 — Execute.** Apply exactly the approved items, then report per the Output
Shape below. Unapproved items are dropped, not queued.

## The Four Lanes

Sweep each lane; for every candidate apply the effectiveness gate and the memory
test ("would a wrong decision happen without it?").

| Lane | Candidate | Destination |
|---|---|---|
| ① Tooling (CLI/MCP/skill) | Friction hit **repeatedly this session** or corroborated by others | Issue tracker (GitHub Issues, Jira, …) — **dup-check first**; duplicate → bump/comment, not new |
| ② Project context | Knowledge not derivable from code; broken/missing CLAUDE.md sections | CLAUDE.md / docs/*.md in the repo |
| ③ Memory | User corrections (esp. repeated), workflow conventions verified this session | memory file + MEMORY.md index line |
| ④ Hygiene (report, don't silently fix) | Credentials/tokens in artifacts, broken leftover files, stashes, temp dirs | Tell the user; delete only your own scratch |

## Staleness Sweep (most-missed step)

**Your own changes rot nearby docs the same day.** For each thing you changed this
session, ask: which existing doc/memory/CLAUDE.md *describes* that behavior? Open
those specific files and fix contradictions NOW.

- This is NOT scope creep — it is closing damage your session created.
- Scope creep would be reading/summarizing docs *unrelated* to your changes. Don't.

## Anti-Forcing Rules

- **Repo-derivable facts never become memories** (build tool, file locations, code
  structure) — the repo already records them. Under "maximize" pressure this is the
  first rule agents break.
- A fact absorbed into a doc this session does not ALSO get a memory.
- One-off friction you self-resolved in seconds: skip, and say so.
- No invented follow-up work (backfill tickets, retros for trivia) — demand must be
  실증, not "이왕 하는 김에".

## Output Shape

After Phase 2: per lane, what was done (with file/issue refs) → then the **"의도적
스킵" list with one-line reasons** (gate-fails and user-rejected items alike). Skips
are deliverables, not omissions.
