# ADR 051 — 평가 설계 독립성을 team-review Tests 관점에 편입

- **날짜**: 2026-08-26
- **변경 내용**: Paperthin `mandela`의 검증 독립성 개념을 새 자산 없이 `team-review`의 조건부 Tests 점검으로 이식한다.
- **대상**: `.agents/skills/team-review/SKILL.md`, `.agents/skills/README.ko.md`, 평가 독립성 계약 테스트
- **사유**: 현행 Tests 관점의 기준선 검토가 실행 증거 누락은 차단했으나 동일 model·rubric·curation recipe의 순환성은 차단 사유가 아니라고 판정했다.

## 결정

eval·metric·experiment·benchmark·scorer·holdout이 성공 근거인 대상에서만 reviewer가 model·scorer·designer·dataset 역할과 independent external ground truth를 확인한다. scorer가 자신이 만든 rubric을 채점하는 폐회로, validator와 designer의 recipe 공유, train/holdout의 labeler·curation 공유, hypothesis framing 누출을 대표 실패로 본다.

이 검사는 기존 Tests perspective 안에서 수행한다. 새 perspective·reviewer·fan-out·skill·agent·hook은 만들지 않는다. root §13-2와 Solo protocol의 재실행은 실행 결과의 독립성을 계속 담당하고, 이 결정은 성공 기준 설계의 독립성만 담당한다.

## 대안

| 대안 | 판정 | 이유 |
|---|---|---|
| Paperthin 전체 설치 | 기각 | description 고정 비용이 ADR 032 예산을 넘고 기존 라우팅과 충돌 |
| `mandela` 독립 스킬 신설 | 기각 | 조건부 Tests 점검으로 충분하며 새 라우팅·유지 비용 불필요 |
| 정적 hook으로 강제 | 기각 | 독립 ground truth 여부는 문맥적 설계 판단이라 안정적인 정적 술어가 없음 |
| 현행 유지 | 기각 | 기준선에서 평가 순환성을 verdict 근거로 올리지 못한 실패를 관측 |

## 결과

- 평가 설계를 포함하지 않는 리뷰의 절차와 호출 수는 변하지 않는다.
- 평가 설계를 포함하는 리뷰는 테스트 개수뿐 아니라 성공 판정의 외부 기준을 확인한다.
- 상세 채택·기각 근거와 재검토 조건은 `docs/proposals/2026-08-26-paperthin-review.md`, 실행 계약은 `docs/specs/2026-08-26-evaluation-independence-review.md`가 담당한다.
