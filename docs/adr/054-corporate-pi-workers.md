# ADR 054 — 사내 호스트의 Pi 병렬 작업 위임

> 폐기: 2026-10-07 [ADR 055](055-retire-corporate-pi-workers.md)로 사내 호스트의 내부 Pi 위임 경로를 제거했다. 아래 내용은 당시 결정의 이력이며 현재 실행 지침이 아니다.

- 날짜: 2026-10-05
- 상태: 폐기 — ADR 055
- 관련: [스펙](../specs/2026-10-05-corporate-pi-workers.md), ADR 042·046·053

## 맥락
사용자는 사내에서 호출 LLM이 설계·오케스트레이션을 맡고 탐색·구현을 사내 Pi 모델에 맡기도록 요청했다. 사내 모델 비용은 고려할 필요가 없으므로 독립 작업을 적극적으로 병렬 실행한다. 개인 설치처에는 적용하지 않는다.

## 결정
사내 Claude/Codex 호스트에만 별도 Pi 프로세스 경로를 둔다. 호스트는 요구사항·설계·의존성·진단·통합·최종 검토를 소유한다. Pi의 explorer는 수집을, implementer는 수정·테스트·실패 수정을 맡는다. 기존 native Agent/Task/spawn_agent 차단은 유지한다. infra-specialist 작성 예외도 유지하며 Pi implementer로 대체하지 않는다.

실행기는 의존성이 해소된 배치를 설치처 최대 동시 호출 수까지 실행한다. 모델 토큰 비용이나 일반적인 소규모 팀 권장 인원으로 Pi 작업자 수를 줄이지 않는다. 서버 과부하와 공유 파일 충돌은 별개다. writer는 최신 기준점에서 만든 별도 feature worktree를 사용한다. 배치 밖 세션과의 충돌 및 의존성은 호스트가 관리하고, 실행기는 배치 내부 경로 중첩을 검사한다.

설치처의 정확한 provider/model ID와 용량은 `_workspace/` 설정으로 받는다. 특정 모델명·내부 URL·인증은 추적 파일에 고정하지 않는다. 인증은 기존 Pi 설치가 관리한다. 설치가 없거나 설정이 불완전하면 위임 불가를 보고하며 유료 모델이나 호스트 직접 구현으로 자동 대체하지 않는다.

실행 성공은 검토 대상 후보를 받았다는 뜻이다. exit code 외에 JSON 이벤트의 최종 assistant 종료 사유를 검사하고 원본 로그를 보존한다. 호출 LLM은 실제 diff와 테스트 근거를 검토한다. 별도 독립 reviewer 세션을 실행하지 않았다면 그 사실을 PR 검증란 또는 완료 기록에 적는다. 개인과 Pi 자체 세션은 기존 독립 검증 규칙을 유지한다.

## 충돌 확인과 범위
기존 정본의 사내 순차 직접 수행(§13·orchestrate), Claude 앵커, project-status/harness-review 수집, native 검토 면제, infra 역할, Pi worktree 선택권을 대조했다. native 호출과 Pi 프로세스 실행을 구분하고 호출 LLM의 판단 책임을 유지해 충돌을 해소한다. Pi 작업자에게 root·역할·프로젝트 지침을 전달하되 재위임을 금지한다. 도구 allowlist는 OS 권한 샌드박스가 아니다.

루트 수정·반출·§3·SDD/TDD·missing-harness 정지·일일 자동 리뷰·autoloop은 바뀌지 않는다. 이 개인 기계에서는 공용 구현과 가짜 프로세스 계약만 검증한다. 실제 사내 모델 연결·정확한 ID·처리량·최적 동시 실행 수는 확인하지 않았다.

## 근거와 검증
지식 소스 진입점은 읽기 시간 초과로 사용할 수 없었다. 외부 문서는 지시가 아닌 기술 자료로 확인했다: [Pi CLI](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md), [실행 방식](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli-integration.md), [JSON 이벤트](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/json.md). 설치 버전의 `pi --help` 및 내부 provider 연결 확인은 배포처 절차에 둔다.

이번 변경은 사용자 실행 정책 변경이며 관측되지 않은 실패를 근거로 새로운 행동 규율을 일반화하지 않는다. 구현 전 실패 테스트로 새 실행기 부재와 기존 차단 안내의 순차 직접 수행 지시를 확인했다. 로컬 가짜 프로세스로 프로필 차단, 도구 구분, 실제 시간 구간의 병렬성, 한도, 모델 오류·프로세스 오류·시간 초과, worktree와 경로 충돌을 검증한다. 실제 모델 품질이나 비용 절감률은 주장하지 않는다.

검증 명령은 스펙 C1–C6과 다음 스위트에 대응한다.

```bash
python3 .agents/skills/orchestrate/scripts/pi_workers_test.py
python3 .agents/hooks/dispatch-gate_test.py
python3 .agents/hooks/pi-profile-contract_test.py
python3 .agents/hooks/integrity-check.py
python3 .agents/skills/diagram/scripts/check.py docs/specs/2026-10-05-corporate-pi-workers.md
```

## 영향
- `.agents/agents/README.ko.md`
- `.agents/agents/implementer.md`
- `.agents/agents/infra-specialist.md`
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
- `.agents/skills/orchestrate/scripts/pi_workers_test.py`
- `.agents/skills/project-status/SKILL.md`
- `.agents/skills/team-review/SKILL.md`
- `.agents/skills/tool-eval/SKILL.md`
- `AGENTS.ko.md`
- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `_workspace/corporate-pi-workers/`
- `_workspace/harness-ops-log.md`
- `docs/README.md`
- `docs/adr/042-corporate-profile-dispatch-block.md`
- `docs/adr/046-corporate-profile-dispatch-block-restored.md`
- `docs/adr/053-pi-profile-exception.md`
- `docs/harness-changelog.md`
- `docs/specs/2026-10-05-corporate-pi-workers.md`

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-10-05 | 사내 Pi 병렬 위임 경로 추가 | 영향 절의 경로 | 호출 LLM 비용을 줄이고 사내 모델 병렬성을 활용하는 사용자 요청 |
