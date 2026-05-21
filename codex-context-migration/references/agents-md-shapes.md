# AGENTS.md Shapes

Use this reference when writing native, bridge, or dual-run `AGENTS.md` files.
Keep always-loaded files compact.

## Native AGENTS.md

Use for Codex-native repos when durable source context can be safely flattened.

```markdown
# Project Name

One paragraph with purpose and scope.

Follow `/path/to/workspace/AGENTS.md` for workspace policy.

## Instruction Authority

This `AGENTS.md` is the authoritative Codex instruction file for this
repository. Earlier instruction files were audited during migration but are
not authoritative unless this file explicitly references them. `CLAUDE.md`,
when present, is retained only as migration source material; if it differs
from this file, follow `AGENTS.md`.

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

When parent policy mode is `inherit-parent`, add near the top:

```markdown
Follow `<absolute-or-repo-relative-parent>/AGENTS.md` for workspace policy.
This child repository is an independent Git repo, so Codex will not load the
parent policy automatically when sessions start here.
```

Do not add the parent reference blindly. The user must choose `inherit-parent`,
and the referenced parent file must be relevant to that child repo.

## Bridge AGENTS.md

Use when source context is useful but too large or domain-heavy to flatten in
one pass.

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

## Dual-run AGENTS.md

Use when the current workspace remains Claude-operated and Codex is added
alongside it.

```markdown
# repo-name

Codex entry point for this repository.

Follow `/workspace/AGENTS.md` for Codex workspace policy.

## Instruction Authority

This `AGENTS.md` is for Codex. `CLAUDE.md` remains the Claude Code instruction
source and is intentionally preserved. Do not rewrite Claude-specific commands,
hooks, or slash-command workflows unless the user asks for a Codex-native
conversion.

## Codex Notes

- Repo facts that Codex must know immediately.
- Any Codex-specific command, safety, or parent-policy differences.
```

Do not call a dual-run result incomplete merely because `CLAUDE.md` remains.
Judge it by whether Codex has a clear entry point, parent-policy references are
explicit, and Claude-specific behavior is not misrepresented as Codex behavior.

## Claude-Artifact Repos

Preserve product-specific Claude facts when they are the repository subject:

```markdown
## Repository Context

This repo syncs Claude Code configuration files. `CLAUDE.md`,
`~/.claude/settings.json`, and hook scripts are real managed artifacts, not
Codex instruction sources.
```
