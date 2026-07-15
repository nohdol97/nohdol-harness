# nohdol-harness

여러 프로젝트(웹·앱·백엔드·k8s·AWS)를 한 곳에서 지휘하기 위한 **루트 하네스 워크스페이스**.

Claude Code / Codex를 **이 디렉토리에서 열고** 프로젝트 작업을 지시하면, 하네스가 요청을 관련 프로젝트로 라우팅하고 해당 프로젝트의 규칙(AGENTS.md)을 로드해 작업한다. 이 저장소가 추적하는 것은 **하네스뿐**이다 — 실제 프로젝트 코드는 `project/` 아래 각자의 독립 git 저장소에 산다.

## 디렉토리 구조

```
nohdol-harness/
├── AGENTS.md              # 단일 원본(공용 규칙) — 가드레일·라우팅·진화 트리거·티어 매핑
├── REGISTRY.md            # 프로젝트 레지스트리 — 설치처별 데이터 (미추적, harness-install로 생성)
├── CLAUDE.md              # AGENTS.md 포인터
├── .agents/               # 에이전트·스킬 정의 원본 (공용)
│   ├── agents/            # 표준 팀원 7종 — explorer·architect·troubleshooter·implementer·infra-specialist·reviewer·integrator
│   ├── skills/
│   │   ├── orchestrate/     # 작업 규모 판정 게이트 + 에이전트 팀·병렬·크로스 프로젝트 오케스트레이션
│   │   ├── metaskill/       # 하네스 생성·개선·프로젝트 스캐폴딩
│   │   ├── harness-review/  # 주간 하네스 운영 점검 (진화 트리거·무결성)
│   │   ├── harness-install/ # 새 컴퓨터 설치 부트스트랩 (REGISTRY.md 생성)
│   │   ├── project-status/  # 전체 프로젝트 현황 팬아웃 리포트
│   │   ├── branch-workflow/ # 하위 프로젝트 브랜치·PR 워크플로우 (main 최신화→브랜치→rebase→PR)
│   │   ├── doc-writer/      # 일관 형식 문서 작성 (스펙·리포트·README·런북·PR 본문 템플릿)
│   │   ├── team-review/     # 규모 스케일링 팀 리뷰 (관점 팬아웃 + 통합 게이트, 스펙 대비 판정)
│   │   ├── work-tracker/    # 세션 영속 작업 추적 (GitHub Issues, ccpm 패턴, ADR 009)
│   │   └── release/         # 머지 이후 배포·릴리스 워크플로우 (런북 → 단계별 확인 → 검증)
│   ├── hooks/             # Claude 세션 훅 — agentsview-daemon.py (동기화 데몬 자동 기동), harness-review-reminder.py (일일 경량·주간 전체 점검 자동 트리거), _common.py (훅 공통 부트스트랩 단일 원본 — stdio UTF-8 재구성, ADR 없음·스펙 2026-07-15)
│   ├── githooks/          # 전역 core.hooksPath 대상 — tdd-gate.py (커밋 시점 TDD 강제, 도구 무관 — ADR 008·014·015) + 진입 shim·로컬 훅 체인, 등록은 harness-install 1단계
│   └── projects/          # 하위 프로젝트 하네스 원본 — 설치처별 데이터 (미추적, ADR 006)
├── .claude/               # → .agents/ 심링크 + settings.json(훅 등록) (Claude Code + Codex가 같은 파일을 봄)
├── docs/
│   ├── adr/               # 구조적 결정 기록 (ADR)
│   └── specs/             # 루트 자체 코드(훅 등)의 스펙 (SDD, AGENTS.md 13절)
├── project/               # 하위 프로젝트들 — 각자 독립 git 저장소 (이 저장소는 미추적, 하네스 파일 없음)
├── dev/                   # 실험·임시 개발 공간 (미추적)
└── _workspace/            # 세션 산출물 — 팀 작업 중간 결과물 (미추적)
```

## 새 컴퓨터에 설치하기

