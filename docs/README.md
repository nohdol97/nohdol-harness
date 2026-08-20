# docs/ — 결정·스펙·제안 지도 (MOC)

이 파일은 `docs/` 하위 문서의 **탐색 인덱스**다(obsidian Map-of-Content 착안). ADR·스펙이 늘면서 "어느 결정이 어느 결정을 대체했는지", "어느 스펙이 어느 코드·ADR에 걸리는지"를 파일을 다 열지 않고 한눈에 보기 위한 것이다. 규칙의 단일 원본은 여전히 [AGENTS.md](../AGENTS.md)이고, 이 인덱스는 **길잡이일 뿐 내용을 복제하지 않는다**(링크만).

> **동기화 의무**: ADR·스펙·제안을 새로 만들거나 상태가 바뀌면(대체·구현·기각) 이 인덱스의 해당 행을 **같은 커밋에서 갱신**한다(metaskill 절차·AGENTS.md 6절). 인덱스가 현실과 어긋나면 REGISTRY.md와 같은 이유로 아무도 안 믿게 된다.

## ADR (구조적 결정 기록) — `docs/adr/`

상태: **활성** = 유효, **부분 대체(→NNN)** = 일부 결정이 후속 ADR로 대체됨(각 ADR 상단 배너에 어느 부분인지 명시). ADR은 불변 기록이라 대체돼도 삭제하지 않는다 — 결정의 역사를 남긴다.

