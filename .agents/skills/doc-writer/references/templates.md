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
<이번에 의도적으로 하지 않는 것 — 범위 방어선. 반입 대상이면 "(사내에서 후속 진행)"을 제목에 달고 사내 후속 항목을 여기에 열거한다>

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

**Fires when REGISTRY.md has a 「사내 반입 경계」 section AND the target project's 반입 column reads `사내`** — the project is built here and carried into a corporate environment for follow-up work. **Read both signals, in that order.** No section means this install site has no corporate carry-in, so skip silently no matter what the column says (a column value surviving a section's removal is stale, not authoritative). Section present but column `미확인` — ask the user once, write the answer back to the registry row, then proceed on the answer; `로컬` skips. **Exception: a row registered as a category bundle** (see the registry's 등록 규약) may hold `미확인` deliberately because its projects differ; write the answer to the sub-harness's per-project table instead of flattening the bundle row. With both signals positive, the three handover principles recorded in that section are not optional prose — they must be visible in these existing sections. **Add no new sections** (the fixed structure above still governs); place them as follows:

- **비목표** — retitle to `## 비목표 (사내에서 후속 진행)` and enumerate the corporate follow-up items. Naming them in the spec is what keeps unattended sessions (autoloop) from re-deciding the boundary every iteration; boundaries stated only in chat do not survive a context reset.
- **인터페이스 / 설계 개요** — define the cut as an **adapter boundary**: the interface plus a contract test asserting that every implementation returns the same result shape. Exclusion alone forces a redesign on the corporate side, so the seam is the deliverable, not the omission.
- **완료 기준** — two criteria, both **countable**, in the same `"~하면 ~된다"` form the section already requires. Existence-shaped wording (`체크리스트가 README에 있다`) is not usable: an empty heading satisfies it, and an unattended session (autoloop) will write exactly that, since its only mechanical gate is the presence of a 완료 기준 section. Bind them to something with a number instead — ① every item enumerated in 비목표 has a matching entry in the README carry-in checklist (**item counts match**, so the criterion fails while any item is missing) ② running each corporate follow-up path prints the "미구현, 사내 후속" notice and exits non-zero (**one case per path**) rather than silently no-op. Both counts derive from the 비목표 enumeration, so an empty enumeration makes them vacuous — that state means the 반입 classification is wrong, not that the criteria are met: a project with no corporate follow-up item is `로컬`, so fix the registry row rather than shipping two criteria that count to zero.

Keep company-identifying values out of the spec text: hostnames, internal URLs, cluster or namespace names, internal app names, org or team names, account IDs. Public product and technology names (k8s, ArgoCD, OIDC) are **not** restricted — the axis cannot be stated without them, and a name every company uses identifies none. The test is one sentence: *does this string point at our company's instance of the thing?* The spec is committed and leaves the repository (root AGENTS.md §3).

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
<번호 목록 = diff 읽기 가이드(§13-0 사용자 성장): 파일 나열이 아니라 변경 단위를 **읽어야 할 순서로** 나열하고, 각 항목에 **왜 이 부분이 중요한지 한 줄**을 붙인다 — 사용자가 순서대로 읽고 이해하도록>

## 연결
- 스펙: <`docs/specs/...` 경로. 없으면 "해당 없음 — <사유: 사소한 수정 등>">
- 이슈: <`Closes #N` (work-tracker 등록 작업). 없으면 "해당 없음">

## 검증
<실행한 명령과 실제 결과 — 예: `npm test` 34/34 통과. "테스트 통과" 같은 무증거 선언 금지>

## 리뷰 포인트
<판단이 필요한 지점·자율 결정·트레이드오프. 각 항목은 **결과만("X로 함")이 아니라 결정 공간을 가르친다**: 무엇 대 무엇의 갈림길이었고, 이 맥락에서 이 선택인 이유(§13-0 사용자 성장 — 자명한 결정은 생략). 없으면 "없음">
```

Check: does 변경 내용 read as an ordered reading-guide with a "why it matters" line per item / does 리뷰 포인트 teach the decision space (fork + reason) not just the outcome / does the verification section contain actual commands and numbers / are spec/issue links stated (with a reason if absent) / can the PR's purpose be understood from the summary alone.
