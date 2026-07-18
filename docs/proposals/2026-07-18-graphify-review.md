# 제안: graphify 검토 — 채택 보류, 하네스 호환 파일럿 실측 제안

- 날짜: 2026-07-18 / 결과: **기각(sona_app 파일럿 실측 미달)** — 2026-07-18 파일럿 완료, 아래 "파일럿 실측 결과" 참조. 다른 스택(정식 tree-sitter 추출·import 해소되는 언어)에서는 재검토 여지 있음
- 출처: github.com/Graphify-Labs/graphify (MIT, 90k★, YC S26, v0.9.18 — 분석 커밋 8cee776) — 코드베이스를 tree-sitter AST 기반 지식 그래프(`graphify-out/graph.json`)로 만들어 파일 검색 전에 그래프를 조회하게 하는 스킬+CLI
- 상세 수집 리포트: `_workspace/grapify-review/phase1_explorer_report.md` (미보존 — 요지는 이 문서에 반영)

## 분석 요지 (사실)

- **인프라 부담이 낮다**: 데몬·DB·임베딩 없음 — Python CLI + 평면 JSON. 코드 그래프는 tree-sitter 결정적 빌드(LLM 비용 $0). ADR 018에서 claude-mem 기각의 핵심이던 "상시 워커+벡터 DB" 문제가 없다.
- **신선도는 자동이 아니다**: 기본은 수동 `graphify update`(에이전트 준수 의존). git 훅·watch는 opt-in이고 대형 저장소 전체 재빌드는 "수 시간"(자체 주석), 삭제 파일은 ghost 노드 잔존. stale 그래프는 오답 유도 실패 모드(state rot과 동일).
- **절감 수치는 우리 기준선과 다르다**: "71.5x"는 전체 코퍼스 컨텍스트 밀어넣기 대비. 자체 표 기준 코드만 8.8x, 소형 코퍼스 ~1x. **표적 grep·explorer 팬아웃 대비 실측은 어디에도 없다** — 이 하네스의 기준선은 후자다.
- **Codex 지원은 약하다**: Codex 쪽 훅은 의도적 no-op — 정적 문구 주입뿐. 두 CLI 병행인 이 하네스에서 이득이 비대칭.

## 하네스 충돌면 (기본 설치기를 그대로 쓸 수 없는 이유)

| graphify 설치기 동작 | 충돌하는 하네스 규칙 |
|---|---|
| `graphify claude install`: 프로젝트 CLAUDE.md에 섹션 append + `.claude/settings.json`에 PreToolUse 훅 2종(모든 Bash·Read·Glob 호출마다 서브프로세스+넛지 60~70 tok) | 루트 CLAUDE.md는 `@AGENTS.md`+앵커만(ADR 021), settings.json은 추적 파일, 하위 프로젝트 CLAUDE.md 금지(12절), 호출당 넛지는 상시 토큰 비용 |
| `graphify codex install`: 프로젝트 루트 AGENTS.md에 섹션 append | 루트 AGENTS.md는 추적 단일 원본 + 크기 예산 40k(수정 주체는 metaskill), 하위 프로젝트에는 AGENTS.md 자체를 두지 않음(12절 중앙 관리) |
| 전역 `~/.claude/CLAUDE.md` append | 사용자 전역 파일이라 허용 가능(11절 전역 설치 원칙과 정합) — 단 내용 확인 후 |

→ **파일럿은 설치기 미사용**: 전역 스킬(`~/.claude/skills/graphify/`)과 CLI만 쓰고, 훅·CLAUDE.md/AGENTS.md 자동 편집은 배제한다. 라우팅은 하네스 문서(하위 AGENTS.md의 스킬 목록)가 운반한다 — 12절 원칙 그대로.

## 파일럿 설계 (승인 시 실행)