| ADR | 날짜 | 상태 | 제목 |
|---|---|---|---|
| [001](adr/001-initial-harness.md) | 2026-07-12 | 부분 대체(→005·021·027) | 루트 하네스 초기 구성 |
| [002](adr/002-project-dir-separation.md) | 2026-07-12 | 부분 대체(→024) | 하위 프로젝트 저장소 분리 (`project/` 미추적, `dev/`는 024로 제거) |
| [003](adr/003-perfectionism-clause-removal.md) | 2026-07-12 | 활성 | "완벽주의 금지" 절 삭제 및 1차 독립 검증 반영 |
| [004](adr/004-registry-separation-standard-roster.md) | 2026-07-12 | 부분 대체(→005) | 레지스트리 분리(REGISTRY.md)와 표준 팀원 로스터 완성 |
| [005](adr/005-registry-untracked-portable-harness.md) | 2026-07-12 | 활성 | 하네스 이식성: REGISTRY.md 미추적, 경로 규약 이관, 티어 탈모델명 |
| [006](adr/006-subproject-harness-central-management.md) | 2026-07-13 | 활성 | 하위 프로젝트 하네스 중앙 관리 (원본 루트 일원화·미추적) |
| [007](adr/007-lazy-project-skills.md) | 2026-07-13 | 활성 | 하위 스킬·에이전트 지연 생성 + 프로젝트 로컬 배치 |
| [008](adr/008-tdd-gate-hook.md) | 2026-07-13 | 부분 대체(→014·015·024) | TDD 게이트 훅 (13절 실행 계층 강제) |
| [009](adr/009-work-tracker-session-persistence.md) | 2026-07-13 | 활성 | 세션 영속 작업 추적 (work-tracker, ccpm 패턴) |
| [010](adr/010-orchestrate-universal-gate.md) | 2026-07-13 | 활성 | orchestrate 범용 게이트화 (팀 판정 + 검증 필수 + 하이브리드) |
| [011](adr/011-roster-expansion-7-agents.md) | 2026-07-13 | 활성 | 표준 로스터 확장 (4종 → 7종) |
| [012](adr/012-installation-profile-push-policy.md) | 2026-07-14 | 활성 | 설치처 프로필(개인/사내)과 하네스 업데이트 대기 큐 |
| [013](adr/013-evolution-signal-expansion.md) | 2026-07-14 | 활성 | 진화 트리거 4신호 체계 (수축·효율 신호 신설) |
| [014](adr/014-tdd-gate-git-hook-layer.md) | 2026-07-14 | 부분 대체(→015) | TDD 게이트의 git 훅 계층 추가 (도구 무관 강제) |
| [015](adr/015-tdd-gate-single-git-layer.md) | 2026-07-14 | 활성 | TDD 게이트 git 계층 단일화 (008·014 일부 대체) |
| [016](adr/016-internal-communication-language.md) | 2026-07-15 | 활성 | 내부 통신 언어 정책 (모델만 읽으면 영어, 사용자면 한국어) |
| [017](adr/017-code-minimalism-product-code.md) | 2026-07-16 | 활성 | 코드 최소주의 — 제품 코드 (ponytail 이식) |
| [018](adr/018-claude-mem-adoption.md) | 2026-07-16 | 활성 | claude-mem 최소 채택 (세션 경계 리마인더·점진적 공개·private 마커) |
| [019](adr/019-codex-sessionstart-hook-parity.md) | 2026-07-16 | 부분 대체(→029·031) | Codex SessionStart 훅 병행 (파리티·공용 스크립트는 유효, 등록 위치·키·활성화 주장은 대체) |
| [020](adr/020-infra-domain-review-specialization.md) | 2026-07-16 | 활성 | 인프라 도메인 리뷰 특화 (team-review 인프라 관점을 infra-specialist가 리뷰 모드로) |
| [021](adr/021-claude-md-agents-import.md) | 2026-07-16 | 활성 | CLAUDE.md `@AGENTS.md` 임포트 (단일 원본 항상-온) + 변경 이력 분리 |
| [022](adr/022-superpowers-adoption.md) | 2026-07-17 | 활성 | superpowers 규율 착안 3건 이식 (압박 테스트·신선한 증거·리뷰 수신 규율) |
| [023](adr/023-secret-gate-hook.md) | 2026-07-18 | 활성 | secret-gate 훅 (3절 시크릿 금지의 실행 계층 승격) |
| [024](adr/024-remove-dev-dir.md) | 2026-07-19 | 활성 | `dev/` 실험 공간 디렉토리 제거 (실작업은 전부 `project/`, tdd-gate `dev/` 예외 삭제) |
| [025](adr/025-autoloop-driver.md) | 2026-07-19 | 부분 대체(→048) | autoloop — 외부 driver·게이트 3종은 유지, 단일 구현 반복·Codex writer 정책은 048로 대체 |
| [026](adr/026-oh-my-openagent-adoption.md) | 2026-07-19 | 활성 | oh-my-openagent 검증·운영 착안 5건 이식 + integrity-check 무결성 점검 훅 |
| [027](adr/027-codex-agent-adapters.md) | 2026-07-19 | 활성 | Codex custom-agent 얇은 어댑터 (`.agents/agents` 원본 → `.codex/agents` 로더 계층) |
| [028](adr/028-gate-reminder-hook.md) | 2026-07-22 | 활성 | gate-reminder 훅 — 진단→구현 전환점 orchestrate 게이트 상기의 실행 계층 승격 (세션당 1회 차단) |
| [029](adr/029-codex-hook-parity-default.md) | 2026-07-22 | 부분 대체(→031) | 세션 훅 Codex 파리티 기본값 (인라인 등록·실측 계약은 031, 파리티와 fail-open은 유효) |
| [030](adr/030-english-harness-assets.md) | 2026-07-22 | 활성 | 모델-로드 하네스 자산 영어 단일 원본 전환 (§15 개정, 한글 뷰 3종 + 드리프트 가드, ADR·스펙·changelog는 한글 유지) |
| [031](adr/031-codex-runtime-contract.md) | 2026-07-25 | 활성 | Codex 런타임 계약 실측 정렬 (32KiB 방어, 인라인 훅, trust, custom-agent 발행 확인) |
| [032](adr/032-token-efficient-orchestration.md) | 2026-07-25 | 활성 | 토큰 효율형 오케스트레이션 (호출 예산·델타 재사용·세션 경계·상시 노출 예산) |
| [033](adr/033-knowledge-source-routing.md) | 2026-07-26 | 활성 | 지식 소스를 설계 단계 라우팅에 편입 (§7 8항, REGISTRY 기록 시에만 발동·임의 경로·요약은 증거 아님·fail-open) |
| [034](adr/034-vault-write-delegation.md) | 2026-07-28 | 활성 | vault 쓰기 경로 신설(`vault-write`)과 노트 계약 정본의 참조 위임 — 사본 없이 `nohdol-study` references를 런타임 참조, 부재 시 정지, index/log/hot 기록 필수 |
| [035](adr/035-subproject-worktree-workflow.md) | 2026-07-29 | **부분 대체(→043)** | 하위 프로젝트 쓰기 작업의 worktree 선행 생성(`project/.worktrees/`, `origin/main` 직접 분기, 세션 cwd는 루트 유지)과 머지 실측 기반 정리 — 정본은 `branch-workflow`, `wrapup`이 위임 |
| [036](adr/036-ownership-boundary-placement-and-vocabulary.md) | 2026-08-02 | 활성 | 소유권 경계를 둘로 분할 — 규칙(영역 표·중단 게이트)은 프로젝트 저장소에 중립 어휘(`공용`/`배포처`)로, 역할 배정만 하위 하네스에. `carry-in.md` → `site-setup.md` |
| [037](adr/037-tier-gate-dispatch-enforcement.md) | 2026-08-03 | **대체됨 → 040** | 티어 매핑의 실행 계층 승격 — 발행 시 `model` 미지정 차단(`tier-gate`), 값 판정 없음·`inherit`는 미지정 동치·fail-open. **판정 방향이 뒤집혔다**(발행 지점 강제라는 결정은 040이 유지) |
| [038](adr/038-corporate-profile-verification-exemption.md) | 2026-08-03 | **부분 대체(→042)** (045가 폐기했다가 046이 되살림) | 사내 프로필의 검증 목적 발행 면제 — reviewer·관점 팬아웃·리뷰 fan-in integrator·infra-specialist 리뷰 모드를 끄고 메인 루프 자체 검증+면제 기록으로 대체, 명시 요청은 실행. 훅(`review-gate`)이 막는 것은 `reviewer` 타입 하나 |
| [039](adr/039-diagram-obligation-and-skill-port.md) | 2026-08-03 | 활성 | 다이어그램 의무의 **임계값 기반** 발동 조건 + `diagram` 스킬 nohdol-study 포팅 — 스펙·PR 본문·work-tracker 이슈에서 필수(임계값을 넘을 때만), 그 외 권고. 붙잡는 단계는 둘로 갈린다: **품질**은 doc-writer 자체 검증의 체커, **의무**는 유형별(스펙=team-review·reviewer·architect / PR 본문=branch-workflow 마무리 4 / 이슈=work-tracker 등록) |
| [040](adr/040-tier-gate-inversion-lightweight-ban.md) | 2026-08-04 | 활성 | `tier-gate` 판정 반전(037 대체) — 미지정(=세션 모델 상속)은 통과, REGISTRY.md 「경량 모델」 절이 나열한 등급 지정만 차단. 우회는 `[light-ok]`. 모델명은 코드가 아니라 그 미추적 절에 두어 ADR 005 유지 |
| [041](adr/041-comprehension-quiz-removal.md) | 2026-08-04 | 활성 | **PR 전 이해도 퀴즈 게이트 제거** — `branch-workflow` 마무리 4단계(퀴즈 스펙 단일 원본)를 삭제하고 그것을 실행시키던 `orchestrate`·`team-review`의 리뷰 창 퀴즈 문단, 5절 루트 원격 PR 사이클의 면제 괄호, 13-0의 퀴즈 회수 문구를 함께 걷어냈다. 이후 단계는 4(PR 생성)·5(머지)로 당겨진다. 13절 서두의 「사용자 이해는 완료의 요건」과 그 리포트 의무(결정 갈림길 교습 + diff 읽기 가이드)는 유지하되, **이제 무엇도 그것을 붙잡지 않는다는 사실을 조항 안에 명시**해 점검이 이를 결함으로 재개봉하지 않게 했다. 사용자 판정(2026-08-04) + 실측: 9일 사이 퀴즈 장치 자체를 주제로 한 이력 행 7건, 그중 4건이 사용자 지적·결정발 수리다 |
| [042](adr/042-corporate-profile-dispatch-block.md) | 2026-08-04 | 활성 (045가 폐기했다가 046이 되살림) | **사내 프로필에서 서브에이전트 발행 전면 차단**(038 범위 확장) — 검증 축만 끄던 것을 **역할 무관 발행 축 전체**로 넓혔다: 빌드 측·모든 `integrator` 용도·로스터 밖 타입·`subagent_type` 미지정까지 포함하고, `infra-specialist` 하나만 통과(비용이 아니라 블라스트 반경으로 판정하는 축 — 7절 5항 admission 선확인). **우회 표식 폐기**(`[review-ok]`). `orchestrate` 판정은 항상 「직접 수행」으로 수렴하고, 팬아웃이 절차인 스킬(`project-status`·`team-review`·`harness-review`)은 정지가 아니라 **메인 루프 순차 수행으로 저하**한다. 훅 개명 `review-gate.py` → `dispatch-gate.py` |
| [043](adr/043-corporate-branch-in-checkout-and-worktree-bootstrap.md) | 2026-08-05 | 활성 | **사내 프로필의 worktree 폐기**(035 부분 대체) — 그 사이트에서 worktree로부터의 커밋·푸시·PR이 실패해 `project/<이름>/` 체크아웃 하나에서 브랜치를 전환한다. 035가 **구조로** 막던 두 실패(낡은 시작점·재개 시 `main` 복귀)가 **절차로** 되돌아오고, 정리에서 `worktree remove`의 거부가 하던 데이터 손실 검사가 사라지므로 `status --porcelain` 선검사로 보상한다(실측: 더티 상태에서 `checkout main`은 성공하며 파일을 데려가고, `worktree remove`는 exit 128로 거부). 개인 프로필은 worktree 유지 + **의존성 부트스트랩을 시작 절차에 명시**(6개 프로젝트 전부 `.venv` 7~27MB, 재생성 8~12초 2회 측정) — editable 설치라 심볼릭 링크 공유는 금지(어느 트리를 import하는지가 호출 방식에 달렸고 위험한 형태가 더 짧다) |
| [044](adr/044-mattpocock-skills-partial-adoption.md) | 2026-08-07 | 활성 | **mattpocock/skills 부분 채택** — 통설치 기각(ADR 022와 동일 범주: 25개 description 고정 로드·트리거 전면 충돌·§11 심링크 제약), 착안 4건만 이식: ① `harness-review` 신호 ④에 죽은 규칙 판정 방법(무동작·환경-캐시 테스트, 새 의무 아님) ② §13-0을 「1회 일괄」에서 **프론티어 라운드**로 정련(독립 질문은 종전대로 한 라운드) ③ `wait-what` 스킬 신설(슬래시 전용 — ADR 041이 남긴 이해도 요건의 당기는 쪽) ④ `orchestrate/references/product-design.md` 신설(deep module 어휘·폐기 전제 프로토타입, 참고·허용). ①④를 의무로 안 적은 이유는 공통규칙 15 ②의 실측 실패 부재 |
| [045](adr/045-corporate-profile-dispatch-restored.md) | 2026-08-07 | **폐기(→046)** | **사내 프로필의 발행 차단 폐기**(042·038 대체) — 설치처 프로필을 발행의 판정 입력에서 빼고 `dispatch-gate`를 삭제했다. 같은 날 046이 철회해 커밋이 revert됐으므로 **현재 규칙이 아니다**. 남겨 둔 이유는 §6 규약과, 「프로필 분기를 넣고 빼는 데 무엇이 드는가」의 실측치(35개 파일)를 046이 이 파일에서 인용하기 때문 |
| [046](adr/046-corporate-profile-dispatch-block-restored.md) | 2026-08-07 | 활성 | **ADR 045 철회 — 사내 발행 차단 복원**(042·038 다시 활성) — 사용자 판정 「비용 때문에 안 되겠다」로 `1b1779f`를 revert. **되돌리지 않은 것 3건**: 045를 검증하다 발견된 테스트 결함(C4b 대상 선택을 파일명 → `read_profile` 보유 여부, R18 어서션을 게이트 이름 → 고유 문구, R21 `gate-reminder` 어서션을 개수로) — 전부 042 시절부터 있던 것이라 차단 여부와 무관하다. 독립 검증 발행 없음(비용이 롤백 사유 — 사용자 결정) |
| [047](adr/047-autoloop-observation-dashboard.md) | 2026-08-19 | 활성 | autoloop 표시 상태를 게이트 체크포인트에서 분리하고 loopback 전용 읽기 대시보드 추가 |
| [048](adr/048-autoloop-structured-orchestration.md) | 2026-08-19 | 활성 | autoloop 구조화 task DAG·ready-set 병렬 dispatch·writer별 worktree 격리·agent/task dashboard 투영 |
| [049](adr/049-autoloop-dashboard-operator-experience.md) | 2026-08-19 | 활성·부분 대체 | autoloop 대시보드의 최소 개요·T 핸드오프·압축 Coordination을 고정 |
| [050](adr/050-autoloop-plan-repair-and-scope-aware-waves.md) | 2026-08-20 | 활성 | 잘못된 planner DAG의 1회 자동 수정과 겹치는 writer `file_scope`의 wave 직렬화 |

