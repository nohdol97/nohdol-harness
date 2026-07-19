---
name: harness-install
description: Bootstrap this harness on a new machine after cloning. Verifies .claude symlinks, creates untracked workspace directories (project/, _workspace/), scans existing projects, interviews the user, and generates the installation-specific REGISTRY.md with path conventions. Use when the user says 하네스 설치, 초기 설정, 새 컴퓨터 세팅, REGISTRY.md 만들어줘, or when REGISTRY.md is missing at session start. Re-run keywords - install, bootstrap, setup, 설치, 초기화.
---

# harness-install — 새 설치처 부트스트랩

## 왜 이 스킬인가

이 하네스는 클론만으로는 완성되지 않는다. **설치 환경별 요소(REGISTRY.md, `.agents/projects/`, `project/`, `_workspace/`)는 의도적으로 git에 없기 때문이다**(ADR 002·005·006). 이 절차 없이 작업을 시작하면 라우팅 근거(REGISTRY.md)가 없어 크로스 프로젝트 판단이 불가능하고, 심링크가 깨진 채 `.claude/`에 실파일이 생기는 우회가 발생한다.

**REGISTRY.md가 없는 세션은 설치 미완료 상태다** — 다른 작업 요청이 와도 이 스킬을 먼저 안내한다.

## 절차

### 1. 심링크·개행·git 훅 계층 검증

