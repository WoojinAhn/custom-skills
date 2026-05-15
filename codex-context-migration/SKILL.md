---
name: codex-context-migration
description: Use when migrating Claude Code or other agent instruction context into Codex AGENTS.md, including CLAUDE.md audits, workspace layering, private context separation, MCP review, and instruction-load validation.
---

# Codex Context Migration

Use this skill to migrate repository or workspace context from Claude-era files
such as `CLAUDE.md`, `.claude/`, `.mcp.json`, and Claude memory into Codex
`AGENTS.md` files without blindly copying stale, private, or tool-specific
state.

This is a guidance-based skill. Prefer judgment and audit records over a single
automatic rewrite.

## Core Rule

Do not treat migration as a filename rename. Treat it as a source-of-truth
decision:

- Project facts and cross-agent rules move to `AGENTS.md`.
- Claude-specific mechanics stay out of `AGENTS.md` unless they are rewritten
  as Codex-relevant behavior.
- Long procedures become referenced docs or bridge pointers.
- Sensitive people, credentials, private routing, or live operational data go
  to private local references, not repo instructions.
- Stale or generic material is omitted and recorded in the audit.

## Workflow

1. Inventory the source.

```bash
git status --short --branch
git remote -v
find . -maxdepth 3 \( -name CLAUDE.md -o -name AGENTS.md -o -name .mcp.json -o -path '*/.claude/*' \) -print
```

Also check Claude memory when applicable:

```bash
find ~/.claude/projects -maxdepth 1 -type d | grep '<encoded-path-or-repo-name>'
find ~/.claude/projects/<encoded-cwd>/memory -maxdepth 2 -type f -print
```

2. Classify each section or memory file.

Use these buckets:

- `project-fact`: stack, architecture, commands, tests, repo layout
- `cross-agent-rule`: security, branch policy, generated files, API contracts
- `workflow-procedure`: release, review, handoff, incident, schedule procedure
- `tool-specific`: Claude hooks, slash commands, MCP startup, session behavior
- `private-sensitive`: real people, employee IDs, credentials, internal routing
- `stale-or-generic`: outdated paths, deleted commands, broad platitudes

3. Decide native, bridge, private, or omit.

- `native`: write concise Codex-oriented `AGENTS.md`.
- `bridge`: create a short `AGENTS.md` that points to parent layers and the
  local source file when the source is too large to flatten safely.
- `private`: copy to a local private path such as
  `~/.codex/private/<domain>/...` and reference it from global instructions
  only when needed.
- `omit`: leave out and document why.

4. Build the layer model.

- Global defaults live in `~/.codex/AGENTS.md`.
- Workspace policy can live at `<workspace>/AGENTS.md`.
- If children are separate Git repositories, do not assume parent discovery.
  Add a global dispatcher that tells Codex to read the workspace policy when
  working under that tree.
- Repo `AGENTS.md` should contain only repo-specific commands, architecture,
  gotchas, and exceptions.

5. Copy files conservatively.

- Preserve tracked files, even if they are named `.env`.
- Exclude untracked local secrets and generated state: `.venv/`, `node_modules/`,
  caches, build output, `.pytest_cache/`, `.playwright-mcp/`, and raw session
  logs.
- Before excluding `.env`, check whether it is tracked:

```bash
git ls-files --error-unmatch .env >/dev/null 2>&1 && echo tracked || echo untracked
```

6. Write an audit.

Create one audit file per repo or workspace. Use
`references/audit-template.md` as the starting point.

7. Validate instruction loading.

For Git repos:

```bash
codex exec -C <repo> -s read-only --ephemeral \
  "Do not modify files. List active instruction files and summarize repo-specific rules in 5 bullets."
```

For non-Git context directories:

```bash
codex exec -C <dir> --skip-git-repo-check -s read-only --ephemeral \
  "Do not modify files. List active instruction files and summarize repo-specific rules in 5 bullets."
```

Update the audit with the active instruction files reported by Codex.

## Done Criteria

A migration is not complete until these are true:

- The target has an `AGENTS.md` or an intentional bridge `AGENTS.md`.
- Workspace/global layering is explicit, especially when child directories are
  separate Git repositories.
- Each migrated repo or context directory has an audit record.
- Private or sensitive context is either omitted or moved to a local private
  reference, not copied into repo instructions.
- Tracked files are preserved, including tracked `.env` files.
- Generated/local state is excluded unless it is intentionally tracked source.
- `.mcp.json` or equivalent MCP setup is either explicitly migrated or
  explicitly deferred.
