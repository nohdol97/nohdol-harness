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
│   ├── agents/            # 표준 팀원 4종 — explorer·implementer·reviewer·integrator
│   └── skills/
│       ├── orchestrate/     # 에이전트 팀 구성·병렬 작업·크로스 프로젝트 오케스트레이션
│       ├── metaskill/       # 하네스 생성·개선·프로젝트 스캐폴딩
│       ├── harness-review/  # 주간 하네스 운영 점검 (진화 트리거·무결성)
│       ├── harness-install/ # 새 컴퓨터 설치 부트스트랩 (REGISTRY.md 생성)
│       └── project-status/  # 전체 프로젝트 현황 팬아웃 리포트
├── .claude/               # → .agents/ 심링크 (Claude Code + Codex가 같은 파일을 봄)
├── docs/adr/              # 구조적 결정 기록 (ADR)
├── project/               # 하위 프로젝트들 — 각자 독립 git 저장소 (이 저장소는 미추적)
├── dev/                   # 실험·임시 개발 공간 (미추적)
└── _workspace/            # 세션 산출물 — 팀 작업 중간 결과물 (미추적)
```

## 새 컴퓨터에 설치하기

클론만으로는 미완성이다 — 설치처별 요소(REGISTRY.md, `project/`, `dev/`)는 의도적으로 git에 없다. 클론 후 Claude Code / Codex에 **"하네스 설치"**라고 요청하면 `harness-install` 스킬이 심링크 검증 → 디렉토리 생성 → 프로젝트 스캔 → 인터뷰 → REGISTRY.md 생성까지 진행한다.

## 동작 방식

1. **라우팅**: 요청을 받으면 `REGISTRY.md`의 프로젝트 레지스트리에서 관련 프로젝트를 식별하고 해당 하네스를 로드한다. (공용 규칙은 AGENTS.md, 설치 환경별 프로젝트 목록은 REGISTRY.md)
2. **단일 프로젝트** 작업은 그 프로젝트 하네스로 직접, **다중 프로젝트** 작업은 `orchestrate` 스킬로 팀을 구성해 진행한다. 팀은 표준 로스터 4종(explorer·implementer·reviewer·integrator)을 재사용하며, 위임 깊이는 최대 2단계다.
3. **새 프로젝트**는 "프로젝트 새로 만들어줘"라고 지시하면 `metaskill`이 인터뷰 → 스캐폴딩 → 하네스 생성 → 레지스트리 등록까지 수행한다.
4. **진화**: 같은 요청 3회 / 같은 실패 2회 / 하네스 우회 관찰 시 metaskill이 에이전트·스킬 신설을 제안한다.

## 안전 가드레일

- 파괴적 작업(리소스 삭제, 프로덕션 배포·롤백, DB 마이그레이션, force push, IAM 변경)은 **예외 없이 실행 전 사용자 확인**.
- 시크릿·자격증명은 하네스 파일과 `_workspace/`에 절대 기록하지 않는다.

## 규칙 상세

모든 규칙의 단일 원본은 [AGENTS.md](AGENTS.md)다. 구조적 결정의 배경은 [docs/adr/](docs/adr/)를 본다.