- **심링크**: `readlink .claude/agents .claude/skills`가 `../.agents/agents`, `../.agents/skills`를 가리키는지 확인한다. 깨져 있으면 재생성(`ln -sfn`), 심링크 불가 환경이면 sync 스크립트로 대체하고 그 사실을 ADR로 기록한다(루트 AGENTS.md 11절). Windows에서 심링크가 **경로 문자열이 담긴 일반 파일**로 클론됐다면 개발자 모드 활성화 또는 `git config core.symlinks true` 후 재체크아웃한다.
- **git 훅 계층 등록(tdd-gate 도구 무관 강제 — ADR 014·015)**: `git config --global core.hooksPath <루트 절대경로>/.agents/githooks`를 등록한다. 13절 TDD 게이트의 **유일한 실행 계층**이라(단일화 — ADR 015) 미등록 머신은 게이트가 없는 상태이며, 전역 git 설정은 저장소로 전파되지 않아 설치 단계에서 잡아야 한다(이후 공백은 harness-review 주간 무결성 점검이 감시). **이미 다른 값이 설정돼 있으면 덮어쓰지 말고 사용자에게 확인한다**(기존 훅 체계와 충돌 가능). 검증: `git config --global --get core.hooksPath` 확인 후 `python3 .agents/githooks/tdd-gate_test.py` 통과.
- **Codex 세션 훅 검증 (macOS·Linux만 — 실험 기능·Windows 미지원, ADR 019)**: 활성화(`.codex/config.toml`의 `[features] codex_hooks = true`)와 등록(`.codex/hooks.json`)은 **둘 다 추적돼 클론 즉시 켜진다**(항상 활성) — 머신마다 켜는 단계가 없다. 이 설치처에서 **Codex CLI도 쓰면** 새 Codex 세션을 열어 리마인더가 주입되는지 확인한다 — 단, **마커가 최신이고 트리가 깨끗하면 침묵이 정상**이다(2026-07-16 노이즈 재개정 — 기한 전 상태 줄 없음). 확실한 검증은 마커 부재 상태(첫 설치)에서 전체 점검 지시가 뜨는지로 한다(훅은 SessionStart cwd=프로젝트 루트를 전제로 `$PWD` 경로를 쓴다 — 안 뜨면 그 전제부터 점검). **폴백**: repo-local config.toml 활성화가 인터랙티브에서 안 먹는 이슈(openai/codex #17532) 가능성이 있으므로, 안 뜨면 `~/.codex/config.toml`(전역)에 `[features] codex_hooks = true`를 병합(기존 키 보존)하고 재확인한다. Codex를 안 쓰는 설치처면 건너뛴다(파일은 무해한 비활성 상태로 남는다).
- **개행(CRLF) 검증**: SKILL.md 첫 줄이 CR 없이 `---`인지 확인한다 — CRLF면 frontmatter 파싱이 깨져 **모든 스킬이 목록에 이름만(무설명) 표시되고 자동 트리거가 죽는다**. `.gitattributes`가 LF를 강제하지만, 그 도입 전에 클론한 저장소는 `git config core.autocrlf false` 후 `git rm -rf --cached . && git reset --hard`로 재체크아웃해야 반영된다. 확인: `git config core.autocrlf`(false/input이어야 함), `file .agents/skills/metaskill/SKILL.md`(CRLF 표기 없어야 함).

### 2. 미추적 디렉토리 생성

`_workspace/`를 생성하고, 프로젝트 공간은 **기본 규약(`project/`)을 제안값**으로 생성한다(이미 있으면 유지). 5단계 인터뷰에서 다른 경로 규약을 택하면 그에 맞게 조정하고 `.gitignore`도 함께 갱신한다 — 공용 `.gitignore`의 `project/` 항목은 기본 규약 기준이다. `.gitignore`가 미추적 요소 + `REGISTRY.md` + `.agents/projects/`를 포함하는지 확인한다.

### 3. 보조 도구 설치 (전부 선택 — 실패해도 설치 절차는 계속)

#### 3a. agentsview (권장)

세션 이력 검색·비용 추적·시크릿 스캔 도구. harness-review의 신호 실측(반복 요청·실패)과 시크릿 사후 검증이 이것을 1차 데이터 소스로 쓴다.

> **주의 — 이 도구는 모델 지식에 없다**: agentsview는 최신 도구(2026)라 학습 데이터에 없을 수 있다. **"그런 CLI는 존재하지 않는다"고 기억으로 단정하지 말 것** — 존재 근거는 https://github.com/kenn-io/agentsview (릴리스 바이너리 실재). 설치 명령을 실행해서 확인한다.

1. 설치 여부 확인: `agentsview version` **그리고** `agentsview skills list` 둘 다 성공해야 "설치됨"이다 — 성공하면 3번(DB 검증)으로 건너뛴다. **함정 두 가지**: ① 데스크톱 앱(dmg/AppImage/setup.exe)은 CLI와 **별개 산출물**이라 앱이 있어도 `agentsview` 명령이 PATH에 없을 수 있다 — CLI를 추가 설치한다(공존 가능, 같은 로컬 DB 공유). ② 구버전 CLI는 `skills` 서브커맨드가 없다 — install.sh 재실행으로 최신화한다.
2. 설치 (**macOS·Ubuntu/Linux·Windows 전부 지원**): macOS/Linux는 `curl -fsSL https://agentsview.io/install.sh | bash` 또는 `brew install --cask agentsview`(macOS), Windows는 `powershell -ExecutionPolicy ByPass -c "irm https://agentsview.io/install.ps1 | iex"`. **install.sh가 차단·실패하면 대체 경로**: GitHub Releases(`https://github.com/kenn-io/agentsview/releases`)에서 OS·아키텍처에 맞는 바이너리(`linux_amd64.tar.gz`, `darwin_arm64.tar.gz`, `windows` zip/exe 등)를 받아 압축 해제 후 PATH에 둔다(sha256 체크섬 제공). 텔레메트리를 원치 않으면 `AGENTSVIEW_TELEMETRY_ENABLED=0`을 셸 프로필에 추가한다(사용자에게 선택 확인).
3. **로컬 DB 초기화·검증 (기본값 고정)**: `agentsview daemon start`로 첫 동기화를 실행하고, 로컬 SQLite DB가 `~/.agentsview/`에 생성됐는지 확인한다(위치 변경이 필요하면 `AGENTSVIEW_DATA_DIR` — 어느 경우든 **이 머신 안**). 이후의 동기화는 자동이다 — **SessionStart 훅(`agentsview-daemon.py`)이 세션이 열릴 때마다 데몬 기동을 보장**하고, 떠 있는 데몬이 세션 파일을 감시하며 실시간 동기화한다(수동 sync 불필요). **외부 DB 동기화(`pg push`, 원격 DuckDB/Quack)는 설정하지 않는다** — 세션 로그에는 회사 데이터·시크릿이 섞일 수 있어 머신 밖으로 내보내지 않는 것이 3절 가드레일과 정합이다. `~/.agentsview/config.toml`에 `[pg.*]` 대상이 이미 있으면 사용자에게 알린다.
4. finding-history 스킬을 **전역으로** 설치: `agentsview skills install` (`~/.claude/skills/`·`~/.agents/skills/` 대상) — 에이전트가 과거 세션을 검색할 수 있게 된다. **이 워크스페이스에 `--project`로 설치하지 않는다**(루트 AGENTS.md 11절: 외부 도구 스킬은 전역 — 심링크를 거쳐 공용 저장소에 도구 산출물이 커밋되는 것 방지).
5. 설치 실패·오프라인·사용자 거부 시 건너뛰고 완료 보고에 그 사실을 남긴다 — harness-review는 agentsview 없이도 기존 관찰 방식으로 동작한다.

#### 3b. defuddle (선택 — 웹 본문 추출)

`defuddle` 스킬이 쓰는 CLI다. 웹페이지에서 본문만 추출해 WebFetch 대비 토큰을 줄인다(네비·광고·사이드바 제거). **이 설치처에서 웹 리서치·문서 수집(deep-research(Claude Code 내장)·doc-writer)을 자주 하면** `npm i -g defuddle`로 전역 설치한다.

- **필수가 아니다**: 미설치여도 `defuddle` 스킬이 자동으로 WebFetch로 폴백하므로 건너뛰어도 기능이 죽지 않는다 — 순수 토큰 최적화용이다.
- 설치 여부 확인: `command -v defuddle`. 오프라인·전역 npm 권한 부재·사용자 거부 시 건너뛰고 완료 보고에 남긴다.
- **전역 설치만** 한다(`npm i -g`) — 이 워크스페이스에 프로젝트-로컬로 두지 않는다(외부 도구는 전역, 루트 AGENTS.md 11절과 정합).

#### 3c. context7 MCP (선택 — 라이브러리 문서 조회)

`context7` 스킬이 쓰는 MCP 서버다. 라이브러리·프레임워크·SDK의 **버전별 최신 문서**를 실시간 조회해, 기억 기반 오답(폐기된 API·바뀐 설정)을 없앤다. **이 설치처에서 서드파티 라이브러리 개발(웹·앱·백엔드)을 하면** 등록한다.

- **필수가 아니다**: 미설치여도 `context7` 스킬이 자동으로 WebFetch/WebSearch로 폴백하므로 건너뛰어도 기능이 죽지 않는다 — 순수 정확도·토큰 최적화용이다(defuddle과 같은 성격).
- 등록 여부 확인: `claude mcp list`에 `context7`이 있는지 본다. 없으면 **user 스코프(전역)로** 등록: `claude mcp add context7 --scope user -- npx -y @upstash/context7-mcp`. 반영은 **다음 세션부터**다(CLI가 세션 시작 시 MCP를 로드).
- **user 스코프로만** 등록한다 — 이 워크스페이스에 `.mcp.json`(project 스코프)로 커밋하지 않는다. MCP는 설치처별 요소라 REGISTRY.md·`.agents/projects/`처럼 git에 올리지 않는 것이 ADR 005와 정합이고, 이 하네스는 거의 모든 세션을 루트에서 열기 때문에(12절) 전역 등록이면 어느 프로젝트 작업에서든 뜬다.
- 오프라인·네트워크 정책·사용자 거부 시 건너뛰고 완료 보고에 남긴다. **무단 등록하지 않는다.**

> **SuperClaude 잔재 MCP 주의**: 과거 SuperClaude가 심어둔 `magic`·`sequential-thinking` MCP가 남아 있으면 이 설치처의 정책상 제거 대상이다(sequential-thinking은 네이티브 사고가 대체, magic은 실사용 미확인 — 2026-07-18 결정). `claude mcp list`에서 발견되면 사용자에게 알리고, 승인 시 `claude mcp remove <이름> --scope user`로 제거한다. `playwright`·`context7`은 유지한다.

#### 3d. 컨텍스트 상시 표시 (선택 — Claude Code statusLine)

세션에 컨텍스트(토큰)가 얼마나 쌓였는지 입력창 근처에 **상시 표시**한다. 오토컴팩트가 다가오는지 곁눈질로 파악해 세션 관리에 도움이 된다.

- **Codex**: TUI 푸터에 토큰/컨텍스트 사용량이 **기본 상시 표시**된다 — 설정할 것이 없다(`config.toml`에 관련 토글 없음). "켜져 있나" 물어볼 필요 없이 이미 켜진 상태로 안내한다.
- **Claude Code**: **네이티브 토글이 없어** statusLine 스크립트가 필요하다. stdin JSON의 `model.display_name`·`context_window.used_percentage`·`total_input_tokens`·`context_window_size`를 읽어 한 줄로 출력한다(어떤 입력에도 크래시 없이 `[claude]`로 폴백).
- **설정 여부 확인**: `~/.claude/settings.json`에 `statusLine` 키가 있는지 본다. **없으면 사용자에게 켤지 묻고**(선택), 승인 시 아래를 적용한다:
  1. 단일 원본 스크립트를 전역 위치로 복사: `cp .agents/skills/harness-install/references/claude-statusline.py ~/.claude/statusline.py` (표준 라이브러리만 쓰는 python3 스크립트 — jq 미설치 환경 대비, 하네스 훅과 같은 `python3` 사용).
  2. `~/.claude/settings.json`(전역 — 머신별 설정)에 `statusLine` 병합: `{"type":"command","command":"python3 ~/.claude/statusline.py","padding":0}`. 기존 키를 보존하고 JSON 유효성을 파싱으로 검증한다.
  3. 샘플 JSON을 파이프로 넣어 스크립트가 한 줄 출력하는지 확인(정상·null·경고·깨진 입력). 다음 렌더부터 표시된다.
- **전역(`~/.claude/`)에 둔다** — 컨텍스트 표시는 개인 표시 취향이라 추적 하네스 `settings.json`(정책)이 아니라 머신별 전역 설정에 넣는다(hooksPath·MCP 전역 등록과 같은 계층). 스크립트의 단일 원본만 하네스가 추적한다.
- 사용자 거부 시 건너뛰고 완료 보고에 남긴다 — 표시 편의 기능이라 미설정이어도 무해하다(`/context` 명령으로 언제든 상세 조회 가능).

### 4. 기존 프로젝트 스캔

`project/` 하위 디렉토리를 나열하고, 각각에 대해 관찰 가능한 사실(하위 구성, git 저장소 여부, 하네스 유무 — `.agents/projects/<이름>/` 존재 기준(루트 AGENTS.md 12절), 스택 단서)을 수집한다. **역할·목적은 각 프로젝트의 README·문서를 직접 읽어 요약해 채운다** — 문서가 없으면 "미확인". **추측으로 채우지 않는다** — 관찰과 추측이 섞이면 레지스트리 전체를 믿을 수 없게 된다.

### 5. 구체화 인터뷰

스캔 결과(문서에서 읽은 역할 요약 포함)를 보여주고 사용자에게 확인한다: **설치처 프로필(개인/사내 — 루트 AGENTS.md 5절)**, 레지스트리 단위(묶음 vs 개별), 이 설치처의 경로 규약(기본: `project/<이름>/` + 독립 git 저장소). 프로필이 **사내**면 그 의미를 함께 안내한다 — 이 저장소(추적 하네스 파일)는 수정·커밋·푸시하지 않으며, 하네스 개선 사항은 `_workspace/harness-updates.md` 대기 큐에 기록되어 개인 설치처에서 적용된다. **역할은 묻지 않는다**(문서 관찰로 이미 채움 — 사용자가 정정하는 경우만 반영). **연관 프로젝트는 묻지 않는다** — 실작업에서 프로젝트들이 함께 엮일 때 갱신된다(루트 AGENTS.md 1절). 프로젝트가 아직 없으면 빈 표로 시작한다.

### 6. REGISTRY.md 생성

다음 구조로 생성한다: 미추적 경고 헤더 → **설치처 프로필(개인/사내 — 사내면 "하네스 수정·푸시 금지, 개선은 대기 큐" 한 줄 병기)** → 경로 규약(이 설치처) → 레지스트리 표(이름/경로/스택/역할/연관 프로젝트/하네스 유무) → 변경 이력(초기 1행). **연관 프로젝트 컬럼의 초기값은 "미기록"** — 실작업 관찰로 채워진다는 각주를 표 아래 남긴다. 확정하지 못한 값은 "미확인"으로 명시하고 라우팅 단정 금지 경고를 남긴다.

### 7. 완료 판정

- [ ] 심링크 2개 정상 (`.claude/` 아래 실파일 없음)
- [ ] 전역 `core.hooksPath`가 `.agents/githooks`를 가리킴 (미등록·거부 시 사유가 완료 보고에 있음)
- [ ] (Codex 사용 + macOS/Linux 설치처면) 새 Codex 세션에서 리마인더 주입 확인(마커 부재 시 전체 점검 지시 — 마커 최신+깨끗한 트리면 침묵이 정상, 2026-07-16) — 활성화는 저장소 커밋(`.codex/config.toml`)이라 별도 등록 불요, 안 뜨면 `~/.codex/config.toml` 폴백(#17532) (Codex 미사용·Windows면 사유가 완료 보고에 있음)
- [ ] SKILL.md 개행이 LF — `/skills` 목록에 각 스킬의 description이 표시됨 (무설명이면 CRLF·frontmatter 문제)
- [ ] agentsview 설치됨 + 로컬 SQLite DB(`~/.agentsview/` 또는 `AGENTSVIEW_DATA_DIR`) 생성 확인 + 외부 DB 동기화 미설정 + finding-history 스킬 전역 설치됨 (건너뛰었으면 사유가 완료 보고에 있음)
- [ ] (선택) defuddle 설치됨 또는 건너뜀 사유가 완료 보고에 있음 — 미설치는 무해(`defuddle` 스킬이 WebFetch로 폴백)
- [ ] (선택) context7 MCP가 `claude mcp list`에 있음(user 스코프) 또는 건너뜀 사유가 완료 보고에 있음 — 미설치는 무해(`context7` 스킬이 WebFetch/WebSearch로 폴백). SuperClaude 잔재 magic·sequential-thinking이 있으면 제거 안내됨
- [ ] (선택) 컨텍스트 상시 표시 — Claude Code `~/.claude/settings.json`에 `statusLine`이 있고 `~/.claude/statusline.py` 배치됨, 또는 사용자 거부/건너뜀 사유가 완료 보고에 있음. Codex는 기본 상시 표시(설정 불요)임을 안내
- [ ] REGISTRY.md 존재 + **설치처 프로필(개인/사내)** + 경로 규약 + 표 + 변경 이력 (사내 프로필이면 수정·푸시 금지 의미가 안내됨)
- [ ] `git status`에 REGISTRY.md·project/가 나타나지 않음 (ignore 확인)
- [ ] 미확인 항목이 "미확인"으로 정직하게 표기됨

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 새 설치처 | REGISTRY.md 부재 → 라우팅 불능, 임의 작업 시작 | 고정 절차로 설치 완결 후 작업 |
| 심링크 | 깨진 채 방치 → `.claude/` 실파일 우회 발생 | 1단계에서 검증·복구 |
| 레지스트리 품질 | 추측 혼입 | 관찰+인터뷰 분리, 미확인 정직 표기 |
