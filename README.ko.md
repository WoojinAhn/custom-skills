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
| [`codex-context-migration`](codex-context-migration/SKILL.md) | Claude-era repo context를 Codex `AGENTS.md`로 audit-first 이관. context-only/full-workspace 복사, generated instruction 검토, 하위 repo parent-policy inheritance, native/bridge/private/omit 결정, private context 분리, MCP audit, instruction-load 검증 포함. |
| [`triangulated-review`](triangulated-review/SKILL.md) | 3 reviewer 패러럴 코드 감사 (senior + codex max + simplify) + 단일 reviewer 발견에 대한 codex fact-check. CursorMeter #61 5-reviewer 실험의 cost-pruned 버전. |
| [`zoom-caption-capture`](zoom-caption-capture/SKILL.md) | Zoom 웹 클라이언트의 `iframe#webclient` 내부에 `MutationObserver`를 붙여 실시간 자막을 스트리밍 캡처. 토큰 단위 overlap merge + Blob 다운로드로 dump. raw buffer는 무손실 보존, cleanup은 LLM pass에서 처리. |

### `codex-context-migration`

`CLAUDE.md`, `.claude/`, memory, `.mcp.json` 같은 Claude-era context를
Codex-native `AGENTS.md` 레이어로 옮길 때 사용합니다.

스킬은 먼저 출발지/목적지 root, 복사 모드(`context-only` 또는
`full-workspace`), 기존 `AGENTS.md`의 신뢰 수준을 기록합니다. 독립 하위 Git
repo가 workspace/root 정책을 상속해야 하는지도 묻습니다. 그다음 source
material을 분류하고, 각 영역을 native instruction, bridge, private local
context, omit 중 어디에 둘지 결정한 뒤 `codex exec`로 결과를 검증합니다.

생성 또는 변환된 `AGENTS.md`는 기본적으로 결함으로 보지 않고, 검토해야 할
provenance로 다룹니다. 품질 판단은 repo 사실, stale reference 검사, domain
fact 보존 여부, execution context 갱신 여부 같은 증거를 기준으로 남깁니다.

특히 Claude-era context에서 넘어오면서 workspace root 정책과 하위 repo,
private local context, MCP 설정, generated instruction 검증이 함께 필요한
사용자에게 잘 맞습니다. 작은 단일 repo라면 inventory, rewrite, validation만
가볍게 적용하면 됩니다.

### `triangulated-review`

일반적인 단일 reviewer 검토만으로는 신뢰도가 부족할 때 사용합니다. 큰 기능을
merge한 직후, public release 전, 또는 품질/보안 리스크가 큰 수정 묶음을
적용하기 전에 적합합니다.

스킬은 세 개의 독립 review lens를 병렬로 돌리고, 겹치는 finding은
consolidation하며, 단일 reviewer만 제기한 finding은 별도 fact-check pass로
검증한 뒤 적용합니다. HIGH/CRITICAL finding만 요구하는 이유는, 이 workflow를
만든 실제 세션에서 MEDIUM finding이 대부분 noise였고 실제 적용 가치가 낮았기
때문입니다.

false positive와 과도하게 큰 commit이 주요 리스크인 큰 code review에 잘
맞습니다. 사소한 PR, formatter-only diff, 작은 단일 파일 수정에는 쓰지 않는
쪽이 낫습니다.

### `zoom-caption-capture`

사용자가 이미 Zoom Web Client 회의에 들어가 있고 live caption이 보이는
상태에서 transcript나 회의록 원천 자료를 만들고 싶을 때 사용합니다. 스킬은
Zoom의 `iframe#webclient` 내부에 `MutationObserver`를 붙여 caption snapshot을
기록하고, JSON dump를 만든 뒤 Markdown으로 변환할 수 있게 합니다.

핵심 설계는 먼저 무손실로 캡처하고 cleanup은 나중에 하는 것입니다. Zoom
caption box는 rolling window라서, 스킬은 raw fragment를 보존하고 token-level
overlap merge는 중간 결과로만 사용합니다. 최종 회의록은 captured payload를
기준으로 한 번 더 정리하는 흐름을 전제로 합니다.

web-client Zoom 회의에서 caption이 이미 켜져 있을 때 가장 잘 맞습니다. 사용자를
대신해 회의에 join하지 않고, native Zoom app에는 적용되지 않으며, Zoom이
caption initial만 노출하는 경우 full speaker name을 추론하지 않습니다.

## 작성 컨벤션

- Frontmatter: `name`, `description`; Claude skill은 필요 시 `argument-hint`, `allowed-tools` 추가
- 본문은 영어 (config file 규칙); 사용자 노출 prose는 한국어가 더 명확하면 한국어 허용
- 모든 스킬은 적어도 한 번의 실제 세션 경험을 코드화해야 함 — speculative skill 금지
- 알려진 실패 모드가 있으면 본문 마지막에 anti-patterns 섹션
- Codex/OpenAI 스킬 목록에 노출하려면 `agents/openai.yaml` 추가 (UI + policy metadata; 스키마: [openai/codex skill-creator](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/references/openai_yaml.md))
