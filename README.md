**English** | [한국어](README.ko.md)

# custom-skills

Personal Claude Code skills, distilled from real sessions.

Each skill lives in its own directory with a `SKILL.md` (frontmatter + body). To use a skill, symlink it into `~/.claude/skills/`:

```bash
ln -s ~/home/custom-skills/<skill-name> ~/.claude/skills/<skill-name>
```

Claude Code picks them up on the next session.

## Skills

| Skill | One-liner |
|---|---|
| [`triangulated-review`](triangulated-review/SKILL.md) | Three-reviewer parallel code audit (senior + codex max + simplify) with codex fact-check on single-reviewer findings. Cost-pruned form of the 5-reviewer pass run on CursorMeter #61. |

## Authoring conventions

- Frontmatter: `name`, `description` (Claude's auto-invoke signal), `argument-hint`, `allowed-tools` as needed
- Body in English (config file rule); user-facing prose can be Korean where it helps
- Each skill should encode lessons from at least one real session — no speculative skills
- Anti-patterns section at the end if the skill has known failure modes
