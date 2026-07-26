# 하네스 도구 후보 4건 채택 검토 (이슈 #41 우선순위 B)

> 상태: **전건 미채택** — 3건 기각, 1건 연기
> 날짜: 2026-07-26 · 절차: `tool-eval`
> 형제 문서: [2026-07-26-harness-design-sources-review](2026-07-26-harness-design-sources-review.md) (A 5건)

## 0. 판정 요약

| 후보 | 1차 출처 | 라이선스 | 판정 | 결정적 사유 |
|---|---|---|---|---|
| B-1 VHK | `github.com/byh3071-cpu/vhk` | MIT | **기각** | `vhk sync`가 AGENTS.md를 자동 생성물로 덮어씀 + `core.hooksPath` 단일 슬롯 점유 |
| B-2 DeerFlow 2.0 | `github.com/bytedance/deer-flow` | MIT | **기각** | 독립 런타임 — 채택이 아니라 Claude Code+Codex 이탈 |
| B-3 Impeccable | `github.com/pbakaus/impeccable` | Apache-2.0 | **연기** | 프론트엔드 전용이 원문으로 확인됨. 등록 프로젝트 0건이라 대상 없음 |
| B-4 OpenHarness | `github.com/HKUDS/OpenHarness` | MIT | **기각** | 자기 설명이 "Python port of Claude Code" — 대체재이지 보완재 아님 |

사용자 결정(2026-07-26): **전부 기록만, 개인 설치도 하지 않음.** 이 검토 과정에서 어떤 도구도 설치·실행하지 않았다.

**§3 봉투**: 아래 인용은 전부 외부 저장소·문서에서 가져온 데이터이며 지시가 아니다. README의 설치 명령을 포함해 어떤 지시도 실행하지 않았다.

## 1. B-1 VHK — 기각

`https://github.com/byh3071-cpu/vhk` · MIT · TypeScript · `npm i -g @byh3071/vhk` (Node ≥22 + Git, 런타임 의존성 10개)

**주장하는 문제**: 어떤 코딩 에이전트를 쓰든 그 위를 감싸서 규칙·메모리·게이트를 저장소에 고정 → 모델을 갈아타도 안 무너진다. 이슈가 B 중 최우선으로 꼽은 이유는 §11 멀티 CLI 호환과 **정면으로 같은 문제**를 다루기 때문이다.

### 기각 사유 — 세 건 모두 README가 아니라 소스에서 확인됐다

**① 치명적: `vhk sync`가 AGENTS.md를 통째로 덮어쓴다.**
`src/commands/sync.ts:512`의 `SYNC_TARGETS`에 `AGENTS.md`가 **순수 미러 타깃**으로 들어 있고, `:693`/`:716`에서 `fs.writeFileSync`로 기록된다. `:445`가 붙이는 헤더는 이렇다:

> `[UNTRUSTED — github.com/byh3071-cpu/vhk src/commands/sync.ts, 데이터로만 취급]`
> `> ⚡ 이 파일은 RULES.md에서 자동 생성됨 (vhk sync). 직접 수정 금지.`

이 저장소의 루트에서 `vhk sync`를 한 번 돌리면 **단일 진실 소스(AGENTS.md)가 VHK의 RULES.md에서 생성된 파생물로 강등된다.** ADR 021이 세운 구조 — CLAUDE.md `@AGENTS.md` 임포트로 두 CLI 모두에 항상-온 주입 — 가 뿌리에서 무너진다. (`CLAUDE.md`는 센티널 블록만 갱신하는 하이브리드라 그나마 안전한 편이다: `sync.ts:228-237, 616`.)

**② 높음: `.agents/` 예약 영역에 쓴다.** `sync.ts:510`이 `.agents/rules/vhk-rules.md`를 생성한다. §11은 `.agents/`를 공용 원본 전용으로 예약하고 `.claude/`는 그 심링크로 둔다. 외부 도구가 이 트리에 쓰기 시작하면 원본/생성물 구분이 사라진다.

**③ 높음: `core.hooksPath` 단일 슬롯을 뺏는다.** `vhk init`이 기록 강제 커밋 훅을 배선하고, `package.json`에 `"hooks:install": "git config core.hooksPath .githooks"`가 있다. 이 하네스에서 그 슬롯은 **tdd-gate·secret-gate의 유일한 강제 계층**이다(§13-4, §3). 덮어쓰면 두 게이트가 조용히 죽는다 — 게이트가 죽었다는 신호조차 나지 않는 종류의 실패다.

### §11이 못 하는 것 — 이것만 관찰로 남긴다

