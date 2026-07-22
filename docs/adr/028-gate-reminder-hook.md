# ADR 028: gate-reminder 훅 — 진단→구현 전환점 게이트 상기의 실행 계층 승격

- **날짜**: 2026-07-22
- **변경 내용**: PostToolUse(Bash)/PreToolUse(Edit|Write 계열) 세션 훅 `gate-reminder.py` 신설 — 조사성 Bash(kubectl·argocd·로그 등)가 관찰된 세션에서 제품 코드 첫 Edit/Write를 세션당 1회 차단하고 orchestrate Phase 0-1 게이트 판정 선언을 지시한다. 동시에 프롬프트 계층도 보강: CLAUDE.md 앵커·AGENTS.md 7절 3항·orchestrate SKILL.md continuation 항에 "읽기 전용 진단이 코드 수정으로 넘어가는 전환점도 재판정 대상 — 첫 Edit/Write가 트리거" 문구 추가.
- **대상**: `.agents/hooks/gate-reminder.py`(+테스트·스펙), `.claude/settings.json`, CLAUDE.md, AGENTS.md 7절, orchestrate SKILL.md
- **사유**: 같은 세션(사내, mx-ai-store live-editor 2026-07-21/22)에서 진단→수정 전환점의 게이트 우회가 **2회** 발생 — 1회차는 사용자가 직접 지적("왜 orchestrate 호출 안됐어")했고 자가 정정을 선언했음에도, ArgoCD Degraded 진단에서 동일 패턴이 재발했다. 자가 정정이 "명시적 구현 요청"이라는 트리거 조건에 갇혀, 진단이 조용히 구현으로 미끄러지는 변형을 놓친 것이다. 8절 신호 ②(같은 실패 2회, 사용자 정정 포함)이자 "기계적 차단이 가능하면 훅으로 승격" 원칙의 적용 — 프롬프트 문구만으로는 전환 시점을 붙잡지 못했음이 실측됐으므로, 문구 보강(상기 빈도)과 실행 계층 개입(전환 시점 포착)을 함께 둔다.

## 설계 결정

1. **차단은 세션당 최대 1회, fail-open**: 목적은 판정 강제가 아니라 "판정 없이 미끄러지는 것"의 차단이다. 첫 수정 호출을 1회 막고 판정 선언을 지시한 뒤 재시도는 통과시킨다 — 오탐(이미 판정된 세션·발행된 implementer)의 비용이 재시도 1회로 상한된다. 훅의 모든 오류는 통과(exit 0).
2. **Claude 세션 계층이 정당하다 (tdd-gate의 git 계층 이동과 다른 이유)**: tdd-gate는 커밋 산출물 검사라 도구 무관 git 계층(ADR 014·015)이 맞았지만, 이 훅은 **세션 중 라우팅 행동**(수정 도구 첫 호출 시점)의 교정이라 git 훅으로는 개입 시점이 존재하지 않는다. Codex에는 PreToolUse 상당 이벤트가 없어 미등록 — Codex 세션은 AGENTS.md 7절 3항 문구(네이티브 로드)가 담당하고, 이 비대칭은 수용한다(문구 계층은 양 CLI 공통, 기계 계층은 Claude 한정).
3. **진단 패턴은 보수 목록**: 실측된 우회(kubectl·ArgoCD·로그) 중심 — kubectl / argocd / stern / journalctl / docker logs / helm status·get / aws logs. 과잉 매칭은 오탐 차단으로 규율을 노이즈화한다(16절). 재발 관찰 시 확장한다.
4. **`_workspace/`·임시 경로 쓰기는 소모 없이 통과**: 서브에이전트 리포트·스크래치 쓰기는 제품 코드 수정이 아니다 — 상태를 유지해 진짜 제품 코드 첫 수정에서 상기한다.

상세 계약·완료 기준: docs/specs/2026-07-22-gate-reminder-hook.md. 같은 큐 배치에서 branch-workflow에도 "세션 재개·모델 전환 후 브랜치 재확인" 예방 절차가 추가됐다(별도 실사례 — 재개 직후 main 직커밋 직전 발견).
