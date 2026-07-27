---
name: triangulated-review
description: Use when planning a substantial code-review pass — post-merge of a feature, pre-release audit, or any moment a single-reviewer pass would feel too low-confidence to trust without verification. Triggers include triangulated review, 삼각 리뷰, parallel review pass.
argument-hint: [scope-hint]
allowed-tools: Bash, Read, Grep
---

# Triangulated Review

Three independent reviewers in parallel → consolidate → fact-check single-reviewer findings → **deliver a confirmed findings report**.

This skill stops at review confidence. It does **not** apply fixes, open tracking issues, commit, or verify quantitative README claims.

This skill is the codified, cost-pruned form of the 5-reviewer pass run on CursorMeter (see #61) — the post-mortem on that pass concluded that 5 lenses were noisy and that fact-check alone replaces a full cross-comment round.

## When to use
- After merging a substantial feature
- Pre-public-release quality/security pass
- Any time you'd otherwise trust a single reviewer blindly

Skip for: trivial PRs, single-file fixes, formatter-only diffs.

## Out of scope

Do **not** do these as part of this skill:

- Applying fixes or rewriting code
- Creating tracking issues / clustering commits
- Running `swift test` (or repo equivalent) as a gate between fix clusters
- A/B measuring memory, latency, binary size, or other release-note claims

If the user asks to apply findings afterward, that is a **separate** follow-up — not this skill's workflow.

## Scope
Read the repo's `CLAUDE.md` first and honor anything explicitly out-of-scope or accepted-as-known-limitation. Default scope = entire `Sources/` + `Tests/` (or repo equivalent) of the current branch. Override with the argument if the user supplied one (e.g. "files changed since v0.2.1").

## Round 1 — parallel dispatch

All three in background via the `Agent` tool with `run_in_background: true`.

| Reviewer | subagent_type | Lens |
|---|---|---|
| `senior` | `senior-tech-mentor` (max effort) | architecture, state machines, lifecycle, real-world failure modes |
| `codex` | `codex:codex-rescue` (`--fresh --effort max`) | framework-level behaviors, security/privacy surface, deep reasoning |
| `simplify` | `general-purpose` | reuse + code quality + efficiency, one combined pass |

Every prompt **must** include:
- "Read `CLAUDE.md` first; skip anything it accepts."
- "**Report HIGH and CRITICAL only. Do not include MEDIUM or nitpicks** — they create consolidation noise."
- Output format: severity → file:line → what's wrong (1 line) → why (1 line) → minimal fix sketch (1 line) → confidence (high/med/low).
- Cap each report at ~400 words.
- End with "if I had two hours, the top three to fix first are…"

Why the MEDIUM exclusion: in the original 5-reviewer run, 22 MEDIUM findings were collected and 0 were ever applied. Pure noise.

## Consolidation

After all three complete:
- Tag each finding by its source reviewer.
- **Consensus (2+ reviewers agree on the same file/area)** → trust without fact-check; mark `confirmed (consensus)`.
- **Single reviewer** → flag for the round-2 fact-check.

Show the user a compact table before proceeding:

```
| Finding | Reviewers | Action |
|---|---|---|
| <one-line summary> | senior + codex | confirmed (consensus) |
| <one-line summary> | codex only | fact-check |
```

## Round 2 — single-reviewer fact-check (one codex call)

Dispatch **one** `codex:codex-rescue --fresh --effort max` agent with all single-reviewer findings batched into the prompt. For each:
- CONFIRMED / REFUTED / PARTIAL
- file:line evidence (one or two lines that prove or disprove)
- severity adjustment if the original is overstated
- minimal fix sketch if confirmed

This catches LLM misreads of call chains and conceptual groupings that don't survive a close read. In the CursorMeter pass: 1 REFUTED + 1 PARTIAL out of 9 single-reviewer findings — the fact-check earned its keep.

**Do not** dispatch a cross-comment round between reviewers. Over-engineered: fact-check alone was sufficient in practice.

## Deliverable

End with a single confirmed-findings report:

```
| Finding | Severity | Sources | Status | Evidence / fix sketch |
|---|---|---|---|---|
| … | HIGH | senior + codex | confirmed (consensus) | … |
| … | CRITICAL | simplify | confirmed | … |
| … | HIGH | codex | refuted | … |
```

Optional closing lines (no execution):
- Top three to fix first (from consensus + confirmed)
- Explicit note that application, commits, and quantitative claim checks are out of scope

## Cost discipline

Each reviewer reads the whole codebase. Three reviewers ≈ 3× read cost. Resist adding a fourth lens unless it covers ground the existing three definitely miss. Cross-comment rounds compound this — skip them.

## Anti-patterns

- Asking for "all severity levels" → you'll get noise you ignore anyway
- Trusting a single high-confidence reviewer because they sound authoritative → always fact-check single-reviewer claims
- Sliding from review into apply/commit without the user asking → out of scope; stop at the report
- Treating a memory/latency claim in the release notes as "covered by the review" → it isn't; that needs a separate A/B pass outside this skill

## Skill maturity disclosure

This skill was **distilled from a single real session** (CursorMeter #61) rather than the synthetic subagent baseline that `superpowers:writing-skills` mandates as the RED phase. The Iron Law was bent: deployment is the first real test. Each invocation is treated as a delayed RED run — observed rationalizations and loopholes get logged here and the skill refactored.

### Refactor log

| Date | Trigger | Rationalization / loophole observed | Fix applied |
|------|---------|-------------------------------------|-------------|
| 2026-07-19 | Scope creep in skill body | Application + A/B measurement lived in the same skill as review orchestration, pulling agents past the confidence deliverable | Trimmed to review-only: stop at confirmed findings report; apply/issue/commit/A/B explicitly out of scope |

### Open loopholes (untested)

These are paths the original session didn't stress; future invocations should watch for them.

- The "HIGH/CRITICAL only — no MEDIUM" instruction in reviewer prompts has not been verified to actually suppress MEDIUM output in practice. Reviewers may comply, partially comply, or rationalize ("this is HIGH because…").
- Skipping the cross-comment round between reviewers is asserted to be sufficient. Untested on a scenario where fact-check itself returns ambiguous verdicts.
- Agents may still try to "helpfully" start applying confirmed findings after the report — watch for this and refuse unless the user starts a separate apply pass.

Closing a loophole = add a row to the refactor log and tighten the relevant section above.
