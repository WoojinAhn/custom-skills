# Migration Audit Template

Source: `<source path>`
Destination: `<destination path>`

## Source State

- Branch:
- Remote:
- Working tree:
- Source root:
- Destination root:
- Operation mode: `guided-auto` / `setup-in-place` / `migrate-full-workspace` / `context-only`
- Copy mode detail: none / `context-only` / `full-workspace`
- Guided-auto defaults accepted: yes/no/n/a
- Guided-auto plan command:
- Guided-auto inferred defaults:
  - Operation mode default:
  - Target posture default:
  - Parent policy mode default:
  - Child repo selection default:
- Guided-auto confirmations requested:
- Guided-auto confirmations resolved:
- Guided-auto blocked auto-actions:
- Inventory command:
- Import scan command:
- Import recursion depth checked:
- Source Git repo count:
- Destination Git repo count:
- Claude rule files discovered:
- Local memory files discovered:
- Copied/excluded assets:
- Global/user instruction loading mechanism:
- Codex `AGENTS.override.md` coverage:
- Codex `project_doc_fallback_filenames`:
- Codex `project_doc_max_bytes`:
- Codex `child_agents_md`:
- Codex instruction size risk:
- Source `AGENTS.md` trust mode: `trusted` / `generated-review` / `unknown`
- Parent policy mode for child Git repositories: `isolated` / `inherit-parent`
- Target posture: `codex-native` / `dual-run-current-workspace`
- `CLAUDE.md` disposition: absorbed / retained-source / retained-active / omitted
- Parent policy reference coverage:
- Child repo migration selection mode: `all` / `selected` / `defer-children`
- Child repo selection coverage:

## Claude Source Coverage

| Source type | Found | Action |
| --- | --- | --- |
| `CLAUDE.md` |  |  |
| `.claude/CLAUDE.md` |  |  |
| `CLAUDE.local.md` |  | Private / omitted / migrated |
| `.claude/rules/*.md` |  | Nested `AGENTS.md` / reference / omitted |
| Claude `@import` files |  | Inline / reference / private / omitted |

## Runtime Config Classification

| Source | Runtime type | Risk | Codex destination | Action | Evidence |
| --- | --- | --- | --- | --- | --- |
| `.claude/settings.json` | permissions/hooks/defaults |  | Codex config / private / defer |  |  |
| `.claude/settings.local.json` | local overrides | private/local | private / omit |  |  |
| `.claude/hooks` or hook entries | executable runtime behavior | writes/network/production | Codex hook / defer / omit |  |  |
| `.claude/commands` | slash-command workflow | Claude-only syntax/private routing | Codex skill candidate / reference / omit |  |  |
| `.claude/skills` | Claude skill package | tool/runtime assumptions | skill migration candidate / defer |  |  |
| `.mcp.json` | MCP server config | credentials/write scope | Codex MCP config / defer |  |  |
| `SessionStart` | startup context injection | dynamic/private context | `AGENTS.md` / private / defer |  |  |

## Plugin Ecosystem Classification

| Source plugin/skill | Source ecosystem | Purpose | Codex-native candidate | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| `frontend-design` | `claude-plugins-official` | frontend UI generation | `build-web-apps@openai-curated` | Codex-native replacement / retained / deferred |  |
| `superpowers` | `claude-plugins-official` | workflow skills | `superpowers@openai-curated` | Codex-native replacement / retained / deferred |  |
| `playwright` | `claude-plugins-official` | browser automation | MCP Playwright + `browser@openai-bundled` | Codex-native replacement / retained / deferred |  |
| `mcp-server-dev` | `claude-plugins-official` | MCP/server development | `openai-developers` / `plugin-eval` research candidate | retained / third-party exception / deferred |  |
| `cc` | third-party bridge | reverse bridge / compatibility | none known | third-party exception / deferred |  |

## Child Repo Selection

| Child repo | Existing context | Action | Reason |
| --- | --- | --- | --- |
| `example-repo` | `CLAUDE.md`, no `AGENTS.md` | `include-native` | Durable repo facts are concise |
| `current-claude-repo` | active Claude workspace | `include-dual-run` | Preserve `CLAUDE.md`; add Codex entry point |
| `claude-config` | Claude settings sync repo | `defer` / `exclude` | Claude-native config/tooling requires explicit user opt-in |
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

## Claude Rules Classification

| Rule file | Scope | Action | Evidence |
| --- | --- | --- | --- |
| `.claude/rules/example.md` | path-scoped | Nested `AGENTS.md` / reference / omitted |  |

## Import Classification

| Import | Source file | Resolved | Action | Evidence |
| --- | --- | --- | --- | --- |
| `@docs/example.md` | `CLAUDE.md` | yes/no | Inline / reference / private / omitted |  |

## Source AGENTS.md Assessment

| Source `AGENTS.md` | Classification | Evidence | Action |
| --- | --- | --- | --- |
| `example/AGENTS.md` | generated-review | Compared against durable source and repo facts | Reused / revised / ignored |

## Deferred Or Omitted

- Raw session logs:
- MCP registration:
- Claude runtime config:
- Claude rules/imports:
- Long procedures:
- Stale material:

## Quality Comparison

- Source child `AGENTS.md` count:
- Target child `AGENTS.md` count:
- Confirmed child repo selection:
- Actual copied child repo coverage:
- Actual instruction rewrite coverage:
- Target authority statement coverage:
- Target posture coverage:
- Dual-run bridge coverage:
- Parent policy reference coverage:
- Claude rules/local/import disposition:
- Claude runtime config disposition:
- Codex override/config disposition:
- Codex instruction size risk:
- `.claude/rules` coverage:
- `CLAUDE.local.md` disposition:
- `@import` coverage:
- Unresolved/broken imports:
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
