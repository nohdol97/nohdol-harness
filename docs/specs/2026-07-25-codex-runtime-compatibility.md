# 스펙: Codex 런타임 호환성 복구

- 날짜: 2026-07-25 / 상태: 구현됨
- 관련: `_workspace/codex-compat-audit-2026-07-25/phase2_integrator_final-report.md`, ADR 019·027·029

## 배경

Codex CLI 0.144.6 실측에서 루트 `AGENTS.md`가 기본 32 KiB 로딩 한도를 넘어 후반 규칙이 잘렸고, R14는 40,000바이트까지 허용해 이를 통과시켰다. custom agent, SessionStart 출력, PreToolUse·PostToolUse도 정적 등록과 실제 런타임 동작이 일치한다고 확인되지 않았다. 설정과 문서에는 폐기 예정 키와 trust 이전에도 즉시 활성화되는 것처럼 읽히는 설명이 남아 있다.

## 목표

- 신선한 기본 Codex 환경에서도 루트 항상-온 규칙의 끝까지 로드된다.
- 무결성 검사가 Codex 기본 로딩 한도보다 먼저 비대화를 차단한다.
- Codex 설정은 현재 공식 키와 trust 계약을 정확히 표현한다.
- custom agent와 훅의 지원 범위를 설치된 최신 CLI에서 재측정하고, 확인된 동작만 보장한다.
- Claude Code 호환성과 기존 하네스 규범의 의미를 유지한다.

## 비목표

- 공식 계약에 없는 훅 출력의 모델 문맥 주입 래퍼를 추측해 구현하지 않는다.
- Codex 한계를 숨기기 위해 `.agents/agents/*.md` 역할 원본을 복제하거나 구체 모델·sandbox를 어댑터에 고정하지 않는다.
- R14를 위해 범용 WARN 계층을 새로 만들지 않는다.
- Windows에서 아직 공식 지원되지 않는 Codex 훅 동작을 보장하지 않는다.

## 요구사항

1. **R1 — 항상-온 크기:** 루트 `AGENTS.md`는 32,000바이트 이하여야 한다. 매 턴 필요한 가드레일·라우팅·완료 게이트·언어·최소주의 규칙은 유지하고, 특정 스킬 발동 때만 필요한 절차와 사례 산문은 포인터 또는 짧은 이유로 압축한다.
2. **R2 — 기계 차단:** integrity-check R14는 32,000바이트까지 통과시키고 32,001바이트부터 실패시킨다. 메시지와 주석은 토큰 예산이 아니라 Codex 기본 32,768바이트 한도 대비 안전 여유를 근거로 든다.
3. **R3 — 설정:** `.codex/config.toml`은 `[features].hooks = true` 정식 키와 인라인 `hooks.<Event>` 정의를 사용하고, 로딩되지 않은 `.codex/hooks.json` 병렬 원본을 두지 않는다. 신뢰된 저장소의 전역 지침 결합 여유를 위해 `project_doc_max_bytes = 65536`을 보조책으로 두되, trust 이전에는 적용되지 않으므로 R1을 1차 방어선으로 유지한다.
4. **R4 — 훅 역할:** SessionStart plain stdout/additional context는 모델 developer context, `systemMessage`는 UI·이벤트 스트림 표면으로 취급한다. 필수 판단 규칙은 `AGENTS.md`, 기계 차단은 PreToolUse·git hook, 주기 작업은 명시 호출에 둔다. 별도 JSON 래퍼나 미문서 출력 형식은 추측해 추가하지 않는다.
5. **R5 — 런타임 프로브:** 최신 설치 CLI에서 다음을 독립적으로 측정한다: prompt-input 파일 끝, custom agent 열거와 실제 spawn, SessionStart 표시, PreToolUse·PostToolUse 입력과 차단 의미. 미지원 기능은 지원으로 문서화하지 않고 명시적 제한으로 남긴다.
6. **R6 — 문서 정합:** ADR·스펙·AGENTS.md·설정 주석의 활성화, 주입, 지원 버전 주장이 R5 결과 및 공식 Codex 계약과 일치해야 한다.
7. **R7 — 회귀 보존:** 기존 회귀와 Codex 입력·R18 계약 테스트를 합친 Python 회귀 200개 및 현재 저장소 무결성 검사가 모두 통과해야 한다.
8. **R8 — 플랫폼 경계:** 이번 변경은 훅 스크립트의 인코딩·인터프리터 체인을 바꾸지 않는다. macOS에서 런타임을 실측하고, Windows 미검증 범위를 문서에 남긴다.

## 인터페이스 / 설계 개요

- `AGENTS.md`는 항상-온 판단 계약만 보유한다. 상세 실행 절차는 기존 스킬·에이전트·ADR·스펙을 단일 원본으로 사용한다.
- `.agents/hooks/integrity-check.py`의 R14가 저장소 내부 정적 방어선이다.
- `.codex/config.toml`은 신뢰된 저장소에서 적용되는 방어적 2차 설정이다.
- `codex debug prompt-input`과 실제 CLI 세션 프로브가 런타임 계약의 증거다.

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1): `wc -c AGENTS.md`가 32,000 이하이고 `codex debug prompt-input` 결과에 파일 마지막 규칙이 존재한다.
- [x] C2 (R2): 32,000바이트 fixture는 R14 PASS, 32,001바이트 fixture는 FAIL이다.
- [x] C3 (R3): TOML 파싱이 성공하고 `codex features list`에서 `hooks`가 활성화되어 있으며 저장소 설정에 `codex_hooks`가 없다.
- [x] C4 (R4·R5): SessionStart·PreToolUse·PostToolUse 프로브가 실제 표시·입력·차단 결과를 남기며, 문서는 관찰 범위를 넘겨 주장하지 않는다.
- [x] C5 (R5): custom agent 7종의 런타임 열거와 1종 실제 spawn 결과를 남긴다. 현재 CLI가 지원하지 않으면 그 제한과 대체 경로를 문서화한다.
- [x] C6 (R6): `rg`로 폐기 키, “클론 즉시 활성”, 미입증 developer-context 주입 주장을 검사했을 때 활성 문서에 모순이 없다.
- [x] C7 (R7): 전체 Python 회귀 200/200과 integrity-check 현재 저장소 실행이 PASS다.
- [x] C8 (R8): macOS 실측 범위와 Windows 미검증 범위가 완료 보고에 구분되어 있다.
- [x] C9 (R1·R6): 독립 reviewer가 AGENTS.md 축소 전후의 필수 규범 보존과 Codex 계약 정합을 PASS한다.

## 미해결 질문

없음. 런타임 지원 여부는 설계 추측이 아니라 R5 프로브 결과로 확정한다.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-25 | 초안 작성 및 구현 기준 확정 | 전체 | Codex 호환성 감사 M1~M4와 후속 교차 검토를 실행 가능한 완료 기준으로 전환 |
| 2026-07-25 | 구현·런타임 실측·독립 재검토 완료(C1~C9) | 전체 | reviewer F1~F3 재작업 후 200/200·무결성 43/43·최종 PASS |
