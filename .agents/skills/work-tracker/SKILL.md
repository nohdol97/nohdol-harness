---
name: work-tracker
description: "Persist work state across sessions using GitHub Issues (ccpm pattern) - register multi-session epics with spec-linked task checklists, log progress when pausing, resume from open issues, close via PR Closes #N. Falls back to docs/backlog.md in the project repo when there is no GitHub remote. Use when work will span multiple sessions or PRs, or when the user says 작업 등록, 백로그에 넣어줘, 이어서 하자, 하던 작업 뭐였지, 진행 상황 기록해줘, checkpoint, save progress, where was I (these route here, not to external checkpoint skills). Do NOT use for continuing an in-progress implementation step in the SAME session (진행해줘/계속 → orchestrate gate re-entry) - this skill resumes REGISTERED cross-session work. Re-run keywords - work-tracker, backlog, issue, epic, resume, 작업 등록, 백로그, 이어서, 재개."
---

# work-tracker — 세션 영속 작업 추적 (ccpm 패턴)

## 왜 이 스킬인가

`_workspace/`와 세션 컨텍스트는 **미보존**이다(루트 AGENTS.md 4절) — 세션이 끝나면 "어디까지 했고 다음이 뭔지"가 어디에도 남지 않아, 다음 세션이 git 이력만 보고 상태를 역추적해야 한다. 이 스킬은 ccpm 패턴을 채택해 **작업 상태의 영속 저장소를 프로젝트 저장소 자체**(GitHub Issues, 없으면 `docs/backlog.md`)에 둔다. 이유: 상태는 코드와 같은 곳에 있어야 어긋나지 않고, 설치처가 바뀌어도(ADR 005 이식성) 함께 따라온다.

## 등록 기준 (남발 금지)

**한 세션에 끝나지 않을 작업만 등록한다** — 여러 PR로 쪼개지는 작업, 며칠 규모의 에픽, 사용자가 명시적으로 "등록해줘"라고 한 작업. 이유: 모든 작업을 등록하면 이슈 무덤이 되어 아무도 읽지 않는다 — 지연 생성 원칙(ADR 007)과 같은 철학이다. 한 세션에 끝나는 작업의 상태 인계는 등록 없이 그 세션의 PR·커밋으로 충분하다.

## 저장소 선택 (프로젝트 저장소 기준)

1. **GitHub 원격 + `gh` 사용 가능** → GitHub Issues (기본).
2. **원격이 없거나 GitHub이 아님** → 프로젝트 저장소의 `docs/backlog.md`에 같은 구조(에픽 섹션 + 태스크 체크리스트 + 진행 로그)로 기록하고 커밋한다.
3. 루트 하네스 저장소의 장기 작업도 같은 규칙(GitHub Issues)을 쓴다.

## 흐름 1 — 등록 (작업 시작 시)

```bash
gh issue create --title "<간결한 작업명>" --label epic --body "$(cat <<'EOF'
## 배경
<한 단락 — 왜 이 작업인가>

## 스펙
<docs/specs/... 경로 또는 "스펙 작성 예정(13절)">

## 태스크
- [ ] <완료 기준 단위의 태스크 1>
- [ ] <태스크 2>

## 진행 로그
(세션이 끝나거나 중단할 때 코멘트로 추가)
EOF
)"
```

- 태스크는 **스펙의 완료 기준(C번호) 단위**로 쪼갠다(13절 SDD) — 체크 하나가 검증 가능한 상태 변화 하나에 대응해야 재개 시점이 명확하다.
- 코드 작업이면 `branch-workflow` 시작 절차로 이어가고, 브랜치명·커밋에 이슈 번호를 참조한다(예: `feat/login-oauth` + 커밋 본문 `#12`).
- **시크릿·자격증명을 이슈 본문에 절대 쓰지 않는다**(가드레일 3절) — 이슈는 저장소 밖(GitHub)에도 남는 외부 발행물이다.

## 흐름 2 — 진행 기록 (세션 종료·중단 시)

작업을 끝내지 못하고 세션을 닫을 때 **반드시** 남긴다 — 이 코멘트가 다음 세션의 시작점이다:

```bash
gh issue comment <번호> --body "$(cat <<'EOF'
### 진행 로그 (YYYY-MM-DD)
- 완료: <이번 세션에 끝낸 것 — 커밋/PR 링크>
- 다음: <바로 이어서 할 구체적 첫 행동>
- 막힘: <블로커와 원인, 없으면 생략>
EOF
)"
```

동시에 본문의 태스크 체크박스를 갱신한다(`gh issue edit`). `_workspace/`의 중간 산출물 중 다음 세션에 필요한 결론은 **요약해서 코멘트로 옮긴다** — 원본은 미보존이다. 옮길 때 **`<private>…</private>`로 표시된 부분은 제외한다**(민감 경로·내부 URL·개인 정보 — 루트 AGENTS.md 3절 가드레일). 이슈·코멘트는 저장소 밖에도 남는 외부 발행물이므로, 시크릿 금지(가드레일 3절)와 함께 이 제외를 지킨다.

기록을 마치면 **다음 세션 시작 프롬프트를 복붙용 코드블록으로 제시**한다(wrapup 5단계·carryover 저장 모드와 동일 형식 — 단독 호출에서도 같은 경험): `이어서 하자 — #<번호> <이슈 제목>. 첫 행동: <방금 남긴 진행 로그의 "다음" 항목>`. "첫 행동"은 진행 로그에서 그대로 가져온다(지어내지 않는다 — 어긋나면 재개 지점이 둘이 된다).

## 흐름 3 — 재개 ("이어서 하자", "하던 작업 뭐였지")

```bash
gh issue list --state open --label epic   # 대상 프로젝트 저장소에서
gh issue view <번호> --comments           # 마지막 진행 로그 확인
```

마지막 진행 로그의 "다음" 항목이 시작점이다. 코드 작업이면 해당 브랜치 존재를 확인하고(`git branch -a`), 없거나 머지됐으면 branch-workflow 시작 절차부터 다시 밟는다. 어느 프로젝트인지 모호하면 REGISTRY.md의 레지스트리 순으로 열린 epic 이슈를 조회해 보고한다.

## 흐름 4 — 완료

- PR 본문에 `Closes #<번호>`를 넣는다(branch-workflow 마무리 절차) — 머지(사용자) 시점에 이슈가 자동으로 닫혀, 상태와 코드가 같은 순간에 정리된다.
- PR 없이 끝나는 작업(문서·조사 등)은 결론 코멘트를 남기고 `gh issue close <번호>`.
- `docs/backlog.md` 방식이면 항목을 "완료" 섹션으로 이동하고 커밋한다.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 세션 경계 | 상태가 컨텍스트와 함께 소실 — git 이력으로 역추적 | 진행 로그 코멘트에서 즉시 재개 |
| 상태 위치 | checkpoint 등 세션 로컬 장치 — 설치처를 못 넘음 | 프로젝트 저장소(이슈)에 영속 — 어디서든 조회 |
| 완료 정합 | 작업은 끝났는데 추적 항목은 열린 채 방치 | PR `Closes #N`으로 코드와 상태가 함께 닫힘 |
| 노이즈 | 모든 작업을 기록하면 이슈 무덤 | 멀티 세션 작업만 등록 (등록 기준 고정) |
