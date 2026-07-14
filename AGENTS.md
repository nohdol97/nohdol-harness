# 루트 AGENTS.md — 멀티 프로젝트 하네스

> **이 저장소에는 하네스가 있다.** 이 디렉토리는 여러 하위 프로젝트(웹·앱·백엔드·k8s·AWS 등)를 담는 모노 워크스페이스이자, 그 프로젝트들의 하네스를 관리하는 하네스 프로젝트다.
> **어떤 작업이든 시작 전에 반드시 이 파일을 읽고, 하위 프로젝트 작업이라면 해당 프로젝트의 AGENTS.md도 읽는다.**
> 이 파일이 단일 원본(single source of truth)이다. CLAUDE.md는 이 파일을 가리키는 포인터일 뿐이다.

## 1. 프로젝트 레지스트리 → REGISTRY.md (미추적 — 설치처에서 생성)

라우팅 판단의 유일한 근거는 루트의 **REGISTRY.md**다. 어떤 프로젝트를 어디에 두는지는 이 하네스를 설치한 컴퓨터마다 다르므로, REGISTRY.md는 **git에 올리지 않는다**(gitignore, ADR 005). 경로 규약(프로젝트 배치 위치, 실험 공간 등)도 설치처별 사항이므로 REGISTRY.md에 기재한다.

**이 하네스를 새 컴퓨터에 설치(클론)하면 가장 먼저 REGISTRY.md를 생성해야 한다** — Claude Code / Codex에 "REGISTRY.md 만들어줘" 또는 "하네스 설치"라고 요청하면 `harness-install` 스킬이 프로젝트 스캔과 인터뷰로 생성한다. REGISTRY.md가 없는 세션은 설치 미완료 상태로 간주하고 harness-install을 먼저 안내한다.

프로젝트가 생기거나 없어지면 **metaskill이 REGISTRY.md를 갱신할 의무**가 있다. 크로스 프로젝트 여부는 레지스트리의 "연관 프로젝트" 컬럼으로 판단한다.

**컬럼 채우는 방식 (2026-07-13 사용자 확정)**:
- **역할**: 인터뷰로 묻지 않고 프로젝트의 README·문서를 **직접 읽어** 채운다. 문서가 없으면 "미확인"으로 정직하게 표기한다. 이유: 사용자 기억보다 프로젝트 문서가 정확하고, 인터뷰 부담을 줄인다.
- **연관 프로젝트**: 설치·인터뷰 시점에 추측으로 채우지 않는다. **실작업에서 사용자가 프로젝트들을 함께 엮을 때**(크로스 프로젝트 작업 수행 시) 그 세션이 작업 종료 시점에 해당 행들을 갱신한다 — 초기값은 "미기록". 이유: 추측된 연관은 라우팅을 오염시키고, 관찰된 연관만이 근거가 된다.
- **경로 규약**: 현행 유지 — harness-install 인터뷰에서 확정한다(기본 `project/<이름>/`).

## 2. 상속과 우선순위

- 하위 프로젝트 AGENTS.md는 이 루트 AGENTS.md를 **상속**하며, 첫 줄에 상속 사실을 명시한다.
- 규칙이 충돌하면 **더 구체적인 하위 프로젝트 규칙이 우선**한다. 이유: 도메인 맥락을 아는 쪽이 더 정확한 판단을 내리기 때문이다.
- **단, 아래 3절 안전 가드레일만은 항상 루트가 우선하며 하위에서 완화할 수 없다.**

## 3. 안전 가드레일 (하위에서 완화 불가)

이 하네스는 인프라(k8s, AWS)까지 다루므로 실수의 반경이 코드베이스를 넘어선다.

- **파괴적 작업은 반드시 실행 전 사용자 확인**: 리소스 삭제, 프로덕션 배포·롤백, DB 마이그레이션 실행, `git push --force`, IAM/권한 변경 등. **예외 없음** (dev 환경 포함 전부 확인 — 2026-07-12 사용자 확정).
- **시크릿·자격증명은 하네스 파일과 `_workspace/`에 절대 기록하지 않는다.**

## 4. `_workspace/` 규약

