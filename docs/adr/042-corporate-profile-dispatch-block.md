# ADR 042 — 사내 프로필에서 서브에이전트 발행 전면 차단

- **날짜**: 2026-08-04
- **상태**: 활성
- **관련**: [ADR 038](038-corporate-profile-verification-exemption.md)(이 ADR이 차단 범위를 확장 — 검증 축 → 발행 축), ADR 037·040(같은 발행 지점의 tier-gate), ADR 012(설치처 프로필), AGENTS.md 7절 5·6항·13절 3항, 스펙 `2026-08-04-dispatch-gate-hook`(전신 `2026-08-03-review-gate-hook`을 대체)

## 변경 내용

1. **프로필이 `사내`면 서브에이전트 발행을 역할과 무관하게 차단한다.** ADR 038이 껐던 검증 축(`reviewer`·관점 팬아웃·리뷰 fan-in)에 더해 빌드 측(`implementer`·`explorer`·`troubleshooter`·`architect`), 모든 `integrator` 용도, **로스터 밖 타입**(`general-purpose` 등), **`subagent_type` 미지정**까지 전부 포함한다.
2. **`infra-specialist` 하나만 통과한다.** 7절 5항이 k8s·IaC를 이 역할로 보내는 근거가 admission 선확인이라, 이 축은 비용이 아니라 **블라스트 반경**으로 판정한다 — 끊었을 때 더 비싼 유일한 축이다.
3. **우회 표식을 없앤다.** ADR 038의 `[review-ok]`를 폐기한다. 필요하면 훅 등록을 걷는 것이 유일한 경로이며, 그것은 설정 파일 diff로 남는다.
4. **`orchestrate` 판정표가 한 행으로 수렴한다** — 「단독 서브에이전트」·「생성-검증 쌍」·「팀」이 도달 불가라 판정은 항상 「직접 수행」이다. 게이트 자체는 계속 밟는다(거기서 기록되는 것은 범위와 위험이고, 순차 계획이 그 판정 위에 선다).
5. **팬아웃이 절차인 스킬은 정지가 아니라 저하한다** — `project-status`(Phase 1 수집·Phase 2 통합), `team-review`(양 모드), `harness-review`(주간 수집)는 계속 발동하되 메인 루프가 순차로 수행하고 산출물에 **팬아웃 없이 돌았다**고 적는다.
6. **훅을 `review-gate.py` → `dispatch-gate.py`로 개명하고 판정을 반전한다.** 이름을 유지하면 `implementer`를 막는 훅이 `review-gate`라고 불리게 된다 — 인덱스·요약 층에 가장 오래 남는 종류의 거짓 표지다. 스펙·테스트·등록(`.claude/settings.json`, `.codex/config.toml`)·무결성 R18 목록·`_common` 소비자 목록을 같은 커밋에서 옮겼다.

## 대상

`.agents/hooks/dispatch-gate.py`(구 `review-gate.py`), `.agents/hooks/dispatch-gate_test.py`(구 `review-gate_test.py`), `.agents/hooks/_common.py`, `.agents/hooks/_common_test.py`, `.agents/hooks/integrity-check.py`, `.agents/hooks/integrity-check_test.py`, `.agents/hooks/tier-gate.py`, `.agents/hooks/tier-gate_test.py`, `.agents/hooks/harness-review-reminder.py`, `.agents/hooks/harness-review-reminder_test.py`, `.claude/settings.json`, `.codex/config.toml`, `AGENTS.md`(7절 5·6항·13절 3항), `AGENTS.ko.md`, `CLAUDE.md`, `.agents/skills/orchestrate/SKILL.md`, `.agents/skills/team-review/SKILL.md`, `.agents/skills/project-status/SKILL.md`, `.agents/skills/harness-review/SKILL.md`, `.agents/skills/metaskill/SKILL.md`, `.agents/skills/tool-eval/SKILL.md`, `.agents/skills/doc-writer/references/templates.md`, `.agents/skills/README.ko.md`, `.agents/agents/README.ko.md`, `README.md`, `docs/README.md`, `docs/specs/2026-08-04-dispatch-gate-hook.md`(구 `2026-08-03-review-gate-hook.md`), `docs/adr/038-corporate-profile-verification-exemption.md`(대체 배너), `docs/adr/042-corporate-profile-dispatch-block.md`(이 파일), `docs/harness-changelog.md`, `_workspace/harness-ops-log.md`(미추적)

## 사유

**사용자 판정**(2026-08-04): "orchestrate, agents 호출도 사내에서는 안되게 막아줘. 비용이 너무 많이 들어."