**대체 체인**: tdd-gate는 008(Claude Code 한정 PreToolUse) → 014(git 계층 추가, 도구 무관) → 015(git 계층 단일화, PreToolUse 제거)로 진화했고, 예외 경로의 `dev/` 항목은 024로 제거됐다. 008·014의 나머지 결정(차단 지점·fail-open·나머지 예외·commit-msg 선택·전역 hooksPath 등)은 유효하다. Codex 훅은 019(SessionStart 병행) → 029(파리티 기본값) → 031(인라인 설정·trust·실측 계약)로 정렬됐다. 그 밖의 부분 대체: 티어 모델명·REGISTRY.md 추적은 001·004 → 005(탈모델명·미추적), CLAUDE.md 산문 포인터·변경 이력 위치는 001 → 021(`@AGENTS.md` 임포트·changelog 분리), 공용 Markdown agent를 Codex가 직접 읽는 가정은 001 → 027(역할 원본 유지+TOML 어댑터), `project/`·`dev/` 미추적은 002 → 024(`dev/` 제거).

## 스펙 (SDD — 루트 자체 코드) — `docs/specs/`

루트 하네스가 추적하는 코드(훅 등)의 스펙. 하위 프로젝트 스펙은 각 프로젝트 저장소 `docs/specs/`에 있다(13절 — 여기 없음).

