# ADR 055 — 사내 내부 Pi 작업자 경로 폐기

- 날짜: 2026-10-07
- 상태: 활성
- 관련: [스펙](../specs/2026-10-07-retire-corporate-pi.md), ADR 042·046·053·054

## 맥락

사용자가 사내 내부 Pi 모델의 작업 품질에 대한 불만으로 위임 경로 제거를 요청했다. 품질 평가는 사용자 피드백이며 이 개인 설치처에서 사내 실행·모델 성능을 직접 확인하지 않았다. 제거 후 실행 방식은 기존 사내 네이티브 발행 제한을 유지하면서 호스트 직접 수행으로 복원한다.

## 결정

ADR 054의 강제 위임·설치 선행 조건·호스트 직접 구현 금지를 폐기한다. 사내 Claude/Codex 호스트가 수집·설계·구현·테스트·검토를 순차 수행한다. 내부 작업자 부재가 작업 차단 사유가 되지 않는다. 사용자의 사내 내부 에이전트 미사용 확인에 따라 선택적 위임·대체 경로도 제공하지 않는다.

네이티브 발행 차단과 infra 작성 예외는 유지한다. 호스트는 SDD/TDD와 새 검증 근거를 기록하고 별도 독립 reviewer 세션이 없었음을 명시한다. 사내 루트 수정·반출 제한과 worktree 규칙은 유지한다. 개인 설치처와 Pi 자체 세션의 위임·독립 리뷰 규칙은 바꾸지 않는다.

전용 실행기·테스트·비교 스크립트를 제거한다. 참조 문서와 런북에는 실행 명령 없는 폐기 안내만 남겨 오래된 링크가 다시 설치를 유도하지 않게 한다. 이전 ADR·스펙은 폐기 표시 후 이력으로 보존한다. CLI-JSONL 후속은 이 하네스 범위에서 종료한다. 설치별 설정·인증·로그는 삭제하지 않는다.

## 충돌 확인과 검증

루트 §7·§11·§13, CLAUDE 앵커, orchestrate의 구현 소유권·발행 예산·검증 면제, project-status·harness-review 수집, implementer 역할, branch-workflow, PR 생성 템플릿과 한국어 뷰를 함께 대조했다. `dispatch-gate`는 판정 분기 대신 차단 후 대체 절차 안내만 바꾼다. Pi 자체 세션과 사내 호스트의 내부 모델 위임은 별개 축이다.

변경 전 새 계약 테스트와 차단 안내 테스트가 실패하는 것을 확인한 뒤 수정했다. 새 계약 4개·기존 차단 14개·Pi 자체 세션 회귀 4개와 정합성 55개가 통과했고, 설치 파일 보존 해시가 일치했다. 독립 리뷰에서 발견한 잔여 위임 문구 3곳은 계약 재현 후 수정했으며 최종 리뷰는 모두 PASS였다. 지식 소스 진입점은 읽기 시간 초과로 사용하지 못했다. 정책 철회는 사용자 결정이며 효과를 증명하기 위한 사내 실측이나 임의 성능 수치를 만들지 않는다.

## 영향

- `.agents/agents/README.ko.md`
- `.agents/agents/implementer.md`
- `.agents/hooks/corporate-host-contract_test.py`
- `.agents/hooks/dispatch-gate.py`
- `.agents/hooks/dispatch-gate_test.py`
- `.agents/skills/README.ko.md`
- `.agents/skills/branch-workflow/SKILL.md`
- `.agents/skills/doc-writer/references/templates.md`
- `.agents/skills/harness-review/SKILL.md`
- `.agents/skills/metaskill/SKILL.md`
- `.agents/skills/metaskill/references/patterns.md`
- `.agents/skills/orchestrate/SKILL.md`
- `.agents/skills/orchestrate/references/corporate-pi.md`
- `.agents/skills/orchestrate/scripts/pi_workers.py`
- `.agents/skills/orchestrate/scripts/pi_workers_benchmark.py`
- `.agents/skills/orchestrate/scripts/pi_workers_test.py`
- `.agents/skills/project-status/SKILL.md`
- `.agents/skills/team-review/SKILL.md`
- `.agents/skills/tool-eval/SKILL.md`
- `AGENTS.ko.md`
- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `_workspace/harness-ops-log.md`
- `_workspace/retire-corporate-pi/`
- `docs/README.md`
- `docs/adr/042-corporate-profile-dispatch-block.md`
- `docs/adr/046-corporate-profile-dispatch-block-restored.md`
- `docs/adr/053-pi-profile-exception.md`
- `docs/adr/054-corporate-pi-workers.md`
- `docs/harness-changelog.md`
- `docs/runbooks/pi-worker-cli-setup.md`
- `docs/specs/2026-10-05-corporate-pi-workers.md`
- `docs/specs/2026-10-06-pi-worker-cli-compatibility.md`
- `docs/specs/2026-10-06-pi-worker-economy.md`
- `docs/specs/2026-10-06-pi-worker-recovery.md`
- `docs/specs/2026-10-07-retire-corporate-pi.md`

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-10-07 | 사내 Pi 위임 폐기·호스트 직접 수행 복원 | 영향 절의 경로 | 사용자 실행 정책 변경. 기존 안전·위임 제한과 Pi 자체 세션 지원 유지 |
