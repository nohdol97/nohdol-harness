---
name: harness-review
description: Harness operations review in two modes - daily lite (scan the three expansion signals since the last check) and weekly full (adds the shrink/efficiency signal - unused skills, token-waste patterns - plus symlink/registry/frontmatter integrity), proposing concrete metaskill actions. Runs as a background subagent (the main loop dispatches, reports the summary, handles approval) and is auto-triggered by the SessionStart reminder hook via markers. Use when the reminder fires or the user says 일일 점검, 주간 점검, 하네스 리뷰, harness review. Do NOT use for creating/scaffolding or actually applying changes to the harness (→ metaskill), nor for an on-demand usage audit of one specific external tool/plugin (→ tool-audit) - harness-review only scans signals and proposes, it never edits the harness itself. Re-run keywords - harness-review, daily, weekly, evolve, 일일 점검, 주간 점검, 진화.
---

# harness-review — 하네스 운영 점검 (일일 경량·주간 전체 2모드)

## 왜 이 스킬인가

루트 AGENTS.md 8절은 진화 트리거 4신호를 관찰하는 것을 운영 습관으로 요구한다. 관찰 절차가 스킬로 고정되어 있지 않으면 이 습관은 몇 주 안에 증발한다 — 하네스는 쓰이면서 어긋난 부분이 드러날 때만 진화할 수 있다. 이 스킬은 **관찰과 제안**만 담당한다. 실제 생성·개선의 실행은 metaskill의 몫이다 (역할 분리: 관찰자가 곧바로 실행까지 하면 제안의 근거 검증이 생략된다).

## 실행 모드 (리마인더 훅이 지정 — 2단 주기)

| 모드 | 주기 | 범위 | 완료 마커 |
|---|---|---|---|
| **일일 경량** | 1일 | 1단계 신호 수집만 — 마지막 점검 이후 세션 대상. 무결성 점검 생략(주간의 몫) | `.harness-review-daily-last` |
| **주간 전체** | 7일 | 1~3단계 전부 | `.harness-review-last` + daily 둘 다 |

일일 모드는 **신호가 없으면 "신호 없음" 한 줄 보고 후 마커 갱신으로 끝낸다** — 매일의 비용은 스캔 몇 분이어야 유지된다. 신호가 있으면 주간과 동일하게 3단계(제안 생성)로 넘어간다.

**일일 모드 범위·비용 상한**: 데이터 소스는 **agentsview 질의(마지막 마커 이후 세션)·`git log`·경량 파일 확인(`_workspace/` 작업명 나열, team-log.jsonl의 `task_failed` grep, 디렉토리 존재 확인 — 신호 수집 표 ①~③의 파일시스템 항목은 일일 모드에서 이 수준까지만)으로 한정**한다 — 하네스 파일 전수 읽기·스킬/에이전트 본문 재독 금지(구조·무결성은 주간의 몫). agentsview 미설치 시 일일 모드는 git log+경량 파일 확인만으로 스캔하고 그 사실을 보고에 명시한다. 목표 비용은 서브에이전트 **3만 토큰 이내** — 무신호 보고에 112k 토큰이 쓰인 실측(2026-07-17, 신호 ④의 취지 적용 — 반복 임계 전이나 매일 재발이 구조적으로 확정된 비용이라 즉시 처방)이 이 상한의 근거다. 루트 8절 "실수 즉시 기록" 규율이 1회차 교훈을 담당하므로, 일일 스캔은 **반복** 신호 탐지에만 집중한다.

## 실행 방식 (서브에이전트 위임 — 메인 루프 직접 수행 금지)

메인 루프가 점검을 직접 수행하면 첫 응답이 점검에 점유되어 사용자 요청이 밀리고, 메인 컨텍스트가 점검 세부(파일 목록·중간 판단)로 오염된다(2026-07-14 사용자 확정). 관찰은 위임 가능하지만 승인은 대화가 필요하다 — 경계를 여기에 둔다.

