# 스펙: worklog-reminder 훅 — 세션 경계 진행-기록 리마인더

- 날짜: 2026-07-16 / 상태: 구현됨
- 관련: 루트 AGENTS.md 14절(work-tracker 세션 영속), work-tracker SKILL.md 흐름 2·3, docs/specs/2026-07-14-harness-review-reminder-hook.md(훅 규격 선례), docs/adr/018(claude-mem 채택), docs/proposals/2026-07-16-claude-mem-adoption.md

## 배경

14절은 "세션을 넘는 작업의 상태는 프로젝트 저장소에 영속화"하고 **세션 종료·중단 시 진행 로그(완료/다음/막힘)를 남기는 것이 재개의 시작점**이라고 규정하지만(work-tracker 흐름 2), 그 실행이 **사용자·모델의 기억에 의존**한다 — 세션이 급히 닫히면 진행 로그가 어디에도 남지 않아 다음 세션이 git 이력으로 상태를 역추적해야 한다(harness-review-reminder가 주간 점검에 대해 해결한 것과 같은 종류의 공백).

claude-mem(github.com/thedotmack/claude-mem, Apache-2.0)은 이 "세션 경계 컨텍스트 유실"을 SessionEnd/Stop 훅으로 **세션 전체를 캡처·압축**해 로컬 워커·SQLite·벡터 DB에 쌓아 해결한다. 그 인프라 전체는 이 하네스의 무의존·이식성 원칙(ADR 005)과 충돌해 채택하지 않되(제안서 참조), **"세션 경계에서 진행 상태를 잃지 않는다"는 착안 하나**를 무의존 방식으로 옮긴다.

## 목표

- 다음 세션 **SessionStart에 로컬 git으로 이전 세션이 남긴 미커밋 작업을 감지**해, 있으면 work-tracker 흐름 2(진행 로그) / 흐름 3(재개)을 환기하는 한 줄을 세션 컨텍스트에 주입한다. 미커밋 변경이 없으면 **침묵**한다(harness-review-reminder와 달리 상태 한 줄도 남기지 않는다 — 이 훅의 "정상"은 깨끗한 트리이고, 매 세션 출력은 노이즈다).

## 비목표

- 세션 전수 캡처·압축·시맨틱 검색(claude-mem의 워커·DB) — 채택하지 않는다(제안서 비목표, ADR 018). 이 훅은 **감지·환기**만 하고 상태를 쓰지 않는다.
- SessionEnd/Stop 훅으로의 구현 — 그 이벤트는 모델을 깨우지 못해 지시를 세션에 주입할 수 없다(harness-review-reminder와 동일 제약). 이전 세션의 미커밋 작업은 지속형 설치처에서 워킹 트리에 그대로 남으므로, 다음 SessionStart의 로컬 git 조회로 같은 경계 보호를 얻는다.
- 멀티세션 여부의 자동 판정 — 로컬만으로는 GitHub epic 이슈 존재를 알 수 없다(gh는 네트워크라 훅 부적합). 그래서 메시지는 단정이 아니라 조건부 환기이며, "멀티세션 작업만 해당"을 문구로 명시한다.
- ~~Codex 세션 트리거~~ → **2026-07-16 채택(ADR 019)**: Codex v0.114+가 동일 포맷 SessionStart 훅을 지원해 이 훅을 `.codex/hooks.json`에도 등록했다(스크립트 무변경 — 도구 무관). 활성화는 머신 로컬(`[features] codex_hooks = true`)·macOS/Linux 한정(실험·Windows 미지원). macOS 실측 검증은 harness-updates.md 대기 항목.

## 요구사항

