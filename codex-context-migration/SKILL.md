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
- Parent policy mode for child Git repositories:
  - `isolated`: child repos stand alone; do not reference workspace policy.
  - `inherit-parent`: child repos should follow workspace/root policy, similar
    to Claude-style parent memory. Add or update each child `AGENTS.md` with an
    explicit reference to the parent policy.
- Child repo migration selection:
  - `all`: migrate every discovered child repo unless a concrete exclusion
    risk is found.
  - `selected`: inventory child repos, propose include/exclude/defer choices,
    and ask the user to confirm before modifying child repos.
  - `defer-children`: migrate only the workspace/root context now; leave child
    repos untouched and record that coverage is deferred.
- Whether child Git repositories should receive native `AGENTS.md` files now
  or temporary bridge files.

If a source `AGENTS.md` appears generated, do not treat that as a defect by
itself. Treat it as a signal to verify provenance, intended transformations,
and consistency with durable source files.

2. Inventory the source.

Use the bundled read-only inventory helper when scanning a workspace with child
repositories:

```bash
python3 <skill-dir>/scripts/inventory.py \
  --source <source-root> \
  --destination <destination-root> \
  --format markdown
```

The helper only reports candidates and weak review signals. Do not treat
`suggested_action` as a final include/exclude decision; use it to avoid missed
repos and to prepare the user confirmation checklist.

```bash
git status --short --branch
git remote -v
find . -maxdepth 3 \( -name CLAUDE.md -o -name CLAUDE.local.md -o -name AGENTS.md -o -name AGENTS.override.md -o -name .mcp.json -o -path '*/.claude/*' \) -print
```

Also check Claude memory when applicable:

```bash
test -f ~/.claude/CLAUDE.md && printf '%s\n' ~/.claude/CLAUDE.md
find ~/.claude/projects -maxdepth 1 -type d | grep '<encoded-path-or-repo-name>'
find ~/.claude/projects/<encoded-cwd>/memory -maxdepth 2 -type f -print
```

When migrating a workspace containing child repositories, count them in both
source and destination:

```bash
find <source-root> -name .git -type d -prune | wc -l
find <destination-root> -name .git -type d -prune | wc -l
```

List child repo candidates before modifying them:

```bash
find <source-root> -mindepth 2 -name .git -type d -prune -print
```

For each candidate, record path, existing `CLAUDE.md`, existing `AGENTS.md`,
repo activity if visible, and whether it looks generated, vendored, archived,
private, or tightly coupled to Claude-specific tooling.

Claude instruction sources can be broader than a single top-level
`CLAUDE.md`. Inventory these before rewriting:

- `CLAUDE.md`: shared repo or workspace memory.
- `.claude/CLAUDE.md`: project-local Claude memory, when present.
- `CLAUDE.local.md`: local/private memory; normally private or omitted.
- `.claude/rules/*.md`: path-scoped rules; migrate to nested `AGENTS.md` files
  or references when scope matters, not blindly to the workspace root.
- `@path` imports inside Claude markdown files; classify each imported file as
  `inline`, `reference`, `private`, or `omit` before migration.
- `~/.claude/CLAUDE.md` and `~/.claude/projects/...` memory when it is relevant
  to the migrated workspace; treat personal/local content as private by
  default.

When the terminal supports interactive checkbox selection, use it for the child
repo include/exclude pass. Otherwise present a plain-text checklist and wait for
confirmation before touching child repos.

3. Classify each section or memory file.

Use these buckets:

- `project-fact`: stack, architecture, commands, tests, repo layout
- `cross-agent-rule`: security, branch policy, generated files, API contracts
- `workflow-procedure`: release, review, handoff, incident, schedule procedure
- `tool-specific`: Claude hooks, slash commands, MCP startup, session behavior
- `private-sensitive`: real people, employee IDs, credentials, internal routing
- `stale-or-generic`: outdated paths, deleted commands, broad platitudes

Classify Claude runtime configuration separately from instructions:

- `.claude/settings.json` and `.claude/settings.local.json`: permissions,
  hooks, model/tool defaults, and local overrides. Map to Codex `config.toml`,
  Codex hooks/MCP setup, private local config, or defer; do not dump the raw
  JSON into `AGENTS.md`.
- Permission allow/deny patterns: split the durable policy intent from Claude
  tool matcher syntax. Safety intent can become concise `AGENTS.md` guidance;
  matcher syntax belongs in Codex config or a deferred runtime migration.
- `.claude/hooks/` or hook entries in settings: executable runtime behavior.
  Keep only durable intent in `AGENTS.md`; migrate executable behavior to the
  Codex runtime only when the target environment supports it and the user
  confirms it.
- `.claude/commands/`: slash-command workflows. Convert to a Codex skill or
  referenced procedure only when the workflow is still useful outside Claude.
- `.claude/skills/`: Claude skill packages. Treat as skill-migration
  candidates, not repo instruction text.
- `.mcp.json`: MCP server config. Compare with the Codex MCP config shape,
  required env, command, args, and enabled tools before migrating.
- SessionStart or auto-memory behavior: classify the durable learning, not the
  Claude-specific loading mechanism.

Also classify each source `AGENTS.md`:

- `authoritative-source`: user-authored, current, and consistent with repo facts
- `generated-usable`: generated, but verified against `CLAUDE.md` and code
- `generated-review`: generated or converted, and not yet verified against
  durable sources and repo facts
