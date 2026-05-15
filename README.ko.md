[English](README.md) | **한국어**

# custom-skills

실제 세션에서 추출한 개인용 Claude Code / Codex 스킬 모음.

각 스킬은 자체 디렉토리에 `SKILL.md` (frontmatter + 본문)로 존재합니다.
Claude Code에서 사용하려면 `~/.claude/skills/`에 symlink 걸기:

```bash
ln -s ~/home/custom-skills/<skill-name> ~/.claude/skills/<skill-name>
```

Codex에서 사용하려면 `~/.codex/skills/`에 symlink 또는 copy:

```bash
ln -s ~/home/custom-skills/<skill-name> ~/.codex/skills/<skill-name>
```

다음 새 세션부터 해당 agent가 인식합니다.

## Skills

| 스킬 | 한 줄 설명 |
|---|---|
| [`codex-context-migration`](codex-context-migration/SKILL.md) | Claude-era repo context(`CLAUDE.md`, `.claude`, memory, MCP)를 Codex `AGENTS.md` 레이어로 audit-first 이관. private context 분리와 instruction-load 검증 포함. |
| [`triangulated-review`](triangulated-review/SKILL.md) | 3 reviewer 패러럴 코드 감사 (senior + codex max + simplify) + 단일 reviewer 발견에 대한 codex fact-check. CursorMeter #61 5-reviewer 실험의 cost-pruned 버전. |

## 작성 컨벤션

- Frontmatter: `name`, `description`; Claude skill은 필요 시 `argument-hint`, `allowed-tools` 추가
- 본문은 영어 (config file 규칙); 사용자 노출 prose는 한국어가 더 명확하면 한국어 허용
- 모든 스킬은 적어도 한 번의 실제 세션 경험을 코드화해야 함 — speculative skill 금지
- 알려진 실패 모드가 있으면 본문 마지막에 anti-patterns 섹션