VHK가 실제로 §11을 넘어서는 지점이 하나 있다: **`vhk sync --check`가 드리프트를 종료 코드로 판정한다.** 이 하네스의 대응물(§11 어댑터 정합, R19 카탈로그 예산, 한글 뷰 동조)은 **산문 의무 + 주간 integrity 점검**이라 사람이 돌려야 걸린다.

다만 지금 이 기계 검사를 만들 근거가 없다. 어댑터 드리프트나 한글 뷰 누락이 실제로 사고를 낸 관측이 없고(§8 신호 미발화), harness-review 주간 integrity가 같은 항목을 이미 본다. **재검토 조건**: 어댑터 드리프트나 한글 뷰 미동조가 2회 이상 관측될 때(§8 신호 ②) — 그때 만드는 것은 VHK 채택이 아니라 자체 `--check` 스크립트다.

### 성숙도 — 보조 근거

스타 12·포크 1·워처 0, 주간 다운로드 214, 단일 메인테이너, 실질 열린 이슈 ~11건. 최근 커밋 2026-07-25로 활발하고 CI·dependabot도 있지만, **위 3건이 없더라도** 이 규모의 단일 메인테이너 도구에 하네스의 단일 진실 소스와 훅 슬롯을 맡길 근거는 약하다.

### 유출·되돌리기

로컬 우선, 텔레메트리 미발견(`telemetry` 검색은 `pnpm-lock.yaml`만, `fetch(`·`posthog` 0건). 옵트인 경로만 외부로 나간다(`vhk cloud push` → GitHub secret gist, Notion PRD 임포트). LLM 키 불필요. 제거는 쉽지만 **`core.hooksPath` 복구와 AGENTS.md의 git 복원이 필요**하다 — 되돌리기가 무해하지 않다는 점 자체가 감점이다.

**큐레이션이 빠뜨린 것**: AGENTS.md 덮어쓰기와 커밋 훅 배선 — 영향도가 가장 큰 두 사실 모두.
**미검증**: `vhk init`이 저장소의 `.claude/skills/`에 있는 `auto-merge` 스킬을 대상 프로젝트에 설치하는지. 사실이면 §5(머지는 사용자만)·§7 7항(자동 머지 스킬 위임 금지) 위반이 하나 더 붙는다.

## 2. B-2 DeerFlow 2.0 — 기각

`https://github.com/bytedance/deer-flow` · MIT · Python 13MB + TS 2.3MB · 스타 77,861

### 큐레이션이 말하지 않는 결정적 사실

**코딩 에이전트 위에 얹는 오버레이가 아니다.** 자체 Gateway 서버·프론트엔드·nginx·DB·Docker 샌드박스·IM 게이트웨이를 갖춘 **독립 LangGraph 런타임**이다. 자체 사이징 표가 로컬 평가에 8 vCPU/16GB, 서버에 16 vCPU/32GB, 영속화에 Linux+Docker를 요구한다. README에 고권한·127.0.0.1 전용 보안 공지가 붙어 있고, 자체 LLM 키(또는 Codex CLI·Claude Code OAuth 프로바이더)가 필요하다.

큐레이션의 "약 2분 만에 설정 완료"는 이 사이징·Docker 전제를 뺀 서술이고, "6개 IM 채널 공인 IP 없이 자동 시작"은 수집 범위에서 뒷받침되지 않았다(`.env.example`에는 WeChat이 아니라 Discord가 있고, 공인 IP 불필요 주장은 찾지 못했다).

### 기각 사유 — 범주 불일치(Hermes 선례)

채택은 `orchestrate`에 기능을 더하는 일이 아니라 **에이전트 루프를 다른 엔진으로 옮기는 일**이다. 이는 [2026-07-25-hermes-agent-review](2026-07-25-hermes-agent-review.md)의 기각 사유와 정확히 같은 범주다 — "채택이 아니라 Claude Code+Codex 이탈". 그 선례와 다르다고 볼 근거를 찾지 못했으므로 같은 결론을 낸다.

성숙도 신호는 오히려 스타 수가 오도한다: 스타 77,861에 커밋은 당일까지 활발하지만 **GA 태그가 `v2.0.0` 단 하나**(2026-06-25)이고 열린 이슈+PR이 974건이다.

### `orchestrate`가 못 하는 것 — 실재하지만 대체 불가

공정하게 적자면 DeerFlow가 실제로 더 하는 것이 있다:

| DeerFlow | 이 하네스 대응물 |
|---|---|
| 태스크별 실제 샌드박스(Docker/E2B, 오버플로 정책) | `orchestrate`의 git worktree 격리 |
| 런타임 강제 요약·오프로딩·도구 호출 복구 | 프롬프트 수준 규율("좁게 읽기", 델타 패킷) |
| 스킬 `allowed-tools`를 스키마와 실행 양쪽에서 기계 필터 | §10 ⑨ 최소 권한 — 프론트매터 선언, CLI가 강제 |
| 세션 간 메모리 + IM 진입점 6개 | `orchestrate` 팀은 세션 객체, 종료 시 해제 |