**ADR 038이 같은 축의 절반이었다.** 하루 전 그 ADR은 같은 비용 근거로 검증 발행만 껐고, 빌드 측 발행을 **명시적으로 비목표**에 두면서 근거를 "사용자가 지목한 비용 축이 검증"이라고 적었다. 그 전제가 하루 만에 갱신된 것이므로 이것은 038의 번복이 아니라 **같은 판정의 확장**이다 — 038이 세운 구조(발행 시점 강제, 프로필을 판정 입력으로, 메인 루프 대체 + 면제 기록, 그 기록을 붙잡는 단계)는 전부 그대로 쓰고 범위만 넓혔다.

**축이 넓어지면서 038이 감수했던 두 구멍이 닫힌다.** 초판은 로스터 밖 타입과 `subagent_type` 미지정을 통과시켰고, 이유는 둘 다 "리뷰 의도인지 타입으로 판정할 수 없다"였다. 새 축에는 그 질문 자체가 없다 — 어느 쪽이든 발행이고 비용은 같다. 초판 스펙 4절이 「과잉 차단 축」·「과소 차단 축」으로 나눠 설명해야 했던 규칙-훅 간극도 함께 사라진다: 이제 규칙이 끄는 것과 훅이 막는 것이 같은 넓이다.

**`integrator` 축은 038의 must-fix가 이번엔 성립하지 않는다.** 그때 독립 검증 2인이 각각 지적한 결함은 "타입으로 막으면 `project-status` Phase 2가 사내에서 통째로 죽고 정당한 우회가 없다"였다. 이번에는 죽지 않는다 — 그 스킬이 **메인 루프 인라인 수행으로 저하**하도록 같은 커밋에서 규정했기 때문이다(사용자 결정). 즉 그 결함은 차단 범위를 좁혀서가 아니라 **대체 경로를 만들어서** 해소한다.

**우회 표식을 없앤 것은 내 판단이고 근거는 비용 논리의 방향이다.** 사용자 답변은 새 게이트에 우회를 둘 것인가에 대한 "안 둔다 — 사내에선 예외 없음"이었다. `[review-ok]`를 남기면 **가장 비싼 역할에만 탈출구가 있고 더 싼 역할에는 없는** 상태가 되어, 이 ADR이 딛고 선 근거와 정면으로 어긋난다. 되돌리려면 이 항만 되돌리면 된다.

**규칙 15 ①은 충족, ②는 충족하지 못한다 — 기록에 남긴다.** 초안 조건(프로필 `사내` + Agent 발행)은 정당화 사례에 실제로 발동한다: 사용자가 지목한 `orchestrate`·`agents` 호출이 전부 `Agent` 도구를 거치므로 훅이 그 자리에서 막는다. 그러나 **이 표면에 이 저장소가 가진 측정된 실패는 0건**이다 — 비용 실측(1회 약 100k 토큰, 2026-07-17 reviewer 6회 평균)은 개인 설치처 값이고, 사내 설치처의 발행 기록은 여기 없다(ADR 038이 같은 문장을 적었고 하루 만에 달라지지 않았다). 즉 이 조항은 위반을 막는 게이트가 아니라 **비용 판정의 성문화**이며, 그 사실을 숨기지 않는다.

## 영향

- **잃는 것**: 사내에서 병렬 수집·독립 검증·관점 팬아웃이 전부 사라진다. 리뷰는 저자가 자기 작업을 보는 것이 되고, 그 사실이 산출물에 적힌다. 컨텍스트 위생도 잃는다 — 수집·리뷰 상세가 메인 컨텍스트에 그대로 쌓이므로 큰 작업은 세션 경계를 더 자주 넘게 된다(§13-2 이월 조항이 그때 발동한다).
- **얻는 것**: 사내 세션의 발행 비용이 `infra-specialist` 하나를 빼면 0이 된다.
- **안 잃는 것**: 테스트·스펙 게이트·§3 가드레일·증거 4종은 그대로다. 이 변경이 없애는 것은 **팬아웃**이지 증거가 아니다.
- **되돌리기**: 이 ADR을 대체하는 ADR + `EXEMPT_AGENTS`를 되돌리는 한 줄. 부분 되돌리기도 그 상수 하나로 된다(예: 038 상태로 복귀하려면 `reviewer` 외 전 역할을 면제에 넣는 대신 판정을 다시 화이트리스트로 뒤집는다).
- **관측되지 않은 채 나간다**: 이 설치처는 `개인`이라 차단 경로가 실환경에서 돈 적이 없다. 판정은 임시 REGISTRY.md를 깐 테스트 12건 + 변이 6종으로만 확인했다.
