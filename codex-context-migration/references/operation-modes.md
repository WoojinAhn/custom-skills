# Operation Modes and Guided-Auto Decisions

Use this reference when a migration needs more detail than the compact workflow
in `SKILL.md`.

## Operation Modes

- `guided-auto`: planning mode for users who do not want to choose every label
  up front. Run inventory, infer safe defaults, write those defaults into the
  audit, and ask only about risky or materially changing decisions before
  editing. With a destination path, default to `migrate-full-workspace` +
  `codex-native`; without one, default to `setup-in-place` +
  `dual-run-current-workspace`.
- `setup-in-place`: keep the existing workspace/repo hierarchy and add or
  update Codex `AGENTS.md`, parent-policy references, audits, and optional
  Codex config checks in place. This is the default when the user wants to try
  Codex without moving code.
- `migrate-full-workspace`: copy the workspace and child repositories to a new
  destination, then rewrite Codex context there. This is the default when the
  user wants a separate Codex-native workspace.
- `context-only`: copy only instructions, memory, MCP config, and referenced
  knowledge files to a destination while leaving code repositories to be cloned
  or managed separately.

Destination root is required for `migrate-full-workspace` and `context-only`.
It is not required for `setup-in-place` unless the user wants audit/output
files written elsewhere.

## AGENTS.md Trust Mode

- `trusted`: source `AGENTS.md` is user-authored and may be used as source.
- `generated-review`: source `AGENTS.md` appears generated or mechanically
  converted; verify it against durable sources and repo facts before using it.
- `unknown`: compare against `CLAUDE.md` and repo facts before using it.

If a source `AGENTS.md` appears generated, do not treat that as a defect by
itself. Treat it as a signal to verify provenance, intended transformations,
and consistency with durable source files.

## Parent Policy and Child Repo Selection

- `isolated`: child repos stand alone; do not reference workspace policy.
- `inherit-parent`: child repos should follow workspace/root policy, similar to
  Claude-style parent memory. Add or update each child `AGENTS.md` with an
  explicit reference to the parent policy.

Child repo migration selection:

- `all`: migrate every discovered child repo unless a concrete exclusion risk
  is found.
- `selected`: inventory child repos, propose include/exclude/defer choices, and
  ask the user to confirm before modifying child repos.
- `defer-children`: migrate only the workspace/root context now; leave child
  repos untouched and record that coverage is deferred.

Child Git repositories can receive native `AGENTS.md`, temporary bridge files,
dual-run bridge files that keep `CLAUDE.md` authoritative for Claude, or
copy-only treatment when they are submodules, worktrees, vendored, generated,
or outside the intended migration scope.

## Target Posture Details

- `codex-native`: the destination is intended to be operated primarily by
  Codex. Convert durable Claude-era context into Codex-native `AGENTS.md`
  files. Keep `CLAUDE.md` only as retained source material or remove it from
  the active path when the user explicitly wants a clean Codex workspace.
- `dual-run-current-workspace`: the destination is the current workspace that
  is still actively operated by Claude Code, and Codex is being added alongside
  it. Preserve `CLAUDE.md` and Claude runtime files unless they are
  private/generated exclusions. Add `AGENTS.md` as a Codex entry point or
  bridge, but do not rewrite or delete Claude-native behavior just to make the
  workspace look Codex-only.

## Guided-Auto Decision Tree

1. Run inventory with `--guided-auto-plan`.
2. Show inferred operation mode, target posture, trust mode, parent policy,
   child selection, destination path relation, and blocked auto actions.
3. Accept safe defaults only after showing them to the user.
4. Ask for confirmations flagged by the plan:
   - target posture
   - `AGENTS.md` trust mode when source `AGENTS.md` exists
   - child repo plan
   - private/local context disposition
   - runtime config disposition
   - MCP write/production access
   - plugin ecosystem decisions
   - destination overlap or merge behavior
5. Never silently migrate `CLAUDE.local.md`, personal memory, hooks,
   permissions, MCP write/production access, third-party bridges, or retained
   Claude plugins.
6. Prefer Codex-native plugin candidates when available, but ask before
   retaining Claude official plugins or bridges.
7. Use `selected` child repo handling by default for multi-repo workspaces.
