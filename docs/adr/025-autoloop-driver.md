# ADR 025: autoloop — 세션 외부 드라이버 기반 자율 멀티세션 루프

- **날짜**: 2026-07-19
- **변경 내용**: 자율 멀티세션 루프 자산을 신설했다 — `.agents/skills/autoloop/`(발사대 스킬: start/status/stop 3동사) + `scripts/driver.py`(루프 본체: 세션 바깥의 Python 프로세스가 `claude -p` headless를 반복 기동). 반복 간 상태는 `_workspace/autoloop/<작업명>/carryover.md` 핸드오프 노트로 넘기고, 산출물·로그도 같은 디렉토리에 둔다(§4 규약). CLAUDE.md 라우팅 앵커에 트리거("자율 루프"·"무인 실행"·"밤새 돌려줘")를 추가했다.
- **대상**: `.agents/skills/autoloop/`(SKILL.md, scripts/driver.py, scripts/driver_test.py), CLAUDE.md 앵커, docs/specs/2026-07-19-autoloop-driver.md
- **사유**: 한 세션 컨텍스트를 넘는 작업의 무인 완주("wrapup→clear→재개" 자동화)가 필요한데, `/clear`는 CLI 명령이라 세션 안의 모델이 스스로 부를 수 없다. **드라이버를 세션 바깥에 두면 새 프로세스 = 새 컨텍스트**라 clear가 구조적으로 해결된다 — 이 아키텍처 결정(스킬이 본체가 아니라 발사대)이 이 ADR의 핵심이다. 사용자 요청·설계 합의 2026-07-19(목적: 멀티세션 완주 + 자율 개발, 안전 범위: 읽기·편집만 무인).
- **핵심 설계 결정**:
  - **게이트 3종이 존재 조건**: ① 안전 — `acceptEdits` + allow/disallow 목록, 파괴적 작업은 `blocked` 정지 후 사용자 이월(§3 완화 불가, `bypassPermissions` 전면 금지) ② 검증 — 테스트는 드라이버가 독립 실행한 결과만 증거(§13 신선한 증거의 무인 버전), `done` 주장은 읽기 전용 reviewer 검증 반복의 PASS 필수 ③ 정지 — 7종 종료 조건(done/blocked/stalled/exhausted/stopped/cost/error)으로 반드시 유한 종료. 무인 모드는 하네스 소프트 게이트(리뷰·증거)를 침식하므로, 재량이던 검증을 루프 구조의 필수 단계로 승격했다.
  - **불변 앵커로 드리프트 방지**: 매 반복 프롬프트에서 목표(스펙 경로)는 불변이고, 갱신되는 것은 핸드오프 노트·테스트 실측·리뷰 피드백뿐이다 — "프롬프트 자동 개선"을 목표 재작성이 아니라 상태 주입으로 한정했다.
  - **완료 판정 오라클은 스펙**: "완료 기준" 절 없는 스펙으로는 기동을 거부한다(R9) — 모델 자가평가가 결승선이 되는 것을 차단.
  - **무의존**: Python 3 stdlib만 사용(§16 사다리 5단). Claude Agent SDK의 permission callback 대신 CLI allow/disallow 목록으로 동등 경계를 긋는다 — 이 규모에서 새 의존성보다 낫다.
  - **기존 자산과의 경계**: `/loop`(내장, 세션 안 반복)·carryover(수동 이월)·work-tracker(크로스 세션 정식 추적)를 대체하지 않는다 — autoloop은 "세션 교체가 필요한 무인 반복"만 담당하고, 노트 스키마는 carryover 템플릿을 차용한다.
  - **멀티 엔진(2026-07-19 확장)**: 드라이버는 헤드리스 세션을 `claude -p` 또는 `codex exec`로 돌리며, 역할별 엔진을 지원한다(`--engine`·`--implement-engine`·`--verify-engine`) — "구현은 Claude, 검증은 Codex" 같은 교차 엔진 요구를 충족한다. **Codex 안전 게이트는 sandbox 레벨**(구현=workspace-write·검증=read-only)이라 Claude의 fine-grained allow/deny보다 coarse하다: 네트워크 기본 차단으로 원격 파괴 작업(kubectl·aws·push)은 봉쇄되나 워크스페이스 내 로컬 파괴 명령은 정책 밖이라, 어느 엔진이든 인프라·배포 스펙 금지·blocked 이월이 방어선이다. **bypass 계열은 두 엔진 모두 절대 금지**(§3 완화 불가 — Claude `--dangerously-skip-permissions`, Codex `--dangerously-bypass-approvals-and-sandbox`). 티어→모델 해석은 엔진과 직교로 유지(§9 탈모델명). 스펙 R13~R15, 완료 기준 C16·C17.
- **스펙**: docs/specs/2026-07-19-autoloop-driver.md (완료 기준 C1~C17, 회귀 테스트 37항목 통과 — reviewer 독립 검증 2회: 초기 BLOCK→재작업→PASS, 멀티엔진 PASS)