| 스펙 | 상태 | 대상 코드 | 관련 ADR |
|---|---|---|---|
| [2026-07-13-tdd-gate-hook](specs/2026-07-13-tdd-gate-hook.md) | 구현됨 | `.agents/githooks/tdd-gate.py` | 008·014·015 |
| [2026-07-14-agentsview-daemon-hook](specs/2026-07-14-agentsview-daemon-hook.md) | 구현됨 | `.agents/hooks/agentsview-daemon.py` | — |
| [2026-07-14-harness-review-reminder-hook](specs/2026-07-14-harness-review-reminder-hook.md) | 구현됨 | `.agents/hooks/harness-review-reminder.py` | 013·019 |
| [2026-07-15-hooks-common-bootstrap](specs/2026-07-15-hooks-common-bootstrap.md) | 구현됨 | `.agents/hooks/_common.py` | 040(REGISTRY 절 판독기 2종) |
| [2026-07-16-worklog-reminder-hook](specs/2026-07-16-worklog-reminder-hook.md) | 구현됨 | `.agents/hooks/worklog-reminder.py` | 018·019 |
| [2026-07-18-secret-gate-hook](specs/2026-07-18-secret-gate-hook.md) | 구현됨 | `.agents/githooks/secret-gate.py` | 023 |
| [2026-07-19-autoloop-driver](specs/2026-07-19-autoloop-driver.md) | 구현됨 | `.agents/skills/autoloop/scripts/driver.py` | 025 |
| [2026-07-19-integrity-check-script](specs/2026-07-19-integrity-check-script.md) | 구현됨 | `.agents/hooks/integrity-check.py` | — (제안: 2026-07-19-oh-my-openagent-adoption) |
| [2026-07-19-codex-agent-adapters](specs/2026-07-19-codex-agent-adapters.md) | 구현·실발행 확인 | `.codex/agents/*.toml` | 027·031 |
| [2026-07-22-gate-reminder-hook](specs/2026-07-22-gate-reminder-hook.md) | 구현됨 | `.agents/hooks/gate-reminder.py` | 028 |
| [2026-07-25-codex-runtime-compatibility](specs/2026-07-25-codex-runtime-compatibility.md) | 구현됨 | `AGENTS.md`, `.codex/`, `.agents/hooks/integrity-check.py` | 019·027·029·031 |
| [2026-07-25-token-efficiency-contract](specs/2026-07-25-token-efficiency-contract.md) | 구현됨 | `CLAUDE.md`, `.agents/skills/`, `.agents/agents/`, `.agents/hooks/integrity-check.py` | 032 |
| [2026-08-03-tier-gate-hook](specs/2026-08-03-tier-gate-hook.md) | 구현됨(040으로 개정) | `.agents/hooks/tier-gate.py` | 037·040 |
| [2026-08-04-dispatch-gate-hook](specs/2026-08-04-dispatch-gate-hook.md) | 구현됨 | `.agents/hooks/dispatch-gate.py` | 038·042·046 |
| [2026-08-03-autoloop-engine-harness-load-symmetry](specs/2026-08-03-autoloop-engine-harness-load-symmetry.md) | 구현됨(048로 해결) | `.agents/skills/autoloop/scripts/driver.py` | 025·048 |
| [2026-08-14-harness-functional-and-language-audit](specs/2026-08-14-harness-functional-and-language-audit.md) | 구현됨 | 루트 규칙·문서·훅·CLI 로더 | — |
| [2026-08-19-autoloop-dashboard](specs/2026-08-19-autoloop-dashboard.md) | 구현됨 | `.agents/skills/autoloop/scripts/{driver.py,dashboard.py}` | 025·047 |
| [2026-08-19-autoloop-orchestration-runtime](specs/2026-08-19-autoloop-orchestration-runtime.md) | 구현됨 | `.agents/skills/autoloop/scripts/{driver.py,dashboard.py}` | 025·047·048 |
| [2026-08-19-autoloop-dashboard-operator-ux](specs/2026-08-19-autoloop-dashboard-operator-ux.md) | 확정·구현 완료, 독립 검증 미완료 | `.agents/skills/autoloop/{dashboard-ui/,scripts/dashboard.py,scripts/dashboard_test.py}` | 047·048·049 |

