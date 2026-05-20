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
| [`codex-context-migration`](codex-context-migration/SKILL.md) | Claude-era repo context를 Codex `AGENTS.md`로 audit-first 이관. context-only/full-workspace 복사, generated instruction 검토, native/bridge/private/omit 결정, private context 분리, MCP audit, instruction-load 검증 포함. |
| [`triangulated-review`](triangulated-review/SKILL.md) | 3 reviewer 패러럴 코드 감사 (senior + codex max + simplify) + 단일 reviewer 발견에 대한 codex fact-check. CursorMeter #61 5-reviewer 실험의 cost-pruned 버전. |
| [`zoom-caption-capture`](zoom-caption-capture/SKILL.md) | Zoom 웹 클라이언트의 `iframe#webclient` 내부에 `MutationObserver`를 붙여 실시간 자막을 스트리밍 캡처. 토큰 단위 overlap merge + Blob 다운로드로 dump. raw buffer는 무손실 보존, cleanup은 LLM pass에서 처리. |

### `codex-context-migration`

`CLAUDE.md`, `.claude/`, memory, `.mcp.json` 같은 Claude-era context를
Codex-native `AGENTS.md` 레이어로 옮길 때 사용합니다.

스킬은 먼저 출발지/목적지 root, 복사 모드(`context-only` 또는
`full-workspace`), 기존 `AGENTS.md`의 신뢰 수준을 기록합니다. 그다음 source
material을 분류하고, 각 영역을 native instruction, bridge, private local
context, omit 중 어디에 둘지 결정한 뒤 `codex exec`로 결과를 검증합니다.

생성 또는 변환된 `AGENTS.md`는 기본적으로 결함으로 보지 않고, 검토해야 할
provenance로 다룹니다. 품질 판단은 repo 사실, stale reference 검사, domain
fact 보존 여부, execution context 갱신 여부 같은 증거를 기준으로 남깁니다.

특히 Claude-era context에서 넘어오면서 workspace root 정책과 하위 repo,
private local context, MCP 설정, generated instruction 검증이 함께 필요한
사용자에게 잘 맞습니다. 작은 단일 repo라면 inventory, rewrite, validation만
가볍게 적용하면 됩니다.

## 작성 컨벤션

- Frontmatter: `name`, `description`; Claude skill은 필요 시 `argument-hint`, `allowed-tools` 추가
- 본문은 영어 (config file 규칙); 사용자 노출 prose는 한국어가 더 명확하면 한국어 허용
- 모든 스킬은 적어도 한 번의 실제 세션 경험을 코드화해야 함 — speculative skill 금지
- 알려진 실패 모드가 있으면 본문 마지막에 anti-patterns 섹션
- Codex/OpenAI 스킬 목록에 노출하려면 `agents/openai.yaml` 추가 (UI + policy metadata; 스키마: [openai/codex skill-creator](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/references/openai_yaml.md))
