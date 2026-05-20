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

## Good Fit

Use this skill when the migration has more than one source of context or when
blind conversion could lose important intent:

- A workspace root has policy that should apply across multiple child
  repositories.
- A repository has both durable project facts and tool-specific Claude-era
  mechanics.
- Private local context, MCP configuration, or memory files need separation
  before instructions are made public or shared.
- Existing `AGENTS.md` files may be generated, converted, stale, or mixed with
  source material that needs verification.

For a small single repository with one short `CLAUDE.md`, use only the
inventory, classification, native rewrite, and validation parts of the
workflow.

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

1. Establish the migration scope before copying or rewriting.

Ask for, infer, or explicitly record these choices before starting:

- Source root and destination root.
- Copy mode:
  - `context-only`: migrate instructions, memory, MCP config, and referenced
    knowledge files only.
  - `full-workspace`: also copy code repositories and ordinary project files.
- `AGENTS.md` trust mode:
  - `trusted`: source `AGENTS.md` is user-authored and may be used as source.
  - `generated-review`: source `AGENTS.md` appears generated or mechanically
    converted; verify it against durable sources and repo facts before using it
    as source.
  - `unknown`: compare against `CLAUDE.md` and repo facts before using it.
- Whether child Git repositories should receive native `AGENTS.md` files now
  or temporary bridge files.

If a source `AGENTS.md` appears generated, do not treat that as a defect by
itself. Treat it as a signal to verify provenance, intended transformations,
and consistency with durable source files.

2. Inventory the source.

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

When migrating a workspace containing child repositories, count them in both
source and destination:

```bash
find <source-root> -name .git -type d -prune | wc -l
find <destination-root> -name .git -type d -prune | wc -l
```

3. Classify each section or memory file.

Use these buckets:

- `project-fact`: stack, architecture, commands, tests, repo layout
- `cross-agent-rule`: security, branch policy, generated files, API contracts
- `workflow-procedure`: release, review, handoff, incident, schedule procedure
- `tool-specific`: Claude hooks, slash commands, MCP startup, session behavior
- `private-sensitive`: real people, employee IDs, credentials, internal routing
- `stale-or-generic`: outdated paths, deleted commands, broad platitudes

Also classify each source `AGENTS.md`:

- `authoritative-source`: user-authored, current, and consistent with repo facts
- `generated-usable`: generated, but verified against `CLAUDE.md` and code
- `generated-review`: generated or converted, and not yet verified against
  durable sources and repo facts
- `stale`: contradicts code, commands, paths, or active workspace layout

Generation alone is not a quality signal. Judge generated or converted files
by whether they preserve domain facts, update execution context correctly, and
cover the intended workspace scope.

4. Decide native, bridge, private, or omit.

- `native`: write concise Codex-oriented `AGENTS.md`.
- `bridge`: create a short `AGENTS.md` that points to parent layers and the
  local source file when the source is too large to flatten safely.
- `private`: copy to a local private path such as
  `~/.codex/private/<domain>/...` and reference it from global instructions
  only when needed.
- `omit`: leave out and document why.

Prefer `native` for child repositories when the durable source is concise
enough to flatten. Use a bridge only when native conversion would be unsafe in
the current pass.

5. Build the layer model.

- First identify how the target Codex environment loads global or user-level
  instructions. Use `~/.codex/AGENTS.md` only when that path is valid for the
  user's setup; otherwise record the actual mechanism in the audit.
- Workspace policy can live at `<workspace>/AGENTS.md`.
- If children are separate Git repositories, do not assume parent discovery.
  Add a global dispatcher that tells Codex to read the workspace policy when
  working under that tree.
- Repo `AGENTS.md` should contain only repo-specific commands, architecture,
  gotchas, and exceptions.

6. Copy files conservatively.

For `context-only`, copy only instruction/memory/knowledge/MCP material and
document that code repositories were intentionally not copied.

For `full-workspace`, copy code and ordinary project files too, while still
excluding generated local state.

- Preserve tracked files, even if they are named `.env`.
- Exclude untracked local secrets and generated state: `.venv/`, `node_modules/`,
  caches, build output, `.pytest_cache/`, `.playwright-mcp/`, and raw session
  logs.
- Before excluding `.env`, check whether it is tracked:

```bash
git ls-files --error-unmatch .env >/dev/null 2>&1 && echo tracked || echo untracked
```

After a full-workspace copy, verify that source and destination repo counts
match and that tracked status differences are explained by pre-existing source
state or intentional migration files.

7. Rewrite `AGENTS.md` natively.

When source `AGENTS.md` is `generated-review`, compare it with `CLAUDE.md`,
durable docs, and repo facts before deciding whether to reuse, revise, or
ignore it as source material.

Do not perform broad product-name replacement. Preserve domain facts such as:

- Real package names, npm scopes, binary names, and import paths.
- Real CLI commands used by the repo, even if they include `claude`.
- Dataset labels, examples, URLs, and directory names that are part of the
  project's subject matter.

Rewrite only execution context:

- Active instruction file names: `CLAUDE.md` -> `AGENTS.md` when describing
  Codex behavior.
- Workspace paths: source root -> destination root.
- Local private/reference paths: `.claude/...` -> Codex-equivalent private or
  reference paths when appropriate.
- Tool-specific workflow text only when the target behavior is actually Codex
  behavior.

Each native child `AGENTS.md` should state its authority relationship:

```markdown
## Instruction Authority

This `AGENTS.md` is the authoritative Codex instruction file for this
repository. Earlier instruction files were audited during migration but are
not authoritative unless this file explicitly references them. `CLAUDE.md`,
when present, is retained only as migration source material; if it differs
from this file, follow `AGENTS.md`.
```

8. Write an audit.

Create one audit file per repo or workspace. Use
`references/audit-template.md` as the starting point.

9. Validate instruction loading.

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

10. Validate migration quality.

For generated or converted source `AGENTS.md`, compare quality against the native
target using objective checks:

- Count source and target child `AGENTS.md` files.
- Compare generated or converted `AGENTS.md` files against durable sources for
  unusually shallow changes, such as mostly renamed headings, unchanged
  tool-specific procedures, or broad product-name substitutions.
- Search active target `AGENTS.md` files for stale source paths and stale
  `CLAUDE.md` authority references.
- Search for suspicious mechanical substitutions such as changed package names,
  CLI binaries, URLs, examples, or data labels.
- Spot-check suspicious hits against source code before calling them errors.
- Normalize intended transformations from `CLAUDE.md` to target `AGENTS.md`
  and compare bodies when feasible.

Quality conclusions must be evidence-based. Treat generation as provenance,
not as a defect. Mark a file as lower quality only when it contradicts repo
facts, preserves stale execution context, or omits required child coverage.

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
- If full-workspace copy was requested, source and destination repo counts
  match or every mismatch is explained.
- If source `AGENTS.md` files were generated or converted, the audit records
  whether they were reused, revised, or ignored, with evidence.
- Quality comparison records evidence for any claim that one migration result
  is better than another.

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

1. Copy to a private local path such as
   `~/.codex/private/<domain>/<name>.md`, or the equivalent private path for
   the target Codex setup.
2. `chmod 600` the file.
3. Add a narrow reference in the active global/user instruction location
   describing when to read it.
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
