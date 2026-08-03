# Document templates (single source per type)

Section structure and order are fixed. Leave inapplicable sections as "해당 없음 — <사유>" (not applicable — reason). **Sole exception: the sections template 3A marks conditional are omitted outright** — that template states the exception and its bounds.

> Templates 1, 3A, 3B, 4, 5 produce **user-facing documents** (root AGENTS.md section 15) — their template text is Korean and the drafted document is written in Korean. Template 2 produces a model-only internal report — written in English.

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
<이번에 의도적으로 하지 않는 것 — 범위 방어선. 이관 대상이면 "(배포처에서 후속 진행)"을 제목에 달고 배포처 후속 항목을 여기에 열거한다>

## 요구사항
<기능·비기능 요구사항. 번호 목록 R1, R2, ... (테스트가 이 번호를 참조한다)>

## 인터페이스 / 설계 개요
<API·데이터 구조·화면 등 바뀌는 경계면. 상세 설계가 아니라 경계만.
**다이어그램 발동 조건 — 임계값을 넘는 것이 하나라도 있으면 Mermaid 다이어그램을 넣는다**(`diagram` 스킬 1절이 정본): ⓐ 행위자 2인 이상 + **메시지 3개 이상**, 그중 하나는 직전 것의 단순 응답이 아님 → `sequenceDiagram` ⓑ **상태 3개 이상** + '다음'이 아닌 전이 하나 이상(되돌아가는 루프, 둘이 도달하는 상태, 이른 종료) → `stateDiagram-v2` ⓒ **결정 2개 이상**, 또는 각 갈래가 2단계 이상 이어지는 결정 하나 → `flowchart` ⓓ **구성요소 4개 이상 + 그들 사이 관계 3개 이상이며 그 관계가 단일 선형 사슬이 아님** → `flowchart`(사슬은 N개면 관계가 항상 N−1개라 개수로는 못 거른다 — `A → B → C → D`는 한 문장이다).
**임계값이 곧 규칙이다** — 행위자·상태·분기·구성요소라는 맨 형태는 어느 기술 문서에나 있어서, 임계값 없는 조건은 전부에 발동하고 소음을 의무화한다(실측: 임계값 없던 초안이 이 저장소의 관할 절 전부에 발동했다).
**어느 것도 못 넘으면 넣지 않는다.** 애매하면 결정 기준은 하나다 — *이 절이 답하려는 질문에 답하려면 읽는 사람이 관계 둘 이상을 동시에 들고 있어야 하는가.* 한 문장으로 손실 없이 다시 쓸 수 있으면 그리지 않는다. **다른 형식으로 이미 그려진 다이어그램(ASCII 등)이 있으면 충족된 것**이며, Mermaid 전환은 그 파일을 다음에 손댈 때 한다>

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

Check: can every completion criterion be turned into a test as-is / is there a non-goals section / are the requirements numbered / **if the 설계 개요 firing condition applies, is the diagram there and does `check.py` pass on it**.

**A completion criterion that mentions documentation must name which document gets what, not just the filename.** `README가 갱신된다` names a file and nothing else, so whoever receives it satisfies it by **copying reference detail into README** — the state 3A forbids ("내용 복사 금지, 링크만"), reached through a criterion that reports as met. Name the layer instead: **reference detail** (config keys, field schemas, metric values, behavioral rules) goes to the reference document under `docs/`, and **README gets a one-line entry plus a link**. When a metric's direction, threshold, or determinism changes, name the metrics reference too.

> **Why the obligation belongs here rather than in 3A**: 3A fires when someone *writes a README*; a spec's completion criteria are written outside it, are more specific, and are what an implementer follows. So a duplication 3A already forbids gets built anyway, by way of the criterion. Measured: on 2026-08-02 the same sentence (`README.md가 갱신된다`) was written into two consecutive specs in one session. The first produced a 459-line README whose seven per-feature sections ran 268 lines — 58% of the file — while `docs/config-reference.md` already carried most of that content (five of the seven; the two uncovered were the diagnosis section, genuinely new, and the undeclared-tool limitations section, where config-reference pointed back at README). The second was caught before it ran.

