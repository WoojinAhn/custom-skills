[English](README.md) | **한국어**

# custom-skills

실제 세션에서 추출한 개인용 Claude Code / Codex 스킬 모음.

각 스킬은 자체 디렉토리에 `SKILL.md` (frontmatter + 본문)로 존재합니다.
Claude Code에서 사용하려면 `~/.claude/skills/`에 symlink 걸기:

```bash
ln -s <repo-path>/<skill-name> ~/.claude/skills/<skill-name>
```

Codex에서 사용하려면 `~/.codex/skills/`에 symlink 또는 copy:

```bash
ln -s <repo-path>/<skill-name> ~/.codex/skills/<skill-name>
```

다음 새 세션부터 해당 agent가 인식합니다.

## 대표 스킬

[`codex-context-migration`](codex-context-migration/SKILL.md)이 이 repo에서
공개용으로 가장 신경 쓴 핵심 스킬입니다. `CLAUDE.md`를 단순 rename하지 않고,
Claude-era workspace/repository context를 Codex `AGENTS.md`로 audit-first
이관하는 흐름을 다룹니다. Claude runtime mechanics를 always-loaded instruction에
그대로 dump하지 않는 것도 중요한 목표입니다.

Quick inventory:

```bash
python3 codex-context-migration/scripts/inventory.py \
  --source ~/old-workspace \
  --destination ~/new-codex-workspace \
  --format markdown
```

일반적인 흐름:

1. agent에게 `codex-context-migration`을 사용하라고 요청하고 workspace root를
   알려줍니다.
2. agent가 먼저 어떤 작업을 원하는지 묻습니다.
   - 현재 workspace에 Codex를 세팅 (`setup-in-place`)
   - 전체 workspace를 새 Codex 목적지로 복사 (`migrate-full-workspace`)
   - 고급 옵션: context/knowledge/config 파일만 복사 (`context-only`)
3. agent가 inventory helper를 실행하고, 하위 repo별 include/exclude/defer
   제안을 만든 뒤 파일 수정 전에 확인을 받습니다.
4. 확인 후 `AGENTS.md`, audit record를 작성하고 `codex exec`로 instruction
   loading을 검증합니다.

## Skills

| 스킬 | 한 줄 설명 |
|---|---|
| [`codex-context-migration`](codex-context-migration/SKILL.md) | Claude-era repo context를 Codex `AGENTS.md`로 audit-first 세팅/이관. in-place setup, full-workspace migration, 하위 repo include/exclude 선택, Claude rules/local/import inventory, generated instruction 검토, parent-policy inheritance, Codex discovery/config audit, runtime config 분리, MCP audit, instruction-load 검증 포함. |
| [`triangulated-review`](triangulated-review/SKILL.md) | 3 reviewer 패러럴 코드 감사 + 단일 reviewer 발견에 대한 fact-check. 더 큰 multi-reviewer 실험을 cost-pruned한 형태. |
| [`zoom-caption-capture`](zoom-caption-capture/SKILL.md) | Zoom 웹 클라이언트의 `iframe#webclient` 내부에 `MutationObserver`를 붙여 실시간 자막을 스트리밍 캡처. 토큰 단위 overlap merge + Blob 다운로드로 dump. raw buffer는 무손실 보존, cleanup은 LLM pass에서 처리. |

### `codex-context-migration`

`CLAUDE.md`, `.claude/`, memory, `.mcp.json` 같은 Claude-era context를
Codex-native `AGENTS.md` 레이어로 옮길 때 사용합니다.

스킬은 먼저 operation mode를 고릅니다. 현재 workspace에 Codex를 세팅할지,
전체 workspace를 새 목적지로 이관할지, 또는 고급 옵션으로 context-only 복사를
할지 정합니다. 기존 `AGENTS.md`의 신뢰 수준, 독립 하위 Git repo가
workspace/root 정책을 상속해야 하는지, 각 하위 repo를 include, exclude,
copy-only, defer 중 어떻게 처리할지도 먼저 확정합니다. 그다음 source material을
분류하고, 각 영역을 native instruction, bridge, private local context, omit 중
어디에 둘지 결정한 뒤 `codex exec`로 결과를 검증합니다.
`claude-config` 같은 Claude-native config/tooling repo는 전체 workspace
이관이라고 자동 포함하지 않고, 명시적인 defer/exclude 후보로 먼저 올립니다.
Claude official plugin도 Codex 기본값으로 보지 않습니다. 먼저 Codex
official/curated/bundled 대안을 검토하고, Claude 쪽 plugin은 호환성 판단을
명시적으로 거친 뒤에만 유지합니다.

큰 workspace에서는 포함된 `scripts/inventory.py` helper로 사용자가 지정한
출발지/목적지 경로 기준의 read-only 하위 repo/context 표를 만들 수 있습니다.
`.claude/rules`, `CLAUDE.local.md`, Claude `@import` count, Codex override
파일, runtime-config 약한 신호까지 함께 보여줍니다. 이 helper는 누락 방지용
inventory 도구일 뿐이며, 최종 include/exclude 판단은 audit workflow 안에서
확정합니다.

생성 또는 변환된 `AGENTS.md`는 기본적으로 결함으로 보지 않고, 검토해야 할
provenance로 다룹니다. 품질 판단은 repo 사실, stale reference 검사, domain
fact 보존 여부, execution context 갱신 여부 같은 증거를 기준으로 남깁니다.

Claude hooks, permissions, slash commands, skills, MCP server, SessionStart 같은
runtime config는 durable instruction과 별도로 분류해서, `AGENTS.md`가
Claude-specific mechanics dump가 되지 않게 합니다.

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
