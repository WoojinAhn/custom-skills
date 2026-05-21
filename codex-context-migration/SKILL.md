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
automatic rewrite. When the user wants a low-friction path, use
`guided-auto`: draft a conservative plan from inventory signals, then ask only
for choices that materially affect files, privacy, runtime permissions, hooks,
MCP write/production access, third-party bridges, or Claude plugin retention.

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

Ask for, infer, or explicitly record these choices before starting.

If the user asks for `guided-auto`, first generate and show a conservative
migration plan, then ask only for the risky confirmations listed in that plan.
Otherwise, ask explicitly before copying or rewriting when these choices are
not already stated: operation mode, target posture, parent policy mode, child
repo migration selection, and whether child repos should be native, bridge, or
dual-run. The target posture must always be confirmed in the user's words
because `codex-native` and `dual-run-current-workspace` require opposite
handling of `CLAUDE.md`.

- Operation mode:
  - `guided-auto`: planning mode for users who do not want to choose every
    migration label up front. Run inventory, infer safe defaults, write those
    defaults into the audit, and ask only about risky or materially changing
    decisions before editing. With a destination path, default to
    `migrate-full-workspace` + `codex-native`; without a destination path,
    default to `setup-in-place` + `dual-run-current-workspace`.
  - `setup-in-place`: keep the existing workspace/repo hierarchy and add or
    update Codex `AGENTS.md`, parent-policy references, audits, and optional
    Codex config checks in place. This is the default when the user wants to
    try Codex without moving code.
  - `migrate-full-workspace`: copy the workspace and child repositories to a
    new destination, then rewrite Codex context there. This is the default when
    the user wants a separate Codex-native workspace.
  - `context-only`: advanced/special-case mode. Copy only instructions,
    memory, MCP config, and referenced knowledge files to a destination while
    leaving code repositories to be cloned or managed separately.
- Source root. Destination root is required for `migrate-full-workspace` and
  `context-only`; it is not required for `setup-in-place` unless the user wants
  audit/output files written elsewhere.
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
- Target posture:
  - `codex-native`: the destination is intended to be operated primarily by
    Codex. Convert durable Claude-era context into Codex-native `AGENTS.md`
    files. Keep `CLAUDE.md` only as retained source material or remove it from
    the active path when the user explicitly wants a clean Codex workspace.
  - `dual-run-current-workspace`: the destination is the current workspace that
    is still actively operated by Claude Code, and Codex is being added
    alongside it. Preserve `CLAUDE.md` and Claude runtime files unless they are
    private/generated exclusions. Add `AGENTS.md` as a Codex entry point or
    bridge, but do not rewrite or delete Claude-native behavior just to make the
    workspace look Codex-only.
- Child repo migration selection:
  - `all`: migrate every discovered child repo unless a concrete exclusion
    risk is found.
  - `selected`: inventory child repos, propose include/exclude/defer choices,
    and ask the user to confirm before modifying child repos.
  - `defer-children`: migrate only the workspace/root context now; leave child
    repos untouched and record that coverage is deferred.
- Whether child Git repositories should receive native `AGENTS.md` files now,
  temporary bridge files, or dual-run bridge files that intentionally keep
  `CLAUDE.md` authoritative for Claude while adding Codex routing.

If a source `AGENTS.md` appears generated, do not treat that as a defect by
itself. Treat it as a signal to verify provenance, intended transformations,
and consistency with durable source files.

2. Inventory the source.

Use the bundled read-only inventory helper when scanning a workspace with child
repositories:

For `setup-in-place`:

```bash
python3 <skill-dir>/scripts/inventory.py \
  --source <source-root> \
  --guided-auto-plan \
  --include-artifacts \
  --format markdown
```

For destination-based migration:

```bash
python3 <skill-dir>/scripts/inventory.py \
  --source <source-root> \
  --destination <destination-root> \
  --guided-auto-plan \
  --include-artifacts \
  --format markdown
```