- `stale`: contradicts code, commands, paths, or active workspace layout

Generation alone is not a quality signal. Judge generated or converted files
by whether they preserve domain facts, update execution context correctly, and
cover the intended workspace scope.

4. Decide child repo coverage, then native, bridge, private, or omit.

For each child repo, choose one action:

- `include-native`: migrate or create a native repo `AGENTS.md`.
- `include-bridge`: create a bridge `AGENTS.md` because native flattening is
  unsafe in the current pass.
- `include-copy-only`: copy the repo when `full-workspace` is requested, but do
  not rewrite instructions yet.
- `exclude`: do not copy or rewrite this child repo during this migration.
- `defer`: leave the repo untouched for a later pass.

Good exclusion or defer candidates include:

- Archived, stale, or unrelated repos under the same workspace root.
- Vendored, generated, sample, or throwaway projects.
- Repos containing private local experiments or sensitive operational context.
- Claude-native configuration or tooling repos, such as `claude-config`, mobile
  Claude setup repos, Claude slash-command collections, Claude settings sync
  repos, and Claude skill/plugin development repos.
- Repos whose useful context is mostly Claude hooks, slash commands, session
  mechanics, or other tool-specific behavior that cannot be rewritten safely.
- Repos with no durable project facts to migrate in the current pass.

Do not exclude a repo just because it contains Claude-era files. Exclude or
defer it only when there is a concrete reason, and record that reason.
Conversely, do not silently include a Claude-native config/tooling repo just
because `full-workspace` copy was requested or because it has a useful
`CLAUDE.md`. Present it as `defer` or `exclude` unless the user explicitly opts
in to copying or bridging that repo.

For material inside an included repo, choose one destination:

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
- Check for `AGENTS.override.md` in global, workspace, and repo scopes. It can
  change instruction precedence and should not be overwritten or ignored.
- Check the user's Codex `config.toml` when available for instruction-loading
  settings such as `project_doc_fallback_filenames`, `project_doc_max_bytes`,
  and `child_agents_md`. Record the observed values or that they were not
  available.
- Keep generated `AGENTS.md` and `AGENTS.override.md` compact. If either file
  is near or above the configured project-doc byte limit, split detailed
  procedures into references and keep only routing instructions in the loaded
  file.
- Workspace policy can live at `<workspace>/AGENTS.md`.
- If children are separate Git repositories, do not assume parent discovery:
  Codex loads project instructions from the current Git/project root up to the
  current working directory, so a parent workspace `AGENTS.md` outside the child
  repo root is not automatically active.
- If parent policy mode is `inherit-parent`, add an explicit parent-policy
  reference to each child repo `AGENTS.md`. This may be a native repo file with
  a parent-policy paragraph, or a bridge file when repo-specific context is not
  ready to flatten.
- If parent policy mode is `isolated`, record that choice in the audit and do
  not add parent references to child repos.
- Repo `AGENTS.md` should contain only repo-specific commands, architecture,
  gotchas, and exceptions.

6. Copy files conservatively.

For `context-only`, copy only instruction/memory/knowledge/MCP material and
document that code repositories were intentionally not copied.

For `full-workspace`, copy code and ordinary project files too, while still
excluding generated local state.

- Apply the confirmed child repo selection before copying. `exclude` and
  `defer` child repos are not copied or rewritten. `include-copy-only` repos
  are copied but their instruction files are not rewritten in this pass.
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

For Claude `@import` sources, avoid assuming Codex will load them the same way.
Inline only short durable rules that must always apply. Use explicit reference
links for long procedures, private local references for sensitive material, and
omit stale imports with an audit note.

Each native child `AGENTS.md` should state its authority relationship:

```markdown
## Instruction Authority

This `AGENTS.md` is the authoritative Codex instruction file for this
repository. Earlier instruction files were audited during migration but are
not authoritative unless this file explicitly references them. `CLAUDE.md`,
when present, is retained only as migration source material; if it differs
from this file, follow `AGENTS.md`.
```

When parent policy mode is `inherit-parent`, include a parent-policy reference
near the top of each child `AGENTS.md`:

```markdown
Follow `<absolute-or-repo-relative-parent>/AGENTS.md` for workspace policy.
This child repository is an independent Git repo, so Codex will not load the
parent policy automatically when sessions start here.
```

Do not add this reference blindly. The user must choose `inherit-parent`, and
the referenced parent file must be relevant to that child repo.

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
- Compare the confirmed child repo selection against actual copied/rewritten
  repos.
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
- Parent policy mode for child Git repositories is recorded as `isolated` or
  `inherit-parent`. If `inherit-parent`, child `AGENTS.md` files explicitly
  reference the parent workspace policy because Codex does not load it across
  independent Git repo boundaries.
- Child repo migration selection is recorded, including include/exclude/defer
  decisions and reasons. Excluded or deferred child repos are not modified, and
  `include-copy-only` repos are not instruction-rewritten.
- Each migrated repo or context directory has an audit record.
- Private or sensitive context is either omitted or moved to a local private
  reference, not copied into repo instructions.
- Tracked files are preserved, including tracked `.env` files.
- Generated/local state is excluded unless it is intentionally tracked source.
- `.mcp.json` or equivalent MCP setup is either explicitly migrated or
  explicitly deferred.
- `codex exec` read-only validation reports the expected active instruction
  files.
- Codex discovery config and override files are checked or explicitly marked
  unavailable, and oversized instruction-file risk is handled or documented.
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
