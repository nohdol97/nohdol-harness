# ADR 020 — 인프라 도메인 리뷰 특화 (team-review 인프라 관점을 infra-specialist가 리뷰 모드로)

- **날짜**: 2026-07-16
- **변경 내용**: team-review의 리뷰 특화 축을 **관점(concern) 하나에서 관점 + 인프라 도메인 둘로** 확장한다. 대상에 k8s·AWS·매니페스트·IaC 변경이 포함되면 **정확성·보안 관점 중 인프라 해당분을 `infra-specialist`가 리뷰 모드(읽기 전용·Edit 금지·design 티어·비작성자 한정)로 맡고**, 인프라 리뷰 체크리스트(리소스 상한/admission·rollout/PDB·시크릿 참조·스코프 명시·롤백)를 그 관점 프롬프트에 포함한다. **웹·앱·백엔드 등 다른 도메인 리뷰어는 신설하지 않는다**(관점 팬아웃 + 대상 AGENTS.md로 충분 — 16절 최소주의).
- **대상**: `.agents/skills/team-review/SKILL.md`(팀 모드 인프라 특화 규약·체크리스트), `.agents/agents/infra-specialist.md`(1절 ④·10절 티어 정합)
- **사유**: 사용자 관찰(2026-07-16 — "구현 방향별로 reviewer도 특화할 필요 없나"). 하네스는 **구현(build)** 을 도메인으로 특화했지만(implementer + 유일 도메인 특화 `infra-specialist`) **리뷰(review)** 는 관점(정확성·보안·테스트·규약·성능·단순성·UX)으로만 특화하고 도메인으로는 generic reviewer 하나였다 — 비대칭. generic reviewer는 대상 AGENTS.md를 읽어도 네임스페이스 리소스 상한·admission control 같은 **운영 지식**은 못 본다. 실패 증거: 직전 라운드(ADR 019 이후 병합 PR)의 k8s 매니페스트 리뷰 갭 — 상한 미확인 값이 `apply`가 아니라 pod·PVC **생성 시점**에 FailedCreate로 터졌다(infra-specialist 2절 pre-flight가 build 쪽에서 푼 것과 같은 종류의 갭이 review 쪽에 남아 있었다).

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| 인프라만 도메인 특화 (채택) | 대상에 인프라 변경 포함 시 인프라 관점을 `infra-specialist`가 리뷰 모드로 담당 | build 쪽 유일 도메인 특화(infra-specialist)와 대칭. 인프라는 환원 불가능한 운영 지식이 있어 관점 팬아웃 + 문서만으로 안 메워짐 — build에서 infra-specialist를 둔 이유와 동일 논리가 review에도 성립 |
| 리뷰 모드 = 읽기 전용·design 티어 | Edit 금지(검증자로 배치 — reviewer 원칙), design 티어 호출(검증 false negative 방어 — 루트 9절) | infra-specialist는 tools에 Edit 보유·tier: implement이므로, 리뷰 역할일 때는 프롬프트로 Edit 금지 + Agent 호출 시 model을 design 티어로 지정한다(team-review 리뷰어 티어 규칙과 동일) |
| 독립성 예외 | orchestrate 빌드에서 그 매니페스트를 infra-specialist가 작성했으면 이 배치를 안 쓰고 generic reviewer가 인프라 체크리스트로 검증 | 자기 작성물 자기 검증은 생성-검증 독립성 붕괴(reviewer 1절). 외부 diff·PR 리뷰(team-review 표준 진입)는 비작성자라 항상 배치 가능 |
| 웹·앱·백엔드 도메인 리뷰어 기각 | 도메인별 리뷰어를 늘리지 않는다 | 16절 최소주의·YAGNI. 그쪽은 관점 팬아웃 + 대상 프로젝트 AGENTS.md로 갭 증거가 없고, 도메인 리뷰어는 관점 축과 곱해져 에이전트가 폭발한다. 인프라만 실패 증거·환원 불가 지식이 있어 특화 |
| 새 에이전트 0개 | 기존 infra-specialist를 리뷰 관점에 재사용(agentType 지정), 체크리스트는 프롬프트 규약 | team-review가 이미 관점별로 reviewer를 재사용하는 패턴의 연장. 인프라 검증 지식은 대부분 **기준(체크리스트)** 문제라 프롬프트 규약으로 흡수 가능 — 16절 사다리 2(재사용) |

## 검증

- **단일 원본**: 인프라 특화 규약·체크리스트는 team-review SKILL.md 팀 모드에만, infra-specialist 1절 ④·10절은 그 규약을 참조(중복 아님 — 티어·역할 정합).
- **정합**: infra-specialist 2절 admission pre-flight(build 쪽 상한 선확인)와 체크리스트 ①이 같은 기준을 review 쪽에서 재확인 — 생성·검증 양쪽에서 같은 갭을 막는다.
- **경계**: Phase 0에서 인프라는 위험도 높음 → 항상 팀 모드로 승격되므로 단독 모드에 인프라 경로가 생기지 않는다.
