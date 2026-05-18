**English** | [한국어](README.ko.md)

# custom-skills

Personal Claude Code / Codex skills, distilled from real sessions.

Each skill lives in its own directory with a `SKILL.md` (frontmatter + body).
To use a Claude Code skill, symlink it into `~/.claude/skills/`:

```bash
ln -s ~/home/custom-skills/<skill-name> ~/.claude/skills/<skill-name>
```

To use a Codex skill, symlink or copy it into `~/.codex/skills/`:

```bash
ln -s ~/home/custom-skills/<skill-name> ~/.codex/skills/<skill-name>
```

The target agent picks it up on the next session.

## Skills

| Skill | One-liner |
|---|---|
| [`codex-context-migration`](codex-context-migration/SKILL.md) | Audit-first migration from Claude-era repo context (`CLAUDE.md`, `.claude`, memory, MCP) into Codex `AGENTS.md` layers, with private-context separation and instruction-load validation. |
| [`triangulated-review`](triangulated-review/SKILL.md) | Three-reviewer parallel code audit (senior + codex max + simplify) with codex fact-check on single-reviewer findings. Cost-pruned form of the 5-reviewer pass run on CursorMeter #61. |
| [`zoom-caption-capture`](zoom-caption-capture/SKILL.md) | Stream Zoom Web Client live captions via a `MutationObserver` inside `iframe#webclient`, with token-level overlap merging and Blob-download dump. Lossless raw buffer + deferred cleanup so an LLM pass can produce final minutes. |

## Authoring conventions

- Frontmatter: `name`, `description`; Claude skills may also use `argument-hint`, `allowed-tools` as needed
- Body in English (config file rule); user-facing prose can be Korean where it helps
- Each skill should encode lessons from at least one real session — no speculative skills
- Anti-patterns section at the end if the skill has known failure modes
- To expose a skill in Codex/OpenAI skill lists, add `agents/openai.yaml` (UI + policy metadata; schema: [openai/codex skill-creator](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/references/openai_yaml.md))
