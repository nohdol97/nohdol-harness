# ADR 018 — claude-mem의 최소 채택 (세션 경계 리마인더 + 점진적 공개 + private 마커)

- **날짜**: 2026-07-16
- **변경 내용**: claude-mem(github.com/thedotmack/claude-mem, Apache-2.0)을 분석하고 **패턴 3개를 무의존 방식으로 이식**한다. ① 세션 경계 진행-기록 리마인더 훅(`worklog-reminder.py`, SessionStart) 신설, ② `_workspace/` 리포트의 점진적 공개(2단) 규약(AGENTS.md 4절 + explorer 출력), ③ `<private>` 제외 마커(AGENTS.md 3절 가드레일 + work-tracker 흐름 2). claude-mem의 **런타임 인프라(로컬 HTTP 워커·SQLite·Chroma 벡터 DB·Bun/uv)와 전수 자동 캡처는 채택하지 않는다.**
- **대상**: `.agents/hooks/worklog-reminder.py`(+회귀 테스트·스펙), `.claude/settings.json`(SessionStart 등록), AGENTS.md 3·4절, `.agents/agents/explorer.md`, `.agents/skills/work-tracker/SKILL.md`, docs/proposals/2026-07-16-claude-mem-adoption.md, docs/specs/2026-07-16-worklog-reminder-hook.md
- **사유**: 사용자 요청(2026-07-16 — "claude-mem을 분석하고 적용할 수 있는 것을 검토·적용"). claude-mem은 이 하네스와 같은 Claude Code 확장이지만 **무거운 인프라로 자동 전수 기억**을 지향하는 반면, 이 하네스는 **가벼운 규약으로 의도적 상태 영속**(work-tracker, ADR 009)을 지향한다 — 방향이 달라 시스템 이식은 이식성 원칙(ADR 005)·최소주의(ADR 017)와 충돌한다. 다만 철학과 정합하며 저비용인 착안 3개는 채택 가치가 있다.

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| ① 세션 경계 리마인더 채택 | SessionStart 훅이 로컬 git으로 이전 세션의 미커밋 작업을 감지해 work-tracker 흐름 2/3을 환기 | 14절 흐름 2("세션 종료 시 진행 로그")의 실행이 기억 의존 — harness-review-reminder가 주간 점검에 대해 푼 공백과 같은 종류. claude-mem은 SessionEnd 캡처로 풀지만, 그 이벤트는 모델을 못 깨우므로(리마인더와 동일 제약) SessionStart 로컬 감지로 같은 경계 보호를 무의존으로 얻는다. 스펙: docs/specs/2026-07-16-worklog-reminder-hook.md |
| ② 점진적 공개 리포트 규약 채택 | 발견 많은 `_workspace/` 리포트 = 요약 인덱스(ID·severity·요지) + ID 참조 상세 2단. 단일 원본 AGENTS.md 4절, explorer 출력에 반영 | claude-mem의 최강 이식 후보 — 리포트는 쓰기 1회·읽기 N회(15절)라 인덱스 후 필터가 재독 토큰을 곱으로 줄인다(claude-mem "10x 토큰 절감"의 원리). 인프라 없이 프롬프트 규약으로 흡수. 짧은 리포트는 생략(16절 최소주의) |
| ③ `<private>` 제외 마커 채택 | 외부 발행물(이슈·PR·코멘트)로 옮길 때 `<private>` 내용 제외. 3절 가드레일 + work-tracker 흐름 2 | 기존 시크릿 가드레일(3절)의 연장선 — `_workspace`→이슈 요약 이동 시 민감정보 누출 지점에 명시적 마커를 준다. 소규모 보강 |
| 워커·SQLite·Chroma·Bun/uv 스택 기각 | 로컬 HTTP 워커·벡터 DB·별도 런타임 매니저를 도입하지 않는다 | ADR 005(미추적 이식형 하네스)와 정면 충돌 — 이 하네스는 의도적으로 마크다운+python 훅만으로 설치처를 따라오게 설계됐다. 상시 서비스·벡터 DB·런타임 매니저는 무의존·이식성을 깬다. 시맨틱 검색 이득 < 운영 부담 |
| 전수 자동 캡처 기각 | 세션 전체를 자동 관찰·압축·저장하지 않는다 | work-tracker의 "멀티세션 작업만 등록 — 이슈 무덤 방지"(ADR 009)·16절 최소주의와 충돌. 이 하네스의 공백은 '전수 기억'이 아니라 의도적 상태 영속이었고 그건 이미 해결됨. ①은 캡처가 아니라 감지·환기만 한다 |
| 문서로만 이식 | ②③은 규칙 문서(AGENTS.md·에이전트·스킬)에만, ①은 훅 1개로. claude-mem 코드베이스를 복제하지 않는다 | 규칙의 유일 운반체는 문서다(12절). ponytail 채택(ADR 017)과 같은 원칙 — 배송 기계 전체가 아니라 착안만 옮긴다. 이 채택 자체가 16절 사다리 1(YAGNI)·2(재사용)의 실천 |

## 검증

- **스펙**: `docs/specs/2026-07-16-worklog-reminder-hook.md` — R1~R6·C1~C7.
- **회귀 테스트**: `.agents/hooks/worklog-reminder_test.py` 12케이스 전부 통과(2026-07-16) — build_message·dirty_count(실 git 저장소)·main 흐름·cp949·fail-open 포함.
- **분석·비목표 상세**: `docs/proposals/2026-07-16-claude-mem-adoption.md`.