## 제안 (외부 도구 분석·채택 설계) — `docs/proposals/`

외부 도구·패턴을 분석하고 무엇을 이식하고 무엇을 기각할지 설계한 문서. 채택되면 결과가 ADR로 확정된다(제안 = 과정, ADR = 결정).

| 제안 | 결과 | 요지 |
|---|---|---|
| [2026-07-15-ponytail-adoption](proposals/2026-07-15-ponytail-adoption.md) | → ADR 017 | ponytail 코드 최소주의 결정 사다리 이식(원칙+리뷰 관점만, 배송 기계 기각) |
| [2026-07-16-claude-mem-adoption](proposals/2026-07-16-claude-mem-adoption.md) | → ADR 018 | claude-mem 착안 3개 무의존 이식(워커·벡터 DB·전수 캡처 기각) |
| [2026-07-17-superpowers-adoption](proposals/2026-07-17-superpowers-adoption.md) | → ADR 022 | superpowers 규율 착안 3개 문서 이식(플러그인 통설치·나머지 11스킬 기각) |
| [2026-07-18-loop-engineering-adoption](proposals/2026-07-18-loop-engineering-adoption.md) | → ADR 023 | loop-engineering 시크릿 게이트 1건 이식(unattended 루프·npm 도구군·L1-L3 기각 — 원칙 층은 기수렴) |
| [2026-07-18-graphify-review](proposals/2026-07-18-graphify-review.md) | 기각(파일럿 미달) | graphify 코드 지식 그래프 — sona_app 실측: Dart 줄번호 0%·역추적 빈결과·범위 grep보다 ~17배 토큰. TS 등 타 스택 재검토 여지 |
| [2026-07-19-oh-my-openagent-adoption](proposals/2026-07-19-oh-my-openagent-adoption.md) | → ADR 026 | oh-my-openagent 검증·운영 착안 5건(증거 4필드·무결성 기계 점검·untrusted 봉투·팀 런 교훈 노트·위임 발행 형식 강화) — 오케스트레이션·루프 층은 기수렴 판정, 실행 계층 기능·자동 머지 기각 |
| [2026-07-22-karpathy-guidelines-adoption](proposals/2026-07-22-karpathy-guidelines-adoption.md) | 부분 채택(§16·team-review — ADR 017 연장) | karpathy-guidelines 4원칙 중 Surgical Changes만 이식(변경 줄 요청 소급성) — 3원칙은 기수렴 기각, 플러그인 설치 기각 |
| [2026-07-22-rtk-adoption](proposals/2026-07-22-rtk-adoption.md) | 조건부 채택(harness-install 3e·§13-2) | rtk 명령 출력 압축 프록시 — 훅 모드 설치 단계(선택·텔레메트리 명시 차단) + 증거 원문 규칙 보강. Codex 모드·수치 신뢰는 보류(실측 후 tool-audit) |
| [2026-07-22-caveman-internal-comms](proposals/2026-07-22-caveman-internal-comms.md) | 기각 | 내부 통신 전보체(케이브어) 전환 — 손실 압축 실효 10~15% vs 지시 정밀도 손실 재작업 비대칭으로 기각, §15 영어 유지(적재 구조 절감 축이 대체) |
| [2026-07-25-agentmemory-review](proposals/2026-07-25-agentmemory-review.md) | 기각 | agentmemory 상시 메모리 서버(훅 전량 캡처+벡터·그래프 검색) — ADR 018 정면 충돌·니치 기충족(agentsview·auto-memory·문서 4계층)·상시 비용 역행·외부 임베딩 §3 우려. 마이크로 포팅 후보 6건 전부 기수렴/충돌 판정 |
| [2026-07-25-understand-anything-adoption](proposals/2026-07-25-understand-anything-adoption.md) | **철회**(채택 후 같은 날) | Understand-Anything 코드 지식 그래프 — 채택했다가 같은 날 철회. 사유: 코드를 대신 시각화해 떠먹여 "사용자 이해=완료 요건" 성장 원칙(직접 읽기)과 결이 반대 + graphify 범주. 하네스에서 완전 제거(도구 금지는 아님, 개인 사용 가능). claude-video는 유지 |
| [2026-07-25-claude-video-adoption](proposals/2026-07-25-claude-video-adoption.md) | 채택(직접 호출 전용 — harness-install 3g) | claude-video `/watch` 영상 이해 스킬 — 순수 신규 역량(중복 0)·opt-in-per-use. Whisper 폴백이 오디오를 제3자 전송하는 게 유일 §3 유출, 사내·민감 녹화는 `--no-whisper`/자막 전용 |
| [2026-07-25-hermes-agent-review](proposals/2026-07-25-hermes-agent-review.md) | 기각 | Nous Hermes Agent 자기호스팅 런타임 — 범주 불일치(채택 아니라 Claude Code+Codex 이탈)·간판 기능(자율 스킬 생성·대화 검색 DB)이 ADR 007·018과 정면 충돌·니치 기충족·Nous Portal 클라우드 경유 §3 유출. agentskills.io 이식형 SKILL.md 표준만 관찰 보류 |
| [2026-07-26-clew-review](proposals/2026-07-26-clew-review.md) | 기각(실측 미달) | Clew 멀티에이전트 트레이스 낭비 탐지 CLI — 57세션·3,759 툴 스팬 실측: 하네스 세션 낭비 0건, 전체 0.05%(2건)이고 그 2건도 도구 리포트 자체가 정당한 재실행 가능성 명시. 절감 상한 $0.50 대비 `[detect]` 경량 설치가 낭비 검출 시 크래시해 실질 757MB 강제. 증폭 비용의 계산 구조(측정값 아닌 상한)만 ADR 032 사유로 반영 |
| [2026-07-26-context-engineering-rules-review](proposals/2026-07-26-context-engineering-rules-review.md) | 부분 채택(Layer 1 적용 완료 2026-07-26, Layer 2·3 보류) | Anthropic "Claude 5 세대 컨텍스트 엔지니어링 규칙" 1차 출처 대조 — 원문 8축 중 6축 기수렴 실측(상시 32,637B : 지연 197,590B = 1:6.1). "80% 감축"은 제품 시스템 프롬프트 대상이라 범주 오적용으로 기각, AGENTS.md 스킬 분산은 §11·§12 Codex 가드레일 소실로 기각. **Layer 1(미설치 도구명 SuperClaude·gstack 정리)만 적용 — reviewer PASS, 사실 오류 정정이라 ADR 무개정.** Layer 2(순수 중복 앵커 3개 1,039B=상시의 3.2%)는 ADR 021 개정이 선행 조건이라 보류, Layer 3(rubric·비-markdown 스펙)은 프로젝트 등록 시 재평가 |
| [2026-07-26-harness-design-sources-review](proposals/2026-07-26-harness-design-sources-review.md) | 전건 규칙 무변경(후보 1건은 관측 후 규칙화로 보류) | 하네스 설계 자료 5건(이슈 #41 A-2~A-6) 1차 출처 대조. A-2 OpenAI 하네스 엔지니어링 기각(§11 Codex 축 미접촉·자동 머지 등 §5·§13 정면 충돌·원문 자체가 고처리량 한정), A-3 Anthropic 장기 실행 부분 채택(generate-verify 불변식 보강, 단 품질 주장은 전부 N=1 미반복), A-4 HyperAgents 기각(**논문에 "harness" 0회 — 표제가 블로거 프레임**·CC BY-NC-SA·100반복 8,860만 토큰), A-5 Managed Agents 기각(두뇌/손은 모델 분리가 아니라 하네스/샌드박스 분리라 §9 근거 불가), A-6 동적 워크플로우 기각(실축이 §7이고 orchestrate 기수렴). **유일한 규칙 변경 후보: A-3·A-5가 독립 도달한 "모델 업그레이드 시 우회 장치는 죽은 코드가 된다" → 신호 ④ 주간 점검에 모델 버전 변경 발화 조건 편입(신호 신설 아님). 2026-07-26 사용자 결정으로 관측 후 규칙화 보류 — 손해 관측 0건이라 §8 선제 생성 금지 원칙 적용, 발화 경로는 규칙이 아니라 메모리 `model-upgrade-dead-workarounds`** |
| [2026-07-30-loop-graph-engineering-review](proposals/2026-07-30-loop-graph-engineering-review.md) | 부분 채택(autoloop 3건 — 스펙 R16·R5-1·R17) · 신규 스킬 기각 | 루프·그래프 엔지니어링(사용자 제공 글, 자체적으로 떠도는 수치 5종을 가짜로 판정 — 수치 무이식) 대조. 원시개념 9종 중 7종 기수렴, 부분 2종은 기록된 결정(orchestrate 팀 비영속·work-tracker 체크포인트 반대편 배치). **채택은 개념이 아니라 우리 구현 누수 3개**: R16 체크포인트(재개가 노트만 물려받아 정체·누적비용·피드백이 재기동마다 초기화 → 게이트 우회 가능), R5-1 결과 3분류(러너 고장을 red로 뭉개 오타 난 `--test-cmd`가 반복 예산 소각), R17 테스트 래칫(`acceptEdits` Edit으로 단정을 지우면 드라이버가 스스로 green 보고). **신규 `graph` 스킬 기각** — A-6 동적 워크플로우 선례 기각 + §8 신호 부재 + orchestrate 트리거 충돌. autoloop 팬아웃·사전 정적 검사·rewind도 기각 |
| [2026-07-26-harness-tool-candidates-review](proposals/2026-07-26-harness-tool-candidates-review.md) | 전건 미채택(3 기각·1 연기) | 도구 후보 4건(이슈 #41 B) tool-eval. B-1 VHK 기각 — **`vhk sync`가 AGENTS.md를 자동 생성물로 덮어쓰고(`sync.ts:512`) `core.hooksPath`를 점유해 tdd-gate·secret-gate를 무력화**, 소스에서 확인(README 미기재). B-2 DeerFlow·B-4 OpenHarness 기각 — 범주 불일치(독립 런타임·Claude Code Python 포트), Hermes 선례 동일. B-3 Impeccable 연기 — 프론트엔드 전용이 원문으로 확인됐고 등록 프로젝트 0건이라 대상 부재(재평가 시 `impeccable.style` 텔레메트리·`settings.local.json` 훅 설치 확인 필요). 일반화 후보: 외부 도구가 AGENTS.md·CLAUDE.md·`.agents/`·`core.hooksPath`를 쓰기 대상으로 삼으면 기능 평가 이전에 구조 침해로 기각 |
| [2026-07-27-gist-mirror-readonly](proposals/2026-07-27-gist-mirror-readonly.md) | 검토 중(사용자 결정 대기) | 2026-07-26 철회한 하위 하네스 secret gist 미러를 **단방향 read-only형**으로 재도입 제안 — 철회 사유였던 §3 방향 통제를 사내 무자격증명(secret gist는 인증 없이 URL로 읽힘, `gist` 스코프는 write 전용)으로 기계 해결 |
| [2026-07-30-change-record-check-mechanization](proposals/2026-07-30-change-record-check-mechanization.md) | 기각(실측 미달) | 공통 규칙 14를 `integrity-check.py`로 기계화하는 검토 — **원안 술어는 측정 가능한 실사례(`c66e5f6:158`)를 놓친다**(그 행이 근거 커밋 6개를 인용해 "해시 없음" 판별자가 먼저 꺼지며, 측정을 적는 행이 곧 근거를 대는 행이라 구조적이다). 그것을 잡는 술어는 `2a6fe3b`에서 12건 중 1건만 진짜 — 처방·서사·저장소 밖 측정이 대량 오탐. 재제안은 정밀도 해법 동반을 조건으로 한다. 이 문서 자신이 규칙 14의 시험대가 돼 2라운드 연속 BLOCK을 받았고, 「BLOCK 2회+ → 선정리」에 따라 불안정한 수치를 걷어내는 쪽으로 정리했다 |
| [2026-07-31-gitignored-record-confirmation](proposals/2026-07-31-gitignored-record-confirmation.md) | 보류(선정리 — 규칙 변경 없음) | 대상 컬럼이 적은 gitignore 경로(ops-log 등)의 줄이 끝내 안 쓰이는 실패 3회(신호 ②)에 대한 공통 규칙 11 조항. 1안 순서·2안 마감 검사 모두 독립 검증 BLOCK — 근본 미결은 "gitignore 기록의 due가 언제인가"이고 규칙 11 단독 범위로는 못 푼다. 후보 3안과 근거 기록 |
| [2026-08-01-harness-semantic-search-pilot](proposals/2026-08-01-harness-semantic-search-pilot.md) | 기각(파일럿 미달) | 로컬 임베딩(ollama)으로 하네스 문서 104건·1.19MB를 의미 검색하는 안. `vault-search`의 `semantic.py`를 경로 파라미터화해 포팅하고 **사전 고정한 3축 바**로 실측 — `bge-m3`가 재현율 5/8(62.5%)·퇴행 4/4(100%)로 ①②를 통과했으나 **초기 빌드 644.47초가 300초 바의 2.15배**라 기각(사후 바 조정 없음, graphify 선례). 증분 catch-up은 3.0초로 통과. **모델 가설은 방향이 맞고 이유가 달랐다** — 코퍼스 언어 가설은 반증(`nomic`은 한국어·영어 코퍼스 양쪽 0점)이고 진짜 축은 **질의 언어**였다(`nomic` 한국어 질의 0/12 대 영어 2/3, rank-1 문서 3종·점수 폭 0.063의 순위 붕괴). 바보다 큰 제약은 **반환 단위** — `bge-m3` 히트 9건 중 실제 답 구절은 4~5건이라 235KB changelog에서는 파일 지목만으로 부족. 재검토는 ①빌드 실측 통과 ②구절 수준 반환을 함께 요구하며 질의 30건 이상으로 표본 보강. `nomic-embed-text`는 재검토 대상 아님 |
| [2026-08-07-mattpocock-skills-review](proposals/2026-08-07-mattpocock-skills-review.md) | 부분 채택(→044) | aihero.dev/skills(25스킬, MIT) 대조 — 워크플로 척추는 orchestrate·team-review·troubleshooter·doc-writer·§13+tdd-gate가 이미 상회하거나 겹쳐 통설치 기각(ADR 022와 동일 범주, 다른 점 미발견). `grep` 실측으로 확인한 잔여 공백 4건만 이식하고, `wayfinder`(결정 티켓·fog of war)와 `CONTEXT.md` 용어집은 실사용 관찰 시 재검토로 남김 | 022·041·044 |
