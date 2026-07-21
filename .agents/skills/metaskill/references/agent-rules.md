# 에이전트 정의 규칙 — 10섹션 템플릿

에이전트 정의 파일은 `.agents/agents/<이름>.md`에 둔다 (`.claude/agents`는 심링크). metaskill과 orchestrate가 팀원을 정의할 때 이 템플릿을 따른다.

## frontmatter (필수 4필드)

```yaml
---
name: <이름>
description: <Pushy 공식 — 동사 나열 + 트리거 상황 + 재실행 키워드 (+ 인접 역할과 경계가 겹치면 "Do NOT …"/"~는 제외" 부정 트리거 권장 — 오라우팅 능동 차단). 영문 기술 + 한국어 재실행 키워드 병기 권장>
tools: <허용 도구 화이트리스트 — 최소 권한>
tier: design | implement | explore   # 모델 매핑은 루트 AGENTS.md 9절 표가 유일 원본
---
```

**tier는 CLI가 해석하지 않는다** — 실제 적용은 오케스트레이터가 팀원 생성(Agent 호출) 시 9절 표에 따라 `model` 파라미터를 지정하는 것으로 이루어진다(orchestrate "티어 적용" 규칙). 정의 파일에 구체 모델명을 고정하지 않는 이유: 모델명은 시점마다 바뀌지만 역할은 바뀌지 않는다(9절).

## Codex custom-agent 어댑터 (루트 에이전트 필수)

루트 에이전트는 원본 `.agents/agents/<이름>.md`와 함께 `.codex/agents/<이름>.toml`을 둔다(ADR 027). TOML에는 Codex 필수 필드 `name`·`description`·`developer_instructions`만 두고, `developer_instructions`가 현재 작업 디렉터리부터 상위로 대응 Markdown을 찾아 **작업 전 전문을 읽도록** 지시한다. `name`·`description`은 원본 frontmatter와 정확히 일치시킨다.

역할 본문·`tools`·`tier`를 TOML에 복사하지 않는다. 특히 `model`·`model_reasoning_effort`·`sandbox_mode`를 고정하면 9절 동적 티어와 부모 세션 권한을 별도 원본으로 갈라놓으므로 넣지 않는다. 생성 후 `python3 .agents/hooks/integrity-check.py`로 Markdown↔TOML 1:1·메타데이터·계약 참조를 검증한다.

**tools 필드가 가드레일 1순위다.** 최소 권한, 도구 최소화, 명시적 제외. 이유: 프롬프트의 "하지 마라"는 어길 수 있지만 없는 도구는 쓸 수 없다. 단, **남겨둔 도구의 사용 범위 제한(예: "Write는 `_workspace/` 전용")은 프롬프트 제약이므로 완전 강제가 아니다** — 정의 문서에 보장 수준을 과대 기술하지 말 것.

**조회·검증 역할(Edit 미보유 — explorer·reviewer·troubleshooter 류)의 Bash는 저장소 상태(작업 트리·인덱스·HEAD) 불변이 규약이다 (이 단락이 단일 원본)**: 비교 목적 `git stash`·`checkout/restore`·`reset`·`clean` 금지 — "stash pop으로 복구되니 무해"해 보여도, 같은 작업 트리에 오케스트레이터·병행 작업의 uncommitted 변경이 공존할 수 있다(2026-07-21 실측 2회 — 스택 브랜치 작업 중 리뷰어 stash 반복). before/after 비교는 `git diff <ref>..<ref>`·`git show <commit>:<path>`로, **HEAD 이동이 필요한 진단(`git bisect` 등)은 `git worktree add` 격리 사본에서** 수행하고 끝나면 제거한다(worktree 추가·제거는 메인 트리 불변). 구현 역할(Edit 보유)도 자기 산출물이 아닌 **비교 목적의 트리 조작(stash)은 동일 금지**다.

## 본문 필수 섹션

1. **핵심 역할 — 범위 설정**: 하는 일과 함께 **하지 않는 일**의 경계를 명시. (예: "리뷰어는 코드를 수정하지 않는다")
2. **작업 원칙 — 판단 기준**: 두 선택지가 충돌할 때 어느 쪽을 택할지. (예: 속도 vs 정확성 → 정확성) 이유: 판단 기준 없는 에이전트는 충돌 상황마다 다른 답을 낸다.
3. **입출력 프로토콜**: 에이전트 간 API 계약. 입력 형식, 출력 형식, 중간 산출물은 `_workspace/<작업명>/phase{N}_{에이전트명}_{내용}.md`. 파일 출력 언어뿐 아니라 **오케스트레이터에게 반환하는 최종 텍스트의 언어**도 명시한다 — 기본은 영어(루트 15절, 모델만 읽는 채널)이고, 그 에이전트의 산출물이 사용자에게 그대로 전달되는 문서(예: integrator 최종 통합 리포트, architect 스펙 초안)일 때만 한국어 예외를 둔다.
4. **팀 통신 프로토콜**: 누구에게, 무엇을, 언제 보내는지. SendMessage에는 발견 사실 + 수신자가 취해야 할 행동을 명시. 메시지 형식 고정(JSON): `{type, severity, file, line, claim, request}`
5. **에러 핸들링 — 종료 조건**: 구체적 실패 시나리오와 최대 재시도 횟수. 기본: 1회 재시도, 2회 실패 시 누락을 명시하고 진행, 팀원 2명 이상 실패 시 팀 해체 후 사용자 보고.
6. **협업 — 팀 안에서의 위치**: 누구와 어떤 순서로 연결되는지 (의존성 그래프상 위치).
7. **품질 자체 검증**: 출력 반환 전 자기 점검 체크리스트.
8. **재호출 지침**: 새 세션에서도 하네스가 자동으로 다시 호출되도록 — 어떤 상황·키워드에서 이 에이전트를 다시 써야 하는지 명시.
9. *(frontmatter의 tools로 충족)* — 본문에서 도구 사용 제약의 이유를 한 줄 보강.
10. *(frontmatter의 tier로 충족)* — 티어 선택 근거를 한 줄 보강.