- 위치는 **루트에 단일**로 둔다. 이유: 크로스 프로젝트 작업의 산출물을 한 곳에서 조율하기 위해서다.
- 구조: `_workspace/<작업명>/`
- 산출물 네이밍: `phase{N}_{에이전트명}_{내용}.md` (예: `phase2_researcher-a_report.md`)
- 팀 이벤트: `_workspace/<작업명>/team-log.jsonl`에 append-only — 이벤트 스키마(7종)와 기록 시점은 orchestrate 스킬의 **이벤트 계약**이 단일 원본이다. 실행 모드(팀/서브에이전트) 무관하게 오케스트레이터가 기록한다.
- `_workspace/`는 gitignore 대상이다. 세션 산출물이지 하네스가 아니다. team-log.jsonl 포함 전체 미보존(2026-07-12 사용자 확정). **예외**: `_workspace/harness-updates.md`(하네스 업데이트 대기 큐, 5절 설치처 프로필)와 점검 마커(`.harness-review-*`)는 세션을 넘는 운영 데이터라 정리 대상에서 제외한다.

## 5. git 규칙

- **저장소 분리**: 루트 저장소는 하네스(AGENTS.md, CLAUDE.md, README.md, `.agents/`, `.claude/` 심링크와 settings.json, `.gitignore`, `.gitattributes`, `docs/` — adr/은 구조 결정, specs/는 루트 자체 코드(훅 등)의 스펙)만 추적한다. 하위 프로젝트는 각자 **독립 git 저장소**에서 커밋·푸시한다(ADR 002, 배치 위치는 REGISTRY.md 경로 규약). 이유: 프로젝트마다 배포·CI 주기가 다르며, 하네스 이력이 프로젝트 커밋에 묻히면 안 된다.
- **커밋 컨벤션**: Conventional Commits. 스코프에 프로젝트명을 포함한다. 예: `feat(web): ...`, `fix(k8s): ...`, `chore(harness): ...` (하위 프로젝트 저장소에서도 동일 컨벤션 적용)
- 하네스 파일(AGENTS.md, CLAUDE.md, README.md, `.agents/`, `.claude/` 심링크와 settings.json, `.gitignore`, `.gitattributes`, `docs/`)은 **절대 gitignore에 넣지 않는다.** gitignore 대상은 설치 환경별 요소 — `_workspace/`, `project/`, `dev/`, `REGISTRY.md`, `.agents/projects/`(및 OS 파일) — 뿐이다(ADR 002·005·006).
- 하네스 변경 커밋에는 해당 파일의 **변경 이력 테이블 갱신을 같은 커밋에 포함**한다. 이유: 이력과 코드가 어긋나면 이력을 아무도 믿지 않게 된다.
- **작업 완료 시 커밋·푸시를 기본으로 진행한다** (사용자 상시 승인, 2026-07-12). 단, `git push --force` 등 파괴적 git 작업은 3절 가드레일에 따라 여전히 개별 확인이 필요하고, **사내 프로필 설치처에서는 이 기본이 적용되지 않는다**(아래 설치처 프로필 규칙).
- **설치처 프로필 (개인/사내)**: 이 저장소는 개인 계정 소유이므로, 설치처가 어디냐에 따라 푸시 가능 여부가 갈린다. 프로필은 REGISTRY.md 상단에 기록한다(harness-install 인터뷰) — `개인`(하네스 수정·커밋·푸시 가능) / `사내`(**추적 하네스 파일 수정·커밋·푸시 전면 금지** — 사내 머신에서 개인 원격으로의 푸시는 보안 정책 위반이고, 커밋만 쌓아도 결국 푸시가 필요해 발산한다). **사내에서 하네스 개선이 필요하면 저장소를 고치는 대신 `_workspace/harness-updates.md`(미추적) 대기 큐에 기록한다.** 항목 형식: `## YYYY-MM-DD 제목` 아래 상태(대기/적용됨) / 대상 파일 / 변경 내용 / 사유·근거(신호) — 변경 내용은 **그 세션의 맥락 없이도 개인 머신에서 그대로 적용할 수 있는 수준**으로 구체적으로 쓴다(대상 절·문구·추가 위치까지). 이 파일은 미추적이라 git으로 전달되지 않는다 — 사용자가 내용을 개인 머신으로 직접 옮기고(파일 복사·붙여넣기), 개인 설치처에서 "하네스 업데이트 적용"을 요청하면 metaskill이 항목을 적용하고 상태를 `적용됨`으로 갱신한다. **프로필 미기록 상태에서 하네스 파일을 수정하게 되면 먼저 사용자에게 프로필을 확인해 REGISTRY.md에 기록한다**(단, 이 저장소를 직접 클론해 PR로 작업하는 원격 세션은 개인 프로필로 간주). 이유: 수정 자체를 개인 설치처로 이월해야 사내 정책과 하네스 진화가 양립한다.
- **하위 프로젝트 브랜치 규칙**: 하위 프로젝트 작업은 `branch-workflow` 스킬을 따른다 — 시작 시 main 최신화 후 새 브랜치, 마무리 시 PR 직전 rebase → 푸시 → PR 생성(머지는 사용자). **이 루트 하네스 저장소만 main 직커밋 예외**다(문서 중심, 2026-07-12 인터뷰 확정).
- **배포·릴리스 규칙**: 머지 이후 배포는 `release` 스킬을 따른다 — 런북 초안(롤백 절 필수) → 변경 단계별 사용자 확인(3절, dev 포함 예외 없음) → 배포 후 검증 → work-tracker 마무리. 외부 배포 스킬(플러그인 등)은 이 절차 안의 보조 도구로만 쓴다.

