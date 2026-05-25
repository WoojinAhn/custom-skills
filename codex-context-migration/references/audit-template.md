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
- Manifest command:
- Manifest written before copy: yes/no/n/a
- Remote freshness gate command:
- Remote freshness gate result:
- Remote freshness decisions required:
- MCP audit command:
- MCP target baseline command:
- MCP decisions requiring approval:
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

## Migration Manifest

The manifest is the authoritative copy plan. It must be recorded before any
bulk copy for `migrate-full-workspace`.

| Path | Kind | Remote state | Decision | Reason | Evidence |
| --- | --- | --- | --- | --- | --- |
| `example-repo` | `product-repo` | `fresh` / `behind` / `no-remote` | migrate / exclude / defer / already-present |  |  |
| `workflow-utils` | `agent-runtime-tool` |  | exclude / defer | Agent runtime/config repository | settings/hooks files and install script target agent runtime config |
| `skill-source-repo` | `skill-source-repo` |  | migrate / defer | Source material, not installed runtime copy |  |

Manifest summary:

- Included:
- Excluded:
- Deferred:
- Already present:
- Needs review:
- Stale or behind sources:

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

## MCP Capability Audit

MCP migration is capability re-selection, not config copying. Source MCP config,
Claude MCP settings, and existing target MCP registrations are evidence only.

| MCP | Origin | Transport | Auth state | Risk | Codex-native equivalent | Decision | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `context7` | source / target | stdio-command | unsupported / n/a | low | optional MCP | manual-review / already-present | Mark already-present only when target config has `[mcp_servers.context7]`; Claude marketplace catalog presence is not enough |
| `node_repl` | target | stdio-command | unsupported | Codex runtime | Codex app runtime | already-present |  |
| `remote-notes` | target | remote-url | not logged in / unknown | auth/external data | none / reviewed MCP | cleanup-candidate / defer |  |
| `prod-writer` | source | remote-url | token/env | credentials/write/production | none known | defer |  |

MCP summary:

- Already present:
- Codex-native:
- Deferred:
- Cleanup candidates:
- Manual review:
- Omitted:

Marketplace note:

- Claude marketplace/catalog presence alone is not evidence that an MCP is
  Claude-managed or installed. Active MCP ownership comes from Codex MCP config,
  `codex mcp get/list`, or an installed plugin manifest, not from a catalog
  entry.

## Global Claude Runtime Snapshot

| Category | Found | Action | Evidence |
| --- | --- | --- | --- |
| Global settings | yes/no | migrate / defer / omit | `~/.claude/settings.json` keys checked |
| Global hooks | yes/no | defer / omit / migrate with approval | Hook events and commands checked |
| Global commands | yes/no | rewrite / defer / omit | Command filenames checked |
| Global plugins | yes/no | already-present / defer / omit | Plugin names and target availability checked |
| Global skills | yes/no | already-present / rewrite / defer / omit | Skill package names checked |

## Plugin Ecosystem Classification

Codex-native candidates are not guarantees. Verify target-environment
availability and behavior before choosing a replacement.

| Source plugin/skill | Source ecosystem | Purpose | Codex-native candidate | Decision | Evidence |
| --- | --- | --- | --- | --- | --- |
| `frontend-design` | `claude-plugins-official` | frontend UI generation | target Codex skill/plugin if installed | already-present / rewrite / defer |  |
| `superpowers` | `claude-plugins-official` | workflow skills | target Codex skill/plugin if installed | already-present / rewrite / defer |  |
| `playwright` | `claude-plugins-official` | browser automation | MCP Playwright + browser plugin if installed | already-present / rewrite / defer |  |
| `mcp-server-dev` | `claude-plugins-official` | MCP/server development | target Codex skill/plugin if installed | already-present / third-party exception / defer |  |
| `cc` | third-party bridge | reverse bridge / compatibility | none known unless target plugin exists | already-present / third-party exception / defer |  |

## Child Repo Selection

| Child repo | Existing context | Action | Reason |
| --- | --- | --- | --- |
| `example-repo` | `CLAUDE.md`, no `AGENTS.md` | `include-native` | Durable repo facts are concise |
| `current-claude-repo` | active Claude workspace | `include-dual-run` | Preserve `CLAUDE.md`; add Codex entry point |
| `agent-config-sync-repo` | Agent settings sync repo | `defer` / `exclude` | Runtime/config tooling requires explicit user opt-in |
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
- Manifest-to-copy consistency:
- Forbidden path scan command:
- Forbidden path scan result:
- Codex-native forbidden active paths found:
- Stale source path/reference search:
- Suspicious mechanical substitution search:
- Normalized source-to-target comparison:
- Confirmed defects:
- Confirmed preserved domain facts:

## Verification

- `codex exec` command:
- Codex CLI unavailable: `yes/no`
- Deferred state: `deferred-codex-cli-unavailable` / `none`
- Active instruction files reported:
  - `<path>`
  - `<path>`
- Notes:
