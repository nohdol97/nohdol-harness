# Hermes Agent 검토 — 기각 기록

- 날짜: 2026-07-25 / 상태: **기각** (사용자 확정 2026-07-25)
- 대상: https://github.com/nousresearch/hermes-agent (Nous Research, 자기호스팅 에이전트 런타임)
- 관련: ADR 007(지연 생성·drift 방지), ADR 018(검색형 교훈 저장소 기각), 루트 AGENTS.md §3·§8·§9·§11, docs/proposals/2026-07-25-agentmemory-review.md

## 대상 요약

Nous Research의 "self-improving AI agent" — **자체 에이전트 런타임**(파이썬 `run_agent.py`/`agent/` 루프, 자체 CLI, 자체 프로바이더 라우팅)이다. 간판 기능은 built-in learning loop: 복잡 작업 후 **스킬 문서를 자율 생성**하고, 사용 중 자기개선하며, 지속을 스스로 넛지하고, 과거 대화를 검색한다. 그 위에 멀티플랫폼 게이트웨이(Telegram/Discord/Slack/WhatsApp/Signal + CLI), 6종 터미널 백엔드(local/Docker/SSH/Singularity/Modal/Daytona, serverless hibernation), cron(자연어 반복 작업), MCP 통합, 프로바이더 라우팅(Nous Portal 300+ 모델/OpenRouter/OpenAI), FTS5 대화 검색 + LLM 요약 리콜, Honcho dialectic 유저 모델링, `~/.hermes/skills/`(agentskills.io 이식형 `SKILL.md` 표준), 서브에이전트 병렬 spawn(RPC로 zero-context-cost turn), 트래젝토리 압축(차세대 tool-calling 모델 학습용).

## 기각 근거

1. **범주 불일치 — 채택이 아니라 런타임 교체**: Hermes는 이 하네스처럼 Claude Code 위에 얹는 규약이 아니라 별도 에이전트 런타임이다. "쓴다"는 곧 **Claude Code + Codex 환경 이탈**이며, §11(멀티 CLI 규약·심링크·훅 파리티)이 전제하는 실행 기반 자체를 버린다. add-on 이식 대상이 아니라 상호배타 대체재라 부분 이식이 성립하지 않는다.
2. **간판 기능이 이미 명시 기각한 축**: 자율 스킬 생성·자기수정 → ADR 007(자동 생성 자산 drift)·"사용자만 병합" 철학과 충돌. 대화 검색 DB → ADR 018(검색형 교훈 저장소 기각, 축은 축적이 아니라 승격)과 정면 충돌. 자동화의 false negative가 무실수 목표에 손실이라는 사용자 방침과도 역행. 즉 Hermes로 가면 안전을 위해 넣은 게이트를 자동화로 되돌리는 방향이다.
3. **니치 기충족**: 서브에이전트 병렬 → orchestrate/team·Workflow, cron/무인 → autoloop·schedule·loop, MCP → ToolSearch, 프로바이더/모델 선택 → §9 티어 매핑, command approval·isolation → §3·secret-gate·tdd-gate·worktree, 유저 모델링·영속 메모리 → auto-memory(`user` 타입)+MEMORY.md, 대화 회상 → agentsview finding-history, RPC zero-context-cost → rtk+Workflow. 남는 순증 역량이 없다.
4. **§3 데이터 유출 축**: Nous Portal 툴 게이트웨이·프로바이더 라우팅이 **클라우드 경유**다. 사내 계정 사용자에겐 코드·컨텍스트가 제3자 모델 라우터를 지나는 실질 리스크 — 외부 DB 동기화 금지와 같은 축(runtime-egress-caveat 메모리·§3 시크릿 금지).
5. **범위 밖 기능이 다수**: 멀티플랫폼 메신저 게이트웨이, serverless 백엔드, 트래젝토리 학습 압축은 개인 상시비서·모델 벤더 용도다. 터미널 개발 하네스의 필요와 무관하다.

## 마이크로 포팅 후보 검토

| Hermes 착안 | 판정 | 이유 |
|---|---|---|
| 복잡 작업 후 스킬/교훈 지속 넛지 | 기수렴 | §8 "첫 발생 시 교훈 기록" + wrapup 스킬. 자동 넛지 훅은 wrapup과 중복이라 순가치 낮음 |
| 자율 스킬 생성·사용 중 자기개선 | 충돌 | ADR 007·metaskill 사용자 승인 게이트 — 무단 자동 생성은 원칙 위반 |
| FTS5 대화 검색 + LLM 요약 리콜 | 충돌 | ADR 018(검색형 저장소 기각), agentsview로 기충족 |
| 서브에이전트 병렬 spawn / RPC zero-context turn | 기수렴 | orchestrate·Workflow·rtk가 같은 토큰 발상 |
| agentskills.io 이식형 `SKILL.md` 표준 | 관찰(보류) | 지금 도입은 사용자 없는 churn. 생태계가 이 표준으로 수렴하면 크로스툴 이식성 가치 — 신호 시 harness-review 재검토 |

## 재검토 조건

- **agentskills.io 표준**만 관찰 항목: 외부 스킬 이식 실수요가 신호 ①(3+회)로 잡히면 `.agents/skills/` 자체 규약과의 이식성만 재검토. 그 경우에도 Hermes 런타임 도입이 아니라 스킬 파일 포맷 상호운용 한정.
- Hermes 런타임 자체는 범주 불일치·§3 유출로 재검토 조건 없음(개인 용도 상시비서가 별도 필요해지면 이 개발 하네스와 병행하는 별개 도구로 볼 사안이지 대체재 아님).

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-25 | 검토·기각 기록 | 신규 | 사용자 검토 요청("hermes 쓰는 편이 낫지 않아?") → 기각 권고 승인(제안=과정 원칙, §6 — 기각도 기록해 재검토 반복 방지) |