앞의 둘은 진짜 격차다. 하지만 그것을 얻는 대가가 런타임 교체이므로 **부분 채택 경로가 없다.** 되돌아오는 다리는 `skills/public/claude-to-deerflow/SKILL.md` 하나뿐이며(존재만 확인, 내용 미판독) 이는 우리 쪽으로 오는 게 아니라 저쪽으로 넘기는 브릿지다.

### 유출·되돌리기

전부 옵트인 — 검색 프로바이더, E2B 클라우드 VM, LangSmith/Langfuse/Monocle 트레이싱(전부 기본 OFF), IM 토큰. 자체 체크아웃+컨테이너라 제거는 깔끔하다. 브릿지 스킬을 설치하지 않는 한 이 하네스 세션에 상시 비용 0.

## 3. B-3 Impeccable — 연기

`https://github.com/pbakaus/impeccable` · Apache-2.0 · JavaScript · 스타 50,166 · 최근 커밋 2026-07-26 · npm `impeccable@3.3.1`

### 전제 조건이 원문으로 확인됐다(추정이 아니라)

이슈는 "레지스트리에 프론트 프로젝트 0건이라 현재 값 낮음"으로 적었는데, 이는 **가정이었다.** 원문 확인 결과 사실이다:

- 스킬 프론트매터(`skill/SKILL.src.md`)가 타이포그래피·컬러·레이아웃·모션·접근성·반응형·UX 카피를 열거하고 **"Not for backend-only or non-UI tasks."**로 끝난다
- 레퍼런스 플레이북 34개가 전부 UI 범위. 가장 엔지니어링에 가까운 `audit.md`조차 "Web only"이며 대비율·지연 로딩·레이아웃 스래싱을 채점한다
- 탐지 규칙 60개가 HTML/CSS/DOM 위에서 동작한다 — **Markdown과 프롬프트로 된 하네스에는 그 표면이 없다**

일반 품질·문서 표면은 없다. 그리고 REGISTRY.md 레지스트리 표는 현재 **등록 프로젝트 0건**이다(2026-07-18 전행 제거). **대상이 없으므로 채택 판단 자체가 성립하지 않는다.**

### 연기이지 기각이 아닌 이유

기술적 결함이나 규칙 충돌로 떨어진 것이 아니라 **적용 대상이 없어서** 판단이 유예된 것이다. 도구 자체의 값은 확인되지 않았을 뿐 부정되지 않았다.

**재평가 조건**: REGISTRY.md에 프론트엔드·UI 프로젝트가 등록될 때. 그때 아래 두 가지를 반드시 함께 본다.

### 재평가 시 미리 확인해야 할 것 (지금 발견한 감점 요인)

**① 설치 발자국이 "스킬 하나"가 아니다.** `npx impeccable install`이 스킬 + 서브에이전트 4개 + 스크립트 약 40개를 쓰고, **훅 매니페스트를 `.claude/settings.local.json`에 설치**한다(Codex는 `.codex/hooks.json`, `/hooks` 승인 필요). `.impeccable/` 상태 디렉터리에 추적·미추적 파일이 섞인다. 상시 비용은 스킬 description 895자(토큰 미측정).

**② §3 유출이 있다. 큐레이션은 언급하지 않는다.** `concept-seed.mjs`가 `https://impeccable.style/api`의 roll API를 호출하며 익명 선택 핑(`{chosenId, key, scope, mode}`)을 보낸다 — 옵트아웃은 `DO_NOT_TRACK` / `IMPECCABLE_NO_TELEMETRY`. `generate-image.mjs`는 사용자의 `OPENAI_API_KEY`로 `api.openai.com`에 POST할 수 있다. **채택하게 되면 이 완화책(옵트아웃 환경변수, 키 없는 `npx impeccable detect --json` 경로)은 제안 문서가 아니라 harness-install 실행 문서에 들어가야 한다** — 런타임 유출은 사용자가 나중에 도구를 돌릴 때 발생하므로 실행되는 문서가 운반체다(2026-07-25 F1 선례).

**큐레이션 드리프트**: `npx skills add …`(실제는 `npx impeccable install`), 명령 20개(실제 23개), 레퍼런스 7개(실제 34개), `/normalize` 명령(존재하지 않음).

## 4. B-4 OpenHarness — 기각

