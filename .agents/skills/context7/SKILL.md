---
name: context7
description: Fetch current, version-specific documentation for libraries, frameworks, SDKs, APIs, and CLI tools via the context7 MCP (resolve-library-id then query-docs) instead of answering library API questions from memory. Use when the user asks how to use, configure, install, migrate, or debug a specific library or framework - React, Next.js, Prisma, Tailwind, Django, Spring Boot, etc. Do NOT use for - Anthropic/Claude/LLM/model-id/pricing questions (→ claude-api built-in skill), reading one specific user-given URL (→ defuddle/WebFetch), or general programming concepts and business-logic debugging. When context7 is unavailable, fall back to WebFetch/WebSearch. Re-run keywords - context7, library docs, framework docs, API reference, 라이브러리 문서, 프레임워크 사용법, 라이브러리 사용법, 문서 조회.
---

# context7 — 라이브러리 최신 문서 조회 (기억 대신 문서)

## 왜 이 스킬인가

라이브러리·프레임워크는 버전마다 API가 바뀐다. 모델이 학습 시점의 기억으로 답하면 **폐기된 시그니처·사라진 옵션·바뀐 설정**을 자신 있게 틀리게 알려준다. `context7` MCP는 라이브러리의 **버전별로 정제·색인된 최신 문서**를 실시간으로 가져와 이 오답을 없앤다.

문제는 능력이 아니라 **발동 타이밍**이다. MCP 도구는 그냥 놓여 있을 뿐이고, 모델이 "지금 이걸 써야지" 하고 스스로 떠올려야 호출된다 — 그래서 유용해도 그냥 기억으로 답해버리면 조용히 안 쓰인다. 이 스킬은 그 활성화 층이다: **"라이브러리 사용법·설정·마이그레이션·라이브러리별 에러를 물으면 기억으로 답하지 말고 context7을 먼저 조회하라"**를 트리거로 못박는다(Claude Code 내장 `claude-api` 스킬이 Anthropic 문서에 대해 하는 것과 같은 패턴).

단, 이것은 **외부 MCP 의존**이다. 없거나 실패하면 **항상 WebFetch/WebSearch로 폴백**한다 — 사용자 질문이 도구 부재로 막혀선 안 된다(defuddle 스킬과 같은 얇은 래퍼 방식).

## 절차

1. **부정 트리거 먼저 확인** (description의 `Do NOT use for`):
   - **Anthropic/Claude/LLM·모델 ID·요금** 질문 → 이 스킬이 아니라 **`claude-api` 스킬(Claude Code 내장)**로 간다(context7은 서드파티 라이브러리용).
   - **사용자가 준 특정 URL 본문 읽기** → **`defuddle`/WebFetch**로 간다(context7은 URL 리더가 아니라 라이브러리 색인이다).
   - **일반 프로그래밍 개념·비즈니스 로직 디버깅** → 도구 없이 직접 판단한다(문서 조회 대상이 아니다).

2. **의존성 확인**: context7 MCP 도구(`mcp__context7__resolve-library-id`)가 이 세션에 있는지 본다.
   - 있으면 → 3번.
   - 없으면 → 사용자에게 한 번 물어 설치를 안내하거나(`claude mcp add context7 --scope user -- npx -y @upstash/context7-mcp`, 전역 등록·반영은 다음 세션부터), 거부·불가하면 **즉시 WebFetch/WebSearch 폴백**한다. **무단 설치하지 않는다**. (상시화하려면 harness-install 3c 절차를 따른다 — 새 설치처에서 자동 안내된다.)

3. **라이브러리 ID 해석**: `mcp__context7__resolve-library-id`로 라이브러리 이름(예: "next.js", "prisma")을 context7 ID로 변환한다. 후보가 여러 개면 사용자가 말한 라이브러리와 **가장 정확히 일치하는 것**(정식 명칭·인지도·버전 일치)을 고른다. 애매하면 사용자에게 어느 것인지 확인한다 — 엉뚱한 라이브러리 문서를 긁는 것이 기억으로 답하는 것보다 나쁘다.

4. **문서 조회**: `mcp__context7__query-docs`에 해석된 ID와 **구체적 주제**(예: "app router middleware", "prisma migrate deploy")를 넘겨 필요한 절만 가져온다. 버전이 중요하면(마이그레이션·특정 버전 질문) 버전을 함께 지정한다.

5. **결과 사용**: 가져온 문서를 근거로 답한다. 코드·시그니처·설정 값은 **원문 그대로** 인용한다(번역하면 재현이 깨진다 — 루트 AGENTS.md §15 가드 2). 문서에 없는 부분을 기억으로 메우지 말고, 없으면 없다고 밝힌 뒤 WebFetch/WebSearch로 보강한다.

## 폴백 규칙 (고정)

이 스킬의 모든 실패 경로는 **WebFetch/WebSearch로 수렴**한다: MCP 미설치·설치 거부·ID 해석 실패·조회 빈 결과·연결 오류. 폴백은 실패가 아니라 정상 경로다 — context7은 문서 조회의 **정확도·토큰 최적화 수단**일 뿐, 문서에 접근하는 유일한 통로가 아니다. WebFetch로 공식 문서 URL을 직접 읽는 것으로 답을 완결한다.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 정확도 | 기억 기반 답 → 폐기된 API·바뀐 설정을 자신 있게 오답 | 버전별 최신 문서 근거로 답 |
| 발동률 | context7 MCP가 떠 있어도 모델이 안 떠올려 조용히 미사용 | 트리거가 "기억 대신 조회"를 명시 → 발동률 상승 |
| 견고성 | (해당 없음) | 미설치·실패 시 WebFetch/WebSearch로 자동 수렴 — 기능이 죽지 않음 |
| 경계 | claude-api·defuddle과 트리거 충돌 | 부정 트리거로 라우팅 확정 |
