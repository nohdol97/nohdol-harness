# Paperclip 연결

하네스 원본의 표준 역할과 스킬을 로컬 Paperclip 회사에 등록한다. 원본 `.agents/agents/`와 `.agents/skills/`는 그대로 두며, 생성 지침·설치 ID·모델 선택은 `_workspace/paperclip-sync/`에 둔다.

## 다시 동기화하기

하네스 루트에서 실행한다. 기존 설치의 설정 파일에는 회사·프로젝트·담당자 ID와 실제 모델 선택이 들어 있다. 인증 정보는 넣지 않는다.

```bash
python3 .agents/integrations/paperclip/sync.py --config _workspace/paperclip-sync/config.json
python3 .agents/integrations/paperclip/sync.py --config _workspace/paperclip-sync/config.json --apply
```

첫 명령은 읽기 전용 계획, 두 번째 명령은 적용이다. 서버는 `paperclipai service start`로 시작한다. 계획에서 같은 이름의 비관리 에이전트와 충돌하면 기존 객체를 덮어쓰지 않는다. 실행 중인 역할은 작업이 끝난 다음 동기화한다. 의미상 같은 에이전트 설정은 PATCH를 생략해 Paperclip의 불필요한 계정 재검사를 피한다. 동기화는 제품 업무를 만들거나 에이전트를 호출하지 않는다.

새 설치에서는 `--help`에 표시되는 회사·프로젝트·관리자 ID와 design/implement/explore 모델을 지정한다. 현재 CLI에서 실제 지원하는 모델을 고른다. 모델 이름을 공유 코드에 고정하지 않는다.

## 가져오는 것과 책임

- 표준 역할 7종을 기존 chief-of-staff 아래에 등록한다. 원본 역할 본문과 SHA-256, 설치 경로, `runtime.md` 연결 규칙이 생성 지침에 들어간다.
- 루트 스킬을 git 추적 파일만으로 준비한 뒤 스킬 디렉터리들을 담은 상위 디렉터리를 회사 라이브러리에 가져온다. 각 `SKILL.md`의 YAML 뒤에는 Paperclip 실행 계약 안내를 추가하고 원문 본문과 참조 파일은 보존한다. 원본 SHA-256은 원본의 출처를 나타내며 안내가 추가된 사본의 바이트 hash와는 구분한다. Paperclip 2026.1012.0의 개별 디렉터리 가져오기는 참조 inventory를, `SKILL.md` 파일 가져오기는 비표준 하위 디렉터리를 누락할 수 있어, 상위 디렉터리를 지정하고 모든 추적 파일의 inventory를 확인한다. 무관한 미추적 파일·자격 증명·의존성 디렉터리는 복사하지 않는다. 역할별로 필요한 스킬을 배정한다.
- `orchestrate`와 `autoloop`은 참조용 라이브러리에는 남지만 관리자·관리 역할의 실행 스킬 배정에서 제외한다. 이전에 배정된 이 설치의 두 스킬 키는 동기화 때 해제하며 다른 스킬은 보존한다. 기존 터미널의 두 스킬과 native dispatch 제한은 그대로다.
- 기존 관리자의 지침은 구분된 안내 블록만 추가한다. 기존 모델·권한·기타 설정은 유지한다.
- 신규 역할은 타이머를 끄고, 사용자 업무 배정이나 수동 실행을 기다린다.

## Paperclip에서 협업하는 방식

Paperclip은 이슈·담당자·실행·재시도를 관리한다. `orchestrate`의 CLI 팀 규모 판정이나 native worker 생성 절차를 또 실행할 필요는 없다. 관리자는 전용 `runtime.md`를 따라 작업을 분해하고 완료 기준·의존성·역할을 정하며, 작성자와 별도의 reviewer를 배정하고 통합 결과를 판단한다. Paperclip 설치나 역할 등록만으로 이 판단과 검토가 자동 보장되지는 않는다.

