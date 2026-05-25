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

Use the inventory runtime snapshot when available:

```bash
python3 <skill>/scripts/inventory.py \
  --source <source> \
  --include-global-claude-runtime \
  --format markdown
```

The snapshot is a decision aid, not approval to migrate runtime behavior. It
should list whether global Claude settings, hooks, slash commands, plugins, and
skills were discovered so the audit can say whether each category was reviewed
or missed.

## Decision Vocabulary

Use user-friendly status words in migration notes:

- `migrate`: move or rewrite into Codex-native instructions/config now.
- `exclude`: intentionally leave out of the target.
- `defer`: do not migrate in this pass; keep a note so it can be discussed
  later. This is not a silent omission.
- `already-present`: the capability already exists in the Codex target
  environment, so source files usually should not be copied.
- `needs-review`: the artifact may matter, but the source/runtime assumptions
  are not clear enough for automatic migration.

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

Do not automatically convert `.mcp.json`, Claude MCP settings, or existing
Codex MCP registrations into target Codex MCP config.

MCP migration is capability re-selection, not config copying. Treat every MCP
source as evidence about a desired capability, then choose the Codex-native
target behavior.

Audit first:

- What command is launched?
- Which environment does it target?
- Does it allow writes?
- Is production read-only?
- Are credentials/cookies local?
- Is the MCP server needed for normal Codex work?
- Is an equivalent Codex runtime, bundled plugin, or already-registered MCP
  already present?
- Is the target MCP unauthenticated, failing, or stale?

Register only after user approval when write access or production data is
involved.

Use the MCP audit when available:

```bash
python3 <skill>/scripts/inventory.py \
  --source <source> \
  --include-mcp-audit \
  --format markdown
```

Decision vocabulary:

- `already-present`: Codex already provides the capability; do not copy source
  MCP config.
- `codex-native`: Useful capability that can be intentionally registered in
  Codex.
- `defer`: Auth, credentials, remote data scope, write capability, production
  access, or unclear ownership requires a separate decision.
- `cleanup-candidate`: Active target MCP appears unauthenticated, stale, or
  unused.
- `manual-review`: Capability may be useful, but the target choice is not
  obvious.
- `omit`: No durable use case remains.

Keep MCP and plugin audits aligned, but manage them separately. MCP changes use
`codex mcp ...`; plugin changes use `codex plugin ...`. Verify command support
with `--help` before suggesting exact flags.

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

Distinguish source repositories from installed runtime skills:

- A source repo such as `custom-skills` may be product/workspace material and
  should be classified by purpose, not excluded only because it contains skills.
- Installed runtime copies under Claude plugin/cache/skill directories are
  runtime artifacts. They should normally be `already-present`, `rewrite`, or
  `defer`, not blindly copied into the active Codex workspace.
- When a source repo is copied, run the remote freshness gate first. A stale
  source can make the destination miss tests, scripts, and updated skill
  guidance even when the copy itself succeeds.

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

## Plugin Decision Heuristics

Prefer classification over file copying:

| Source signal | Default decision | Reason |
| --- | --- | --- |
| Plugin/skill already installed in Codex | `already-present` | Avoid stale duplicate copies |
| Claude hook, permission matcher, or SessionStart behavior | `defer` | Executable behavior needs explicit review |
| Slash command with reusable workflow | `rewrite` | Convert intent into a Codex skill/procedure |
| Slash command tied to Claude-only state | `defer` or `omit` | Runtime assumptions may not hold |
| MCP server with credentials/write scope | `defer` | Requires user approval and target config review |
| MCP already provided by Codex runtime or target baseline | `already-present` | Avoid duplicate or stale registrations |
| Target MCP is unauthenticated or failing | `cleanup-candidate` or `defer` | Do not preserve broken runtime state silently |
| Source repo that builds user-facing/product functionality | `migrate` or `include-native` | Purpose is not Claude runtime itself |
| Repo whose primary purpose is Claude config, hooks, relay, or plugin cache | `exclude` or `defer` | Claude-native operational code |

Evidence must include what was checked: settings keys, hook names, command
names, plugin names, skill package names, and whether the target Codex
environment already provides an equivalent capability.
