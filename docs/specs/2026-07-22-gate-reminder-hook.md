# 스펙: gate-reminder 훅 — 진단→구현 전환점의 orchestrate 게이트 상기

- 날짜: 2026-07-22
- 상태: 구현됨
- 대상 코드: `.agents/hooks/gate-reminder.py` (+ `.claude/settings.json`, `.codex/config.toml` 등록)
- 관련: ADR 028·031, 루트 AGENTS.md 7절 3항·8절 신호 ②

## 배경

같은 세션(사내 머신, mx-ai-store live-editor 2026-07-21/22) 안에서 "읽기 전용 진단(kubectl·로그·원인 추적)으로 시작한 흐름이 코드 수정으로 자연스럽게 넘어가는" 전환점에 orchestrate Phase 0-1 게이트를 건너뛴 사례가 **2회** 발생했다. 1회차는 사용자가 직접 지적("왜 orchestrate 호출 안됐어")했고 자가 정정을 선언했음에도, 같은 세션 뒤쪽 ArgoCD Degraded 진단에서 동일 패턴이 재발했다 — 자가 정정이 "명시적 구현 요청"이라는 트리거 조건에 갇혀, 진단이 조용히 구현으로 미끄러지는 변형을 놓쳤다. 루트 AGENTS.md 8절 신호 ②(같은 실패 2회 이상)에 해당하며, 같은 절의 "기계적 차단이 가능하면 훅으로 승격" 원칙에 따라 프롬프트 문구 보강(CLAUDE.md 앵커·AGENTS.md §7-3)과 **별도로** 실행 계층 개입을 둔다. 프롬프트 텍스트만으로는 이 전환 시점을 붙잡지 못했음이 실측됐기 때문이다.

## 목표

- 조사성 Bash 호출(진단 패턴)이 관찰된 세션에서, **제품 코드에 첫 Edit/Write가 닿기 직전에** orchestrate Phase 0-1 게이트 판정 선언을 기계적으로 상기시킨다.
- 상기는 **세션당 최대 1회 차단**으로 강제한다 — 해당 호출을 1회 차단하고(stderr로 지시), 판정 선언 후 재시도는 통과시킨다.
- 어떤 실패도 세션을 막지 않는다(fail-open) — 훅 오류·비정상 입력은 전부 통과(exit 0).

## 비목표

- 게이트 판정의 **내용** 검증(직접 수행/쌍/팀 판정이 맞는지) — 판정 품질은 orchestrate 스킬과 리뷰의 몫이고, 이 훅은 "판정 없이 미끄러지는 것"만 막는다.
- trust 이전이나 Windows에서의 **동작 보장** — Codex 프로젝트 훅은 trust 뒤에만 실행되며 이번 PreToolUse·PostToolUse 실측은 macOS/CLI 0.145.0 범위다. tdd-gate가 git 계층으로 이동한 것(ADR 014·015)과 달리 이 훅은 **커밋 산출물이 아니라 세션 중 라우팅 행동**을 교정하므로 git 훅으로 옮길 수 없다 — 도구 한정 계층이 정당한 경우다.
- 진단 패턴의 완전 열거 — 실측된 우회(kubectl·ArgoCD·로그)를 중심으로 보수적 목록에서 시작하고, 재발 관찰 시 확장한다(과잉 매칭은 오탐 차단으로 규율을 노이즈화한다 — 루트 16절).

## 요구사항

