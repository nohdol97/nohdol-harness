---
name: doc-writer
description: Write project documents in one consistent format - specs, work reports, READMEs, runbooks, PR bodies. Picks the matching template from references/templates.md, drafts in Korean (internal _workspace team reports in English per root AGENTS.md section 15), then self-checks against the template checklist. Use when the user says 문서 작성, 문서 만들어줘, 스펙 써줘, 리포트 정리, README 써줘, PR 본문 써줘, when creating a PR (branch-workflow finish), or when section 13 (SDD) requires a spec before coding. Do NOT use for ADR or change-history-table entries - those follow root AGENTS.md section 6 directly, not this template. Re-run keywords - doc, doc-writer, document, spec, PR, 문서, 문서 작성, 스펙, PR 본문.
---

# doc-writer — 일관 형식 문서 작성

## 왜 이 스킬인가

문서마다 형식이 다르면 읽는 비용이 매번 새로 든다 — 어디에 완료 기준이 있는지, 어디에 결정 사유가 있는지 문서마다 다시 찾아야 하고, 결국 아무도 안 읽게 된다. 이 스킬의 목표는 **같은 종류의 문서는 언제나 같은 형식으로 나오게** 하는 것이다. 형식이 고정되면 사람도 에이전트도 원하는 절을 바로 찾고, 문서 간 비교·검색·재사용이 가능해진다.

## 절차

1. **타입 판별**: 요청을 아래 표에 매핑한다. 애매하면 사용자에게 목적(누가, 언제 읽는 문서인가)을 묻는다.
2. **템플릿 로드**: `references/templates.md`에서 해당 타입 섹션만 읽는다.
3. **초안 작성**: 템플릿의 절 구조·순서를 그대로 따른다. 절을 임의로 추가·삭제·재배열하지 않는다 — 해당 없는 절은 지우지 말고 "해당 없음"과 사유 한 줄을 남긴다(다음 독자가 누락인지 판단하지 않아도 되게).
4. **자체 검증**: 템플릿 하단 체크리스트로 확인 후 완료 선언.

## 타입 → 템플릿 매핑

| 타입 | 언제 | 위치 |
|---|---|---|
| **스펙** | 기능 추가·동작 변경 전 (루트 AGENTS.md 13절 SDD 필수) | 해당 프로젝트 저장소 `docs/specs/YYYY-MM-DD-<제목>.md` |
| **작업 리포트** | 팀·페이즈 산출물 | `_workspace/<작업명>/phase{N}_{에이전트명}_{내용}.md` |
| **README** | 프로젝트·디렉토리 소개 | 대상 디렉토리 루트 |
| **런북(운영 절차서)** | 반복 운영 절차(배포·복구·점검) | 해당 프로젝트 저장소 `docs/runbooks/` |
| **PR 본문** | PR 생성 시 (branch-workflow 마무리 절차 4단계) | `gh pr create --body` 입력 |

ADR·변경 이력 테이블은 이 스킬 대상이 아니다 — 형식의 단일 원본이 루트 AGENTS.md 6절에 있다(두 곳에 두면 어긋난다).

## 공통 문체 규칙 (모든 타입)

- 한국어, 평서문. 한 문장에 한 주장. **예외**: `_workspace/` 팀 중간 리포트(작업 리포트 템플릿)는 영어로 쓴다(루트 AGENTS.md 15절 — 모델만 읽는 내부 산출물, 절 구조는 동일). 사용자가 직접 읽는 문서(스펙·런북·README·PR 본문·integrator 최종 리포트·제안서)는 한국어 그대로다.
- **Why-First**: 규칙·결정에는 이유를 붙인다.
- 제목만 있고 내용 없는 절 금지. 추측은 "미확인"으로 정직하게 표기.
- 코드·명령·경로는 백틱. 날짜는 YYYY-MM-DD.
- 하단에 변경 이력 테이블(날짜/변경 내용/대상/사유) — 살아있는 문서(스펙·런북·README)만. 일회성 리포트는 제외.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 형식 일관성 | 문서마다 다른 구조, 매번 새로 읽는 법 학습 | 같은 타입 = 같은 절 구조 |
| SDD 연결 | 스펙 형식이 매번 달라 완료 기준 누락 | 완료 기준 절이 항상 같은 자리에 |
| 누락 감지 | 빈 절인지 해당 없음인지 구분 불가 | "해당 없음"+사유 명시 규칙 |
