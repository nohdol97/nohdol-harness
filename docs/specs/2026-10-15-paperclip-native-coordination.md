# Paperclip 전용 협업 규칙 분리

## 목표
Paperclip에서 CLI용 orchestrate 스킬을 중복 실행하지 않고 등록된 역할을 배정하며, 사내 CLI의 직접 수행·native 호출 금지·독립 검토 면제가 Paperclip 역할 배정을 막지 않게 한다.

## 요구사항
- R1: Paperclip의 실제 실행 문맥과 전용 계약에서만 적용한다. 일반 CLI의 orchestrate/autoloop와 사내 native dispatch 제한은 그대로 유지한다. 환경 변수 하나나 단순 문서 언급을 실행 문맥으로 인정하지 않는다.
- R2: Paperclip coordinator가 작업 분해·역할 선택·완료 기준·독립 검토·통합 판단을 담당하고 Paperclip이 issue 배정·실행·재시도를 담당한다. 기존 orchestrate의 팀 규모·native dispatch 절차는 Paperclip 작업에 요구하지 않는다.
- R3: orchestrate/autoloop는 관리자와 관리 역할의 실행 스킬 배정에서 제외한다. 재동기화 때도 다시 배정하지 않고, 기존에 배정된 이 설치 소유 키만 remove한다. 원본 및 라이브러리 참조 사본·다른 스킬 배정은 삭제하지 않는다.
- R4: 루트 규칙·생성 역할 지침·관리자 블록·가져온 SKILL.md에서 Paperclip의 전용 협업 규칙이 우선함을 일관되게 알린다. 원본 역할과 스킬 본문은 보존하되 Paperclip용 안내를 추가한다. 사내 direct-execution/dispatch-ban/self-review exemption은 이 문맥에서 적용하지 않는다.
- R5: 데이터 반출·사내 루트 편집 금지·비밀·sandbox·도구 권한·승인·누락 하네스 정지는 유지한다. Paperclip 작업 배정을 허용한다는 이유로 모델 호출을 재개하거나 새 native worker를 띄우지 않는다.
- R6: 현재 pause 상태·개인정보 설정·기존 이슈·레지스트리·연결을 보존한다. 실제 모델 호출 없이 로컬 API로 지침·스킬 배정을 갱신한다. agent config PATCH의 불필요한 hello는 거부한다.

## 완료 기준
- [x] C1: source 규칙과 runtime의 적용 범위가 일치하고 일반 CLI 경로가 보존된다.
- [x] C2: 회귀 테스트가 기존 orchestrate/autoloop 배정 제거·재적용·비관리 배정 보존·스킬 원문/참조 보존을 확인한다.
- [x] C3: 로컬 Paperclip의 관리자·역할에서 두 실행 스킬이 배정되지 않고 새 계약이 반영된다. 에이전트는 기존 pause 상태다.
- [x] C4: 무결성 검사와 독립 검토가 통과하고 운영 안내·변경 이력을 갱신한다.

## 검증 근거
`python3 -B .agents/integrations/paperclip/sync_test.py`: 변경 후 15개 통과, 독립 최종 실행 15개 통과(2.397s). 설치 원본 19개에 대해 YAML·본문·참조·출처 보존을 독립 대조했다. 원본 스킬·역할 및 native dispatch hook에는 변경이 없다. 루트 §11과 한국어 뷰, runtime, 생성 안내, ADR 독립 검토 PASS.

로컬 적용은 회사 스킬 가져오기, 관리자 orchestrate 키 remove, 관리자 지침 PUT으로 완료했다. 재적용은 가져오기만 수행했고 배정·관리자 지침 변경은 0회였다. 8개 에이전트의 배정이 이전 집합에서 해당 설치의 제외 키만 뺀 결과와 같고 pause 상태·runtime 설정이 유지됨을 확인했다. 원문 계약을 포함한 역할 7개 지침과 회사 API가 반환하는 19개 SKILL.md도 확인했다. 기존 업무·프로젝트와 개인정보 설정은 보존됐다.

현재 배정은 모두 version pin 없는 키다. 설치 소스 확인 결과 각 실행은 최신 회사 스킬/로컬 경로를 다시 해석하므로 같은 배정을 불필요하게 add할 필요가 없다. 명시적으로 pin된 외부 배정은 보존하며 최신 사본 적용을 주장하지 않는다. 모델 호출을 유발할 agent config 변경은 허용하지 않았고 새 실행도 시작하지 않았다. 근거 로그는 미추적 `_workspace/paperclip-native-coordination/`에 둔다.

## 비목표와 한계
전용 계약은 모델 지침이며 서버 권한 강제 장치가 아니다. Paperclip이 스펙 완수와 독립 검토를 자동 보장한다고 주장하지 않는다. 사내 데이터 반출 허용, 방화벽 변경, 에이전트 재개, 원격 Git 전송은 포함하지 않는다.

## 변경 이력
| 날짜 | 변경 | 대상 | 사유 |
|---|---|---|---|
| 2026-10-15 | 최초 스펙 | Paperclip 협업 규칙 | 사용자 지적: 중복 orchestration·사내 호출 금지 혼입 |
