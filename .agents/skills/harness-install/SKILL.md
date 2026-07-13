---
name: harness-install
description: Bootstrap this harness on a new machine after cloning. Verifies .claude symlinks, creates untracked workspace directories (project/, dev/, _workspace/), scans existing projects, interviews the user, and generates the installation-specific REGISTRY.md with path conventions. Use when the user says 하네스 설치, 초기 설정, 새 컴퓨터 세팅, REGISTRY.md 만들어줘, or when REGISTRY.md is missing at session start. Re-run keywords - install, bootstrap, setup, 설치, 초기화.
---

# harness-install — 새 설치처 부트스트랩

## 왜 이 스킬인가

이 하네스는 클론만으로는 완성되지 않는다. **설치 환경별 요소(REGISTRY.md, `.agents/projects/`, `project/`, `dev/`, `_workspace/`)는 의도적으로 git에 없기 때문이다**(ADR 002·005·006). 이 절차 없이 작업을 시작하면 라우팅 근거(REGISTRY.md)가 없어 크로스 프로젝트 판단이 불가능하고, 심링크가 깨진 채 `.claude/`에 실파일이 생기는 우회가 발생한다.

**REGISTRY.md가 없는 세션은 설치 미완료 상태다** — 다른 작업 요청이 와도 이 스킬을 먼저 안내한다.

## 절차

### 1. 심링크·개행 검증

- **심링크**: `readlink .claude/agents .claude/skills`가 `../.agents/agents`, `../.agents/skills`를 가리키는지 확인한다. 깨져 있으면 재생성(`ln -sfn`), 심링크 불가 환경이면 sync 스크립트로 대체하고 그 사실을 ADR로 기록한다(루트 AGENTS.md 11절). Windows에서 심링크가 **경로 문자열이 담긴 일반 파일**로 클론됐다면 개발자 모드 활성화 또는 `git config core.symlinks true` 후 재체크아웃한다.
- **개행(CRLF) 검증**: SKILL.md 첫 줄이 CR 없이 `---`인지 확인한다 — CRLF면 frontmatter 파싱이 깨져 **모든 스킬이 목록에 이름만(무설명) 표시되고 자동 트리거가 죽는다**. `.gitattributes`가 LF를 강제하지만, 그 도입 전에 클론한 저장소는 `git config core.autocrlf false` 후 `git rm -rf --cached . && git reset --hard`로 재체크아웃해야 반영된다. 확인: `git config core.autocrlf`(false/input이어야 함), `file .agents/skills/metaskill/SKILL.md`(CRLF 표기 없어야 함).

### 2. 미추적 디렉토리 생성

`_workspace/`를 생성하고, 프로젝트·실험 공간은 **기본 규약(`project/`, `dev/`)을 제안값**으로 생성한다(이미 있으면 유지). 4단계 인터뷰에서 다른 경로 규약을 택하면 그에 맞게 조정하고 `.gitignore`도 함께 갱신한다 — 공용 `.gitignore`의 `project/`·`dev/` 항목은 기본 규약 기준이다. `.gitignore`가 미추적 요소 + `REGISTRY.md` + `.agents/projects/`를 포함하는지 확인한다.

### 3. 기존 프로젝트 스캔

`project/` 하위 디렉토리를 나열하고, 각각에 대해 관찰 가능한 사실(하위 구성, git 저장소 여부, 하네스 유무 — `.agents/projects/<이름>/` 존재 기준(루트 AGENTS.md 12절), 스택 단서)을 수집한다. **역할·목적은 각 프로젝트의 README·문서를 직접 읽어 요약해 채운다** — 문서가 없으면 "미확인". **추측으로 채우지 않는다** — 관찰과 추측이 섞이면 레지스트리 전체를 믿을 수 없게 된다.

### 4. 구체화 인터뷰

스캔 결과(문서에서 읽은 역할 요약 포함)를 보여주고 사용자에게 확인한다: 레지스트리 단위(묶음 vs 개별), 이 설치처의 경로 규약(기본: `project/<이름>/` + 독립 git 저장소). **역할은 묻지 않는다**(문서 관찰로 이미 채움 — 사용자가 정정하는 경우만 반영). **연관 프로젝트는 묻지 않는다** — 실작업에서 프로젝트들이 함께 엮일 때 갱신된다(루트 AGENTS.md 1절). 프로젝트가 아직 없으면 빈 표로 시작한다.

### 5. REGISTRY.md 생성

다음 구조로 생성한다: 미추적 경고 헤더 → 경로 규약(이 설치처) → 레지스트리 표(이름/경로/스택/역할/연관 프로젝트/하네스 유무) → 변경 이력(초기 1행). **연관 프로젝트 컬럼의 초기값은 "미기록"** — 실작업 관찰로 채워진다는 각주를 표 아래 남긴다. 확정하지 못한 값은 "미확인"으로 명시하고 라우팅 단정 금지 경고를 남긴다.

### 6. 완료 판정

- [ ] 심링크 2개 정상 (`.claude/` 아래 실파일 없음)
- [ ] SKILL.md 개행이 LF — `/skills` 목록에 각 스킬의 description이 표시됨 (무설명이면 CRLF·frontmatter 문제)
- [ ] REGISTRY.md 존재 + 경로 규약 + 표 + 변경 이력
- [ ] `git status`에 REGISTRY.md·project/·dev/가 나타나지 않음 (ignore 확인)
- [ ] 미확인 항목이 "미확인"으로 정직하게 표기됨

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 새 설치처 | REGISTRY.md 부재 → 라우팅 불능, 임의 작업 시작 | 고정 절차로 설치 완결 후 작업 |
| 심링크 | 깨진 채 방치 → `.claude/` 실파일 우회 발생 | 1단계에서 검증·복구 |
| 레지스트리 품질 | 추측 혼입 | 관찰+인터뷰 분리, 미확인 정직 표기 |
