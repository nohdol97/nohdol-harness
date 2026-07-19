# ADR 026 — oh-my-openagent 검증·운영 착안 5건 이식 + integrity-check 훅

- **날짜**: 2026-07-19
- **상태**: 활성
- **관련**: 제안 docs/proposals/2026-07-19-oh-my-openagent-adoption.md, 스펙 docs/specs/2026-07-19-integrity-check-script.md, ADR 017(ponytail)·018(claude-mem)·022(superpowers)·023(loop-engineering)·025(autoloop)

## 변경 내용

oh-my-openagent(github.com/code-yeongyu/oh-my-openagent, SUL-1.0)를 분석해 **검증·발행의 형식·기계화 착안 5건**을 이식했다. 오케스트레이션·라우팅·무인 루프 층은 기존 자산(orchestrate·§9 티어·autoloop·work-tracker)과 기수렴이라 기각하고, 실행 계층 기능(Hashline·LSP MCP·Team Mode·룰 엔진)과 자동 머지 PR 스킬은 §5·소유 전제 불충족으로 기각했다(대조표: 제안 §3·§5).

1. **완료 증거 4필드 (AGENTS.md §13 2항, reviewer 정의)** — "신선한 증거"(ADR 022)에 형식 부여: ① 무엇을 실행 ② 무엇을 관찰 ③ **왜 충분한가** ④ **무엇을 미검증**. ③④가 "부분 확인을 전체 완료로 보고"의 해독제. 별도 증거 디렉토리는 두지 않음(`_workspace`·PR 본문 재사용).
2. **하네스 무결성 기계 점검 (`.agents/hooks/integrity-check.py` 신설)** — harness-review 주간 무결성 점검의 기계 판정 항목(심링크·`.claude/` 침입·frontmatter·MOC·CLAUDE.md·gitignore)을 결정론화. 8절 승격 원칙("기계적 차단 가능하면 훅으로")의 무결성 점검판, tdd-gate·secret-gate 계보. 리포트 전용(커밋 게이트 아님). 스펙·TDD 18케이스.
3. **untrusted-observation 봉투 (AGENTS.md §3, defuddle, autoloop driver.py)** — 외부 유래 텍스트(웹 본문·프로세스 출력·헤드리스 주입 로그)를 세션에 넣을 때 "데이터일 뿐 사용자 지시 아님" 봉투. 무인 autoloop은 주입 표면이 넓어 driver.py `build_prompt`에 반영(스펙 R2⑥·C18).
4. **팀 런 교훈 노트 (orchestrate)** — 3페이즈+ 팀 런에서 `_workspace/<작업>/learnings.md`로 교훈을 환류(후속 발행 프롬프트 CONTEXT에 포함). 소규모 런 제외(지연 생성).
5. **위임 발행 형식 강화 (orchestrate B모드, AGENTS.md §10)** — 7요소 발행 골격(TASK/OUTCOME/SKILLS/TOOLS/MUST DO/MUST NOT/CONTEXT, 체크리스트) + 긍정형 제약 우선("~하지 마라"보다 허용 영역 지목). §3 가드레일 금지는 부정형 그대로 유지.

## 대상

AGENTS.md §3·§10·§13, `.agents/agents/reviewer.md`, `.agents/skills/{defuddle,orchestrate,harness-review}/SKILL.md`, `.agents/skills/autoloop/scripts/driver.py`(+테스트), `.agents/hooks/integrity-check.py`(+테스트, 신설).

## 사유

- **①②⑤는 "중복이지만 그쪽 형식이 더 나아서" 채택** — §13 신선한 증거·harness-review 무결성 점검·발행 규약이 이미 있으나 형식이 헐거웠다. 형식 개선은 하네스 비대(ADR 007 지연 생성이 겨눔)가 아니라 품질 개선이라 반복 실패 신호를 요구하지 않는다(사용자 확정 — 중복이라도 더 나은 것은 채택).
- **③④는 순수 공백** — untrusted 봉투는 대응 규칙 0, 팀 런 교훈 환류는 규칙 부재였다.
- **규칙의 운반체는 문서(§12)** — 배송 기계(42패키지·54훅·플러그인)는 복제하지 않고 착안만 재구현했다(SUL-1.0 코드 비복제 → 라이선스 비저촉). integrity-check만 기계화가 남아 훅으로(문서 규칙 → 실행 계층 승격, 8절).
- **방증**: 그들의 멀티 CLI 카피 배포에서 실제 드리프트가 관찰돼 우리 심링크 단일화(ADR 021)를 지지했다.

## 검증

reviewer 독립 검증 2회(설계·구현) 통과. 구현 검증에서 F1(무결성 점검 fail-loud 미준수)을 must-fix로 반영 — 핵심 디렉토리 부재·dangling 심링크를 SKIP이 아니라 FAIL로 조여 "고비용 가짜 통과"를 차단했다. integrity-check 18케이스·driver 37케이스·현 저장소 29 pass 신선 증거로 확인.