## 6. 문서 규칙

- **변경 이력 테이블**(경량 로그): 각 AGENTS.md 하단 필수. 컬럼: 날짜 / 변경 내용 / 대상 / 사유.
- **ADR**(구조적 결정 기록): `docs/adr/NNN-제목.md`. 형식: 날짜, 변경 내용, 대상, 사유.
- **ADR 작성 트리거**: ① 에이전트가 8개 이상이 될 때 ② 현재 구조에 대한 질문이 반복될 때 ③ 패턴 전환(예: 파이프라인→팬아웃)이 일어날 때 ④ 저장소·디렉토리 구조 등 구조적 결정이 일어날 때.

## 7. 라우팅 규칙

1. 요청을 받으면 **REGISTRY.md의 프로젝트 레지스트리**에서 관련 프로젝트를 식별한다.
2. 해당 프로젝트의 AGENTS.md(하네스)를 로드한다.
3. **단일 프로젝트**면 그 하네스로 작업하되, **구현·다단계 작업이면 `orchestrate`의 팀 필요성 판정(Phase 0-1 게이트)을 거쳐** 직접 수행 / 단독 서브에이전트 / 생성-검증 쌍 / 팀 중 하나로 정한다(ADR 010). 판정 없이 복잡한 작업을 단일 컨텍스트로 처리하는 것은 하네스 우회 신호로 취급한다(8절).
4. **다중 프로젝트**(레지스트리의 "연관 프로젝트" 컬럼이 얽히는 요청)면 `orchestrate` 스킬로 팀을 구성한다. 패턴 선택은 `.agents/skills/metaskill/references/patterns.md`의 플로우차트·전환 신호 표를 따르고, **위임 깊이는 2단계(총괄→팀장→실무자)를 초과하지 않는다** — 지연이 기하급수적으로 증가하기 때문이다.

## 8. 진화 트리거 (자동화 판단 규칙)

아래 3신호 중 하나라도 감지되면 **에이전트/스킬 신설 또는 개선을 사용자에게 제안**하고, 승인 시 metaskill로 생성한다. 관찰 절차는 `harness-review` 스킬로 실행하며, 주기는 **2단** — 일일 경량(마지막 점검 이후의 3신호 스캔만, 무신호면 한 줄 보고)과 주간 전체(무결성 점검 포함). **실행은 SessionStart 리마인더 훅이 자동 트리거한다** — 마커(`_workspace/.harness-review-daily-last`·`.harness-review-last`)로 1일/7일 경과를 판정해 다음 세션 시작 시 실행 지시가 주입되므로 기억에 의존하지 않는다(2026-07-14 사용자 확정 — 비효율은 매일 잡는다).

| 신호 | 기준 |
|---|---|
| 반복 요청 | 같은 유형의 요청이 **3회 이상** 반복 |
| 반복 실패 | 같은 실패가 **2회 이상** 반복 |
| 우회 관찰 | 하네스를 우회해서 처리한 사례 관찰 |

## 9. 티어→모델 매핑 (이 표가 유일한 매핑 원본)

에이전트 frontmatter에는 모델명이 아니라 **역할 티어**만 적는다. 이유: 모델명은 CLI·시점마다 계속 바뀌지만 역할은 바뀌지 않기 때문이다. 구체 모델명을 하네스에 고정하지 않고, **사용 중인 CLI의 현재 라인업에서 아래 선택 기준으로 고른다.**

