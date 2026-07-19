---
name: carryover
description: "Save selected work from the current session to a local _workspace carryover note (Markdown) so a later same-machine session can resume it, and load an existing note to continue. Slash-invoked only (/carryover) — the user manually triggers save or resume; this skill is intentionally NOT part of harness auto-routing. Save mode: enumerate this session's work (changed files, decisions, done/open items, blockers), let the user pick which to keep, write a resume-ready template to _workspace/carryover/YYYY-MM-DD-<topic>.md. Resume mode: scan _workspace/carryover/, list notes, load the chosen one and continue. Do NOT use for cross-session/cross-machine epics or multi-PR work tracked in git (→ work-tracker: GitHub Issues/backlog.md) — carryover is local, gitignored, lightweight, same-machine only. Re-run keywords - carryover, 이월 노트, 세션 이월, 카리오버, 이어받기."
---

# carryover — 세션 이월 노트

## 왜 이 스킬인가

세션 컨텍스트와 `_workspace/`는 세션을 넘겨 자동으로 이어지지 않는다. 그런데 GitHub 이슈를 열 정도는 아닌 "이번 세션에서 한 것 중 다음에 이어받고 싶은 몇 가지"가 매번 사라진다. 이 스킬은 그 간극만 메운다 — 사용자가 **남길 작업을 직접 골라** 로컬 `_workspace/carryover/`에 재개 가능한 형식으로 적고, 다음 세션이 그 노트를 골라 이어받게 한다.

**work-tracker와의 경계 (중요 — 대체 아니라 공존)**:

| | work-tracker | **carryover (이 스킬)** |
|---|---|---|
| 저장처 | GitHub Issues / `docs/backlog.md` (git 추적, 크로스 머신) | `_workspace/carryover/*.md` (gitignore, **같은 머신 로컬**) |
| 대상 | 여러 PR·며칠 규모 에픽, 정형 | 이번 세션→다음 세션 **가벼운 핸드오프 메모** |
| 호출 | 자동 라우팅 + 슬래시 | **슬래시 전용**, 자동 라우팅 없음 |

→ 정식 추적이 필요하면 work-tracker로 보낸다. carryover는 로컬 스크래치 핸드오프다. 이유: 이 둘을 섞으면 이슈 무덤이 생기거나(모든 걸 GitHub에), 중요한 크로스 머신 작업이 로컬에만 남아 유실된다.

**이 스킬은 슬래시(`/carryover`)로만 호출된다** — 하네스 라우팅(CLAUDE.md 앵커·§7)에 등록하지 않는다. 이유: 사용자가 "지금 남기겠다/이어받겠다"고 명시적으로 결정하는 순간에만 동작해야 하는 도구이기 때문이다.

## 모드 분기 (첫 판단)

호출 인자로 모드를 정한다.

- 인자에 **재개 신호**(`재개`·`resume`·`이어서`·`이어받`·`불러와`·`load`)가 있으면 → **재개 모드**.
- 그 외(인자 없음 포함) → **저장 모드**. 단, 저장 모드 진입 시 `_workspace/carryover/`에 기존 노트가 있으면 "기존 이월 노트 N개가 있습니다(재개하려면 `/carryover 재개`)"를 한 줄로 알린다.

## 저장 모드

이번 세션에서 한 작업 중 사용자가 고른 것만 로컬 노트로 남긴다.

1. **후보 수집**: 이번 세션의 작업을 후보 항목으로 열거한다.
   - `git status --short`와 `git diff --stat`으로 변경·미커밋 파일을 확인한다(대상 저장소가 하위 프로젝트면 그 저장소에서).
   - 대화에서 내린 **결정**, **완료한 것**, **진행 중·다음 할 일**, **막힌 점**을 뽑는다.
   - 각 후보는 한 줄 요지로 표현한다(예: `sona_app 로그인 리팩토링 — AuthProvider 분리 완료, 테스트 미작성`).
   - **남길 만한 작업이 하나도 없으면**(변경·결정·미완 항목 없음) 저장하지 않고 "이월할 작업이 없습니다"를 알리고 종료한다 — 빈 노트는 부채다.

2. **사용자 선택** (핵심 — 반드시 사용자가 고른다):
   - 후보가 **4개 이하**면 `AskUserQuestion`(multiSelect: true)로 제시해 고르게 한다.
   - 후보가 **5개 이상**이면 번호 매긴 목록을 채팅에 제시하고, 사용자가 남길 번호(또는 "전부")로 답하게 한다 — AskUserQuestion은 옵션 4개가 상한이라 목록이 길면 이 방식이 정확하다.
   - 아무것도 선택하지 않으면 저장하지 않고 종료한다(빈 노트는 부채다).

3. **주제 확정**: 선택된 항목들의 공통 주제로 짧은 슬러그를 만든다(사용자에게 한 번 확인하거나 자명하면 그대로). 여러 무관한 주제가 섞였으면 주제별로 파일을 나눌지 사용자에게 묻는다.