- R1: SessionStart 훅. 기준 디렉토리는 `CLAUDE_PROJECT_DIR`(부재 시 cwd). 그 디렉토리에서 **추적 파일의 미커밋 변경 수**(`git status --porcelain=v1 --untracked-files=no`의 비어있지 않은 줄 수)를 센다.
- R2: 미추적 파일은 제외한다 — 새 산출물·빌드물·`_workspace/` 잔여물이 리마인더를 남발시키면 게이트가 무시된다(fail-open 학습). 신호는 "추적 중인 작업이 커밋되지 않은 상태"다.
- R3: 미커밋 변경이 1개 이상이면 흐름 2/3 환기 메시지를 출력한다 — 브랜치명(있으면), 변경 수, 흐름 2·흐름 3 지시, "멀티세션 작업만 해당" 단서를 포함한다. 0개면 무출력.
- R4: fail-open — git 미설치·비저장소·명령 실패·예외는 전부 무출력 exit 0(세션 시작을 막지 않는다). git 조회 실패는 침묵(변경 수 None → 무출력). 시작 시 stdout을 **UTF-8(errors=replace)로 재구성**한다(cp949 콘솔에서 em dash가 print 예외를 던져 fail-open이 삼키는 장애 방지 — 리마인더 스펙 R4와 동일 원인). 재구성 로직의 단일 원본은 `_common.py`(스펙 2026-07-15-hooks-common-bootstrap), 유실 시 no-op 폴백.
- R5: 읽기 전용 — 마커·상태 파일을 쓰지 않는다. work-tracker의 상태 영속(이슈·backlog)은 스킬의 몫이고 이 훅은 트리거만 한다.
- R6: 회귀 테스트가 `.agents/hooks/worklog-reminder_test.py`로 영속되어야 한다.

## 인터페이스 / 설계 개요

- 등록: 루트 `.claude/settings.json` → SessionStart, command는 인터프리터 탐색 체인 `for p in python3 python py; do "$p" -c "" >/dev/null 2>&1 && exec "$p" "$CLAUDE_PROJECT_DIR/.agents/hooks/worklog-reminder.py"; done; exit 0`(리마인더·agentsview-daemon과 같은 방식 — `.py` 직접 실행의 Windows 실패와 Store 스텁을 실행 확인 `-c ""`로 회피).
- 입력: 없음(stdin 무시). 출력: 미커밋 변경이 있으면 stdout 한 줄(세션 컨텍스트로 주입), 아니면 무출력. 항상 exit 0.
- 부수 효과 없음 — 로컬 git 조회뿐(네트워크 없음, R5: 쓰기 없음).

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R3): 변경 3개 + 브랜치 있음 → 메시지에 "work-tracker"·"흐름 2"·"흐름 3"·브랜치명·변경 수·"멀티세션" 포함.
- [x] C2 (R3): 변경 0개 → `build_message`가 None(무출력).
- [x] C3 (R4): git 조회 실패(변경 수 None) → `build_message`가 None(무출력).
- [x] C4 (R1·R2·R3): 실제 임시 git 저장소 — 깨끗하면 `dirty_count`=0·main 무출력, 추적 파일 수정 시 `dirty_count`=1·main이 메시지 출력. 미추적 파일만 있으면 0. 비저장소 디렉토리 → None.
- [x] C5 (R4): cp949 stdout(한글 Windows 콘솔) + 더티 저장소 → 메시지가 UTF-8로 실제 출력됨(무출력 아님), exit 0.
- [x] C6 (R4): main 내부 예외 → 무출력, exit 0(fail-open).
- [x] C7 (R6): `python3 .agents/hooks/worklog-reminder_test.py` 전 케이스 통과.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-16 | 초안 작성 및 구현 | 전체 | claude-mem 분석·채택(제안서 2026-07-16, ADR 018) — 세션 경계 진행-기록 유실 공백을 무의존 SessionStart 로컬 git 감지로 메움 |
| 2026-07-16 | Codex 세션 트리거 채택 — 비목표에서 in-scope로, `.codex/hooks.json` 등록(스크립트 무변경) | 비목표 | 사용자 요청(맥북 Codex 병행). Codex v0.114+ 동일 포맷 지원. docs/adr/019 |
