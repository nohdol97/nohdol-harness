# ADR 057: Paperclip 역할·스킬 동기화

- 날짜: 2026-10-14
- 상태: 활성

## 배경
사용자가 큰 개발 스펙의 구현·검토를 Paperclip에서 관리하기 위해 기존 하네스의 스킬과 표준 역할을 복제·연결하도록 요청했다. 기존 autoloop 실행기 하나만 보이는 구조 대신 역할별 작업을 Paperclip에서 볼 수 있도록 한다.

## 결정
원본 역할·스킬은 하네스에 유지한다. `.agents/integrations/paperclip/`에서 로컬 원본을 읽어 회사 스킬과 역할별 지침으로 동기화한다. 설치 ID·모델·절대 경로와 생성물은 `_workspace/paperclip-sync/`에만 둔다. 원본 역할 수를 늘리거나 CLI의 기존 동작을 바꾸지 않는다.

Paperclip 실행에서는 티켓·담당자·의존성·검토 라우팅이 협업 수단이다. 원본의 TaskCreate·SendMessage·native dispatch와 로컬 보고서 경로를 이 수단으로 연결한다. 원본의 품질·SDD/TDD·독립 검토·승인 규칙은 보존한다. 같은 작업 트리를 autoloop과 동시에 스케줄링하지 않는다. 관리자에게 제공하는 명시적 실행 계약이며, 문서 자체가 권한 강제 장치라는 주장은 하지 않는다.

신규 에이전트의 주기 실행은 비활성화한다. 기존 관리자 지침에는 구분된 연결 안내만 추가한다. 설치는 제품 업무를 생성하거나 실행하지 않는다. 검토 정책은 이슈 단위로 설정하며, 등록 자체를 전역 검토 강제로 표현하지 않는다.

## 실행 근거와 제약
Paperclip 2026.1012.0의 설치 코드에서 에이전트 생성·스킬 가져오기·지침 경로·검토 정책 API를 확인했다. 기존 회사에는 관리자와 하네스 프로젝트가 있으나 프로젝트 workspace의 cwd가 없어 로컬 스킬 가져오기의 허용 루트 설정이 필요했다.

Codex 0.155.1의 named permission profile로 읽기 역할의 네트워크 보고와 쓰기 차단을 분리했다. 해당 프로필에서 Paperclip health 요청은 성공하고 저장소 내 sentinel 파일 생성은 거부됐다. Paperclip 어댑터의 legacy sandbox 인자와 새 profile 설정을 동시에 넘길 수 없어 읽기·작성 역할별 래퍼로 인자를 변환한다. 관리형 연결은 extraArgs의 config override를 거부하므로 프로필은 래퍼에서 주입한다. 실행 파일명은 계정 hello 검사가 요구하는 `codex`로 생성한다. 전역 사용자 설정을 무시하며, 인증은 Paperclip이 제공하는 CODEX_HOME에서 읽는다. 개인 MCP·플러그인과 프로젝트 훅 신뢰는 자동 이식 대상으로 주장하지 않는다. Paperclip이 생성한 managed MCP 블록의 HTTP gateway만 보존하며, 인증 값은 자식 프로세스 환경으로 전달한다. REA의 별도 서버 프로세스는 Codex 파일 sandbox 밖에 있으며 전체 연결은 관리자·implementer에만 배정한다.

지식 소스 index는 로컬 읽기 오류로 사용하지 못했다. 로컬 구현과 공식 제품 문서를 근거로 삼았다. 기존 원본의 역할 제한과 연결 계약을 대조했으며 integrator의 책임은 코드 머지가 아니라 근거 통합으로 유지했다.

실제 재적용에서 Paperclip의 계정 binding 비교가 객체 키 순서에 의존해 변경 없는 PATCH에도 hello를 다시 실행하는 동작을 확인했다(`routes/agents.js`의 `JSON.stringify` 비교와 binding schema 순서 대조). 따라서 의미상 같은 에이전트 설정에는 PATCH를 생략한다. 실제 모델 호출에서는 목록에 노출된 모델 하나가 계정에서 거부돼, 읽기·작성 경로에서 각각 hello가 통과한 모델을 설치 설정에 기록했다. 특정 모델 이름을 공유 코드에 고정하지 않는다.

## 대안
- 독립 사본 수동 유지: 원본 변경과 충돌하므로 제외.
- 모든 역할을 기존 autoloop 하나로 숨김: 역할별 관리라는 사용자 선택과 맞지 않아 제외.
- Paperclip와 autoloop 동시 배정: 같은 작업의 소유자와 재시도 상태가 중복돼 기본 연결에서 제외.

## 검증·운영
회귀 테스트, 로컬 API 등록·재적용, 실행 환경 hello test, 별도 독립 검토로 확인한다. 제품 스펙을 실제로 완료한 E2E 검증과 모든 hook의 실행 증거는 이번 설치 검증에 포함하지 않는다. 사용법은 `.agents/integrations/paperclip/README.md`, 완료 기준은 `docs/specs/2026-10-14-paperclip-harness-sync.md`에 둔다.

## 변경 이력
| 날짜 | 변경 | 대상 | 사유 |
|---|---|---|---|
| 2026-10-14 | 역할·스킬의 원본 기반 동기화와 Paperclip 실행 계약 | `.agents/integrations/paperclip/` | 사용자 도입 요청, 기존 원본·개인 CLI 동작 보존 |