루트 §11의 Paperclip 예외는 실제 회사·에이전트·실행 문맥을 API로 확인하고 전용 계약을 읽은 실행에만 적용된다. 이 문맥에서는 사내 CLI의 “모든 작업 직접 수행”, “에이전트 호출 금지”, “독립 검토 면제”가 Paperclip 이슈 배정을 제한하지 않는다. 원본 역할·스킬에 남은 해당 문구보다 Paperclip 계약을 우선한다. 일반 CLI 규칙을 삭제하거나 사내 정책 전체를 없앤 것은 아니다. 데이터 반출·사내 루트 파일 수정 제한·승인·sandbox·누락 하네스 정지는 유지한다.

회사 라이브러리의 참조 사본이나 원본 파일이 존재해도 두 CLI 협업 스킬을 실행하라는 뜻은 아니다. 같은 Paperclip 작업의 native 서브에이전트·별도 autoloop 실행은 중복 작업을 만들므로 사용하지 않는다. 이 변경은 일시 정지된 에이전트를 재개하거나 외부 모델 호출을 허용하지 않는다.

## 로컬 레지스트리 반영

`REGISTRY.md`의 레지스트리 표를 제품 프로젝트와 로컬 workspace에 연결한다. 역할·스킬 동기화와 별도로 실행한다.

```bash
python3 .agents/integrations/paperclip/registry_sync.py --config _workspace/paperclip-sync/config.json
python3 .agents/integrations/paperclip/registry_sync.py --config _workspace/paperclip-sync/config.json --apply
```

이름·스택·역할·관계·이관 구분은 프로젝트 설명에, 원본 경로·중앙 규칙 경로·하네스 상태·검사 결과는 workspace의 `metadata.nohdolHarnessRegistry`에 담는다. 결과 ID는 `_workspace/paperclip-sync/registry-manifest.json`에 기록한다. `REGISTRY.md`와 중앙 규칙은 원본으로 유지하며 Git에 포함하지 않는다.

기본 실행은 읽기 전용 계획이다. 적용 전 모든 행의 소유권을 검사하고, 관리 표식 없는 동명 프로젝트와 충돌하면 쓰지 않는다. 다시 적용해도 ID를 유지하고 변경 없는 PATCH를 생략한다. 수동 설명과 무관한 metadata·정책은 보존하며, 원본에서 사라진 항목은 삭제하지 않고 `stale`로 보고한다.

준비된 저장소에는 격리 Git worktree 정책을 설정하되 worktree·업무·에이전트 실행은 만들지 않는다. 저장소나 선언된 중앙 규칙이 없으면 `blocked`로 기록하고 새 실행 workspace를 만들지 않는다. 기존 workspace가 나중에 막힌 경우에는 보존하므로 서버 차원의 실행 금지 장치는 아니다. 에이전트는 제품 작업 직전에 원본을 다시 읽고 루트 §7 정지 조건과 `branch-workflow`의 최신 기준점 확인을 적용해야 한다.

Paperclip 자체의 자동 격리는 인스턴스의 `experimental.enableIsolatedWorkspaces`도 필요하다. 현재 설치에서는 이 값이 꺼져 있고 이번 등록은 실험 기능을 변경하지 않는다. 자동 생성이 된다고 가정하지 말고 실제 전용 worktree를 마련해 실행 workspace에 연결한 뒤 작성자를 배정한다.

## 운영사 데이터 전송 비활성화

Paperclip 2026.1012.0 설치 코드에서 확인한 설정이다. `~/.paperclip/instances/default/config.json`에 `telemetry.enabled=false`, `updates.checkEnabled=false`를 적용한다. 서비스의 LaunchAgent 환경 변수와 instance `.env`에도 다음 값을 유지하고 서비스를 재시작한다.

