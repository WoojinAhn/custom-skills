---
name: triangulated-review
description: Use when planning a substantial code-review pass — post-merge of a feature, pre-release audit, or any moment a single-reviewer pass would feel too low-confidence to trust without verification.
argument-hint: [scope-hint]
allowed-tools: Bash, Read, Grep
---

# Triangulated Review

Three independent reviewers in parallel → consolidate → fact-check single-reviewer findings → apply in clusters.

This skill is the codified, cost-pruned form of the 5-reviewer pass run on CursorMeter (see #61) — the post-mortem on that pass concluded that 5 lenses were noisy and that fact-check alone replaces a full cross-comment round.

## When to use
- After merging a substantial feature
- Pre-public-release quality/security pass
- Any time you'd otherwise trust a single reviewer blindly

Skip for: trivial PRs, single-file fixes, formatter-only diffs.

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
- **Consensus (2+ reviewers agree on the same file/area)** → trust without fact-check, apply.
- **Single reviewer** → flag for the round-2 fact-check.

Show the user a compact table before proceeding:

```
| Finding | Reviewers | Action |
|---|---|---|
| <one-line summary> | senior + codex | apply (consensus) |
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

## Application

Create one tracking issue listing all confirmed findings, with severity and source.

Apply in clusters by topic, **one commit per cluster**:

| Cluster type | Risk | Notes |
|---|---|---|
| Mechanical (enum extraction, guard inserts, formatter cache) | low | batch OK |
| State-machine (cache reset, observer split, retry logic) | medium | separate cluster; tests must cover the changed transitions |
| UI / framework workarounds (NSPopover, NSStackView, layout) | high | separate cluster; **manual smoke test mandatory** before commit |

Run `swift test` (or repo equivalent) between clusters. A failing cluster doesn't block the next one — drop it, file as remaining work, continue.

## Quantitative-claim verification — separate step

The review itself does **not** verify README/release-notes claims of memory footprint, latency, binary size, etc. Run a separate A/B step:

1. `gh release download <prev-tag>`
2. Launch the previous artifact, measure
3. Launch the current build, measure
4. If the regression exceeds measurement noise, file a separate issue and update the docs honestly before publishing

Reference: `~/home/CLAUDE.md § Measurable README claims`.

## Cost discipline

Each reviewer reads the whole codebase. Three reviewers ≈ 3× read cost. Resist adding a fourth lens unless it covers ground the existing three definitely miss. Cross-comment rounds compound this — skip them.

## Anti-patterns

- Asking for "all severity levels" → you'll get noise you ignore anyway
- Trusting a single high-confidence reviewer because they sound authoritative → always fact-check single-reviewer claims
- Applying without clustering → one giant commit makes bisecting impossible
- Treating a memory/latency claim in the release notes as "covered by the review" → it isn't; A/B against the previous release zip

## Skill maturity disclosure

This skill was **distilled from a single real session** (CursorMeter #61) rather than the synthetic subagent baseline that `superpowers:writing-skills` mandates as the RED phase. The Iron Law was bent: deployment is the first real test. Each invocation is treated as a delayed RED run — observed rationalizations and loopholes get logged here and the skill refactored.

### Refactor log

| Date | Trigger | Rationalization / loophole observed | Fix applied |
|------|---------|-------------------------------------|-------------|
| _(empty — first real invocation will populate)_ |  |  |  |

### Open loopholes (untested)

These are paths the original session didn't stress; future invocations should watch for them.

- The "HIGH/CRITICAL only — no MEDIUM" instruction in reviewer prompts has not been verified to actually suppress MEDIUM output in practice. Reviewers may comply, partially comply, or rationalize ("this is HIGH because…").
- Skipping the cross-comment round between reviewers is asserted to be sufficient. Untested on a scenario where fact-check itself returns ambiguous verdicts.
- Cluster ordering (mechanical → state-machine → UI) has not been stress-tested against a codebase where the three categories have hidden dependencies.
- The 3-reviewer cost claim ("≈ half of 5-reviewer") is rule-of-thumb, not token-measured. A real measurement would validate or reset the assumption.

Closing a loophole = add a row to the refactor log and tighten the relevant section above.