1. **대상**: 등록 프로젝트 중 최대 코드베이스 1개(REGISTRY.md 기준 — 후보: sonaapp). `graphify-out/`은 해당 프로젝트 gitignore에 추가.
2. **측정**: 동일 탐색 과업 3건(구조 파악·심볼 추적·크로스 파일 영향 분석)을 ① 현행 explorer/grep ② graphify query로 각각 수행, agentsview로 세션 토큰·소요 시간 실측. 재빌드 시간·stale 재현(파일 수정 후 미갱신 그래프의 오답 여부)도 기록.
3. **판정 기준**: 탐색 토큰 **30% 이상 절감 + 정확도 동등 이상 + 재빌드가 분 단위**면 채택(ADR로 확정, 하위 AGENTS.md에 사용 절차 기재). 미달이면 기각으로 이 문서 갱신. 애매하면 과업을 3건 추가해 재측정.
4. **비용 상한**: 파일럿 자체가 과소모면 본말전도 — 세션 1회, 서브에이전트 포함 20만 토큰 내로 제한.

## 기각해도 잃지 않는 것

기본 설치기의 자동 편집(호출당 훅 넛지·CLAUDE.md append)은 파일럿 여부와 무관하게 **도입하지 않는다** — 상시 비용·단일 원본 규율 위반이라 실측 결과가 좋아도 하네스 호환 방식(문서 라우팅)만 쓴다.

## 파일럿 실측 결과 (2026-07-18, sona_app / Flutter·Dart)

설치는 격리 venv(`graphifyy` 0.9.18, Python 3.14), 대상은 `sona_app/lib`+`test`(229 dart 파일)를 scratchpad 복사본에 빌드 — **프로젝트 저장소·전역 설정 무수정**(빌드 중 프로젝트에 생긴 `graphify-out/` 잔여물은 즉시 제거, git 청결 확인). 판정 기준(탐색 토큰 30%+ 절감 + 정확도 동등 + 재빌드 분 단위) 대비:

| 지표 | 결과 | 판정 |
|---|---|---|
| 재빌드 시간 | lib+test 9초, l10n 제외 5초 (단 **전체 프로젝트 루트는 22,385파일 훑다 2분+ 타임아웃** — `.dart_tool`·미gitignore 산출물, 수동 범위 지정 필요) | △ 범위 지정 시만 통과 |
| **줄 번호 보유율** | **0%** (5,738노드 중 24개) — Dart 추출기가 **정규식**이라 `source_location`을 안 잡는다. 파일은 알려주되 줄은 못 알려줌 → **질의 후 결국 파일을 Read해야 함** | ✗ 토큰 절감 전제 붕괴 |
| 그래프 노이즈 | 초기 노드 78%(21,292/27,112)가 l10n 번역 문자열 — "login"이 아랍어 번역 파일에 매칭. `.graphifyignore`로 제외 가능하나 out-of-box 심각 | ✗ |
| 과업1 "채팅 전송 위치" 토큰 | graphify **1,543 tok**(파일만, 줄 없음) vs explorer 범위 grep **88 tok**(`chat_service.dart:656` 정의 직격) | ✗ graphify가 **~17배 더** 씀 |
| 과업2 "persona_service 역의존성" | graphify `affected` → **"No affected nodes found"**(구조적 강점인데 빈 결과 — Dart 상대경로 import가 정식 노드로 미해소, imports 엣지 1,066개 존재에도 역추적 끊김) vs grep 23파일·211 tok | ✗ 차별화 기능 실패 |

**결론**: 이 하네스의 주력 앱 프로젝트(Flutter/Dart)에서 graphify는 판정 기준을 미달하는 정도가 아니라 **범위 지정 grep보다 토큰을 더 쓰고**(줄 번호 부재로 재독 강제), **간판 기능인 그래프 역추적이 빈 결과**를 냈다. 순진한 grep(l10n 오염) 대비로는 파일 식별이 나았지만, 하네스 기준선은 explorer의 범위 지정 grep이다. 근본 원인 2개(Dart 정규식 추출기의 줄 번호 부재, 상대경로 import 미해소)는 설정으로 못 고치는 구조적 한계다.

**남는 재검토 조건**: ① 정식 tree-sitter 추출 + import가 절대경로로 해소되는 스택(예: web_project의 TypeScript)에서는 줄 번호·역추적이 살아 있을 수 있어 결과가 다를 수 있다 — 필요 시 별도 파일럿. ② l10n·빌드 산출물 자동 제외와 Dart 줄 번호 지원이 상류에서 개선되면 재평가. 그 전까지 Dart 프로젝트에는 도입하지 않는다.
