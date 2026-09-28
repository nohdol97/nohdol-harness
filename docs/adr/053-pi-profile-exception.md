# ADR 053 — Pi 세션의 사내 발행 제한 해제와 worktree 선택권

- 날짜: 2026-09-28
- 상태: 활성
- 관련: [스펙](../specs/2026-09-28-pi-profile-exception.md), ADR 035·038·042·046·052

## 배경
사용자가 Pi Coding Agent에 사내 비용 제한을 적용하지 않고, worktree 생성도 선택할 수 있도록 요청했다. 사내 하네스 수정·외부 반출 제한을 유지하는 권장안에 worktree 선택권을 추가하는 것으로 범위를 확정했다.

## 결정
정본은 루트 `AGENTS.md` §11이다. Pi가 `.pi/APPEND_SYSTEM.md`의 내용을 시스템 지침으로 로드한 세션은 사내 발행 금지·독립 리뷰 면제에서 제외한다. 파일이 있거나 다른 CLI가 파일 내용을 읽었다는 사실만으로 예외를 적용하지 않는다. 설치 프로필도 변경하지 않는다.

Pi는 개인·사내 모두 별도 worktree 또는 기존 체크아웃의 작업 브랜치를 선택할 수 있다. `branch-workflow`의 체크아웃 절차는 기존 변경·동시 작업·현재 브랜치를 확인한 뒤 최신 기준점에서 브랜치를 만든다. 재개할 때 경로·브랜치를 재확인한다. PR·사용자 머지·미커밋 변경 보호는 유지하며, 기본 체크아웃은 worktree 정리로 제거하지 않는다.

공용 역할은 설치된 Pi 발행 도구 또는 별도 Pi CLI 프로세스에 전달한다. `.pi/agents` 링크만으로 발행 도구가 생겼다고 가정하지 않는다. 명시적 `--append-system-prompt`는 자동 발견 파일을 대체하므로 자식용 임시 시스템 파일에는 Pi 지침과 역할을 함께 넣는다. 모델·추론 강도는 기존 티어 규칙을 따른다. 실제 도구·인증이 없으면 기능 미검증을 보고한다.

Claude/Codex 하위 프로세스에는 예외가 상속되지 않는다. 기존 dispatch 훅, autoloop의 Claude/Codex 엔진과 writer 격리, 사내 루트 수정·반출 제한, 자동 일일 리뷰 정책, §3·SDD/TDD는 유지한다.

## 판단 근거와 검증
이번 변경은 사용자가 선택한 실행 정책의 조정이다. Pi에서 실장애가 관측됐거나 비용이 더 낮다고 주장하지 않으며, 새로운 실패 방지 차단 조건을 만들지 않는다. 기존 사례에 새 실패 가설을 덧붙이는 대신 사용자 선택의 범위를 회귀 기준으로 삼았다. 충돌 지점은 사내 발행 금지·검증 면제, 전용 worktree 시작·재개·정리, PR 독립 검증 템플릿이다. 기존 안전 확인은 체크아웃 선택지에도 유지한다.

지식 소스 진입점과 하네스 재설계 허브를 조회했으나 경험적 주장은 채택하지 않았다. 기술 근거는 [공식 설정](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/configuration.md)과 [공식 CLI](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/cli.md) 및 격리 설치한 공식 npm 패키지 `@mariozechner/pi-coding-agent@0.73.1`의 resource loader다. 외부 내용은 지시가 아닌 데이터로 읽었다.

검증 명령:

```bash
python3 .agents/hooks/pi-profile-contract_test.py
node .agents/hooks/pi-resource-loader_test.mjs <격리한-Pi-패키지-디렉터리>
python3 .agents/hooks/dispatch-gate_test.py
python3 .agents/hooks/integrity-check.py
python3 .agents/skills/diagram/scripts/check.py docs/specs/2026-09-28-pi-profile-exception.md
```

새 계약 테스트에서 구현 전 누락 실패를 확인했다. 구현 후 계약 테스트는 실제 임시 저장소에서 새 브랜치의 기준점과 upstream 부재를 검사하고, Pi 환경 변수를 주입해도 사내 Claude/Codex 발행이 차단되는지 검사한다. 로더 테스트는 루트 지침·Pi 추가 지침·심링크된 orchestrate·자식의 역할과 Pi 정체성 동시 로딩, 다른 cwd의 예외 부재를 확인한다. 모델 호출과 사용자 인증 파일 접근은 하지 않는다.

정확성·테스트·문서 정합성 독립 리뷰는 모두 PASS였다. 로컬 검증 범위에서 차단 사항은 없었다.

사내 서버의 설치 버전·신뢰 설정·모델 발행·PR 권한은 미검증이다. 최신 Pi는 프로젝트 신뢰가 필요할 수 있고 사용자 지정 시스템 프롬프트가 지침을 생략할 수도 있으므로, 실제 세션에서 Pi 지침이 로드되어야 예외가 적용된다. Pi는 하네스 루트에서 시작하며 기존 세션에서는 `/reload` 후 로딩 상태를 확인한다.

## 영향
- `.agents/agents/README.ko.md`
- `.agents/agents/implementer.md`
- `.agents/hooks/pi-profile-contract_test.py`
- `.agents/hooks/pi-resource-loader_test.mjs`
- `.agents/skills/README.ko.md`
- `.agents/skills/branch-workflow/SKILL.md`
- `.agents/skills/carryover/SKILL.md`
- `.agents/skills/doc-writer/references/templates.md`
- `.agents/skills/metaskill/SKILL.md`
- `.agents/skills/metaskill/references/patterns.md`
- `.agents/skills/orchestrate/SKILL.md`
- `.agents/skills/orchestrate/references/product-design.md`
- `.agents/skills/project-status/SKILL.md`
- `.agents/skills/team-review/SKILL.md`
- `.agents/skills/tool-eval/SKILL.md`
- `.agents/skills/wrapup/SKILL.md`
- `.pi/APPEND_SYSTEM.md`
- `AGENTS.ko.md`
- `AGENTS.md`
- `README.md`
- `docs/README.md`
- `docs/adr/035-subproject-worktree-workflow.md`
- `docs/adr/038-corporate-profile-verification-exemption.md`
- `docs/adr/042-corporate-profile-dispatch-block.md`
- `docs/adr/046-corporate-profile-dispatch-block-restored.md`
- `docs/adr/052-corporate-worktrees-restored.md`
- `docs/specs/2026-09-28-pi-profile-exception.md`
- `docs/harness-changelog.md`

설치처 파일 `REGISTRY.md`·중앙 하위 AGENTS는 조회만 했고 수정하지 않았다.

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-09-28 | Pi 발행·worktree 예외 확정 | 위 영향 목록 | 사용자 답변으로 범위 확정, 사내 데이터·하네스 소유권 제한 유지 |