1. 점검 지시를 받으면(리마인더 트리거·사용자 직접 요청 동일) 메인 루프는 **explorer 서브에이전트 1기를 백그라운드로 발행**하고 사용자 요청을 병행 처리한다. 서브에이전트 프롬프트에 반드시 포함: ① `.agents/skills/harness-review/SKILL.md`를 읽고 지정 모드(전체/일일)의 절차 1~3단계를 수행하되 **제안은 초안까지만**(생성·수정 실행 금지 — 일일 모드면 위 "범위·비용 상한"을 프롬프트에 그대로 명시) ② 산출물은 `_workspace/harness-review-<YYYY-MM-DD>/`에 저장 ③ 4단계 마커·운영 로그 갱신까지 수행 ④ 최종 반환은 출력 형식(신호·무결성·제안 초안·마커 갱신 여부) 요약. **언어(루트 15절)**: 발행 프롬프트·점검 노트·최종 반환 요약은 영어로 쓰되, **제안서(proposals)·운영 로그·대기 큐 기록은 한국어**(사용자가 읽고 승인하는 문서)로 쓰도록 프롬프트에 명시한다.
2. 서브에이전트 완료 시 메인 루프는 요약을 **한국어로 소화해** 채팅으로 보고하고(영어 반환의 인용·직역 금지 — 15절 언어 섞임 가드) 마커·운영 로그 갱신을 확인한다(누락 시 직접 갱신).
3. **제안 승인과 실행(metaskill 호출, 사내 프로필이면 대기 큐 기록)은 메인 루프의 몫** — 서브에이전트는 관찰·초안까지만. 무단 생성 금지는 위임해도 유지된다.

## 절차

### 1. 신호 수집 (진화 트리거 4신호 — 일일 모드는 ①~③만)

| 신호 | 관찰 방법 |
|---|---|
| ① 반복 요청 3회+ | 최근 세션 기억·`_workspace/` 작업명들·git 커밋 메시지에서 같은 유형 작업의 반복 확인 |
| ② 반복 실패 2회+ (같은 정정 2회+ 포함) | team-log.jsonl의 `task_failed` 이벤트(orchestrate 이벤트 계약), 같은 종류의 재작업 커밋(fix 연쇄), **같은 내용의 사용자 정정 반복**("아니 그게 아니라" 류 — agentsview 세션 검색으로 실측) 확인 |
| ③ 하네스 우회 | **팀 필요성 판정(orchestrate Phase 0-1) 없이 처리된 구현·다단계 작업**(판정 한 줄 보고의 부재가 증거 — 루트 AGENTS.md 7절 3항), orchestrate 없이 처리된 다중 프로젝트 작업, `.agents/` 밖에 생긴 에이전트·스킬 정의, 레지스트리에 없는 프로젝트 디렉토리, **하네스 스킬 트리거가 내장·플러그인·sc:* 외부 스킬로 샌 라우팅**(CLAUDE.md 스킬 우선순위 위반 — 예: PR 생성이 gstack ship으로, 작업 재개가 checkpoint로) |
| ④ 수축·효율 (주간 전체 한정) | **3주+ 무호출**: 각 스킬·에이전트 이름을 `agentsview session search`로 검색해 최근 호출 이력 확인 — 3주 이상 무호출이면 폐기·통합 제안(미설치면 판정 보류 — 근거 없는 폐기 제안 금지). **토큰 과소모 패턴 2회+**: `agentsview stats`로 토큰·비용 상위 세션을 확인하고, 간단 작업에 팀 구성·같은 정보의 반복 수집·불필요한 전체 파일 로딩이 반복됐는지 세션 로그로 확인 → 절차 개선(판정 하향, 산출물 재사용, references/ 분리) 제안 |

**agentsview 연동 (설치된 경우 신호 수집의 1차 데이터 소스)**: `agentsview`가 설치되어 있으면 세션 기억 대신 실측한다 — `agentsview session search "<요청 유형 키워드>"`로 반복 요청·정정을, `agentsview stats`·`agentsview session list`로 재작업·실패 패턴과 토큰·비용을 조회한다. Claude Code·Codex 세션 전체가 인덱싱 대상이라 기억·커밋 메시지보다 정확하고 CLI 간 사각지대가 없다. 미설치면 위 표의 관찰 방법을 그대로 쓰되 ④는 판정 보류한다(설치는 harness-install 3단계).

### 2. 구조 무결성 점검

