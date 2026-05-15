# Migration Audit Template

Source: `<source path>`
Destination: `<destination path>`

## Source State

- Branch:
- Remote:
- Working tree:
- Source root:
- Destination root:
- Copy mode: `context-only` / `full-workspace`
- Source Git repo count:
- Destination Git repo count:
- Copied/excluded assets:
- Source `AGENTS.md` trust mode: `trusted` / `generated-review` / `unknown`

## Section Classification

| Source section | Type | Action |
| --- | --- | --- |
| Project summary | project-fact | Moved to `AGENTS.md` intro |
| Quick Start | project-fact | Moved and path-adjusted |
| Claude hooks/settings | tool-specific | Deferred or omitted |

## Memory Classification

| Memory file | Type | Action |
| --- | --- | --- |
| `example.md` | cross-agent-rule | Moved to `AGENTS.md` |
| `team_routing.md` | private-sensitive | Moved to private local reference |

## Source AGENTS.md Assessment

| Source `AGENTS.md` | Classification | Evidence | Action |
| --- | --- | --- | --- |
| `example/AGENTS.md` | generated-review | Compared against durable source and repo facts | Reused / revised / ignored |

## Deferred Or Omitted

- Raw session logs:
- MCP registration:
- Long procedures:
- Stale material:

## Quality Comparison

- Source child `AGENTS.md` count:
- Target child `AGENTS.md` count:
- Target authority statement coverage:
- Source generated/converted files disposition:
- Stale source path/reference search:
- Suspicious mechanical substitution search:
- Normalized source-to-target comparison:
- Confirmed defects:
- Confirmed preserved domain facts:

## Verification

- `codex exec` command:
- Active instruction files reported:
  - `<path>`
  - `<path>`
- Notes:
