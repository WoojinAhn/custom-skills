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
- Inventory command:
- Source Git repo count:
- Destination Git repo count:
- Copied/excluded assets:
- Global/user instruction loading mechanism:
- Source `AGENTS.md` trust mode: `trusted` / `generated-review` / `unknown`
- Parent policy mode for child Git repositories: `isolated` / `inherit-parent`
- Parent policy reference coverage:
- Child repo migration selection mode: `all` / `selected` / `defer-children`
- Child repo selection coverage:

## Child Repo Selection

| Child repo | Existing context | Action | Reason |
| --- | --- | --- | --- |
| `example-repo` | `CLAUDE.md`, no `AGENTS.md` | `include-native` | Durable repo facts are concise |
| `old-lab` | Claude hooks only | `defer` | Too tool-specific for this pass |
| `vendor/example` | none | `exclude` | Vendored or generated material |

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
- Confirmed child repo selection:
- Actual copied child repo coverage:
- Actual instruction rewrite coverage:
- Target authority statement coverage:
- Parent policy reference coverage:
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
