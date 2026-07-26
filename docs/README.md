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
| [025](adr/025-autoloop-driver.md) | 2026-07-19 | 활성 | autoloop — 세션 외부 드라이버 기반 자율 멀티세션 루프 (게이트 3종·불변 앵커) |
| [026](adr/026-oh-my-openagent-adoption.md) | 2026-07-19 | 활성 | oh-my-openagent 검증·운영 착안 5건 이식 + integrity-check 무결성 점검 훅 |
| [027](adr/027-codex-agent-adapters.md) | 2026-07-19 | 활성 | Codex custom-agent 얇은 어댑터 (`.agents/agents` 원본 → `.codex/agents` 로더 계층) |
| [028](adr/028-gate-reminder-hook.md) | 2026-07-22 | 활성 | gate-reminder 훅 — 진단→구현 전환점 orchestrate 게이트 상기의 실행 계층 승격 (세션당 1회 차단) |
| [029](adr/029-codex-hook-parity-default.md) | 2026-07-22 | 부분 대체(→031) | 세션 훅 Codex 파리티 기본값 (인라인 등록·실측 계약은 031, 파리티와 fail-open은 유효) |
| [030](adr/030-english-harness-assets.md) | 2026-07-22 | 활성 | 모델-로드 하네스 자산 영어 단일 원본 전환 (§15 개정, 한글 뷰 3종 + 드리프트 가드, ADR·스펙·changelog는 한글 유지) |
| [031](adr/031-codex-runtime-contract.md) | 2026-07-25 | 활성 | Codex 런타임 계약 실측 정렬 (32KiB 방어, 인라인 훅, trust, custom-agent 발행 확인) |
| [032](adr/032-token-efficient-orchestration.md) | 2026-07-25 | 활성 | 토큰 효율형 오케스트레이션 (호출 예산·델타 재사용·세션 경계·상시 노출 예산) |
| [033](adr/033-knowledge-source-routing.md) | 2026-07-26 | 활성 | 지식 소스를 설계 단계 라우팅에 편입 (§7 8항, REGISTRY 기록 시에만 발동·임의 경로·요약은 증거 아님·fail-open) |

**대체 체인**: tdd-gate는 008(Claude Code 한정 PreToolUse) → 014(git 계층 추가, 도구 무관) → 015(git 계층 단일화, PreToolUse 제거)로 진화했고, 예외 경로의 `dev/` 항목은 024로 제거됐다. 008·014의 나머지 결정(차단 지점·fail-open·나머지 예외·commit-msg 선택·전역 hooksPath 등)은 유효하다. Codex 훅은 019(SessionStart 병행) → 029(파리티 기본값) → 031(인라인 설정·trust·실측 계약)로 정렬됐다. 그 밖의 부분 대체: 티어 모델명·REGISTRY.md 추적은 001·004 → 005(탈모델명·미추적), CLAUDE.md 산문 포인터·변경 이력 위치는 001 → 021(`@AGENTS.md` 임포트·changelog 분리), 공용 Markdown agent를 Codex가 직접 읽는 가정은 001 → 027(역할 원본 유지+TOML 어댑터), `project/`·`dev/` 미추적은 002 → 024(`dev/` 제거).

## 스펙 (SDD — 루트 자체 코드) — `docs/specs/`

루트 하네스가 추적하는 코드(훅 등)의 스펙. 하위 프로젝트 스펙은 각 프로젝트 저장소 `docs/specs/`에 있다(13절 — 여기 없음).

| 스펙 | 상태 | 대상 코드 | 관련 ADR |
|---|---|---|---|
| [2026-07-13-tdd-gate-hook](specs/2026-07-13-tdd-gate-hook.md) | 구현됨 | `.agents/githooks/tdd-gate.py` | 008·014·015 |
| [2026-07-14-agentsview-daemon-hook](specs/2026-07-14-agentsview-daemon-hook.md) | 구현됨 | `.agents/hooks/agentsview-daemon.py` | — |
| [2026-07-14-harness-review-reminder-hook](specs/2026-07-14-harness-review-reminder-hook.md) | 구현됨 | `.agents/hooks/harness-review-reminder.py` | 013·019 |
| [2026-07-15-hooks-common-bootstrap](specs/2026-07-15-hooks-common-bootstrap.md) | 구현됨 | `.agents/hooks/_common.py` | — |
| [2026-07-16-worklog-reminder-hook](specs/2026-07-16-worklog-reminder-hook.md) | 구현됨 | `.agents/hooks/worklog-reminder.py` | 018·019 |
| [2026-07-18-secret-gate-hook](specs/2026-07-18-secret-gate-hook.md) | 구현됨 | `.agents/githooks/secret-gate.py` | 023 |
| [2026-07-19-autoloop-driver](specs/2026-07-19-autoloop-driver.md) | 구현됨 | `.agents/skills/autoloop/scripts/driver.py` | 025 |
| [2026-07-19-integrity-check-script](specs/2026-07-19-integrity-check-script.md) | 구현됨 | `.agents/hooks/integrity-check.py` | — (제안: 2026-07-19-oh-my-openagent-adoption) |
| [2026-07-19-codex-agent-adapters](specs/2026-07-19-codex-agent-adapters.md) | 구현·실발행 확인 | `.codex/agents/*.toml` | 027·031 |
| [2026-07-22-gate-reminder-hook](specs/2026-07-22-gate-reminder-hook.md) | 구현됨 | `.agents/hooks/gate-reminder.py` | 028 |
| [2026-07-25-codex-runtime-compatibility](specs/2026-07-25-codex-runtime-compatibility.md) | 구현됨 | `AGENTS.md`, `.codex/`, `.agents/hooks/integrity-check.py` | 019·027·029·031 |
| [2026-07-25-token-efficiency-contract](specs/2026-07-25-token-efficiency-contract.md) | 구현됨 | `CLAUDE.md`, `.agents/skills/`, `.agents/agents/`, `.agents/hooks/integrity-check.py` | 032 |

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
| [2026-07-26-harness-tool-candidates-review](proposals/2026-07-26-harness-tool-candidates-review.md) | 전건 미채택(3 기각·1 연기) | 도구 후보 4건(이슈 #41 B) tool-eval. B-1 VHK 기각 — **`vhk sync`가 AGENTS.md를 자동 생성물로 덮어쓰고(`sync.ts:512`) `core.hooksPath`를 점유해 tdd-gate·secret-gate를 무력화**, 소스에서 확인(README 미기재). B-2 DeerFlow·B-4 OpenHarness 기각 — 범주 불일치(독립 런타임·Claude Code Python 포트), Hermes 선례 동일. B-3 Impeccable 연기 — 프론트엔드 전용이 원문으로 확인됐고 등록 프로젝트 0건이라 대상 부재(재평가 시 `impeccable.style` 텔레메트리·`settings.local.json` 훅 설치 확인 필요). 일반화 후보: 외부 도구가 AGENTS.md·CLAUDE.md·`.agents/`·`core.hooksPath`를 쓰기 대상으로 삼으면 기능 평가 이전에 구조 침해로 기각 |