- 심링크: `readlink .claude/agents .claude/skills`가 `../.agents/*`를 가리키는지. **`.claude/` 아래에 심링크가 아닌 실파일이 생겼는지** (생겼다면 우회 신호 — 원본은 `.agents/`에만 있어야 한다).
- git 훅 계층: `git config --global --get core.hooksPath`가 이 하네스의 `.agents/githooks`를 가리키는지 — tdd-gate(13절)의 **유일한 실행 계층**이라 미등록 머신은 게이트가 통째로 꺼진 상태다(pull만 하고 harness-install 1단계를 안 돌린 경우 발생 — ADR 015). 미등록이면 등록 명령을 제안한다.
- 훅 공통 모듈: `.agents/hooks/_common.py`가 존재하는지 — 훅 3종의 stdio UTF-8 재구성 단일 원본이라(스펙 2026-07-15-hooks-common-bootstrap) 유실되면 각 훅이 no-op 폴백으로 조용히 넘어가 cp949 보호가 사라진다(fail-open이라 에러도 안 남). 부재면 복구를 제안한다.
- Codex 훅 등록 일관성: `.claude/settings.json`의 SessionStart 리마인더 2종(`harness-review-reminder`·`worklog-reminder`)이 `.codex/hooks.json`에도 등록돼 있는지 — 한쪽에만 추가되면 Codex 세션에서 리마인더가 누락된다(ADR 019는 두 파일 대칭 등록이 전제). `.codex/config.toml`의 `[features] codex_hooks = true`가 있는지도 확인.
- 문서 지도(MOC) 최신성: `docs/README.md`의 ADR·스펙·제안 행이 `docs/adr/`·`docs/specs/`·`docs/proposals/`의 실제 파일과 일치하는지 — 인덱스에 없는 파일이나 파일 없는 인덱스 행, 대체됐는데 "활성"인 상태가 있으면 보고(루트 AGENTS.md 6절 동기화 의무 위반 = 선언-미구현의 문서판).
- 하위 하네스: `.agents/projects/` 하위 디렉토리 목록과 REGISTRY.md 레지스트리 행("하네스 유무" ✓)이 일치하는지. `project/<이름>/` 안에 하네스 파일(AGENTS.md·CLAUDE.md·`.claude/`·`.agents/`)이 생겼는지 (생겼다면 우회 신호 — 원본은 루트 `.agents/projects/`에만 있어야 한다. 루트 AGENTS.md 12절, ADR 006·007). 하위에 CLAUDE.md가 있으면 구 규격 잔재 — 삭제 제안. 지연 생성된 `skills/`·`agents/`가 있는데 하위 AGENTS.md에 목록·경로 명시가 없으면 로드 불능 상태 — 보고.
- 스킬 로드 가능성: 각 SKILL.md의 frontmatter가 첫 줄 `---` + `description` 보유인지(무설명 스킬은 자동 트리거 불능 — 2026-07-13 장애), 개행이 LF인지(`file` 명령에 CRLF 표기 없어야 함).
- **AGENTS.md 로딩 크기 예산**: `wc -c AGENTS.md`가 **40,000 bytes를 초과하면 다이어트를 제안**한다 — 이 파일은 `@AGENTS.md`로 매 세션 항상-온이라 성장이 곧 고정 토큰 비용이고, 길어질수록 규칙이 본문에 매몰된다. 다이어트 수법: 규칙+이유는 남기고 사례·실측 서술을 changelog/ADR 포인터로 이관(ADR 021 변경 이력 분리와 같은 수법).
- 레지스트리: REGISTRY.md가 존재하는지(없으면 설치 미완료 — harness-install 안내), 존재하면 `project/` 하위 실제 디렉토리 목록과 표가 일치하는지.
- 잔여물: `_workspace/`에서 team-log.jsonl이 **있는데** `team_delete` 이벤트가 없는 작업 디렉토리는 비정상 종료 신호. team-log 자체가 없는 팀 작업 디렉토리는 이벤트 계약 우회 신호(정보성).
- **`_workspace/` 하우스키핑**: 최종 수정이 **14일 경과**한 작업 디렉토리를 삭제 후보로 목록화해 제안한다(예: `find _workspace -mindepth 1 -maxdepth 1 -type d -mtime +14` — 디렉토리 mtime은 근사치라 후보는 참고용, 최종 판단은 사용자 확인). 운영 데이터 예외 3종(`harness-updates.md`·`harness-ops-log.md`·`.harness-review-*` 마커 — 루트 AGENTS.md 4절)은 제외하고, **삭제 실행은 3절 파괴적 작업이므로 사용자 확인 후에만** 한다. 이유: 4절 "미보존" 원칙에 집행 장치가 없어 세션 산출물이 무기한 누적되고 있었다(2026-07-18 관찰 — 감사 디렉토리 5+ 잔존).
- 대기 큐: `_workspace/harness-updates.md`에 상태 `대기` 항목이 있는지(루트 AGENTS.md 5절 설치처 프로필). **개인 설치처**면 이월된 개선이 잠자고 있는 것 — metaskill 적용을 제안한다. **사내 설치처**면 정상(개인 머신 이월 대기 중) — 항목 수만 보고한다.
- 변경 이력: 최근 하네스 커밋마다 변경 이력 갱신이 동반되었는지 — **루트는 `git log -p -- docs/harness-changelog.md`**(ADR 021로 분리), 하위 프로젝트는 해당 AGENTS.md 하단 테이블. CLAUDE.md 첫 줄 `@AGENTS.md` 임포트 존재도 함께 확인(ADR 021 — 산문 링크로 회귀하면 단일 원본이 항상-온이 아니게 된다).
- 시크릿 유출(agentsview 설치 시): `agentsview secrets scan`으로 세션 로그에 시크릿이 샜는지 스캔한다 — 3절 가드레일("기록 금지")은 예방 규칙이고 이것이 사후 검증이다. 발견 시 must-fix로 즉시 사용자 보고.
- 선언-미구현: 선언만 있고 강제 장치(훅·테스트·절차 단계·문구 단정)가 없는 규칙을 목록화한다 — 티어→모델 매핑 미적용, "병렬 실행" 선언의 순차 실행, 침묵 훅이 전부 이 유형이었다. 사용 신호(1단계)로는 안 잡히므로 구조 검사로 잡는다.
- 로딩 비대(토큰 낭비의 하네스 자체 기여분): SKILL.md 본문 500줄 초과(metaskill 공통 규칙 3 위반), 항상 로드되는 CLAUDE.md·description의 비대를 확인한다 — 매 세션의 고정 토큰 비용이므로, 초과분은 `references/` 분리·압축을 제안한다.