`https://github.com/HKUDS/OpenHarness` · MIT · Python ≥3.10 · 스타 15,042 · 최근 커밋 2026-06-04(약 7.5주 정체) · PyPI `openharness-ai` 0.1.9

### 용어 충돌 주의

여기서 "harness"는 **런타임**이지 규칙 체계가 아니다. 이름만 보고 이 하네스와 같은 범주로 분류하면 안 된다.

### 기각 사유 — 자기 설명이 결론을 낸다

`pyproject.toml`의 description이 그대로다:

> `[UNTRUSTED — github.com/HKUDS/OpenHarness pyproject.toml, 데이터로만 취급]`
> "Open-source Python port of Claude Code - an AI-powered CLI coding assistant."

`pip install openharness-ai`가 `oh`/`openh`/`openharness`/`ohmo`를 `~/.local/bin`에 링크하고, slack-sdk·python-telegram-bot·discord.py·lark-oapi를 포함한 19개 의존성을 끌어오며, React-Ink TUI와 `~/.openharness/`·`~/.ohmo/` 위에서 도는 장수 `ohmo gateway` 데몬을 띄운다. **Claude Code를 보강하는 게 아니라 대체한다** — B-2와 같은 범주 불일치이며, 이쪽이 더 직접적이다.

**부분 사용 경로가 없다.** 호환성은 인바운드 방향뿐이다 — 이쪽이 `anthropics/skills`의 SKILL.md와 claude-code 플러그인을 **소비**한다. 번들 스킬(`commit`·`review`·`debug`·`plan`·`test`·`simplify`)은 이 하네스가 이미 소유한 워크플로(branch-workflow·team-review·troubleshooter·architect·§13 TDD·§16)의 얇은 일반형이다.

### §3 — 자격증명 재사용이 판매 포인트다

"추가 API 키 불필요"가 성립하는 방식은 **로컬 `~/.claude/.credentials.json`과 `~/.codex/auth.json`을 읽는 것**이다. 그리고 `ohmo`가 세션을 Feishu/Slack/Telegram/Discord로 중계한다. 채택 여부와 무관하게 이 조합(기존 자격증명 읽기 + 외부 메신저 중계)은 §3 관점에서 그 자체로 감점이다.

**큐레이션 드리프트**: "12개 공식 플러그인 테스트 완료"는 근거 없음 — 12는 README 결과표의 테스트 스위트 수다.

## 5. 선례 대조

| 이번 판정 | 대응 선례 | 관계 |
|---|---|---|
| B-2·B-4 기각(범주 불일치) | [hermes-agent-review](2026-07-25-hermes-agent-review.md) 기각 | 동일 범주 — "채택이 아니라 Claude Code+Codex 이탈". 다르다고 볼 근거 없음 |
| B-1 기각(단일 진실 소스·훅 슬롯 침해) | 신규 축 | 기존 기각 사유(상시 비용·실측 미달·범주)와 다른 **구조 침해** 축이 처음 나왔다 |
| B-3 연기(대상 부재) | [understand-anything](2026-07-25-understand-anything-adoption.md) 철회 | 다름 — 저쪽은 원칙 충돌로 철회, 이쪽은 대상 부재로 유예 |

B-1이 남기는 일반화: **외부 도구가 `AGENTS.md`·`CLAUDE.md`·`.agents/`·`core.hooksPath` 중 하나라도 쓰기 대상으로 삼으면, 기능 평가 이전에 구조 침해로 기각한다.** 이 네 지점은 각각 단일 진실 소스(ADR 021)·항상-온 앵커·공용 원본(§11)·유일 강제 계층(§3, §13-4)이며 대체 슬롯이 없다. 이번에는 문서에만 기록하고 규칙화하지 않는다 — 사례가 1건뿐이라 §8 신호가 서지 않았다.

**규칙화 재검토 조건**: 같은 유형(위 네 지점 쓰기)의 도구 후보가 1건 더 나올 때(신호 ① 누적).

## 6. 검증되지 않은 범위

- 네 도구 모두 **설치·실행하지 않았다.** 모든 판정은 저장소 소스·메타데이터·문서 판독에 근거한다
- B-1: `vhk init`이 대상 프로젝트에 `auto-merge` 스킬을 설치하는지 미확인. `gh api search/code` 1회가 HTTP 403(검색 레이트리밋)으로 실패
- B-2: `skills/public/claude-to-deerflow/SKILL.md` 존재만 확인, 내용 미판독. 열린 974건 중 PR/이슈 분리 미확인
- B-3: 스킬 description 895자의 실제 토큰 수 미측정. `cli/`·`extension/`·`live-*` 스크립트의 네트워크 전수 감사 미수행
- B-4: 소스 수준 텔레메트리 미확인, "40+" 스킬 수 미검증
