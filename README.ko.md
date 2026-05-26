[English](README.md) | **한국어**

# custom-skills

실제 세션에서 추출한 Claude Code와 Codex용 개인 AI agent 스킬 모음.

각 스킬은 자체 디렉토리에 `SKILL.md` (frontmatter + 본문)로 존재합니다.

## Codex 설치

이 저장소는 skill source로 공개됩니다. 아직 Codex plugin으로 패키징되어 있지는
않고, plugin packaging은 marketplace 스타일 설치 경험이 필요해질 때 나중에
추가할 수 있습니다.

스킬을 설치하려면 skill 디렉터리를 `${CODEX_HOME:-$HOME/.codex}/skills/`에
symlink하거나 복사합니다:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s <repo-path>/codex-context-migration \
  "${CODEX_HOME:-$HOME/.codex}/skills/codex-context-migration"
```

설치 후 Codex를 재시작해야 새 skill을 인식합니다.

Codex의 `skill-installer` skill을 사용해 GitHub 저장소 경로로 설치할 수도
있습니다:

```text
WoojinAhn/custom-skills/codex-context-migration
```

마이그레이션은 기존 agent가 아니라 Codex session에서 실행하는 것이 의도입니다.
예시 프롬프트:

```text
Use the codex-context-migration skill to audit source `/path/to/old-workspace`
and prepare a Codex-native migration plan for destination
`/path/to/new-codex-workspace`. Run read-only inventory first and ask before
copying or editing files.
```

## Claude Code 설치

Claude Code도 같은 skill source 형식을 사용할 수 있습니다.
`~/.claude/skills/`에 symlink합니다:

```bash
ln -s <repo-path>/<skill-name> ~/.claude/skills/<skill-name>
```

`codex-context-migration`은 Codex instruction loading 검증과 Codex-native
`AGENTS.md` 작성을 수행하므로, 실행자는 Codex가 더 적합합니다.

## 대표 스킬

[`codex-context-migration`](codex-context-migration/README.md)이 이 repo에서
공개용으로 가장 신경 쓴 핵심 스킬입니다. 상세 README는 스킬 디렉터리 안에 있고,
quick start, diagram, operation mode, before/after 예시를 거기에 둡니다. 이
스킬은 먼저 audit을 수행하고, source instruction 파일을 명령이 아니라 분류할
데이터로 취급하며, durable project fact와 private/runtime context를 분리합니다.

Quick inventory:

```bash
python3 codex-context-migration/scripts/inventory.py \
  --source ~/old-workspace \
  --destination ~/new-codex-workspace \
  --guided-auto-plan \
  --format markdown
```

## Skills

| 스킬 | 한 줄 설명 |
|---|---|
| [`codex-context-migration`](codex-context-migration/README.md) | Claude-era repo context를 Codex `AGENTS.md`로 audit-first 세팅/이관. |
| [`triangulated-review`](triangulated-review/SKILL.md) | 3 reviewer 패러럴 코드 감사 + 단일 reviewer 발견에 대한 fact-check. 더 큰 multi-reviewer 실험을 cost-pruned한 형태. |
| [`zoom-caption-capture`](zoom-caption-capture/SKILL.md) | Zoom 웹 클라이언트의 `iframe#webclient` 내부에 `MutationObserver`를 붙여 실시간 자막을 스트리밍 캡처. 토큰 단위 overlap merge + Blob 다운로드로 dump. raw buffer는 무손실 보존, cleanup은 LLM pass에서 처리. |

### `codex-context-migration`

Claude-era context를 Codex-native `AGENTS.md` 레이어로 옮길 때 사용합니다.
워크플로우, diagram, 예시는 전용
[`codex-context-migration` README](codex-context-migration/README.md)에 둡니다.

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