The helper only reports candidates and weak review signals. Do not treat
`suggested_action` as a final include/exclude decision; use it to avoid missed
repos and to prepare the user confirmation checklist. `--include-artifacts`
adds a separate plugin/skill/command/hook/agent inventory from Codex and Claude
cache/config roots; treat those rows as ecosystem migration evidence, not as
automatic migration decisions.

Use `--artifact-scope all` only when marketplace staging/data must also be
audited; the default `active` scope keeps the artifact table focused on
installed/cache/user roots.

In `guided-auto`, treat the generated plan as a draft:

- Accept safe defaults only after showing them to the user.
- Never silently migrate `CLAUDE.local.md`, personal memory, hooks,
  permissions, MCP write/production access, or third-party bridges.
- Prefer Codex-native plugin candidates when available, but ask before
  retaining Claude official plugins or bridges.
- Use `selected` child repo handling by default for multi-repo workspaces.

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

3. Classify source material and child repo coverage.

Use `references/migration-workflow-details.md` when the migration has child
repos, private memory, runtime config, generated instructions, or unclear
source quality. Record classifications in the audit instead of silently
dropping or rewriting material.

4. Build the layer model and copy/setup files conservatively.

Keep always-loaded Codex instructions compact. If child directories are
independent Git repos, do not assume the parent workspace `AGENTS.md` is active
inside them; add explicit parent-policy references only when the user chose
`inherit-parent`. For copy/setup mode details, use
`references/migration-workflow-details.md`.

5. Rewrite `AGENTS.md` natively.

Treat `CLAUDE.md` as a high-signal intent source, not just text to rename.
Infer the intended working model, then express it in Codex terms. For detailed
rewrite rules and quality checks, use
`references/migration-workflow-details.md`. For native, bridge, and dual-run
file templates, use `references/agents-md-shapes.md`.

6. Handle runtime config, private context, MCP, plugins, and skills.

Do not dump Claude runtime mechanics into `AGENTS.md`. Use
`references/runtime-and-skill-artifacts.md` and
`references/ecosystem-matrix.md` when source context includes private memory,
hooks, slash commands, `.mcp.json`, Claude plugins, Codex plugins, or skill
packages.

7. Write an audit.

Create one audit file per repo or workspace. Use
`references/audit-template.md` as the starting point.

8. Validate instruction loading.

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

9. Validate migration quality.

Use evidence-based checks from `references/migration-workflow-details.md`.
Treat generation as provenance, not as a defect. Mark a file lower quality only
when it contradicts repo facts, preserves stale execution context, or omits
required coverage.

## Done Criteria

A migration is not complete until these are true:

- The target has an `AGENTS.md` or an intentional bridge `AGENTS.md`.
- Operation mode is recorded as `setup-in-place`, `migrate-full-workspace`, or
  advanced `context-only`, and the file changes match that mode.
- Workspace/global layering is explicit, especially when child directories are
  separate Git repositories.
- Parent policy mode for child Git repositories is recorded as `isolated` or
  `inherit-parent`. If `inherit-parent`, child `AGENTS.md` files explicitly
  reference the parent workspace policy because Codex does not load it across
  independent Git repo boundaries.
- Target posture is recorded as `codex-native` or
  `dual-run-current-workspace`, and the treatment of `CLAUDE.md` matches that
  posture.
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
- If `migrate-full-workspace` was requested, source and destination repo counts
  match or every mismatch is explained. If `setup-in-place` was requested,
  before/after Git status is recorded for modified repos.
- If source `AGENTS.md` files were generated or converted, the audit records
  whether they were reused, revised, or ignored, with evidence.
- Quality comparison records evidence for any claim that one migration result
  is better than another.

## References

- `references/audit-template.md`: migration audit template.
- `references/agents-md-shapes.md`: native, bridge, and dual-run `AGENTS.md`
  templates.
- `references/ecosystem-matrix.md`: Claude-to-Codex ecosystem migration matrix.
- `references/migration-workflow-details.md`: classification, child repo
  selection, layer model, copy modes, rewrite rubric, and quality checks.
- `references/runtime-and-skill-artifacts.md`: private context, MCP, runtime
  config, plugin, and skill artifact migration.