4. **파일 작성**: `_workspace/carryover/YYYY-MM-DD-<주제슬러그>.md`에 아래 템플릿으로 쓴다. 날짜는 `date +%F`로 얻는다(추정 금지). `_workspace/carryover/`가 없으면 만든다.
   - 같은 날 같은 주제 파일이 이미 있으면 덮어쓰지 말고 세션 구분 섹션을 append하거나 슬러그에 `-2`를 붙인다(기존 이월 내용 유실 방지).

5. **보고**: 작성한 파일 경로를 사용자에게 알리고, "다음 세션에서 `/carryover 재개`로 이어받을 수 있다"를 한 줄 덧붙인다.

### 노트 템플릿 (재개를 위한 골격)

```markdown
# Carryover: <제목>

- 날짜: YYYY-MM-DD
- 대상 프로젝트/저장소: <이름 또는 경로>
- 한 줄 요약: <이 노트가 무엇에 관한 것인지 — 재개 모드 목록에 이 줄이 뜬다>

## 한 일 (완료)
- …

## 진행 중 · 다음 할 일
- …

## 막힌 점 · 미해결
- …

## 참조 (파일:줄, 명령, 경로, 이슈/PR)
- `path/to/file.ts:120` — …
- 실행 명령: `…`

## 재개 방법
- 어디서부터 어떻게 이어가는지. 재진입할 스킬을 명시한다
  (구현 이어가기면 orchestrate 게이트 재진입, 리뷰면 team-review 등).
```

**"한 줄 요약"은 반드시 채운다** — 재개 모드의 목록이 이 줄로 노트를 구분한다(스킬 description 트리거와 같은 원리로, 목록 품질이 이 줄에 달린다).

## 재개 모드

기존 이월 노트를 골라 이어받는다.

1. **스캔**: `_workspace/carryover/*.md`를 나열한다. 각 노트의 파일명·날짜와 프론트 부분의 "한 줄 요약"을 함께 뽑아 목록으로 만든다. 노트가 없으면 "이월 노트가 없습니다"를 알리고 종료한다.

2. **선택**: 노트가 4개 이하면 `AskUserQuestion`으로, 초과면 번호 목록으로 사용자가 하나(또는 여럿)를 고르게 한다.

3. **로드·소화**: 선택한 노트를 읽고 **한국어로 소화해** 현황(한 일/다음 할 일/막힌 점/참조)을 사용자에게 요약 보고한다. 원문 붙여넣기가 아니라 지금 이어가기 좋게 정리한다.

4. **재진입**: 노트의 "재개 방법"이 가리키는 경로로 이어간다 — 새 구현·동작 변경이면 **orchestrate 게이트를 다시 밟는다**(§7 3항, continuation도 게이트 재진입). 리뷰면 team-review, 문서면 doc-writer. carryover 자체는 작업을 수행하지 않고 재진입 지점만 넘긴다.

5. **정리(선택)**: 작업을 마쳐 노트가 더 필요 없으면 사용자에게 확인 후 해당 노트를 지운다 — 다 쓴 이월 노트가 쌓이면 다음 재개의 목록이 흐려진다.

## 보존 규약 (`_workspace/`인데 왜 안 지워지나)

`_workspace/`는 세션 산출물이라 원칙적으로 정리 대상이지만(루트 AGENTS.md §4), `_workspace/carryover/`는 **정리 제외 목록에 포함**된다(harness-updates.md·harness-ops-log.md·점검 마커와 같은 취급) — 세션을 넘겨 이어받는 것이 존재 이유이기 때문이다. gitignore 대상인 것은 그대로라 **같은 머신에서만** 이어받을 수 있다. 크로스 머신 이월이 필요하면 이건 잘못된 도구다 → work-tracker(git 추적)로 보낸다.

## 주의

- **시크릿·`<private>` 금지의 연장**: 노트에 자격증명을 적지 않는다(§3). 민감 경로·내부 URL 등 `<private>`로 감쌀 내용은 노트에서 제외하거나 태그로 감싼다 — 다만 `_workspace/`는 발행물이 아니라 로컬 스크래치이므로, 외부로 옮길 때(work-tracker 승격 등)의 필터가 핵심이다.
- **완료·통과 주장 금지**: 노트는 "무엇을 했다"의 기록일 뿐, 완료 판정은 §13 신선한 증거(테스트 출력)로만 한다. "다음 할 일"에 검증 미완이면 그 사실을 적는다.
- **파괴적 작업 없음**: 이 스킬은 노트 파일 쓰기·읽기·(확인 후)삭제만 한다. 코드·인프라를 건드리지 않는다.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 세션 넘김 | 이슈 열 정도 아닌 작업이 매 세션 유실 | 고른 작업만 로컬 노트로 이월 |
| 선택성 | 전부 남기거나(무덤) 전부 잃거나 | 사용자가 남길 것만 선택 |
| 재개 | 지난 세션 뭐 했는지 수동 복기 | 노트 골라 즉시 재진입 지점 확보 |
| work-tracker 경계 | 경량 메모까지 GitHub 이슈로 → 무덤 | 경량=로컬 carryover, 정식=work-tracker |