| 티어 | 용도 | 선택 기준 (CLI 무관) |
|---|---|---|
| design | 설계·검증·리뷰·최종 판정 | 해당 CLI의 **최고 성능(최고 추론) 모델** |
| implement | 구현·일반 작업 | 표준(균형) 모델 |
| explore | 탐색·수집·요약 | 표준 모델. 경량 모델은 사용자가 명시 요청한 경우에만 |

> **경량(최저가) 모델 사용 금지** (사용자 전역 정책): 검증·리뷰·최종 확인에서는 절대 금지 — false negative 오탐 시 이미 완료된 작업을 재작업하는 손실이 크다. 사용자가 명시적으로 "빠르게/가볍게" 요청한 경우에만 예외.

## 10. 에이전트 정의 규칙 (metaskill·orchestrate가 팀원 정의 시 따를 것)

에이전트 정의 파일은 `.agents/agents/<이름>.md`에 두고(`.claude/agents`는 심링크), frontmatter에 `name` / `description`(Pushy 공식) / `tools`(허용 도구 화이트리스트) / `tier`(design·implement·explore)를 명시한다. 상세 템플릿: `.agents/skills/metaskill/references/agent-rules.md`

필수 섹션 10가지: ① 핵심 역할(하지 않는 일 포함) ② 작업 원칙(충돌 시 판단 기준) ③ 입출력 프로토콜(`_workspace/` 경로) ④ 팀 통신 프로토콜(JSON 메시지 형식) ⑤ 에러 핸들링(재시도 1회, 2회 실패 시 누락 명시) ⑥ 협업 위치 ⑦ 품질 자체 검증 체크리스트 ⑧ 재호출 지침 ⑨ tools 최소 권한 ⑩ 역할 티어.

## 11. 멀티 CLI 호환 (Claude Code + Codex 병행)

- 에이전트·스킬 정의 원본: `.agents/agents/`, `.agents/skills/` (공용 디렉토리)
- `.claude/agents`, `.claude/skills`는 위 공용 디렉토리로의 **심볼릭 링크** — Claude와 Codex가 같은 파일을 본다.
- **새 에이전트·스킬은 반드시 `.agents/` 원본 디렉토리에 생성한다. `.claude/` 경로에 직접 파일을 만들지 않는다.** 이유: `.claude/`는 심링크일 뿐이라 원본처럼 보이지만, 심링크가 실파일로 대체되는 순간 두 CLI가 서로 다른 파일을 보게 되고 동기화가 조용히 깨진다. `.claude/` 아래 실파일 발견은 하네스 우회 신호로 취급한다(8절).
- 심링크가 불가한 환경이면 sync 스크립트로 대체하고 그 사실을 ADR에 기록한다.
- **외부 도구가 스킬을 설치할 때는 전역 경로(홈 디렉토리)로** 설치한다 — 예: `agentsview skills install` → `~/.claude/skills/`·`~/.agents/skills/`. 이 워크스페이스에 프로젝트 모드(`--project` 등)로 설치하지 않는다. 이유: 워크스페이스의 `.claude/`는 심링크라 설치물이 공용 `.agents/skills/`에 떨어져 **설치처별 도구 산출물이 공용 저장소의 커밋 대상**이 된다.

## 12. 하위 프로젝트 하네스 중앙 관리 (ADR 006)

모든 하위 프로젝트의 하네스는 **이 워크스페이스에서 일원 관리**한다. 하위 프로젝트 디렉토리와 그 git 저장소에는 하네스 파일을 일절 두지 않는다(심링크·복사본 포함). 이유: 하위 프로젝트 작업은 루트에서 세션을 열어 수행하고, 라우팅(7절)이 하네스 읽기를 강제하므로 프로젝트 쪽에 배포 장치를 둘 필요가 없다 — 배포본은 원본과 어긋나는 순간부터 부채다.