```dotenv
PAPERCLIP_TELEMETRY_DISABLED=1
DO_NOT_TRACK=1
PAPERCLIP_UPDATE_CHECK=0
SENTRY_DSN=
SENTRY_DSN_FRONTEND=
SENTRY_DSN_BACKEND=
OTEL_SDK_DISABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_TRACES_EXPORTER=none
OTEL_METRICS_EXPORTER=none
OTEL_LOGS_EXPORTER=none
PAPERCLIP_FEEDBACK_EXPORT_BACKEND_URL=http://127.0.0.1:9
PAPERCLIP_TELEMETRY_BACKEND_URL=
```

일반 설정의 `feedbackDataSharingPreference`는 `not_allowed`로 둔다. **이 값만으로 피드백 API 전송을 차단하지는 않는다.** `feedback-share-client.js`는 URL이 비면 운영사 주소로 돌아가고, 대기·실패 export를 재시도한다. 별도 disable 옵션이 없어 사용하지 않는 로컬 포트 9를 대상으로 지정했다. 이 주소는 외부로 나가지 않지만 피드백 업로드는 실패하며 로컬 재시도 기록이 남을 수 있다. 업데이트 후에도 기본 주소로 되돌아가지 않는지 확인한다.

현재 설치는 loopback 서버·로컬 DB·로컬 파일 저장소와 로컬 백업을 사용하며 관리형 Cloud 설정은 없다. 기존 브라우저 탭은 새로고침해 frontend 오류 수집 설정도 갱신한다. 설정을 바꾸기 전 백업에는 비밀 값이 있을 수 있으므로 저장소나 `_workspace/`에 복사하지 않는다.

이 설정은 확인한 운영사 수집 경로를 비활성화하며 OS 방화벽은 아니다. OpenAI 구독 실행은 로컬 Paperclip → 로컬 Codex → OpenAI로 요청을 보내고 결과를 로컬 Paperclip에 저장한다. OpenAI 호출·사용자가 연결한 GitHub·REA 도구 등 작업 통신은 별개다. 모델 호출까지 중지하면 화면과 기록은 남지만 현재 AI 작업은 진행할 수 없다. 이 세션에서는 외부 작업 통신 범위가 확정될 때까지 기존 idle 에이전트를 잠시 pause했으며, 재개 여부는 사용자 선택을 따른다.

## 스펙을 맡기는 방법

Paperclip에서 해당 제품 프로젝트의 업무를 만들고 기존 chief-of-staff에게 배정한다. 스펙 경로와 완료 기준, 제품 저장소를 명시한다. 예:

> 이 스펙을 nohdol-harness 규칙으로 구현해줘. 완료 기준마다 작업과 검증 근거를 연결하고, 구현 작업에는 reviewer 검토 단계를 설정해줘. 제품 수정은 전용 worktree에서 진행하고, 통합 테스트와 최종 기준 검토 후 PR로 전달해줘. 막힌 항목은 이유와 필요한 결정을 보고해줘.

프로젝트별 로컬 규칙과 레지스트리가 준비돼 있어야 한다. 단순 역할 등록만으로 전 업무에 검토 정책이 자동 적용되지는 않는다. 관리자가 각 구현 이슈를 생성할 때 reviewer를 지정한 `executionPolicy`를 넣도록 `runtime.md`가 안내한다. 실제 이슈에 정책이 있는지 확인해야 한다. PR 머지·배포·DB migration은 기존 승인 경계를 따른다.

## 실행 권한과 한계

구현자·인프라 작성자는 Codex workspace-write, 수집·설계·검토·보고 역할은 read-only를 사용한다. 설치된 Codex가 named permission profiles와 `--ignore-user-config`를 지원해야 한다. `codex_readonly.py`와 `codex_workspace.py`는 Paperclip의 legacy sandbox 인자를 역할별 명명된 프로필로 바꾸고 결과 보고용 네트워크를 허용한다. 읽기 역할은 저장소 쓰기를 차단한다. 생성 실행 파일의 이름은 Paperclip 계정 검사와 호환되도록 `codex`이다. 실제 Codex CLI 경로는 생성 실행 파일에 고정하므로 API가 숨기는 환경 변수 값을 다시 쓸 필요가 없다. 이 프로필의 네트워크는 도메인 제한이 아니다. 불필요한 우회 권한은 부여하지 않는다.

