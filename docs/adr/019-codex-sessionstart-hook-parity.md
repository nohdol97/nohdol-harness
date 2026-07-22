# ADR 019 — Codex SessionStart 훅 병행 (리마인더 2종)

> **부분 대체(→029, 2026-07-22)**: "확인된 이벤트만 등록" 자세와 agentsview-daemon 제외 결정은 ADR 029(파리티 기본값 — 미검증 이벤트·데몬 포함 선제 등록)로 대체됐다. 등록 형식·`$PWD` 경로·활성화 방식·#17532 폴백·macOS/Linux 한정 등 나머지 결정은 유효하다.

- **날짜**: 2026-07-16
- **변경 내용**: `.claude/settings.json`에만 등록돼 있던 SessionStart 세션 훅 중 **리마인더 2종**(`harness-review-reminder`·`worklog-reminder`)을 **`.codex/hooks.json`(추적)** 에도 등록해 Claude Code·Codex 두 CLI에서 같은 리마인더가 뜨게 한다. 훅 스크립트는 **무변경**(이미 도구 무관). 활성화(`[features] codex_hooks = true`)는 **`.codex/config.toml`(추적)로 저장소에 커밋해 클론 즉시 항상 켜지게** 한다(2026-07-16 사용자 지시).
- **대상**: `.codex/hooks.json`·`.codex/config.toml`(신설), `.gitignore`(`.codex/*` 추적 예외 2개), AGENTS.md 5·11절, `.agents/skills/harness-install/SKILL.md`, docs/specs/2026-07-14-harness-review-reminder-hook.md·2026-07-16-worklog-reminder-hook.md(Codex 노트)
- **사유**: 사용자 요청(2026-07-16 — "맥북에서 Codex도 쓰니 미리 동작하게"). 그동안 세션 훅은 "Claude Code 계층"이라 Codex 세션에서 안 도는 것이 알려진 공백이었다(리마인더 스펙 미해결 질문). Codex CLI v0.114+가 **동일 포맷**(`hooks.EventName[].hooks[].command`)의 라이프사이클 훅과 **SessionStart stdout → developer context 주입**을 지원함이 확인돼(공식 훅 문서·다중 출처, 2026-07-16 조사), 스크립트 복제 없이 config 하나로 병행이 가능해졌다.

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| config만 추가, 스크립트 무변경 | `.codex/hooks.json`에 리마인더 2종 등록. 훅 파이썬은 그대로 | 스크립트가 이미 도구 무관하게 설계됨 — fail-open, stdout 출력(Claude·Codex 둘 다 developer context로 소비), `CLAUDE_PROJECT_DIR` 부재 시 `os.getcwd()` 폴백. "규칙·로직은 도구 무관, 등록만 CLI별"이라는 11절 원칙의 실증 |
| 추적 위치 = `.codex/hooks.json` | `~/.codex/`(개인)가 아니라 저장소 루트에 두고 추적 | `.claude/settings.json`(추적)과 대칭 — 훅 등록은 공용 규칙이므로 저장소를 따라와야 하고, 설치처마다 재작성하면 발산한다. 개인 `.codex/config.toml`은 `.gitignore`로 제외 |
| 활성화 = 저장소 커밋(항상 켜짐) | `[features] codex_hooks = true`를 `.codex/config.toml`(추적)에 커밋 — 클론 즉시 켜지고 머신마다 켜는 단계가 없다 | 2026-07-16 사용자 지시("Codex hook 항상 활성"). `[features]`는 repo-local config.toml에서 무시되는 키 목록(notify·model_provider 등)에 없어 반영된다. **리스크 수용**: repo-local config.toml 활성화가 인터랙티브 세션에서 안 뜨는 이슈(openai/codex #17532) 가능성 — 안 뜨면 `~/.codex/config.toml` 전역 플래그로 폴백(harness-install 안내). 프로젝트 `.codex/config.toml`은 하네스 소유 공용 파일이라 개인 값은 `~/.codex/`(전역)에 둔다 |
| 명령 경로는 `$PWD` 기준 | Codex 명령은 `$CLAUDE_PROJECT_DIR` 대신 `$PWD/.agents/hooks/...` | Codex엔 `CLAUDE_PROJECT_DIR`가 없다. SessionStart 훅이 cwd=프로젝트 루트로 실행됨을 전제로 `$PWD`를 쓴다 — 이 전제는 macOS 실측으로 검증한다(harness-updates.md 대기) |
| macOS·Linux 한정 | Windows는 대상에서 제외 | Codex 훅은 실험 기능이고 **Windows 미지원**(공식). 맥북·Linux 설치처에만 적용 |
| agentsview-daemon 제외 | 세션 훅 3종 중 리마인더 2종만 병행, 데몬은 제외 | agentsview가 Codex 세션을 관측하는지 미확인 — 관측 못 하면 데몬 기동은 무의미하다. 확인되면 편입(스펙 대기 관찰) |
| tdd-gate는 대상 아님 | git 훅 계층은 이미 Codex 포함 도구 무관(ADR 014·015) | 이 ADR은 **세션 훅**의 공백만 메운다 |

## 검증

- **포맷 근거**: Codex 훅 공식 문서 및 다중 출처(2026-07-16 조사) — `hooks.SessionStart[].hooks[].command`, matcher(`startup|resume|clear`), SessionStart stdout → developer context, 활성화 `[features] codex_hooks = true`, 실험·Windows 미지원.
- **스크립트 무회귀**: 기존 회귀 테스트 그대로 통과(worklog-reminder 12/12, harness-review-reminder 18/18) — 스크립트를 건드리지 않았다.
- **실측 대기**: 원격 컨테이너엔 Codex 미설치라 실주입은 검증 불가 — macOS Codex 세션에서의 검증을 `_workspace/harness-updates.md` 대기 항목으로 남긴다. `$PWD` cwd 전제와 activation이 이 검증의 확인 대상이다.