- **원본 위치(유일본)**: `.agents/projects/<이름>/` — 구성: `AGENTS.md`, `adr/`, 그리고 필요해졌을 때의 `skills/`·`agents/`. `<이름>`은 REGISTRY.md 레지스트리 행과 일치해야 한다. **하위 CLAUDE.md는 만들지 않는다** — CLAUDE.md는 세션 시작 디렉토리에서 자동 로드되라고 있는 파일인데 이 경로에서 세션을 시작할 일이 없으므로 죽은 파일이다.
- **미추적**: `.agents/projects/`는 REGISTRY.md와 같은 설치처별 데이터다 — 컴퓨터마다 두는 프로젝트가 다르므로 gitignore한다(ADR 005의 연장). 따라서 하위 하네스는 어느 git에도 올라가지 않는다. 이력·원격 복구가 없다는 트레이드오프는 사용자가 수용했다(2026-07-13).
- **라우팅으로 연결**: 하위 프로젝트 작업 시 REGISTRY.md에서 프로젝트를 식별한 뒤 `.agents/projects/<이름>/AGENTS.md`를 읽는다. 이것이 7절 2단계("해당 프로젝트의 AGENTS.md를 로드한다")의 실제 경로다.
- **규칙의 운반체는 문서다**: 가드레일·필수 규칙은 반드시 하위 AGENTS.md(문서)에 싣는다. 스킬·훅·설정은 세션 시작 디렉토리(cwd) 기준으로만 로드되는 편의 장치라, 규칙의 유일한 운반체가 될 수 없다.
- **하위 전용 스킬·에이전트는 지연 생성(lazy)**: 초기에는 만들지 않는다. **반복되는 작업이 관찰되거나 작업 중 "스킬·에이전트로 등록하면 좋겠다" 싶은 것이 나타났을 때** 사용자에게 제안하고, 승인 시 `.agents/projects/<이름>/skills/`·`.agents/projects/<이름>/agents/`에 생성한다(2026-07-13 사용자 확정). 미리 만든 스킬은 실사용과 어긋나 우회되고, 내용 없는 문서는 부채다.
- **하위 스킬·에이전트도 git에 안 들어간다**: `.agents/projects/` 전체가 미추적이므로 자동으로 제외된다. 이 위치는 CLI가 자동 발견하지 못하므로, **하위 AGENTS.md에 스킬·에이전트 목록과 경로를 명시**해 라우팅이 읽게 한다 — 규칙의 운반체는 문서라는 원칙과 같은 메커니즘이다. 여러 프로젝트·설치처에 일반화되는 스킬만 루트 `.agents/skills/`로 승격한다(추적됨).
- **훅**: 하위 프로젝트 전용 훅은 루트 `.claude/settings.json`에 경로 분기형으로만 둔다(스크립트가 대상 경로를 검사해 분기). 훅은 세션 루트 것만 실행되기 때문이다.
- **세션 시작 관행**: 하위 프로젝트 작업을 포함한 모든 작업은 루트에서 세션을 시작한다. `project/<이름>/`에서 직접 열면 하네스가 전혀 로드되지 않는다.

## 13. 개발 방법론 — 스펙 주도(SDD) + 테스트 주도(TDD)

기능 추가·동작 변경에 해당하는 모든 코드 작업에 적용한다(2026-07-13 사용자 확정). 오타·주석·설정값 등 동작이 변하지 않는 사소한 수정은 제외.

1. **스펙 먼저**: 구현 전에 스펙 문서를 확정한다 — `doc-writer` 스킬의 스펙 템플릿(배경·목표·비목표·요구사항·완료 기준) 사용. 위치는 **해당 프로젝트 저장소의 `docs/specs/`** — 스펙은 하네스가 아니라 프로젝트 산출물이므로 코드와 함께 커밋된다. 이유: 스펙 없는 구현은 완료 판정 기준이 없어 리뷰가 취향 싸움이 된다.
2. **테스트 먼저**: 스펙의 완료 기준을 **실패하는 테스트**로 옮긴 뒤 구현한다. 순서: 실패 테스트 → 최소 구현 → 통과 → 리팩토링. 버그 수정은 재현 테스트부터. **테스트 없이 "구현 완료"를 선언하지 않는다.**
3. **리뷰는 스펙 대비로**: 리뷰(`team-review` 스킬, reviewer 에이전트)는 스펙의 완료 기준을 판정 기준으로 삼는다 — 기준이 문서에 있으니 판정이 재현 가능해진다.
4. **실행 계층 게이트(훅)**: 루트 `.claude/settings.json`의 PreToolUse 훅(`.agents/hooks/tdd-gate.py`)이 `git commit` 시점에 코드 파일이 테스트 변경 없이 커밋되는 것을 차단한다. 동작 불변 수정은 **사용자 확인 후** 커밋 메시지에 `[no-test]`를 표기해 통과시킨다. 예외 경로: 루트 하네스 저장소(문서 중심), `dev/`(실험 공간), 최초 커밋. 훅은 Claude Code 세션에만 작동하는 보조 장치이며 규칙의 원본은 이 문서다 — 판단 불가 상황은 통과(fail-open)한다. 훅 수정 시 회귀 테스트(`.agents/hooks/tdd-gate_test.py`)를 통과해야 한다. 상세: docs/adr/008, 스펙: docs/specs/2026-07-13-tdd-gate-hook.md.

