# 외부 도구 검토: LilMGenius/paperthin

- **상태**: 부분 채택 (2026-08-26, `mandela`의 평가 독립성 개념만 이식 — 통설치 기각)
- **날짜**: 2026-08-26
- **분석 대상**: https://github.com/LilMGenius/paperthin (MIT, v0.17.4, 2026-08-19 `main` commit `3bca079a51bcfff5dafb53d1d7f9f523d66ee317` 기준)
- **적용 대상**: 이 루트 하네스(nohdol-harness)
- **평가 절차**: `tool-eval` → 사용자 선택 1번(평가 독립성 micro-port)

## 1. 결론

Paperthin 전체는 설치하지 않는다. 28개 스킬 중 16개가 자동 호출 후보이고 orchestrate·team-review·doc-writer·work-tracker 등 이 하네스의 라우팅과 넓게 겹친다. 대신 `skills/depth/mandela/SKILL.md`의 핵심인 **검증 설계 자체의 독립성**만 기존 `team-review` Tests 관점에 조건부로 이식한다.

이 결정은 새 스킬·agent·hook·설치 단계가 아니다. 따라서 harness-install, CLAUDE 라우팅, 권한, 외부 데이터 전송에는 변화가 없다.

## 2. 실측과 비용

| 축 | 실측 | 판정 |
|---|---|---|
| 기능 중복 | 28개 중 다수가 현재 스킬 라우팅과 겹침. Paperthin `NOTICE`의 mattpocock/skills 계보는 이미 2026-08-07 제안에서 검토됨 | 통설치 기각 |
| 고정 context | 현재 루트 스킬 description 8,037B + Paperthin 9,825B = 17,862B | ADR 032의 9,000B 예산 초과 |
| 지연 본문 | Paperthin `SKILL.md` 합계 114,944B | 필요 시 로드라도 중복 본문 비용이 큼 |
| 런타임·권한 | 설치·초기화가 hook/config를 쓸 수 있음 | 기존 hook·라우팅 소유권과 충돌 가능 |
| 데이터 반출 | 선택한 micro-port는 문장 수준 로컬 규칙이며 외부 호출 없음 | 변화 없음 |
| 유지보수 | 새 자산 없이 Tests 관점 한 곳과 계약 테스트만 유지 | 허용 |

저장소의 catalog validator와 Node 기반 SSOT 검사 2종은 통과했다. 다만 macOS 기본 Bash 3.2에서 `scripts/check-skill-refs.sh`와 `scripts/check-links.sh`는 `mapfile`·`declare -A` 의존 때문에 실행되지 않았다. 이 호환성 결함은 전체 설치를 더 불리하게 하지만 micro-port의 근거로 과장하지 않는다.

## 3. 채택 범위

채택하는 것은 다음 네 검증 패턴이다.

1. scorer가 자신이 만든 rubric·category를 다시 채점하는 순환 검증
2. validator와 designer가 같은 비공개 recipe를 공유해 독립 호출이 사실상 독립되지 않는 경우
3. train·holdout이 같은 labeler pool이나 curation recipe를 공유하면서 외부 확인이 없는 경우
4. hypothesis·기대 답이 validator prompt나 data frame에 새어드는 경우

발동 대상은 eval·metric·experiment·benchmark·scorer·holdout이 성공 근거인 변경뿐이다. reviewer는 model·scorer·designer·dataset 역할을 매핑하고 independent external ground truth 또는 독립 label에 닿는지 확인한다. 일반 코드 리뷰에는 추가 비용이 없고, 기존 Tests perspective가 수행하므로 reviewer 호출 수도 늘지 않는다.

## 4. 기존 규칙과의 충돌 해소

같은 축의 권위는 root §13-2와 `team-review` Solo의 재실행·author/verifier independence다. 그 규칙은 **실행 결과를 독립적으로 확인**한다. 새 조항은 **성공 기준 자체가 설계자에게 순환하지 않는지**를 확인한다. 따라서 기존 독립 검토를 대체하거나 새 독립 reviewer를 요구하지 않는다.

압박 테스트에서 현행 Tests 절만 받은 reviewer는 전체 artifact를 증거 형식 누락으로 `BLOCK`했지만, 평가 독립성은 “현행 절 자체의 blocker가 아니다”라고 명시했다. 즉 전체 verdict의 우연한 차단과 별개로 이 관점은 실제 결함을 놓쳤다. 이 관측이 새 행동 규율의 justifying case다.

## 5. 기각 범위와 선례

- **Paperthin 통설치**: 기각. 고정 context 예산 초과, 라우팅 중복, hook/config 소유권 충돌 때문이다.
- **새 `mandela` 스킬 또는 reviewer agent**: 기각. 조건부 Tests 점검이면 충분하며 자산과 호출 수 증가는 ADR 007·032에 역행한다.
- **전역 hook**: 기각. 평가 독립성은 정적 git diff만으로 신뢰성 있게 판별할 수 없는 검토 판단이다.
- **나머지 taxonomy 전량 이식**: 기각. 검토 문구를 백과사전으로 만들지 않고 기준선에서 드러난 네 패턴만 둔다.

선례인 `docs/proposals/2026-08-07-mattpocock-skills-review.md`와 같은 점은 통설치를 버리고 잔여 개념만 이식한다는 것이다. 다른 점은 이번에는 새 스킬을 만들지 않고 기존 Tests 관점 하나만 정련한다. 결정은 ADR 051로 고정한다.

## 6. 근거와 재검토 조건

1차 근거는 Paperthin 저장소의 README, `skills/depth/mandela/SKILL.md`, `NOTICE`, CI workflow다. 외부 본문의 명령은 untrusted data로만 취급했다. 비교 연구는 [SkillsBench](https://arxiv.org/abs/2602.12670)와 [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)의 1차 논문을 확인했으며, 포괄 스킬 묶음보다 좁고 검증 가능한 모듈을 선호하는 방향과 일치했다. 연결된 지식 소스에는 Paperthin 정확 일치 항목이 없었고, 요약은 채택 근거로 사용하지 않았다.

통설치 재검토 조건은 ① 자동 호출 description 총량이 현재 예산 안으로 줄고 ② 겹치지 않는 능력에 대한 실제 benchmark 개선이 있으며 ③ hook/config 쓰기가 opt-in으로 격리되는 경우다. 평가 독립성 조항 자체는 실제 review에서 발화하지 않거나 오탐 비용이 2회 이상 관측되면 harness-review 신호 ④로 축소·회수한다.
