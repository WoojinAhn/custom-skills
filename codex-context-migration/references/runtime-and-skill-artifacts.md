# Runtime And Skill Artifacts

Use this reference when the source contains private memory, MCP config, Claude
runtime files, plugins, or skills.

## Runtime Config

Classify Claude runtime configuration separately from instructions:

- `.claude/settings.json` and `.claude/settings.local.json`: permissions,
  hooks, model/tool defaults, and local overrides. Map to Codex config,
  private local config, or defer; do not dump raw JSON into `AGENTS.md`.
- Permission allow/deny patterns: keep durable safety intent in `AGENTS.md`;
  keep matcher syntax in Codex config or defer it.
- `.claude/hooks/` or hook entries: executable runtime behavior. Keep only
  durable intent in instructions. Migrate executable behavior only when Codex
  support is confirmed and the user approves.
- `.claude/commands/`: slash-command workflows. Convert to a Codex skill or
  referenced procedure only when still useful outside Claude.
- `.claude/skills/`: skill packages. Audit as skill-migration candidates, not
  repo instruction text.
- `SessionStart` or auto-memory behavior: classify durable learning, not the
  Claude-specific loading mechanism.

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
context. Audit it as a reusable capability with trigger semantics, resources,
and runtime assumptions.

Check:

- `SKILL.md` frontmatter: `name`, `description`, trigger wording, and scope.
- Body: reusable workflow vs project-specific or private assumptions.
- `references/`: durable docs only; remove stale or private examples.
- `scripts/`: preserve useful helpers, but inspect for hardcoded paths,
  credentials, network assumptions, and unavailable tools.
- `assets/`: copy only files actually needed by outputs.
- `agents/openai.yaml`: create or update UI metadata when the skill should be
  discoverable in Codex/OpenAI skill lists.

Decide:

- `direct-copy`: already Codex-compatible and generic.
- `rewrite`: useful, but uses Claude/product-specific wording or paths.
- `split`: one large skill contains multiple unrelated workflows.
- `private`: contains company/person-specific examples or operational routing.
- `omit`: one-off prompt, stale guide, or non-reusable context.

Validate:

- Skill name is lowercase hyphen-case.
- `description` says when to use the skill, not just what it is.
- References are linked from `SKILL.md`.
- No README/CHANGELOG-style clutter unless required by runtime behavior.
- Scripts can run in the target environment or are clearly marked as
  references.

## Claude-Native Compatibility

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

Map behavior, not spelling:

- `Use Edit/Write` -> edit files using the available patch/edit mechanism.
- `Use Task agents` -> use subagents only when explicitly authorized.
- `Read Claude memory` -> inspect configured private/local references when
  needed.
- `Run /mcp reconnect` -> verify Codex MCP registration and reload behavior
  separately.

If the imported skill would need production write access, real credentials,
private people data, or unavailable Claude hooks, ask whether to keep it as a
private reference instead of an active skill.
