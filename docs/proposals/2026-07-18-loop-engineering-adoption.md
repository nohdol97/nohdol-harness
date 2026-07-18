# 제안: loop-engineering 검토 — 시크릿 게이트 1건 이식, 나머지 기각

- 날짜: 2026-07-18 / 결과: → ADR 023 (시크릿 게이트 채택), 나머지 기각
- 출처: github.com/cobusgreyling/loop-engineering (MIT, 5.5k★) — "프롬프트를 치는 사람에서 루프를 설계하는 사람으로"

## 분석 요지

핵심 주장(maker/checker 분리·상태 영속·시도 상한·예산 상한·인간 게이트·실패 카탈로그)을 하네스 현행과 전수 대조한 결과, **대부분 등가물이 이미 있다** — 이 하네스가 ponytail·superpowers·ccpm·claude-mem에서 같은 계열 개념을 선별 이식해 와 원칙 층이 기수렴했기 때문이다. 대조표는 세션 보고(2026-07-18) 참조. 예: verifier의 기각 우선 자세 ↔ reviewer "거짓 통과 > 거짓 차단", attempt cap ↔ orchestrate 재시도 2~3회, budget ↔ 일일 점검 비용 상한, run log ↔ harness-ops-log.md.

## 채택 (1건)

- **기계적 시크릿 커밋 게이트** (`gate.yaml`+loop-gate 착안): 3절 "시크릿 기록 금지"는 문서 규칙뿐이었다 — 8절 승격 원칙("기계적 차단 가능하면 훅으로")에 따라 tdd-gate와 같은 git commit-msg 계층에 `secret-gate.py`를 신설. 상세: docs/specs/2026-07-18-secret-gate-hook.md, ADR 023. loop-gate의 경로 denylist·auto-merge allowlist는 이식하지 않았다 — 하네스에는 auto-merge 자체가 없고(머지는 항상 사용자 몫, 5절), 경로 보호는 3절 사용자 확인 게이트가 담당한다.

## 기각 (근거 포함)

- **7종 unattended 루프 패턴**(daily triage·PR babysitter·CI sweeper 등): 크론/Actions 무인 유지보수 패턴. 하네스는 대화형 세션 + SessionStart 마커 리마인더 구조를 의도적으로 선택했고, 수요 신호 없는 도입은 지연 생성 원칙(ADR 007) 위반.
- **npm 도구군**(loop-audit 점수·loop-cost·loop-init): 자체 관측 수단(agentsview 실측)이 이미 있고, 점수화는 하네스 점검 체계와 중복.
- **L1→L2→L3 단계적 자율성 규칙**: 좋은 원칙이나 현행 자동화가 리마인더 훅 2종뿐이라 적용 대상 부재. **향후 스케줄드 에이전트·unattended 자동화를 도입하게 되면 이 저장소의 단계 롤아웃·budget·kill switch 절을 재참조한다**(이 문서가 그 포인터다).
- **실패 카탈로그 문서·STATE.md 프루닝 규칙 등**: 실수 즉시 기록(8절)·주간 무결성 점검이 같은 역할을 더 가볍게 수행 중 — 문서 신설은 비대.