클론만으로는 미완성이다 — 설치처별 요소(REGISTRY.md, `project/`, `dev/`)는 의도적으로 git에 없다. 클론 후 Claude Code / Codex에 **"하네스 설치"**라고 요청하면 `harness-install` 스킬이 심링크 검증 → **git 훅 계층 등록**(`core.hooksPath` → `.agents/githooks`, tdd-gate의 유일한 실행 계층이라 미등록이면 커밋 게이트가 꺼진 상태) → 디렉토리 생성 → agentsview 설치(세션 이력 실측·시크릿 스캔용, 권장) → 프로젝트 스캔 → 인터뷰 → REGISTRY.md 생성까지 진행한다. 전역 git 설정은 저장소로 전파되지 않으므로 **머신마다 한 번씩** 필요하다.

## 동작 방식

1. **라우팅**: 요청을 받으면 `REGISTRY.md`의 프로젝트 레지스트리에서 관련 프로젝트를 식별하고 해당 하네스(`.agents/projects/<이름>/AGENTS.md`)를 로드한다. (공용 규칙은 AGENTS.md, 설치 환경별 프로젝트 목록은 REGISTRY.md) 하위 프로젝트 하네스는 전부 이 워크스페이스에서 중앙 관리하며, 프로젝트 디렉토리·저장소에는 하네스 파일을 두지 않는다.
2. **구현·다단계 작업**은 `orchestrate`의 팀 필요성 판정(Phase 0-1)을 거친다 — 직접 수행 / 단독 서브에이전트 / 생성-검증 쌍 / 팀 중 규모에 맞게 정하고, 구현이 포함되면 reviewer 독립 검증을 반드시 포함한다. 팀은 표준 로스터 7종(explorer·architect·troubleshooter·implementer·infra-specialist·reviewer·integrator)을 재사용하며, 위임 깊이는 최대 2단계다.
3. **새 프로젝트**는 "프로젝트 새로 만들어줘"라고 지시하면 `metaskill`이 인터뷰 → 스캐폴딩 → 하네스 생성 → 레지스트리 등록까지 수행한다.
4. **작업 방법론**: 기능 추가·동작 변경은 스펙 작성(SDD, `doc-writer`) → 실패 테스트(TDD) → 구현 → 스펙 대비 리뷰(`team-review`) 순서를 따른다 (AGENTS.md 13절). TDD는 전역 `core.hooksPath`의 git commit-msg 훅(`tdd-gate`)이 강제한다 — 코드 변경에 테스트가 없으면 커밋이 차단되며, Claude Code·Codex·수동 커밋 등 **도구와 무관**하게 걸린다(ADR 014·015).
5. **작업 추적**: 세션을 넘는 작업은 `work-tracker`가 프로젝트 저장소의 GitHub Issues에 상태(태스크·진행 로그)를 영속화한다 — "이어서 하자"로 재개한다 (AGENTS.md 14절).
6. **진화**: 같은 요청 3회 / 같은 실패·정정 2회 / 하네스 우회 / 수축·효율(3주+ 무호출 스킬, 토큰 과소모 패턴 — 주간 점검 한정) 관찰 시 metaskill이 에이전트·스킬 신설·개선·폐기를 제안한다.
7. **내부 통신 언어**: 모델만 읽는 산출물(서브에이전트 발행 프롬프트·`_workspace/` 팀 중간 리포트·P2P 메시지)은 영어, 사용자가 읽는 것(채팅 보고·PR·하네스 문서·판정 문서·트리거 키워드)은 한국어 — 한국어가 같은 내용에 ~1.5-2배 토큰이라 중간 산출물만 영어화해 절감한다 (AGENTS.md 15절, ADR 016).

## 안전 가드레일

- 파괴적 작업(리소스 삭제, 프로덕션 배포·롤백, DB 마이그레이션, force push, IAM 변경)은 **예외 없이 실행 전 사용자 확인**.
- 시크릿·자격증명은 하네스 파일과 `_workspace/`에 절대 기록하지 않는다.
- **사내 설치처**(REGISTRY.md의 설치처 프로필)에서는 이 저장소를 수정·커밋·푸시하지 않는다 — 하네스 개선 사항은 `_workspace/harness-updates.md` 대기 큐에 기록해 두고 개인 설치처에서 적용한다 (AGENTS.md 5절).

## 규칙 상세

모든 규칙의 단일 원본은 [AGENTS.md](AGENTS.md)다. 구조적 결정의 배경은 [docs/adr/](docs/adr/)를 본다.
