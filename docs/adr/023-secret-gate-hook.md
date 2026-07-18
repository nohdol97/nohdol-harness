# ADR 023: secret-gate 훅 — 3절 시크릿 금지의 실행 계층 승격

- **날짜**: 2026-07-18
- **변경 내용**: 루트 AGENTS.md 3절 "시크릿·자격증명 기록 금지"에 실행 계층 게이트를 신설했다. `.agents/githooks/secret-gate.py`(git commit-msg 훅)가 스테이징된 diff의 추가 줄에서 형식 확정 자격증명 패턴(개인키 블록·AWS·GitHub·Slack·Google·Stripe·OpenAI/Anthropic 계열)을 탐지해 커밋을 차단한다. 기존 `commit-msg` shim이 tdd-gate에 이어 실행하므로 **신규 머신 설정이 없다**(전역 core.hooksPath 재사용 — ADR 014·015 계층 그대로).
- **대상**: `.agents/githooks/secret-gate.py`, `secret-gate_test.py`, `commit-msg` shim, 루트 AGENTS.md 3절
- **사유**: 3절은 문서 규칙이라 강제력이 없고, 시크릿은 푸시 순간 원격 이력에 영구히 남아 사후 비용(force push + 키 폐기)이 크다. 8절 승격 원칙("기계적 차단이 가능하면 훅으로")의 두 번째 적용 사례다(첫째: tdd-gate). 착안은 loop-engineering의 gate.yaml 기계 게이트(제안: docs/proposals/2026-07-18-loop-engineering-adoption.md), 사용자 승인 2026-07-18.
- **핵심 설계 결정**:
  - **tdd-gate와 달리 예외 저장소가 없다**(루트 하네스·dev/ 포함 전부 적용) — 시크릿은 어느 이력에 들어가도 사고다. 최초 커밋도 검사한다(첫 커밋이 `.env` 유입의 전형).
  - **고신뢰 형식 확정 패턴만** 탐지한다. 일반 대입문·고엔트로피 추정은 비목표 — 오탐이 `[secret-ok]` 남용을 학습시켜 게이트를 죽인다(tdd-gate R3의 false block 교훈). 전수 탐지는 gitleaks 등 전용 도구의 몫.
  - 오탐 우회는 커밋 메시지 `[secret-ok]`(사용자 확인 전제) 단일 경로 — `[no-test]` 전례와 동일하게 메시지에 승인 흔적이 남는다.
  - fail-open·exit 65·UTF-8 stdio 재구성은 tdd-gate 규약을 그대로 공유한다(스펙 R4).
- **스펙**: docs/specs/2026-07-18-secret-gate-hook.md (완료 기준 C1~C12, 회귀 테스트 15항목 통과)
