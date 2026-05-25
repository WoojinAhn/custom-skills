# Migration Workflow Details

Use this reference when a migration has multiple child repos, runtime config,
private memory, or generated instruction files.

## Classification Buckets

Classify each section or memory file before rewriting:

| Bucket | Meaning | Default handling |
| --- | --- | --- |
| `project-fact` | Stack, architecture, commands, tests, repo layout | Native `AGENTS.md` |
| `cross-agent-rule` | Security, branch policy, generated files, API contracts | Native `AGENTS.md` |
| `workflow-procedure` | Release, review, handoff, incident, schedule procedure | Native or reference |
| `tool-specific` | Claude hooks, slash commands, MCP startup, session behavior | Runtime migration or defer |
| `private-sensitive` | Real people, employee IDs, credentials, internal routing | Private reference or omit |
| `stale-or-generic` | Outdated paths, deleted commands, broad platitudes | Omit with audit note |

Classify source `AGENTS.md` files separately:

- `authoritative-source`: user-authored, current, and consistent with repo facts.
- `generated-usable`: generated, but verified against durable sources and code.
- `generated-review`: generated or converted, not yet verified.
- `stale`: contradicts code, commands, paths, or active layout.

Generation alone is not a defect. Judge generated files by preserved domain
facts, updated execution context, and intended workspace coverage.

## Child Repo Decisions

Choose one action per child repo:

| Action | Use when |
| --- | --- |
| `include-native` | Durable repo facts can be rewritten into native `AGENTS.md`. |
| `include-bridge` | Source is useful but too large or risky to flatten now. |
| `include-dual-run` | Claude remains active and Codex needs an entry point. |
| `include-copy-only` | Repo should be copied, but instruction rewrite is deferred. |
| `exclude` | Repo should not be copied or rewritten in this migration. |
| `defer` | Repo needs a later dedicated pass. |

Good `exclude` or `defer` candidates:

- Archived, stale, unrelated, vendored, generated, sample, or throwaway repos.
- Private experiments or sensitive operational context.
- Agent-native config/tooling repos such as settings sync, slash-command
  collections, setup repos, and skill/plugin repos.
- Repos whose useful context is mostly hooks, slash commands, session mechanics,
  or unavailable Claude-only runtime behavior.

Do not exclude just because Claude-era files exist. Record a concrete reason.
Conversely, do not silently include Claude-native tooling repos just because a
full-workspace migration was requested.

## Purpose-Based Classification

Do not classify repositories by string matching alone. Use this procedure:

1. Read a concise source such as `README.md`, package metadata, or the entry
   point.
2. Write a one-line `purpose` in the manifest.
3. Decide whether the repo is:
   - a product repo that uses Claude CLI as an implementation dependency,
   - an ecosystem/catalog repo that treats Claude as data,
   - a skill source repo,
   - a runtime/config repo that manipulates Claude state,
   - or ordinary workspace source.
4. Make the decision from that purpose.

Examples:

- Product app using an agent CLI as an implementation detail: review/retain
  unless the product itself is out of scope.
- Skill source repo: retain as source material, but do not install runtime
  skills unless requested.
- Ecosystem/catalog repo: retain when the catalog remains useful.
- Agent runtime/config sync repo: exclude or defer unless the user explicitly
  opts in.
- Agent session helper: exclude or defer for Codex-native workspace migration.

## Layer Model

- Identify the target Codex global/user instruction mechanism. Use
  `~/.codex/AGENTS.md` only when valid for that setup.
- Check `AGENTS.override.md` in global, workspace, and repo scopes.
- Check Codex config when available for `project_doc_fallback_filenames`,
  `project_doc_max_bytes`, and `child_agents_md`.
- Keep always-loaded instruction files compact. Split long procedures into
  references.
- If children are independent Git repos, do not assume parent workspace
  `AGENTS.md` is loaded. Add an explicit parent-policy reference only when
  parent policy mode is `inherit-parent`.
- Repo `AGENTS.md` should contain repo-specific commands, architecture,
  gotchas, and exceptions.

## Copy Modes

For `setup-in-place`, do not copy repos. Modify only confirmed files in the
active workspace and preserve Claude runtime files unless the user asks for
Codex-native cleanup.

For `context-only`, copy only instruction, memory, knowledge, and MCP material.
Document that code repos were intentionally not copied.

For `migrate-full-workspace`, copy code and ordinary project files while
excluding generated local state:

- Preserve tracked files, including tracked `.env` files.
- Exclude untracked local secrets and generated state such as `.venv/`,
  `node_modules/`, caches, build output, `.pytest_cache/`, `.playwright-mcp/`,
  and raw session logs.