### 3. 제안 생성

- 신호가 감지되면: 어떤 신호가, 어떤 근거로, 어떤 에이전트/스킬 신설·개선으로 이어지는지를 **metaskill 호출 제안** 형태로 정리해 사용자에게 보고한다. 승인 없이 생성하지 않는다.
- **설치처 프로필 분기 (제안 확정 전 REGISTRY.md 프로필 확인 — 루트 AGENTS.md 5절)**: **사내** 설치처면 저장소 수정을 제안하지 않는다 — 사용자 승인 시 제안 내용을 `_workspace/harness-updates.md`에 `대기` 항목으로 기록한다(5절 형식: 대상 파일·변경 내용·사유를 개인 머신에서 맥락 없이 적용 가능한 수준으로). **개인** 설치처면 기존대로 metaskill 실행을 제안한다.
- 신호가 없으면: "신호 없음 — 현재 구조 유지"라고 보고하고 끝낸다. **무신호에 개선을 지어내지 않는다** — 진화 제안은 8절 신호에 근거할 때만 정당하다.

### 4. 완료 마커·운영 로그 갱신 (누락 금지 — 갱신 주체는 점검 수행자, 위임 시 서브에이전트)

- **마커**: 오늘 날짜(**KST 기준** `YYYY-MM-DD`) 한 줄을 기록한다 — **일일 모드**는 `_workspace/.harness-review-daily-last`, **주간 전체 모드**는 `.harness-review-last`와 `.harness-review-daily-last` 둘 다. SessionStart 리마인더 훅(`harness-review-reminder.py`)이 이 마커들로 1일/7일 경과를 판정해 다음 점검을 자동 트리거한다(경과 판정도 KST — 읽기·쓰기 타임존을 맞춘다). 마커를 갱신하지 않으면 매 세션 리마인더가 반복된다.
- **운영 로그**: `_workspace/harness-ops-log.md`에 점검 결과 한 줄을 append한다 — 형식: `- YYYY-MM-DD [전체 점검|일일 점검] 신호 N건(요약) / 무결성 통과|문제 N건 / 제안 N건(요약)`. 이 로그가 "지난 점검에서 뭘 봤고 뭘 개선했는지"의 채팅 밖 단일 기록이다(개선 실행 기록은 metaskill이 `[개선]` 항목으로 append). 리마인더 훅은 기한 전이면 무출력이므로(노이즈 제거, 2026-07-16), 지난 내역은 이 로그로 직접 확인한다.

## 출력 형식

1. 신호 각각의 감지 여부와 근거 (일일: ①~③, 주간: ①~④)
2. 구조 무결성 점검 결과 (통과/문제)
3. metaskill 제안 목록 (없으면 "없음")
4. 완료 마커 갱신 확인

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 진화 트리거 | "주 1회 관찰" 선언만 있고 절차 부재 → 미실행 | 고정 절차로 재현 가능한 점검 |
| 우회 감지 | .claude/ 직접 생성·레지스트리 불일치가 조용히 누적 | 무결성 점검에서 표면화 |
| 오버 엔지니어링 | 점검자가 매번 즉흥 개선안 양산 | 무신호 시 "유지" 보고로 종료 |
