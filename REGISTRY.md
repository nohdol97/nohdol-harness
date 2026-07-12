# 프로젝트 레지스트리

> **이 파일은 설치 환경별(installation-specific) 데이터다.** 공용 규칙(AGENTS.md)은 이 하네스를 설치하는 어느 워크스페이스에서나 동일하지만, 어떤 프로젝트를 두는지는 설치한 곳마다 다르다 — 그래서 분리한다(ADR 004).
> **라우팅 판단의 유일한 근거**이며, 프로젝트가 생기거나 없어지면 **metaskill이 이 표를 갱신할 의무**가 있다. 크로스 프로젝트 여부는 "연관 프로젝트" 컬럼으로 판단한다. 경로 규약(`project/<이름>/`, 독립 git 저장소)은 공용 규칙이므로 AGENTS.md 1절에 있다.

## 레지스트리

| 이름 | 경로 | 스택 | 역할 | 연관 프로젝트 | 하네스 유무 |
|---|---|---|---|---|---|
| app_project | `project/app_project/` | Flutter (sonaapp), Android | 앱 프로젝트 묶음 (하위: android, flutter) | 미확인 | ✗ |
| web_project | `project/web_project/` | Next.js (shifteasy) | 웹 프로젝트 묶음 (하위: shifteasy) | 미확인 | ✗ |
| tool_project | `project/tool_project/` | Go (claude-auto), Python (crypto-bot) 외 | 도구 묶음 (하위: agents, claude-auto, crypto-bot, nohdolbot) | 미확인 | ✗ |
| ops_project | `project/ops_project/` | 미확인 | 운영·LLM 워크플로 묶음 (하위: ax-llm-eval-workflow, llm-team-admin) | 미확인 | ✗ |
| ui-live-editor | `project/ui-live-editor/` | 미확인 | UI 라이브 에디터 (독립 git 저장소) | 미확인 | ✗ |

> ⚠️ 위 5행은 2026-07-12 기존 디렉토리 **관찰 기반 임시 등록**이다. "미확인" 항목과 하네스 생성은 metaskill 구체화 인터뷰로 확정해야 하며, 확정 전에는 이 행들을 근거로 크로스 프로젝트 라우팅을 단정하지 않는다. 일부 항목은 단일 프로젝트가 아니라 **카테고리 묶음**이므로 인터뷰 시 레지스트리 단위(묶음 vs 개별 프로젝트)도 함께 확정한다. 또한 ui-live-editor를 제외한 4개 항목은 **독립 git 저장소가 아직 없다**(ADR 002 규약 미충족) — 인터뷰 시 `git init` 여부도 함께 확정한다.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-12 | AGENTS.md 1절에서 분리 신설, 임시 등록 5행 이관 | REGISTRY.md | 설치 환경별 데이터와 공용 규칙의 분리 (ADR 004) |
