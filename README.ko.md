[English](README.md) | **한국어**

# custom-skills

실제 세션에서 추출한 Claude Code와 Codex용 개인 AI agent 스킬 모음.

각 스킬은 자체 디렉토리에 `SKILL.md` (frontmatter + 본문)로 존재합니다.

## 시작하기

이 저장소는 Codex plugin이 아닌 스킬 소스 디렉터리를 배포합니다.
각 스킬의 용도와 사용 지침은 아래 [스킬 목록](#skills)에서 확인할 수 있습니다.

일반적인 Claude-to-Codex 변환은
[OpenAI의 curated `migrate-to-codex` 스킬](codex-context-migration/README.md#official-skill-first)로
시작합니다.

[`codex-context-migration`](codex-context-migration/README.md)은 다중 저장소,
workspace copy, private context, instruction layering, target posture, 권한 근거에
대한 고급 workspace 감사를 추가합니다. 상세 가이드에서 다음을 확인할 수 있습니다.

- [사용 대상](codex-context-migration/README.md#who-this-is-for).
- [설치](codex-context-migration/README.md#optional-advanced-audit-installation)와
  [업데이트·버전 고정](codex-context-migration/README.md#distribution-and-updates)
  (업데이트 가능한 설치 방식으로 git clone + symlink 권장).
- [빠른 시작](codex-context-migration/README.md#quick-start),
  [다이어그램](codex-context-migration/README.md#workspace-layering),
  [실제 이관 예시](codex-context-migration/references/example-migration.md).

전체 이관 workflow는 Codex에서 실행합니다. Claude Code는
[compatibility mode](codex-context-migration/README.md#runtime-support)에서
읽기 전용 inventory와 감사 계획을 지원합니다.

## Skills

| 스킬 | 한 줄 설명 |
|---|---|
| [`codex-context-migration`](codex-context-migration/README.md) | OpenAI의 Claude-to-Codex 변환기에 더하는 고급 workspace 감사. |
| [`collaborative-development`](collaborative-development/SKILL.md) | 사용 가능한 에이전트를 조합하고 독립 리뷰·실제 검증을 거쳐 승인된 범위까지 개발을 마무리하는 운영 스킬. |
| [`triangulated-review`](triangulated-review/SKILL.md) | 3 reviewer 패러럴 코드 감사 + 단일 reviewer 발견에 대한 fact-check. 더 큰 multi-reviewer 실험을 cost-pruned한 형태. |
| [`zoom-caption-capture`](zoom-caption-capture/SKILL.md) | Zoom 웹 클라이언트의 `iframe#webclient` 내부에 `MutationObserver`를 붙여 실시간 자막을 스트리밍 캡처. 토큰 단위 overlap merge + Blob 다운로드로 dump. raw buffer는 무손실 보존, cleanup은 LLM pass에서 처리. |
| [`session-harvest`](session-harvest/SKILL.md) | 세션 종료 전 durable value(툴링 이슈, 문서, 메모리, hygiene)를 실효성 게이트로 걸러 추출하는 마무리 스윕. 먼저 읽기 전용으로 후보를 제시하고 승인된 항목만 실행. 0건도 유효한 결과이며, 스킵은 침묵이 아니라 사유와 함께 보고. |
| [`trend-briefing-doc`](trend-briefing-doc/SKILL.md) | 링크 하나 또는 주제 한 줄만으로 리서치를 수행해 근거에 따라 사실·영향·불확실성 또는 입장 A/B 구조의 한국어 HTML 트렌드 브리핑을 생성. 카드형 담백한 리포트 톤, 법정/전쟁 메타포 금지. 템플릿 동봉. |
| [`ai-status`](ai-status/SKILL.md) | AI/개발 서비스 상태(Claude, OpenAI, Cursor, GitHub, Gemini + 확장 10개)를 machine-readable status API로 일괄 확인. 운영 장애와 정책/모델 recall/FedRAMP scope incident를 구분해 보고. |

### `collaborative-development`

여러 에이전트나 rescue를 활용하는 비단순 개발에 사용합니다. 사용 가능한
Superpowers와 프로젝트 검토 절차를 연결하고, 오너의 책임·검증 근거·리뷰가
덮는 변경 범위를 명확히 합니다. 참여 모델과 인원수는 고정하지 않고 현재
접근 가능 여부와 과업에 맞춥니다.

`$collaborative-development`와 함께 이슈 또는 원하는 결과, provider·완료 범위
제약을 전달합니다. 스킬 자체가 머지·릴리즈·설치 권한을 부여하지는 않습니다.
사소한 수정이나 리뷰만 하는 요청에는 해당 작업의 전용 절차를 바로 사용합니다.

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

### `session-harvest`

작업 세션을 마무리할 때, context가 사라지기 전에 durable value를 추출하는
스킬입니다. 툴링 friction(issue tracker), 프로젝트 context(docs/CLAUDE.md),
메모리, hygiene의 네 lane을 스윕하고, 모든 후보를 3점검 실효성 게이트(흡수 /
근거 / 사용패턴)에 통과시켜 speculative한 기록이 남지 않게 합니다.

스윕은 두 단계로 나뉩니다. 1단계는 읽기 전용입니다 — 조사하고, 게이트를 적용하고,
항목별 목적지와 사유가 붙은 번호 후보 목록을 의도적 스킵 목록과 함께 제시합니다.
승인 전까지는 아무것도 생성·수정·삭제하지 않으며, 전부 거절하는 것도 유효한 결과입니다.
미승인 항목은 백로그로 쌓이지 않고 폐기됩니다.

원 세션에서 나온 두 가지 설계 포인트: staleness sweep(내 세션의 변경이 그날
바로 주변 문서를 낡게 만든다 — 모순을 지금 고친다), 그리고 anti-forcing
rule("최대한 다 뽑아줘"는 모든 lane을 스윕하라는 뜻이지 기준을 낮추라는 뜻이
아니다; 0건도 유효한 결과이고 스킵은 사유와 함께 보고한다)입니다.

### `trend-briefing-doc`

커뮤니티 링크(Reddit/HN/X) 하나나 주제 한 줄을 균형 잡힌 트렌드 브리핑으로
만들고 싶을 때 사용합니다. 5–6개 출처 수집을 목표로 조사하고, 사실 전달이나
합의된 주제는 사실·영향·불확실성으로, 근거가 있는 서로 다른 입장은 A/B로
구성합니다. 동봉된 `template.html`(Pretendard + JetBrains Mono, 카드 레이아웃,
반응형)로 한국어 HTML 리포트를 렌더링합니다.

스타일은 의도적으로 담백합니다: 인용 댓글은 원문 링크와 함께 번역하고, 마지막
섹션은 승패 선언 대신 관찰과 한계를 서술합니다. 기본 산출물은 self-contained
HTML 파일이며, 발행 연동은 선택입니다. 정적 검증은 선택한 구조와 출처 링크의
존재를 확인합니다. 출처가 주장을 뒷받침하는지는 별도로 검토하며, HTML 검증
통과가 사실관계의 정확성을 보장하지는 않습니다.

### `ai-status`

AI/개발 서비스가 죽었는지 물어볼 때 사용합니다. 동봉된
`scripts/check_status.py`가 machine-readable status API를 병렬로 조회합니다
(핵심 6개 direct, `--extended` 시 서드파티 AIWatch 캐시로 10개 추가) — HTML
스크래핑과 Downdetector는 쓰지 않습니다.

핵심 교훈: **Statuspage incident impact는 운영 상태가 아닙니다.** 정책/컴플라이언스
incident(모델 recall, 수출통제)와 scope 제한 incident(FedRAMP 전용)는 component가
green인 동안 별도 섹션으로 보고해서, "Claude에 빨간 배너가 떴다"가 "Claude
장애"로 오보되지 않게 합니다. provider 표와 incident-kind 분류는
`reference.md` 참고.

## 작성 컨벤션

- Frontmatter: `name`, `description`; Claude skill은 필요 시 `argument-hint`, `allowed-tools` 추가
- 본문은 영어 (config file 규칙); 사용자 노출 prose는 한국어가 더 명확하면 한국어 허용
- 모든 스킬은 적어도 한 번의 실제 세션 경험을 코드화해야 함 — speculative skill 금지
- 알려진 실패 모드가 있으면 본문 마지막에 anti-patterns 섹션
- Codex/OpenAI 스킬 목록에 노출하려면 `agents/openai.yaml` 추가 (UI + policy metadata; 스키마: [openai/codex skill-creator](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/references/openai_yaml.md))

## License

이 저장소는 [MIT License](LICENSE.txt)를 따릅니다. 공개 대상인
`codex-context-migration` 스킬도 catalog-style skill packaging을 위해 자체
[`LICENSE.txt`](codex-context-migration/LICENSE.txt)를 포함합니다.