- `codex exec` read-only validation reports the expected active instruction
  files.
- Deferred native flattening, bridge-only areas, and omitted material are
  documented.

## Native AGENTS.md Shape

Keep always-loaded files compact. A useful first version:

```markdown
# Project Name

One paragraph with purpose and scope.

Follow `/path/to/workspace/AGENTS.md` for workspace policy.

## Commands

Install/build/test/run commands.

## Architecture

The smallest useful map of layers, packages, and boundaries.

## Critical Rules

Branch policy, data safety, auth, generated files, deployment triggers,
API contracts, and test tagging rules.

## References

- `README.md` for user-facing usage.
- `CLAUDE.md` retained as migration source material, if applicable.
```

## Bridge AGENTS.md Shape

Use a bridge when the source context is too large or domain-heavy to flatten in
one pass:

```markdown
# repo-name

Bridge Codex instruction file for this repository.

Follow `/workspace/AGENTS.md` and `/workspace/domain/AGENTS.md`.

Before changing this repo, read local `CLAUDE.md`; it contains detailed
commands, architecture, and operational rules that have not yet been fully
flattened.

## Critical Rules

- Small set of safety and workflow rules that must be loaded immediately.
```

## Private Context

Private context may be migrated, but never into repo instructions.

Good private candidates:

- People/team routing
- Employee numbers, usernames, partner identifiers
- Local operational preferences
- Non-public escalation paths

Recommended pattern:

1. Copy to `~/.codex/private/<domain>/<name>.md`.
2. `chmod 600` the file.
3. Add a narrow reference in `~/.codex/AGENTS.md` describing when to read it.
4. State that private data must not be copied into repo docs, tests, commits,
   PRs, or public issue text unless the user explicitly asks for that exact
   operational output.

## MCP Handling

Do not automatically convert `.mcp.json` into Codex MCP registration.

Audit first:

- What command is launched?
- Which environment does it target?
- Does it allow writes?
- Is production read-only?
- Are credentials/cookies local?
- Is the MCP server needed for normal Codex work?

Register only after user approval when write access or production data is
involved.

## Skill Artifacts

When the source context is a skill, do not import it as plain `AGENTS.md`
context. Audit it as a reusable capability with its own trigger semantics,
resources, and runtime assumptions.

Check:

- `SKILL.md` frontmatter: `name`, `description`, trigger wording, and scope
- `SKILL.md` body: reusable workflow vs project-specific or private assumptions
- `references/`: durable docs only; remove stale or private examples
- `scripts/`: preserve useful helpers, but inspect for hardcoded paths,
  credentials, network assumptions, and unavailable tools
- `assets/`: copy only files actually needed by outputs
- `agents/openai.yaml`: create or update UI metadata when the skill should be
  discoverable in Codex/OpenAI skill lists

Decide:

- `direct-copy`: already Codex-compatible and generic
- `rewrite`: useful, but uses Claude/product-specific wording or paths
- `split`: one large skill contains multiple unrelated workflows
- `private`: contains company/person-specific examples or operational routing
- `omit`: one-off prompt, stale guide, or non-reusable context

Validate:

- Skill name is lowercase hyphen-case
- `description` says when to use the skill, not just what it is
- References are linked from `SKILL.md`
- No README/CHANGELOG-style clutter unless required by runtime behavior
- Scripts can run in the target environment or are clearly marked as references

### Claude-Native Compatibility

Classify Claude-native skills before importing:

- `portable`: Mostly domain or workflow guidance. Safe to rewrite into a Codex
  skill.
- `portable-with-edits`: Useful, but mentions Claude tools, paths, memory, or
  idioms. Rewrite those parts.
- `bridge-only`: Too large or too Claude-specific to flatten safely. Create a
  Codex bridge skill or context pointer and keep the source as reference.
- `not-portable`: Depends on Claude-only runtime features, hooks, slash
  commands, permissions, unavailable MCP servers, or session behavior. Do not
  import as an active Codex skill.

Do not blindly translate Claude tool names to Codex tool names. Map behavior,
not spelling.

Examples:

- `Use Edit/Write` -> edit files using the available patch/edit mechanism
- `Use Task agents` -> use subagents only when the user explicitly authorizes
  delegation
- `Read Claude memory` -> inspect configured private/local references when
  needed
- `Run /mcp reconnect` -> verify Codex MCP registration and reload behavior
  separately

If the imported skill would need production write access, real credentials,
private people data, or unavailable Claude hooks to function, stop and ask
whether to keep it as a private reference instead of an active skill.

## References

- `references/audit-template.md`: migration audit template.
