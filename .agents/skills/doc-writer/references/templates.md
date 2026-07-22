# Document templates (single source per type)

Section structure and order are fixed. Leave inapplicable sections as "해당 없음 — <사유>" (not applicable — reason).

> Templates 1, 3, 4, 5 produce **user-facing documents** (root AGENTS.md section 15) — their template text is Korean and the drafted document is written in Korean. Template 2 produces a model-only internal report — written in English.

## 1. Spec (SDD — root AGENTS.md section 13)

Filename: `docs/specs/YYYY-MM-DD-<제목>.md`

```markdown
# 스펙: <제목>

- 날짜: YYYY-MM-DD / 상태: 초안 | 확정 | 구현됨 | 폐기
- 관련: <이슈·PR·선행 스펙 링크>

## 배경
<왜 이 작업이 필요한가 — 현재 문제·요청 맥락>

## 목표
<이 작업이 끝나면 참이 되는 문장들. 측정 가능하게>

## 비목표
<이번에 의도적으로 하지 않는 것 — 범위 방어선>

## 요구사항
<기능·비기능 요구사항. 번호 목록 R1, R2, ... (테스트가 이 번호를 참조한다)>

## 인터페이스 / 설계 개요
<API·데이터 구조·화면 등 바뀌는 경계면. 상세 설계가 아니라 경계만>

## 완료 기준 (테스트 가능한 형태)
<체크리스트. 각 항목이 곧 테스트 케이스가 된다 — "~하면 ~된다" 형식, 요구사항 번호 참조>
- [ ] C1 (R1): ...
- [ ] C2 (R2): ...

## 미해결 질문
<확정 전 답이 필요한 것들. 없으면 "없음">

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
```

Check: can every completion criterion be turned into a test as-is / is there a non-goals section / are the requirements numbered.

**For specs of root hooks (`.agents/hooks/` session hooks, `.agents/githooks/` git hooks), the completion criteria must include a cross-platform checklist** — the 2026-07-14 Windows failure turned into chains of per-commit fixes (two 3-fix chains) because there was no pre-verification procedure (spec 2026-07-15-hooks-common-bootstrap): ① **Encoding** — the case where output/blocking messages actually get through on a cp949 (Korean Windows) console (common source: `_common.utf8_stdio`) ② **Interpreter** — whether the registered command (the shell chain in settings) fails open when the interpreter is absent or is a Windows Store stub (exists but fails to execute) ③ **External-CLI output judgment** — phrase-based judgment must be tested with **fixtures of actually observed phrases** (both affirmative and negative sentences) (fabricated fixtures let negative-sentence misjudgments like "no ... running" pass).

## 2. Work report (_workspace deliverable)

Filename: `_workspace/<작업명>/phase{N}_{에이전트명}_{내용}.md`

> **Written in English** (root AGENTS.md section 15 — model-only internal deliverable; code/log quotes stay in the original language). Section structure as below (Summary / Findings / Judgement·Recommendations / Limits). **Exception**: integrator final reports, deployment runbooks, and harness-review proposals are read directly by the user, so they are in Korean.

```markdown
# <work-name> — <content> (phase{N}, {agent-name})

- Date: YYYY-MM-DD / Input: <files read, instructions> / Scope: <what was and was not covered>

## Summary
<3 lines max — core findings and conclusions>

## Findings
<Descending severity. Each item: severity (Critical/High/Med/Low) / location (file:line) / claim / evidence>

## Judgement · Recommendations
<Actions derived from the findings. No recommendation without evidence>

## Limits
<What could not be verified — where the next person picks up>
```

Check: does every finding have evidence / is the Limits section honest.

## 3. README

```markdown
# <이름>

<한 문단: 무엇이고, 누구를 위한 것인가>

## 구조 | 시작하기
<디렉토리 트리 또는 설치·실행 최소 명령>

## 동작 방식
<핵심 흐름 번호 목록>

## 규칙 상세 | 참고
<더 깊은 문서로의 링크 — 내용 복사 금지, 링크만>
```

Check: can the purpose be understood from the first paragraph alone / was no other document's content copied.

## 4. Runbook (operational procedure)

Filename: `docs/runbooks/<절차명>.md`

```markdown
# 런북: <절차명>

- 목적: <언제 이 절차를 실행하는가> / 소요: <예상 시간> / 위험도: <가드레일 해당 여부 — 루트 AGENTS.md 3절>

## 사전 조건
<권한·도구·상태 확인. 확인 명령 포함>

## 절차
<번호 목록. 각 단계: 실행할 명령(백틱) + 기대 결과. 파괴적 단계는 ⚠️ 표시 + 사용자 확인 명시>

## 검증
<끝난 뒤 정상 확인 방법>

## 롤백
<실패 시 되돌리는 절차. 불가하면 "롤백 불가 — <대안>">

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
```

Check: does every step have an expected result / do destructive steps carry ⚠️ and a confirmation procedure / is there a rollback section.

## 5. PR body (used in the branch-workflow finish procedure)

Title: commit-convention format `type(프로젝트스코프): 요약` (root AGENTS.md section 5)

```markdown
## 요약
<이 PR이 무엇을 왜 바꾸는가 — 3줄 이내. 리뷰어가 이것만 읽고 diff를 열 수 있게>

## 변경 내용
<번호 목록 — 리뷰어가 diff를 읽는 순서 가이드. 파일 나열이 아니라 변경 단위>

## 연결
- 스펙: <`docs/specs/...` 경로. 없으면 "해당 없음 — <사유: 사소한 수정 등>">
- 이슈: <`Closes #N` (work-tracker 등록 작업). 없으면 "해당 없음">

## 검증
<실행한 명령과 실제 결과 — 예: `npm test` 34/34 통과. "테스트 통과" 같은 무증거 선언 금지>

## 리뷰 포인트
<판단이 필요한 지점, 자신 없는 부분, 트레이드오프 — 없으면 "없음">
```

Check: does the verification section contain actual commands and numbers / are spec/issue links stated (with a reason if absent) / can the PR's purpose be understood from the summary alone.