- Apply confirmed child repo selection before copying.
- Verify source and destination repo counts, or explain every mismatch.
- Generate a manifest before copy and derive include/exclude behavior from
  `decision=migrate` rows.
- Check remote freshness for Git repos with remotes. If a repo is behind
  upstream, record whether to pull first, copy stale local state as-is, exclude,
  or defer.
- Run a dry-run preview before bulk copy. Show surprising exclusions or stale
  repos before the real copy.
- For Codex-native targets, run a post-copy forbidden-path scan for active
  `CLAUDE.md`, `.claude/`, and `.mcp.json` artifacts. Hits fail the migration
  until removed or explicitly bridged.

Recommended staged order:

1. Inventory.
2. Codex ecosystem snapshot.
3. MCP capability audit when MCP config, MCP servers, or target runtime
   registrations are present.
4. Classification.
5. Manifest generation.
6. Dry-run preview.
7. User confirmation for risky/surprising bulk-copy decisions.
8. Copy.
9. Forbidden-path scan.
10. Count delta.
11. Targeted `codex exec`.
12. State summary update.

## MCP Capability Selection

MCP servers are runtime capabilities. Do not copy source MCP config directly
into Codex config.

1. Inventory source `.mcp.json`, Claude MCP settings, and target Codex MCP
   baseline.
2. Classify each capability by purpose, transport, auth state, credentials,
   write/production risk, and Codex-native equivalent.
3. Prefer target runtime or already-registered target MCPs when present.
4. Default unauthenticated, failing, credentialed, remote, write-capable, or
   production MCP servers to `defer` unless the user approves them.
5. Mark target MCPs with no clear use case as `cleanup-candidate`, not
   silently retained.
6. Keep plugin and MCP decisions in the same ecosystem audit, but execute them
   with separate commands.
7. Do not treat a Claude marketplace entry as an installed MCP/plugin. For
   example, `context7@claude-plugins-official` in a marketplace cache can
   coexist with an active Codex `[mcp_servers.context7]`; only the active target
   MCP is `already-present` and should be managed through `codex mcp ...`.
   Source-only optional MCPs remain `manual-review` until the user chooses to
   register them.

## Native Rewrite Rubric

Treat `CLAUDE.md` as high-signal intent, not text to rename. Infer the intended
working model, then express it in Codex terms.

Extract these signals first:

- Project purpose and domain context.
- Stack, commands, test/build/deploy workflow, and repo layout.
- Boundaries, invariants, generated files, data safety, auth, and deployment
  cautions.
- Issue, branch, commit, PR, and review habits.
- Claude mechanics that need Codex equivalents, removal, or a defer note.

| Source signal | Native destination | Rewrite rule |
| --- | --- | --- |
| Overview/domain context | `## Overview` | Keep intent; remove Claude boilerplate. |
| Commands | `## Commands` | Preserve real commands exactly; update stale paths only. |
| Directory map/modules | `## Architecture` | Compress to the smallest useful map. |
| Invariants/safety/deploy cautions | `## Critical Rules` | Keep loaded; do not bury in prose. |
| Issue/branch/commit/review habits | `## Workflow` | Convert agent names only when they describe active behavior. |
| Hooks/slash commands/MCP/session mechanics | `## Deferred Runtime Migration` or omit | Keep durable intent; defer runtime syntax unless Codex support is confirmed. |
| Private people/credentials/routing | Private reference or omit | Never copy sensitive material into repo instructions. |
| Long background procedures | `## References` | Link instead of inlining. |

Avoid broad product-name replacement. Preserve real package names, CLI
commands, import paths, data labels, examples, URLs, and directory names even
when they include `claude`.

For Claude `@import` sources, do not assume Codex loads them the same way.
Inline only short durable rules. Use references for long procedures, private
local references for sensitive material, and audit stale imports as omitted.

## Quality Validation

Use objective checks:

- Count source and target child `AGENTS.md` files.
- Compare confirmed child repo selection against actual copied/rewritten repos.
- Compare generated or converted source files against durable source material.
- Search active target instructions for stale source paths and stale
  `CLAUDE.md` authority references.
- Search for suspicious mechanical substitutions in package names, binaries,
  URLs, examples, or labels.
- Spot-check suspicious hits against source code.
- Normalize intended transformations from `CLAUDE.md` to `AGENTS.md` when
  feasible.

Quality conclusions must be evidence-based. Mark a file lower quality only when
it contradicts repo facts, preserves stale execution context, or omits required
coverage.

## Parallel Classification

For large workspaces, child repo classification can be parallelized. Each worker
may inspect independent repos and return proposed manifest rows, but the
coordinator is the only writer of shared files:

- manifest
- audit
- root `AGENTS.md`
- child `AGENTS.md` files when parent-policy consistency matters
- central indexes or registries

Do not let multiple workers write the manifest concurrently.