**Fires when REGISTRY.md has a 「배포처 이관 경계」 section AND the target project's 이관 column reads `배포처`** — the project is built on the shared-core side and transferred to a deployment site for follow-up work. **Read both signals, in that order.** No section means this install site has no deployment-site handoff, so skip silently no matter what the column says (a column value surviving a section's removal is stale, not authoritative). Section present but column `미확인` — ask the user once, write the answer back to the registry row, then proceed on the answer; `로컬` skips. **Exception: a row registered as a category bundle** (see the registry's 등록 규약) may hold `미확인` deliberately because its projects differ; write the answer to the sub-harness's per-project table instead of flattening the bundle row. With both signals positive, the three handover principles recorded in that section are not optional prose — they must be visible in these existing sections. **Add no new sections** (the fixed structure above still governs); place them as follows:

- **비목표** — retitle to `## 비목표 (배포처에서 후속 진행)` and enumerate the deployment-site follow-up items. Naming them in the spec is what keeps unattended sessions (autoloop) from re-deciding the boundary every iteration; boundaries stated only in chat do not survive a context reset.
- **인터페이스 / 설계 개요** — define the cut as an **adapter boundary**: the interface plus a contract test asserting that every implementation returns the same result shape. Exclusion alone forces a redesign at the deployment site, so the seam is the deliverable, not the omission.
- **완료 기준** — two criteria, both **countable**, in the same `"~하면 ~된다"` form the section already requires. Existence-shaped wording (`체크리스트가 있다`) is not usable: an empty heading satisfies it, and an unattended session (autoloop) will write exactly that, since its only mechanical gate is the presence of a 완료 기준 section. Bind them to something with a number instead — ① every item enumerated in 비목표 has a matching entry in **`docs/site-setup.md`의 배포처 설정 체크리스트** (**item counts match**, so the criterion fails while any item is missing) ② running each deployment-site follow-up path prints the "미구현, 배포처 후속" notice and exits non-zero (**one case per path**) rather than silently no-op. Both counts derive from the 비목표 enumeration, so an empty enumeration makes them vacuous — that state means the 이관 classification is wrong, not that the criteria are met: a project with no deployment-site follow-up item is `로컬`, so fix the registry row rather than shipping two criteria that count to zero.

  **Why the path is fixed at `docs/site-setup.md`**: criterion ① only works if the thing being counted has a known location. Let each project choose, and every spec must carry the path — and the ones that omit it leave the criterion silently unresolvable. **Why not README** is in 3A's corresponding note: that section is maintained at the deployment site, so keeping it in README splits one file's ownership across two machines.

  **The spec must also say the document gets created, and keep the heading fixed.** `docs/site-setup.md` is not produced by any other template, so a spec that only counts against it counts against a file nobody was told to write. State its creation as a **requirement** (an R-number in 요구사항) — **never as a 비목표 item**: 비목표 holds what is deliberately *not* done here, creating the document is done here, and criterion ① counts 비목표 items against the checklist, so an entry there would offset the count by one against the very file it lists. Keep the heading exactly `## 배포처 설정 체크리스트` — criterion ① locates the list by that heading, so a rename breaks the count the same way a missing file does.

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

## 3. README — two templates, one fork

**Which one fires: is there a `.git` directory beside this README?** Beside it → **3A** (the repository's first screen, read by someone deciding whether to use the thing). Not beside it → **3B** (a directory or module README, read by someone already inside the repository). One mechanical test, because the two templates differ in what they are for, not in size — a directory README with a badge row is as wrong as a repository root with no way to run it.

**Language: Korean, both templates** (root AGENTS.md section 15 — user-read). Popular repositories write English READMEs and only their **structure** is ported here; no English variant is produced. Reason: a second-language README is a synchronization obligation of the kind section 15's Korean-view rule already pays for on the harness assets, and it would be paid on every project.

**These templates apply to READMEs written or revised from now on.** Existing READMEs are not retrofitted — the unit of judgment is the writing act, not the file (same rule as REGISTRY.md's outbound-caution scope).

### 3A. Repository-root README

```markdown
# <이름>

> <한 줄 태그라인 — 이 저장소가 무엇을 해주는가. 명사 나열이 아니라 동사로 끝낸다>

<뱃지 줄 — 조건부, 아래 「뱃지 규칙」>

## 이게 뭔가

<2~4문장. 어떤 문제를, 누구를 위해, 어떻게 푸는가. 여기까지 읽고 "나에게 필요한가"가 판단돼야 한다 — 판단이 안 되면 아래를 아무리 잘 써도 읽히지 않는다>

## 데모

<조건부. 저장소에 실제로 있는 이미지·GIF·asciinema만>

## 시작하기

<복사해서 그대로 도는 최소 명령. 설치 → 실행 → 첫 결과가 3단계 이내.
전제(런타임 버전·필요 권한)는 블록 위 한 줄로>

## 사용법

<대표 시나리오 2~3개. 각각 명령·코드 + **실행해서 얻은 실제 출력**. 지어낸 출력 금지(13절 2항 무증거 선언 금지가 문서에도 적용된다)>

## 설정 레퍼런스

<조건부. 옵션 표: 키 | 기본값 | 설명>

## 동작 방식

<핵심 흐름 번호 목록. 내부 구현이 아니라 "입력이 어떤 경로로 결과가 되는가". 구현 상세는 링크로>

## FAQ · 트러블슈팅

<조건부. 실제로 받은 질문·실제로 밟은 오류만>

## 로드맵

<조건부. 스펙·이슈로 존재하는 것만>

## 기여

<조건부>

## 라이선스

<조건부. LICENSE 파일이 있을 때만>

## 참고

<조건부. 더 깊은 문서로의 링크 — 스펙·런북·ADR·`docs/site-setup.md`. 내용 복사 금지, 링크만>
```

**Mandatory sections** (always present): 제목·태그라인, 이게 뭔가, 시작하기, 사용법, 동작 방식.

**Conditional sections** — include when the condition holds, **omit the heading entirely otherwise**. Each condition is a fact about the repository, checkable without judgment:

| 섹션 | 넣는 조건 | 생략 이유 |
|---|---|---|
| 뱃지 줄 | 아래 뱃지 규칙을 통과하는 뱃지가 1개 이상 | 근거 없는 뱃지는 상태를 주장하는 거짓말이다 |
| 데모 | 실행 결과를 담은 이미지·GIF·asciinema 파일이 저장소에 있다 | 플레이스홀더는 "곧 나온다"가 아니라 "관리되지 않는다"로 읽힌다 |
| 설정 레퍼런스 | 사용자가 바꿀 수 있는 설정 키가 1개 이상 | 설정이 없는데 빈 표를 두면 있는 줄 알고 찾는다 |
| FAQ · 트러블슈팅 | 실제로 받은 질문 또는 실제로 밟은 오류가 1건 이상 | 예상 질문은 저자의 상상이라 아무도 안 겪는다 |
| 로드맵 | 다음 작업이 스펙 또는 이슈로 존재한다 | 구두 아이디어를 적으면 약속으로 읽히고 지켜지지 않는다 |
| 기여 | 본인 외 기여자를 받을 저장소다 | 받을 생각이 없는 절차는 유지되지 않는다 |
| 라이선스 | LICENSE 파일이 저장소에 있다 | 파일 없이 섹션만 두면 미정 상태가 정해진 것처럼 보인다 |
| 참고 | 링크할 더 깊은 문서(스펙·런북·ADR·`docs/site-setup.md`)가 있다 | 링크 없는 링크 섹션 |

**These are the only sections exempt from the "해당 없음 + 사유" rule** (SKILL.md procedure step 3). Mandatory sections are not exempt — an inapplicable mandatory section means 3A is the wrong template, not that the section may be dropped.

**배포처 설정 체크리스트는 README에 두지 않는다 — `docs/site-setup.md`가 그 자리다** (스펙 템플릿 1번의 배포처 이관 절이 정본). 이 절은 배포처 세션이 유지하는 내용이라 README에 두면 **한 파일의 일부는 공용이, 일부는 배포처가 소유**하게 되고, 그 상태가 바로 소유권 경계 문서가 막으려는 충돌 표면이다. 파일을 나누면 그 분할 자체가 사라진다. 같은 이유로 배포처 CI 연동·배포처 후속 비목표 서술도 그 문서로 간다. README에는 `## 참고`의 링크 한 줄만 남긴다. **이미 README에 둔 프로젝트를 찾아다니며 고치지 않는다** — 위의 "지금부터 쓰거나 개정하는 README에 적용" 원칙이 그대로 적용된다(판단 단위는 파일의 나이가 아니라 작성 행위).

**뱃지 규칙** (max 4, one line):

- **저장소에 근거 파일이 실제로 있는 뱃지만 단다** — CI 뱃지는 워크플로 파일이 있을 때, 라이선스 뱃지는 LICENSE가 있을 때, 패키지 뱃지는 실제로 배포된 레지스트리 항목이 있을 때, 커버리지 뱃지는 커버리지를 리포트하는 파이프라인이 있을 때. 근거를 확인한 다음 단다.
- **정적 값으로 상태를 흉내내지 않는다** — 하드코딩한 `build: passing` 류는 검증 없이 통과를 선언하는 것이라 root AGENTS.md 13절 2항 위반과 같은 종류다. 상태 뱃지는 상태를 읽어오는 것만 쓴다.
- **뱃지 URL도 저장소 밖으로 나가는 텍스트다** — 외부 뱃지 서비스는 저장소·조직 이름을 URL에 담고 이미지 요청으로 그 이름을 밖에 보낸다. 이관 `배포처` 프로젝트에서는 회사 식별값(조직명·내부 호스트·배포처 앱 이름)이 뱃지 URL에 들어가지 않아야 한다(root AGENTS.md 3절, REGISTRY.md 반출 주의).

Check: 태그라인만 읽고 무엇을 하는 저장소인지 아는가 / 시작하기 블록을 그대로 복사해 돌릴 수 있는가 / 사용법 출력이 실행 결과인가(지어낸 것이 아닌가) / 조건부 섹션 중 조건을 못 채운 채 남은 것이 없는가 / 뱃지가 전부 근거 파일을 가지는가 / 다른 문서 내용을 복사하지 않고 링크했는가.

### 3B. Directory / internal README

```markdown
# <이름>

<한 문단: 이 디렉토리가 무엇이고, 누가 언제 여는가>

## 구조
<디렉토리 트리 — 항목마다 한 줄 설명. 파일 나열이 아니라 "무엇이 어디 있는가">

## 동작 방식
<핵심 흐름 번호 목록>

## 참고
<더 깊은 문서로의 링크 — 내용 복사 금지, 링크만>
```

All four are mandatory; 3B has no conditional sections, so the "해당 없음 + 사유" rule applies here unchanged.

Check: 첫 문단만 읽고 이 디렉토리를 열 이유를 아는가 / 트리 항목마다 설명이 붙었는가 / 다른 문서 내용을 복사하지 않았는가 / 뱃지·데모·로드맵·기여·라이선스 같은 3A 전용 섹션이 섞이지 않았는가.

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
<번호 목록 = diff 읽기 가이드(§13-0 사용자 성장): 파일 나열이 아니라 변경 단위를 **읽어야 할 순서로** 나열하고, 각 항목에 **왜 이 부분이 중요한지 한 줄**을 붙인다 — 사용자가 순서대로 읽고 이해하도록.
**다이어그램 발동 조건과 임계값은 스펙 템플릿과 같다**(`diagram` 스킬 1절 정본) — 이 변경이 순서·상태·분기·구조 중 하나를 **임계값을 넘겨** 바꿨으면 Mermaid로 그린다. **PR 본문은 저장소 상대 경로 이미지를 못 걸므로** 15노드를 넘으면 SVG로 escalate하지 말고 **다이어그램을 쪼갠다**>

## 연결
- 스펙: <`docs/specs/...` 경로. 없으면 "해당 없음 — <사유: 사소한 수정 등>">
- 이슈: <`Closes #N` (work-tracker 등록 작업). 없으면 "해당 없음">

## 검증
<실행한 명령과 실제 결과 — 예: `npm test` 34/34 통과. "테스트 통과" 같은 무증거 선언 금지>
- 독립 검증: <reviewer 라운드 수와 판정(PASS/BLOCK·반영 내용). **`사내` 프로필이라 발행이 면제됐으면 「독립 검증 없음 — 사내 프로필 면제(ADR 038)」라고 적고, 그 자리를 무엇으로 메웠는지**(직접 재실행한 명령·확인 범위)를 잇는다. **이 줄은 비워 두거나 생략할 수 없다** — 면제와 조용한 생략이 사후에 구분되지 않으면 면제 조항 자체가 무의미해진다. **프로필과 무관하게 요구한다**: `개인`에서는 이미 일어난 일을 적는 것뿐이고, 면제 쪽만 이 줄을 지면 "줄이 없다 = 면제다"가 되어 조용한 생략과 다시 구분되지 않는다>

## 리뷰 포인트
<판단이 필요한 지점·자율 결정·트레이드오프. 각 항목은 **결과만("X로 함")이 아니라 결정 공간을 가르친다**: 무엇 대 무엇의 갈림길이었고, 이 맥락에서 이 선택인 이유(§13-0 사용자 성장 — 자명한 결정은 생략). 없으면 "없음">
```

Check: does 변경 내용 read as an ordered reading-guide with a "why it matters" line per item / does 리뷰 포인트 teach the decision space (fork + reason) not just the outcome / does the verification section contain actual commands and numbers / are spec/issue links stated (with a reason if absent) / can the PR's purpose be understood from the summary alone.
