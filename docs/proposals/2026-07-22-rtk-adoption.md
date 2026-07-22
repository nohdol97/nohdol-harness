# 제안: rtk(rtk-ai/rtk) 채택 검토 — 조건부 채택 (설치 단계 + 증거 원문 규칙)

- 날짜: 2026-07-22
- 상태: 조건부 채택 — harness-install 선택 단계(3e) + AGENTS.md §13-2 증거 원문 규칙 보강. 설치 자체는 설치처별 선택(무단 설치 없음)
- 출처: https://github.com/rtk-ai/rtk (사용자 검토·적용 요청)

## 정체 (수집: explorer, git clone 실측 — HEAD 2026-07-22)

**"Rust Token Killer"** — 개발 명령을 대신 실행하고 stdout/stderr를 압축(노이즈 필터·그룹·절단·중복 제거)해 LLM 컨텍스트에 넣는 단일 Rust 바이너리 CLI 프록시. Apache-2.0(LICENSE 실재), v0.42.4, 커밋 1,000+·기여자 10+·마지막 커밋 당일 — 활발히 유지되는 프로젝트다. 예: `git status` ~3,000→~600토큰, `git push` → `ok main`, `cargo test` → `FAILED: 2/15`+실패 줄만. 실패 시 원문 전체를 `~/.local/share/rtk/tee/`에 저장하고 경로를 출력한다.

**Claude 통합**(`rtk init -g`): ① 전역 `~/.claude/settings.json`에 PreToolUse(Bash) 훅 — `git status`→`rtk git status`로 투명 재작성(`updatedInput`), ② `~/.claude/CLAUDE.md`에 `@RTK.md` 임포트 추가, ③ 훅 파일 SHA-256 무결성 기준선(`rtk verify`). Codex 모드는 훅이 아니라 `~/.codex/AGENTS.md` 패치(행동 지시 — "항상 rtk 접두") 뿐이다.

## 안전 태세 (수집 실측 — 채택 판단의 근거)

- **fail-open**: rtk/의존 부재 시 훅이 조용히 통과. 복합·주입형 명령(`&&`, `$()`, 백틱, 파이프)은 재작성하지 않음(테스트 존재 확인).
- **권한 존중**: Claude Code settings.json의 deny/ask/allow 규칙을 읽어 deny/ask 명령은 재작성하지 않고 네이티브 처리에 맡김.
- **가드레일 정합**: rtk는 에이전트가 요청한 명령만 실행(스스로 개시 없음) — 3절 파괴적 작업 확인은 프롬프트 계층이라 영향 없음. git commit 훅(tdd-gate·secret-gate)은 서브프로세스로 그대로 발화.
- **주의점 2건**: ① 압축이 검증 증거를 요약으로 대체(→ 아래 §13-2 보강으로 해소) ② 텔레메트리 문서 모순(README "opt-in" vs DISCLAIMER "기본 수집") — 설치 단계에서 `RTK_TELEMETRY_DISABLED=1` 명시 설정으로 방어(agentsview 전례, 3절 정합).

## 판정

| 항목 | 판정 | 근거 |
|---|---|---|
| 전역 설치 + 훅 모드(`rtk init -g`) | **채택(선택 단계)** | 절감 표면이 이 워크스페이스의 무거운 곳(kubectl·로그·git·테스트 출력)과 정확히 겹침. §15·§4(산출물 계층)와 상보적 — 명령 출력 인제스천 계층은 기존 하네스에 없던 축. 안전 태세 위 4항목 확인 |
| §13-2 증거 원문 규칙 | **채택(하네스 보강)** | 압축 출력("FAILED: 2/15")은 완료 증거의 "관찰한 출력"이 아니다 — 증거 명령은 패스스루(`rtk proxy`)·tee 원문으로 남긴다. 이 한 줄이 "silent rewrite가 검증 밀도를 깎는" 유일한 실질 충돌을 해소 |
| Codex 모드(`~/.codex/AGENTS.md` 패치) | **보류** | 훅이 아닌 행동 지시 계층이라 효과가 약하고, 전역 AGENTS.md 패치가 하네스 단일 원본 체계 밖에 상시 지시를 추가 — Claude 훅 모드 실측 후 재검토 |
| 하네스 저장소 내 설정 커밋 | **기각** | rtk의 훅·임포트는 전역(`~/.claude/`) 대상 — 설치처별 요소는 git에 안 올린다(ADR 005 정합). 추적 settings.json에 넣지 않음 |
| 절감 수치 신뢰 | **보류(실측 대기)** | README "60-90%"는 명시된 추정치(len/4 휴리스틱 벤치). 로컬 `rtk gain` 실측이 있으므로 **설치 3주 후 tool-audit**로 keep/remove 판정(§8 ④와 연결) |

## 미검증 (정직 선언)

- GitHub 스타·인기 지표(세션 프록시가 API 차단), 텔레메트리 실동작 기본값(문서 모순 — 설치 머신에서 확인), **이 컨테이너에서의 실설치**(릴리스 다운로드도 차단됨 — 설치·동작 검증은 설치 머신 몫), gate-reminder(PostToolUse Bash)와의 동거 실측(이벤트가 달라 이론상 무충돌: rtk=PreToolUse 재작성, gate-reminder=PostToolUse 관찰 — 재작성된 `rtk kubectl ...` 명령도 진단 패턴에 그대로 매칭됨).