읽기 역할의 보고서는 Paperclip 댓글·문서로 전달한다. 파일 생성이 필요한 테스트는 별도로 마련한 검증 환경에서 reviewer 또는 다른 비작성자가 해당 revision으로 독립 재실행해야 PASS할 수 있다. 구현자의 원시 결과만으로 대체할 수 없으며 독립 실행이 불가능하면 BLOCK으로 남긴다. `integrator`는 근거 통합 역할이며 코드 머지 담당이 아니다.

스킬 가져오기는 외부 도구 설치와 다르다. 특히 managed CODEX_HOME의 프로젝트 설정·훅 신뢰는 별도다. 두 래퍼는 전역 설정을 무시하므로 개인 MCP·플러그인 설정을 자동 상속하지 않는다. Paperclip이 표시한 managed MCP 블록의 HTTP gateway만 이어받으며 인증 값은 자식 프로세스 환경으로 전달한다. git hooksPath는 운영자 설정을 조회해 확인한다. 제품 스펙 전체의 무인 완료, 외부 연결 도구, 훅 전체의 Paperclip 실행 경로는 별도 검증 대상이다.

## REA 연결

사용자 요청으로 REA 6.4.0도 이 설치의 Paperclip에 연결했다. 패키지는 `~/.paperclip/tools/rea/`에 고정 버전으로 설치하며 개인 Codex 설정을 바꾸는 setup 명령은 사용하지 않는다.

```bash
npm install --prefix ~/.paperclip/tools/rea --save-exact rea-agents@6.4.0
```

Paperclip의 승인된 `local_stdio` 명령 템플릿이 절대 Node 경로와 패키지의 `scripts/rea.mjs mcp`를 실행한다. 실제 MCP `tools/list`에서 받은 도구 스키마를 템플릿에 등록하고, `REA local` 연결과 맞는 버전의 `reverse-engineer-anything` 스킬을 가져온다. 연결 ID·패키지 위치·스킬 키는 `_workspace/paperclip-sync/rea-connection.json`에 있다. REA는 하네스 자체 스킬이 아니므로 `sync.py`가 버전을 올리거나 원본에 복제하지 않는다.

전체 REA 연결은 기존 관리자와 implementer에 배정한다. 탐색·검토 등 읽기 역할에는 외부 프로세스 실행·파일 추출 도구를 자동 노출하지 않는다. REA MCP는 Codex 파일 sandbox 밖의 별도 프로세스이므로 그 sandbox가 MCP 동작까지 막는다고 주장할 수 없다. 기존 승인 경계와 REA 스킬의 대상 실행 조건은 유지한다.

REA로 확인할 대상의 경로와 조사할 기능을 관리자에게 주면 된다. 예: “이 Electron 앱의 설정 저장 방식을 REA로 분석하고 근거와 한계를 정리해줘.” 실제 앱 대신 작은 자체 JavaScript fixture로 연결과 정적 분석을 확인했다. 네이티브 바이너리 분석에는 별도 Hopper/Ghidra/IDA 등의 사용 가능한 엔진이 필요하며 이 설치에서 추가 엔진을 설치하거나 검증하지 않았다.

## 검증

```bash
python3 .agents/integrations/paperclip/sync_test.py
python3 .agents/integrations/paperclip/registry_sync_test.py
python3 .agents/integrations/paperclip/codex_readonly_test.py
python3 .agents/hooks/integrity-check.py
```

공식 인터페이스: [Paperclip 스킬](https://docs.paperclip.ing/reference/skills/), [에이전트 CLI](https://docs.paperclip.ing/reference/cli/agent/), [검토 정책](https://docs.paperclip.ing/guides/power/execution-policy/), [Codex 권한 설정](https://learn.chatgpt.com/docs/config-file/config-reference).
