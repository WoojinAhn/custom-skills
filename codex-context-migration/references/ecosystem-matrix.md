# Claude-to-Codex Ecosystem Migration Matrix

This reference maps Claude Code-era workspace artifacts to Codex-native
destinations. It is a design aid for audits, inventory output, and future
automation; it is not an automatic decision engine.

## Purpose

- Distinguish instruction migration, runtime migration, plugin migration, and
  validation.
- Prefer Codex-native official, curated, bundled, and primary-runtime
  capabilities when available.
- Preserve Claude artifacts only as source material, dual-run compatibility, or
  explicit exceptions.
- Surface user confirmation points before migrating auth, write access, hooks,
  production-facing tools, or third-party bridges.

## Disposition Labels

| Label | Meaning |
| --- | --- |
| `rewrite-native` | Convert durable intent into Codex-native form. |
| `bridge` | Keep source as reference because native flattening is unsafe now. |
| `dual-run-retain` | Preserve Claude behavior and add Codex entry points. |
| `private-or-omit` | Do not place in repo instructions. |
| `defer-runtime` | Requires separate runtime support, auth, or trust research. |
| `codex-native-replacement` | Prefer a Codex-side plugin, tool, or config path. |
| `third-party-exception` | Retain only with explicit reason and confirmation. |

## Artifact Migration Matrix

| Claude-era artifact | Claude meaning | Codex-native destination | Default action | User confirmation | Validation |
| --- | --- | --- | --- | --- | --- |
| `CLAUDE.md` | Project/workspace memory | `AGENTS.md` | `rewrite-native` | If stale, generated, private, or dual-run | Active instruction check |
| `.claude/CLAUDE.md` | Project-local Claude memory | Repo or nested `AGENTS.md` / reference | `rewrite-native` or `bridge` | If scope is unclear | Active instruction and scope check |
| `CLAUDE.local.md` | Private local memory | Private local reference or omit | `private-or-omit` | Yes to carry over | Confirm untracked/not committed |
| `@path` imports | Included Claude memory | Inline/reference/private/omit | Classify first | If sensitive or long | Import coverage audit |
| `.claude/settings.json` | Shared runtime config | Codex config / policy notes / defer | Classify, do not dump | Yes for broad permissions | Inspect Codex config |
| `.claude/settings.local.json` | Local runtime override | Private config or omit | `private-or-omit` | Yes | Confirm not committed |
| Permission allow/deny rules | Claude tool policy | Codex approval/sandbox policy or defer | Preserve intent only | Yes for expanded access | Config and sandbox review |
| `.claude/hooks` / hook entries | Executable automation | Codex hook/runtime equivalent or defer | `defer-runtime` | Yes | Dry-run/manual trust check |
| `.claude/commands` | Slash-command workflows | Codex skill/procedure candidate | Rewrite if reusable | Yes for workflow changes | Skill trigger/manual run |
| `.claude/agents` | Claude subagents | Codex delegation policy/skill/reference | Defer or rewrite | Yes | Agent/tool availability check |
| `.claude/skills` | Claude skill packages | Codex skill candidate | Audit as skill artifact | Yes | Skill load/install check |
| `.mcp.json` | MCP server config | Codex MCP config | Audit first | Yes for auth/write/prod | MCP list and read-only test |
| MCP prompts as slash commands | Claude REPL prompt commands | Codex MCP tool or skill flow | Re-evaluate | Yes | Tool availability check |
| Claude official plugins | Claude plugin ecosystem | Codex official/curated/bundled replacement | Prefer Codex candidate | Yes to retain Claude plugin | Marketplace/cache evidence |
| Third-party bridges | Compatibility workflow | Third-party exception | Retain only with purpose | Yes | Audit reason and runtime test |
| Session commands (`/memory`, `/mcp`, `/hooks`, `/agents`, `/permissions`) | Claude REPL behavior | Codex validation/config notes | `defer-runtime` or omit | If behavior must be preserved | Residue classification |
| `~/.claude` memory | User/global Claude memory | Codex global/private reference | Classify as private by default | Yes | Private-path audit |

## Plugin Ecosystem Matrix

| Claude source | Codex-first check | Default disposition | Validation |
| --- | --- | --- | --- |
| `frontend-design@claude-plugins-official` | `build-web-apps@openai-curated` | `codex-native-replacement` candidate | Compare workflow semantics |
| `superpowers@claude-plugins-official` | `superpowers@openai-curated` | `codex-native-replacement` candidate | Compare skill bodies/triggers |
| `playwright@claude-plugins-official` | Codex MCP Playwright + `browser@openai-bundled` | Split capability mapping | Verify browser vs MCP behavior |
| `mcp-server-dev@claude-plugins-official` | `openai-developers` / related Codex developer tools | Research/defer | Docs/cache inspection |
| `cc@sendbird` or reverse bridges | No Codex-first equivalent assumed | `third-party-exception` | Explicit user-approved purpose |

Do not infer plugin equivalence from names alone. A same-name plugin can still
have different trigger wording, tool access, runtime assumptions, or bundled
references. Inventory output may show candidates, but the migration audit must
record the final decision as `Claude plugin retained`,
`Codex-native replacement`, `third-party exception`, or `deferred`.

## Operation Mode Defaults

| Mode | Claude artifacts | Codex artifacts | Plugin/runtime posture |
| --- | --- | --- | --- |
| `setup-in-place` | Preserve by default | Add Codex entry points | Dual-run compatibility |
| `migrate-full-workspace` | Treat as source material | Rewrite native | Prefer Codex-native replacements |
| `context-only` | Copy/classify context only | Do not imply usable code workspace | Audit/defer runtime decisions |

## Residue Classification

| Residue type | Meaning | Action |
| --- | --- | --- |
| `harmless-domain-fact` | Repo is about Claude or references Claude as product/domain | Keep |
| `retained-compatibility` | Intentional dual-run/bridge behavior | Keep with audit note |
| `rewrite-to-codex` | Stale execution context says Claude but means active agent | Rewrite |
| `defer-runtime` | Hooks, MCP auth, slash commands, permissions need separate migration | Defer |
| `remove-or-private` | Secrets, people routing, local-only memory | Omit/private |

## Validation Pack

| Target | Validation |
| --- | --- |
| Root workspace | Active instruction files, operation mode, runtime baseline, residue summary |
| Child repo | Active `AGENTS.md`, parent policy visibility, `CLAUDE.md` authority status |
| Runtime config | Codex config values, sandbox/approval posture, MCP registrations |
| Plugin ecosystem | Detected Claude plugins, Codex candidates, retained exceptions, unresolved risks |