## 14. 작업 추적 — 세션 영속 (ccpm 패턴)

`_workspace/`와 세션 컨텍스트는 미보존이므로, **세션을 넘는 작업의 상태는 해당 프로젝트 저장소에 영속화**한다(`work-tracker` 스킬) — GitHub 원격이 있으면 GitHub Issues(에픽 이슈 + 태스크 체크리스트 + 진행 로그 코멘트), 없으면 저장소의 `docs/backlog.md`. 이유: 상태는 코드와 같은 곳에 있어야 어긋나지 않는다.

- **등록 기준**: 한 세션에 끝나지 않을 작업만(여러 PR·며칠 규모·사용자 명시 요청). 전수 등록은 이슈 무덤을 만든다 — 지연 생성(ADR 007)과 같은 철학.
- **세션 종료·중단 시** 진행 로그(완료/다음/막힘)를 남기는 것이 재개의 시작점이다. `_workspace/` 산출물 중 다음 세션에 필요한 결론은 요약해 코멘트로 옮긴다.
- **완료는 PR `Closes #N`**로 코드와 상태를 함께 닫는다(branch-workflow 마무리 절차와 연결). 상세: docs/adr/009.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-12 | 루트 하네스 초기 구성 (AGENTS.md, CLAUDE.md, orchestrate, metaskill, ADR 001) | 루트 전체 | harness-bootstrap-prompt.md 기반 초기 구축. 상세 결정은 docs/adr/001-initial-harness.md |
| 2026-07-12 | `project/`·`dev/` 분리 구조 반영 — 경로 규약·저장소 분리 규칙 추가, README 신설 | 1절, 5절, .gitignore, README.md | 하위 프로젝트를 독립 저장소로 운영하기로 사용자 확정. docs/adr/002-project-dir-separation.md |
| 2026-07-12 | `.claude/` 직접 생성 금지 규칙 명시. explorer·reviewer 에이전트, harness-review 스킬 신설 | 11절(구 12절), .agents/agents/, .agents/skills/harness-review/ | 심링크 원본 규칙이 암시에 그침(사용자 지적). orchestrate 반복 역할 2종과 주 1회 진화 관찰 절차의 실행 수단 부재 |
| 2026-07-12 | "완벽주의 금지" 절 삭제, 절 번호 재조정(10→9, 11→10, 12→11), 전 문서 교차 참조 갱신 | 구 9절, 전 문서 | 사용자 방침 — 완성도에 상한 없음. docs/adr/003-perfectionism-clause-removal.md |
| 2026-07-12 | reviewer 1차 독립 검증 반영 — gitignore 문구 정정, 추적 대상 열거 보완, ADR 트리거 ④ 추가, 라우팅 문구 완화, 도구 제약 서술 정직화, 레지스트리 임시 등록 5행 | 1·5·6·7·8절, 에이전트 2종, README, ADR 001 | 검증 발견 F1~F11 — `_workspace/harness-perfection-review/phase1_reviewer_verdict.md` |
| 2026-07-12 | 레지스트리를 REGISTRY.md로 분리, implementer·integrator 신설(표준 로스터 4종 완성), orchestrate 개정(로스터 재사용·게이트 단일 원본 이관, team-log 이벤트 계약) | 1·5·7절, REGISTRY.md, .agents/ | 사용자 확정 — AGENTS.md는 공용, 레지스트리는 설치 환경별. reviewer 3차 검증 통과. docs/adr/004-registry-separation-standard-roster.md |
| 2026-07-12 | 커밋 규칙 변경 — 작업 완료 시 커밋·푸시 기본 진행 | 5절 | 사용자 상시 승인 ("커밋 푸시는 작업 완료하면 무조건 진행") |
| 2026-07-12 | 이식성 개편 — REGISTRY.md 미추적 전환+설치 시 생성 의무, 경로 규약 REGISTRY.md 이관, 티어 표 탈모델명, harness-install·project-status 스킬 신설 | 1·5·9절, .gitignore, .agents/skills/ | 사용자 확정 — 여러 컴퓨터에서 사용. docs/adr/005-registry-untracked-portable-harness.md |
| 2026-07-12 | branch-workflow 스킬 신설 + 5절 하위 프로젝트 브랜치 규칙 추가 | 5절, .agents/skills/branch-workflow/ | 반복 실패 관찰(오래된 브랜치 시작→머지 충돌) + 사용자 인터뷰 확정(main 최신화→새 브랜치→PR 직전 rebase→PR 생성, 머지는 사용자) |
| 2026-07-13 | 12절 신설 — 하위 프로젝트 하네스 중앙 관리: 원본은 `.agents/projects/<이름>/` 단일, 미추적(설치처별), 배포 장치 없음(라우팅이 연결), 하위 전용 스킬·훅은 루트에 | 5·12절, .gitignore, metaskill, orchestrate, harness-review, harness-install, README | 사용자 확정 — 모든 하위 하네스는 루트 워크스페이스에서 관리하고, 컴퓨터마다 프로젝트가 다르므로 REGISTRY.md처럼 미추적. docs/adr/006 |
| 2026-07-13 | 레지스트리 컬럼 채우기 방식 확정 — 역할은 README 등 문서 직접 관찰, 연관 프로젝트는 실작업 관찰 시 갱신(초기 "미기록"), 경로 규약은 인터뷰 유지 | 1절, harness-install, orchestrate, metaskill | 사용자 확정 — 인터뷰 추측 대신 관찰 기반. 추측된 연관은 라우팅을 오염시킨다 |
| 2026-07-13 | 하위 스킬·에이전트 지연 생성 전환 — 초기 키트 폐지, 위치를 루트 접두어에서 `.agents/projects/<이름>/skills/`·`agents/`(미추적)로 변경, 하위 CLAUDE.md 규격 삭제 | 12절, metaskill, scaffold, .agents/projects/README | 사용자 확정 — 반복 관찰·등록 가치 발견 시에만 생성, 프로젝트 스킬은 git 미포함. docs/adr/007 |
| 2026-07-13 | 13절 신설(SDD+TDD 개발 방법론), doc-writer·team-review 스킬 신설 | 13절, .agents/skills/doc-writer/, .agents/skills/team-review/, README | 사용자 확정 — 스펙·테스트 주도 작업 규칙, 일관 형식 문서 작성, 규모 스케일링 팀 리뷰 |
| 2026-07-13 | 13절에 TDD 게이트 훅 추가(4항) — `.agents/hooks/tdd-gate.py`(+회귀 테스트·스펙) + `.claude/settings.json` 신설, 5절 추적 목록에 settings.json·.gitattributes·docs/specs 반영 | 5·13절, .agents/hooks/, .claude/settings.json, docs/specs/, .gitignore | 문서 규칙은 강제력이 없음 — 커밋 시점 차단으로 실행 계층 보증(사용자 승인, Superpowers 패턴). reviewer 1·2차 검증 F1~F12 반영. docs/adr/008 |
| 2026-07-13 | 14절 신설(세션 영속 작업 추적) + work-tracker 스킬 신설 | 14절, .agents/skills/work-tracker/, CLAUDE.md, README | `_workspace/`·세션 컨텍스트 미보존으로 세션 경계에서 작업 상태 유실 — ccpm 패턴 채택(사용자 승인). docs/adr/009 |
| 2026-07-13 | orchestrate 범용 게이트화 — 7절 3항 개정(구현·다단계 작업은 팀 필요성 판정 필수), orchestrate Phase 0-1 판정 4등급·검증 필수 규칙·하이브리드 표준 스켈레톤 신설, patterns.md 복합 패턴 절 확장, CLAUDE.md 스킬 우선순위 신설(특화>게이트, 하네스>외부), harness-review 우회 신호 확장, 규모 임계 단일 원본 지정 | 7절, .agents/skills/orchestrate/·harness-review/·team-review/·metaskill/, .agents/agents/implementer.md, CLAUDE.md, README | 사용자 요청 — 팀 필요 판정 주체 부재로 복잡 작업이 판정 없이 단일 컨텍스트 처리됨. reviewer 검증 F1~F11(외부 스킬 트리거 충돌 포함 — 사용자 지시 기준) 반영. docs/adr/010 |
| 2026-07-13 | PR 본문 템플릿 신설 — doc-writer 템플릿 5번 추가, branch-workflow 마무리 4단계가 참조(Closes #N으로 work-tracker 연결) | .agents/skills/doc-writer/, .agents/skills/branch-workflow/ | 사용자 요청 — PR도 문서처럼 고정 형식으로. 템플릿 단일 원본은 doc-writer. docs/adr/010 |
| 2026-07-13 | 표준 로스터 4종→7종 확장 — architect·troubleshooter·infra-specialist 신설, implementer Edit 서술 정정, orchestrate 로스터 표·스켈레톤 담당 갱신 | .agents/agents/, .agents/skills/orchestrate/, README | 사용자 승인 — 인기 하네스(BMAD·Superpowers 등) 로스터 대조 검토: 스켈레톤 Phase ② 공백(architect), 인과 확정 역할 부재(troubleshooter), 인프라 프로젝트 대응(infra-specialist). docs/adr/011 |
| 2026-07-13 | release 스킬 신설(머지 이후 배포 워크플로우 — 런북→단계별 확인→검증→work-tracker 마무리) + 5절 배포·릴리스 규칙 앵커 + team-review 관점 축에 UX·접근성 추가 | 5절, .agents/skills/release/, .agents/skills/team-review/, CLAUDE.md, README | 사용자 승인(풀스택 커버리지 점검) — PR 머지 이후 절차 공백은 가드레일 최중요 구간의 무절차, 프론트 diff에 접근성 검증 관점 부재. 5절 앵커는 Codex 세션 구속용(규칙은 문서가 운반 — reviewer phase6 F1) |
| 2026-07-14 | agentsview 연동 — harness-review 신호 실측(session search·stats)·secrets scan 사후 검증, harness-install 3단계(도구+finding-history 스킬 전역 설치) 신설, 11절 외부 도구 스킬 전역 설치 규칙 | 11절, harness-review, harness-install | 사용자 승인(kenn-io/agentsview 검토) — 주간 점검의 신호 관찰이 세션 기억 의존에서 세션 이력 실측으로. 프로젝트 모드 설치는 심링크 경유로 공용 저장소를 오염 |
| 2026-07-14 | agentsview-daemon SessionStart 훅 신설(스펙+회귀 테스트) — 세션 시작 시 동기화 데몬 자동 기동, 로컬 DB 고정·외부 동기화 금지 문구 보강 | .agents/hooks/, .claude/settings.json, docs/specs/, harness-install, README | 사용자 요청 — 동기화 수동 기동 제거. fail-open으로 미설치 환경 무간섭 |
| 2026-07-14 | harness-review-reminder SessionStart 훅 신설(스펙+회귀 테스트) — 마지막 점검 7일 경과 시 세션 시작에 실행 지시 주입, harness-review에 완료 마커 갱신 단계 추가 | 8절, .agents/hooks/, .claude/settings.json, docs/specs/, harness-review, README | 사용자 요청(주간 점검 cron화) — 제안 승인에 사람이 필요하고 신호 데이터가 로컬에 있어, 무인 cron 대신 세션 트리거 방식 채택 |
| 2026-07-14 | 점검 주기 2단 확장 — 일일 경량 모드(1일, 3신호 스캔만·무신호 시 한 줄) 신설, 리마인더 훅 마커 2개 판정으로 개정 | 8절, .agents/hooks/harness-review-reminder.py, harness-review, docs/specs | 사용자 확정 — "일주일은 너무 길다, 비효율은 매일 새 세션에서 점검" |
| 2026-07-14 | 설치처 프로필(개인/사내) 신설 — 사내는 추적 하네스 파일 수정·커밋·푸시 금지, 개선 사항은 `_workspace/harness-updates.md` 대기 큐 기록 후 개인 설치처에서 metaskill로 적용. 4절 `_workspace/` 미보존에 큐·마커 예외 명시 | 4·5절, harness-install, harness-review, metaskill, README | 사용자 확정 — 하네스를 사내에서도 쓰는데 저장소는 개인 소유라 사내에서 개인 git 푸시 불가. docs/adr/012 |