- R1 (record): PostToolUse(Bash)에서 command가 진단 패턴(kubectl / argocd / stern / journalctl / docker logs / helm status·get / aws logs)에 걸리면 세션 상태 파일 `_workspace/.gate-reminder/<session_id>`에 `diag`를 기록한다. 상태 파일이 이미 있으면(diag든 reminded든) 덮어쓰지 않는다 — 세션당 1회 원칙.
- R2 (check-차단): PreToolUse(Edit|Write|MultiEdit|NotebookEdit)에서 상태가 `diag`이고 대상 파일이 제외 경로가 아니면: 상태를 `reminded`로 갱신하고, stderr로 게이트 판정 선언 지시(판정 한 줄 선언 + 3+파일→implementer / 인프라 매니페스트→infra-specialist, 이미 선언·발행된 경우 확인 후 재시도)를 출력하고 **exit 2**(도구 호출 차단, stderr가 모델에게 전달됨)한다.
- R3 (check-통과): 상태 파일이 없거나 `reminded`면 exit 0. Claude형 `file_path`·`notebook_path`와 Codex형 `apply_patch.command`의 Add/Update/Delete/Move 경로를 모두 읽는다. 모든 대상이 `_workspace` 또는 시스템 임시 경로(`/tmp/` 등)면 상태를 소모하지 않고 exit 0; 하나라도 제품 경로면 R2로 차단한다.
- R4 (fail-open): stdin JSON 파싱 실패, session_id 부재, 상태 디렉토리 쓰기 실패 등 모든 예외에서 exit 0. stdio는 `_common.utf8_stdio()`로 재구성(유실 시 no-op 폴백).
- R5 (정리): record 시 7일 초과 상태 파일을 기회적으로 삭제한다(mtime 기준, 실패 무시) — 세션 잔재가 누적되지 않게.
- R6 (등록): `.claude/settings.json`에 PostToolUse(matcher `Bash`, `--record`)·PreToolUse(matcher `Edit|Write|MultiEdit|NotebookEdit`, `--check`)로 등록하고, 기존 훅과 같은 python 탐색 래퍼(`for p in python3 python py; ... exec`)를 쓴다 — python 부재 시 exit 0(fail-open). Codex는 `.codex/config.toml` 인라인 PostToolUse·PreToolUse에 `$PWD` 경로로 등록한다(ADR 031). 래퍼 앞에는 R7의 존재 가드를 둔다.
- R7 (등록 존재 가드): 두 등록 모두 `f="<기준 경로>/.agents/hooks/gate-reminder.py"; [ -r "$f" ] || exit 0;`로 시작하고 탐색 래퍼는 확인한 `"$f"`를 실행한다. 이유: 경로가 안 풀리면(빈 `CLAUDE_PROJECT_DIR`, Codex `$PWD`가 루트 아님, 파일 유실·권한) 인터프리터가 exit 2로 죽고, PreToolUse에서 그 값은 도구 호출 차단이다 — R4의 fail-open 훅이 **모든 Edit/Write를 막는** fail-closed로 뒤집힌다(2026-11-27 하네스 전수 점검 C-07 — 가드 없는 `--check`가 빈 `CLAUDE_PROJECT_DIR`에서 rc=2 실측). tier-gate 스펙 R11과 같은 형태이며, 등록 형태의 회귀는 integrity-check R18·R21(스펙 2026-07-19-integrity-check-script 4b)이 맡는다.
- R8 (입력 디코딩): `--record`·`--check` 모두 stdin을 읽기 전에 `_common.utf8_stdio()`로 stdin을 UTF-8(errors=replace)로 재구성한다 — cp949 로케일에서 한글이 든 진단 명령의 판독이 실패하면 R4 fail-open으로 전환점을 놓친다(2026-11-27 하네스 전수 점검 C-05). 훅 자체 코드는 그대로이고 `_common` 단일 원본이 stdin을 포함하게 됐다(스펙 2026-07-15-hooks-common-bootstrap R1).

## 완료 기준

- [x] 진단 명령 record → 상태 파일 `diag` 생성; 비진단 명령은 미생성 (R1)
- [x] `diag` 상태에서 제품 코드 경로 check → exit 2 + stderr에 게이트 지시 + 상태 `reminded` (R2)
- [x] 같은 세션 2번째 check → exit 0 (세션당 1회) (R2)
- [x] `_workspace/`·`/tmp/` 경로 check → exit 0, 상태 `diag` 유지 (R3)
- [x] reminded 상태에서 추가 진단 record → 재무장 안 됨 (R1)
- [x] 비정상 stdin(빈 입력·깨진 JSON·session_id 부재) → record/check 모두 exit 0 (R4)
- [x] 7일 초과 상태 파일은 record 시 정리되고 신선한 파일은 유지 (R5)
- [x] 회귀 테스트: `.agents/hooks/gate-reminder_test.py` 전체 통과 (수정 시 필수)
- [x] Codex CLI 0.145.0에서 PostToolUse 진단 기록 뒤 PreToolUse `apply_patch`가 exit 2로 실행 전에 차단됨
- [x] Codex형 `apply_patch.command`에서 `_workspace` 단독은 diag 유지·통과, 제품 단독/혼합은 exit 2 차단
- [x] `.claude/settings.json`·`.codex/config.toml`의 gate-reminder 등록 4건이 존재 가드형이며, 가드를 지우거나 실행 경로를 `"$f"` 밖으로 바꾸면 integrity-check가 FAIL한다(`integrity-check_test.py`의 `test_every_claude_command_needs_the_existence_guard`·`test_every_codex_command_needs_the_existence_guard`·`test_guard_must_cover_the_executed_path`·`test_live_registrations_carry_the_guard`) (R7)
- [x] `PYTHONIOENCODING=cp949`에서 한글이 든 진단 명령을 원 바이트 UTF-8로 record → exit 0, 상태 `diag`(`test_utf8_payload_arms_under_a_cp949_locale`) (R8)

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-25 | Codex 등록을 인라인 config로 전환하고 Pre·PostToolUse 입력·exit 2 차단 실측 완료 | 비목표·R6·완료 기준 | ADR 031, Codex CLI 0.145.0 macOS 런타임 검증 |
| 2026-07-25 | Codex `apply_patch.command` 대상 경로 파싱과 단독/혼합 회귀 3종 추가 | R3·완료 기준·훅 | 독립 reviewer F1 — `_workspace` patch가 one-shot 상태를 소모해 후속 제품 수정을 무차단하던 회귀 차단 |
| 2026-11-27 | 등록 존재 가드 R7·stdin 디코딩 R8 신설, 완료 기준 2건 추가 | R6·R7·R8·완료 기준, `.claude/settings.json`, `.codex/config.toml`, `gate-reminder_test.py` | 하네스 전수 점검 — C-07: 가드 없는 `--check` 등록이 빈 `CLAUDE_PROJECT_DIR`에서 rc=2로 모든 Edit/Write를 막음(실측). C-05: cp949 stdin 디코딩이 한글 진단 명령 판독을 깸 |
