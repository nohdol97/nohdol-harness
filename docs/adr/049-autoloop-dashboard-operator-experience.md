# ADR 049: autoloop 대시보드를 운영자 중심 작업공간으로 개편

> **부분 대체(2026-08-19)**: 사용자가 실제 관계 시각화와 React·TypeScript 전환을 명시해 기존 결정 3·8·9·10과 “프런트엔드 프레임워크·그래프 라이브러리” 기각안을 아래 내용으로 갱신했다. ADR 047의 Python loopback·읽기 전용·bounded 경계와 ADR 048의 artifact 역할 분리는 유지한다.

> **부분 대체(2026-08-19, 단순화)**: 사용자가 상세 화면의 과잉 정보를 지적해 결정 2·3·6·9·10을 다시 좁혔다. Task DAG와 React Flow·Dagre는 제거하고, 기본 상세은 최소 개요·기록된 T 핸드오프·한 줄 실행 시간축·압축 Coordination만 남긴다. 비용·engine·worktree·integration·commit·evidence는 초기 접힘 세부 정보로 이동한다.

- **날짜**: 2026-08-19
- **변경 내용**: 기존 autoloop 읽기 대시보드의 raw projection 중심 화면을 주의 우선 작업 목록과 task·agent·coordination·worktree·evidence 흐름을 연결한 운영자 중심 master-detail 화면으로 개편한다.
- **대상**: `docs/specs/2026-08-19-autoloop-dashboard-operator-ux.md`, `docs/adr/049-autoloop-dashboard-operator-experience.md`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/harness-ops-log.md`
- **사유**: ADR 047·048로 관측 데이터와 구조화 artifact는 생겼지만 현재 화면은 상태·의존성·병렬 실행·fan-in·주의 지점을 빠르게 판단하도록 우선순위를 설계하지 않았다. 구현 전에 UX 의미와 안전 경계를 고정하지 않으면 시각 개선이 기록에 없는 agent 대화를 꾸며 내거나 legacy를 오류로 보이게 하거나 기존 읽기 전용 경계를 넓힐 수 있다.

## 결정

1. 작업 목록과 선택 작업 상세의 master-detail 구조를 유지하고, 구조화 기록 유무보다 운영 상태를 먼저 판정해 차단·실패·중단·갱신 지연·실행 중·완료 순으로 주의가 필요한 작업을 드러낸다. tracking과 provenance는 배지·필터·동률 보조축이다.
2. 상세 기본 구조는 `최소 개요`, `T 핸드오프`, `한 줄 실행 시간축`, `Coordination 요약`으로 제한한다. 비용·engine·worktree·integration·commit·evidence·diagnostics는 초기 접힘 세부 정보로 이동한다.
3. task 관계는 그래프 대신 기록된 `team-log.jsonl` task event를 시간순 chip과 방향 cue로 잇는다. 이는 대화가 아니라 기록된 작업 전이이며, event가 없을 때 dependency로 추정하지 않는다.
4. `team-log.jsonl`은 bounded coordination timeline으로 읽는다. 현재 감사 가능한 것은 선행 task 완료 뒤 후속 task가 dispatch된 event 순서이며, dependency evidence 전달은 별도로 기록되지 않는다. 이를 전달·자유 대화·내부 추론으로 해석하지 않는다.
5. 기존 API의 `source` 의미는 보존한다. `orchestration.json` 존재 여부를 나타내는 additive `tracking`과 명시적 `dashboard-meta.json`만 읽는 `provenance`를 추가한다. unstructured 작업은 당시 구조화 추적이 없었다고 설명하고 누락 정보를 추정하지 않는다. 이름·경로로 demo를 판정하지 않는다.
6. agent 기본 화면은 모든 실행을 하나의 track에 놓고 ID·상태만 보여 준다. 역할·requested/effective engine·fallback과 worktree·integration 정보는 접힌 세부 정보에서 기록값 그대로 제공한다.
7. 자동 갱신은 선택·상세 위치·포커스를 보존하고 신선도와 갱신 실패를 실행 실패와 분리한다. 색만으로 상태를 전달하지 않으며 키보드·스크린리더·reduced motion·200% 확대를 완료 조건에 포함한다.
8. ADR 047의 loopback·읽기 전용·Host/method/path/symlink·보안 헤더 계약과 ADR 048의 artifact 역할 분리를 유지한다. API 변경은 additive이고, 외부 문자열은 escaped React text child로만 렌더링한다. unsafe HTML·parsing·실행·style·URL sink를 금지하고 read는 bounded다.
9. React·TypeScript·Vite source와 lockfile을 두고 production static build를 커밋한다. runtime frontend 의존성은 React·React DOM만 남기며 handoff와 시간축은 CSS로 만든다. Node/npm은 개발·빌드·테스트 의존성이고 dashboard runtime은 계속 Python 표준 라이브러리만 요구한다. CDN·remote asset·server-side 사용자 상태 저장은 도입하지 않는다.
10. 구현과 독립 검증의 정본은 `docs/specs/2026-08-19-autoloop-dashboard-operator-ux.md`의 R1~R19와 C1~C20이다. 이 ADR은 설계 선택을, 해당 스펙은 테스트 가능한 동작을 소유한다.

## 기각한 대안

- **CSS만 다듬기**: 문제는 색과 간격만이 아니라 상태 우선순위, 관계 연결, legacy 의미의 부재다.
- **채팅형 agent 화면**: runtime은 task 완료와 후속 dispatch 같은 coordinator-mediated event를 기록할 뿐 결과 전달이나 자유 대화를 별도 증명하지 않아 채팅 표현이 기록보다 강한 사실을 암시한다.
- **서버까지 Node로 전환**: Python collector와 loopback 안전 경계를 다시 구현해야 해 이득보다 회귀 위험이 크다. React build는 정적 asset으로 커밋해 Python-only runtime을 유지한다.
- **일반 chart·icon·router·상태관리 framework 추가**: task graph 외 시각화는 CSS·SVG·React로 충분해 의존성 비용을 정당화하지 못한다.
- **legacy 데이터 소급 생성**: 과거 기록에 없는 agent·dependency·worktree를 추정하면 감사 가능한 사실 대신 생성된 서사를 보여 준다.
- **재시도·중단·cleanup 제어**: 관측면과 제어면을 합치며 ADR 047의 안전 경계를 바꾼다. 별도 결정 없이는 허용하지 않는다.

## 결과

- 사용자는 첫 화면에서 주의 작업을 찾고 T 핸드오프 → 한 줄 실행 시간축 → Coordination 요약을 같은 맥락에서 추적할 수 있다.
- agent 간 소통은 실제 event가 있는 범위에서만 관찰되며 직접 채팅 여부를 과장하지 않는다.
- legacy와 synthetic demo의 출처가 명확해져 빈 구조화 영역이 데이터 손실이나 현재 런 오류로 오해되지 않는다.
- 접근성·반응형·polling 안정성·보안 회귀가 시각 품질과 같은 완료 게이트에 들어간다.
- frontend source는 모듈·타입·component test로 분리되고 runtime은 커밋된 정적 build를 Python이 제공한다.
- Light를 첫 방문 기본값으로 두고 System·Dark를 선택할 수 있으며, handoff strip과 한 줄 시간축이 운영 상태를 시각적으로 설명한다.

## 영향

`.agents/skills/autoloop/dashboard-ui/`, `.agents/skills/autoloop/scripts/{dashboard.py,dashboard_test.py}`, `docs/specs/2026-08-19-autoloop-dashboard-operator-ux.md`, `docs/adr/049-autoloop-dashboard-operator-experience.md`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/{autoloop-dashboard-visualization,harness-ops-log.md}`
