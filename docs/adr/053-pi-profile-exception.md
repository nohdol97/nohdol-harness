# ADR 053 — Pi 세션의 사내 발행 제한 해제와 worktree 선택권

> **부분 대체(2026-11-25)**: "사용자 머지 유지"는 [ADR 064](064-session-merge-and-continuous-run.md)의 세션 머지 조건으로 대체됐다.

> **부분 대체(→063, 2026-11-24)**: [ADR 063](063-retire-autoloop.md)이 autoloop을 삭제해 이 ADR의 autoloop 관련 조항은 현재 규칙이 아니다. 그 밖의 결정은 유지한다.

> **부분 대체(→062, 2026-11-24)**: [ADR 062](062-corporate-dispatch-unblocked.md)가 사내 발행 차단 자체를 폐기해, 이 ADR의 「Pi 세션의 사내 발행 제한 해제」는 대상이 없어졌다. Pi 실행 방식과 worktree 선택권은 유지한다.

> 후속: [ADR 055](055-retire-corporate-pi-workers.md)가 ADR 054의 사내 호스트 위임 경로를 폐기하고 호스트 직접 수행을 복원했다. 네이티브 차단과 Pi 자체 세션 정책은 유지한다.

- 날짜: 2026-09-28
- 상태: 부분 대체(→062)
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

## 추가 (2026-11-24): 프로젝트 신뢰와 활성화 조건

Pi 1.6.0은 `.pi/APPEND_SYSTEM.md`·`.pi/skills`·프로젝트 `.agents/skills`를 프로젝트 신뢰 보호 자원으로 다룬다(Pi `docs/security.md`). print·JSON·RPC 모드는 신뢰 프롬프트를 띄울 수 없어, `--approve`·확장 결정·`~/.pi/agent/trust.json` 저장 결정·`defaultProjectTrust: "always"` 중 무엇도 없으면 이 자원을 조용히 건너뛴다. 그러면 이 ADR의 활성화 조건(`APPEND_SYSTEM.md`가 시스템 지침으로 로드됨)이 충족되지 않아 **Pi 예외가 꺼지고 하네스 스킬도 없다**. `AGENTS.md`·`CLAUDE.md`는 신뢰와 무관하게 로드된다.

- 관찰: 2026-11-24 사내 설치처의 Pi 세션(런처가 print/RPC 모드로 실행)에서 하네스 스킬 20개가 목록에 없었고, `pi -p` 재현 3회와 `--skill` 강제 지정 대조로 발견 단계 차단을 확인했다고 보고됐다. 이 개인 설치처에는 Pi가 설치돼 있지 않아 재현하지 않았고, 동작 근거는 npm `@earendil-works/pi-coding-agent@1.6.0` 문서로만 대조했다. 런처가 `--approve`를 넘기는지는 미확인이다.
- 결정: 활성화 조건은 바꾸지 않는다(파일 존재로 판정하지 않는다는 원칙 유지). 신뢰가 없어 꺼진 세션은 일반 정책을 따르고 그 사실을 보고한다(루트 §11). 신뢰 부여는 사용자의 로컬 권한 결정이므로 `harness-install` 3i가 안내만 한다.


## 추가 (2026-11-27): Pi 세션의 §8 교훈 보관소 로드

- 관찰: 루트 §8의 재발 방지 보관소(`~/.claude/projects/<루트 슬러그>/memory/MEMORY.md`와 노트)는 Claude Code만 스스로 로드한다. Pi 1.6.1에는 메모리나 교훈 보관소를 로드하는 기능이 없다(npm 패키지 `docs/configuration.md`·`how-pi-works.md` 대조). 2026-11-27 사내 설치처의 Pi 세션이 전날 저장된 교훈("spawn 수리 완료·실증됨")을 받지 못하고 틀린 전제에서 시작했다고 보고됐다.
- 결정: `.agents/hooks/memory-index.py`가 하네스 루트 경로로 슬러그를 계산해(대·소문자 영문과 숫자 밖의 문자를 모두 `-`로, Claude Code의 프로젝트 디렉터리 규칙) 인덱스 경로와 인덱스만 출력한다. 인덱스가 없으면 아무것도 출력하지 않고 종료 코드는 항상 0이다. `.pi/APPEND_SYSTEM.md`는 세션 시작 때 이것을 실행해, 트리거 상황이 맞는 노트만 열고 새 교훈은 같은 디렉터리에 파일 하나와 인덱스 한 줄로 쓰라고 지시한다. 노트 전체를 싣지 않는 것은 §8의 "검색 데이터베이스 금지"를 지키기 위해서다. Pi 확장(TypeScript)으로 자동 주입하는 안은 프로세스 안에서 코드를 실행하고 이 기기에서 실측할 수 없어 택하지 않았다.
- 한계: 이 지시는 `APPEND_SYSTEM.md`에 있으므로 프로젝트 신뢰가 없어 예외가 꺼진 Pi 세션(위 2026-11-24 절)에는 닿지 않는다. Claude·Codex의 로드 경로는 바꾸지 않았다. Windows 경로의 슬러그(`C:\Users\a\h` → `C--Users-a-h`)는 같은 규칙에서 도출한 값이라 실기에서는 확인하지 않았다. Claude Code가 아주 긴 경로를 줄이는 경우는 반영하지 않았으며, 그때는 인덱스를 찾지 못해 조용히 지나간다.
