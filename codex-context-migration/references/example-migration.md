# Example Migration

This example shows how the skill treats a mixed Claude-era instruction file as
source material to classify, not as text to copy.

## Source `CLAUDE.md`

```markdown
# Atlas Billing

Atlas Billing reconciles usage events from Kafka into monthly invoices. The
critical invariant is that invoice totals must be deterministic for a closed
billing period.

## Commands

- Build: `./gradlew build`
- Test billing rules: `./gradlew test --tests '*BillingRule*'`
- Local replay: `./gradlew :replay:run --args '--period 2026-04'`

## Architecture

- `ingest/` validates usage events and writes normalized records.
- `pricing/` owns plan lookup and discount calculations.
- `invoice/` creates immutable invoice snapshots.

## Private Routing

For production invoice incidents, page Jane directly. The customer escalation
spreadsheet is in a private Drive folder.

## Claude Runtime

The `.claude/settings.json` file allows a `deploy-preview` hook after tests.
The `.mcp.json` file points to the production billing database for read-only
inspection.

## Notes

Always use the team style from @docs/billing-style.md.
Old migration note: replace all usage of legacy-v1 plans by March 2024.
```

## Migrated `AGENTS.md`

```markdown
# Atlas Billing

Atlas Billing reconciles usage events from Kafka into monthly invoices. The
critical invariant is that invoice totals must be deterministic for a closed
billing period.

## Instruction Authority

This `AGENTS.md` is the authoritative Codex instruction file for this
repository. `CLAUDE.md` is retained only as migration source material; if it
differs from this file, follow `AGENTS.md`.

## Commands

- Build: `./gradlew build`
- Test billing rules: `./gradlew test --tests '*BillingRule*'`
- Local replay: `./gradlew :replay:run --args '--period 2026-04'`

## Architecture

- `ingest/` validates usage events and writes normalized records.
- `pricing/` owns plan lookup and discount calculations.
- `invoice/` creates immutable invoice snapshots.

## Critical Rules

- Closed billing periods must produce deterministic invoice totals.
- Treat production database access and deployment hooks as deferred runtime
  decisions; do not encode them as always-loaded instructions.
- Follow `docs/billing-style.md` for billing terminology and formatting.

## Private Context

Production incident routing and customer escalation links are intentionally not
stored in this repository. Use the private local migration note when the user
has explicitly provided it in the current environment.
```

## Private Local Reference Stub

```markdown
# Atlas Billing Private Context

This file is not committed.

- Production invoice incident routing: retained privately.
- Customer escalation spreadsheet: retained privately.
```

## Audit Rows

| Source section | Type | Action |
| --- | --- | --- |
| Project summary | project-fact | Rewritten into `AGENTS.md` intro |
| Commands | project-fact | Rewritten into `AGENTS.md` commands |
| Architecture | project-fact | Rewritten into `AGENTS.md` architecture |
| Private Routing | private-sensitive | Moved to private local reference stub |
| Claude Runtime | tool-specific | Deferred; not copied into `AGENTS.md` |
| `@docs/billing-style.md` | durable reference | Converted to repo-relative reference |
| Legacy-v1 migration note | stale-or-generic | Omitted after date relevance review |

| Runtime source | Risk | Action | Evidence |
| --- | --- | --- | --- |
| `.claude/settings.json` deploy hook | writes/deploy behavior | Deferred | Requires Codex hook design and user approval |
| `.mcp.json` production database | production data access | Deferred | Requires Codex MCP config review and explicit approval |

## Why This Is Not A Rename

The migrated `AGENTS.md` preserves durable repo facts and commands, but it does
not expose private routing, does not turn Claude hooks into Codex instructions,
does not silently carry production MCP access forward, and does not trust stale
notes without review.
