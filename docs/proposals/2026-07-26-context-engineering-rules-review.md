# 설계 검토: Claude 5 세대 컨텍스트 엔지니어링 규칙 대조

- **날짜**: 2026-07-26
- **대상**: 상시 로드 구성(`CLAUDE.md`, `AGENTS.md`, 스킬 description), ADR 021·032
- **1차 출처**: [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) (Anthropic)
- **결론**: **부분 채택** — 미설치 도구명 정리 + 순수 중복 앵커 축소는 채택, 상시 로드 구조 개편은 기각(구조적 제약), 80% 감축 목표는 범주 오적용으로 기각

## 1. 배경

이슈 #41 우선순위 A-1. GeekNews 큐레이션(`topic?id=31782`)이 "시스템 프롬프트 80% 감축·progressive disclosure"를 제목으로 달고 있어, ADR 032가 이미 수행한 상시 로드 압축에 **추가 여지가 있는지, 이미 수렴했는지**가 판정 대상이었다.

§7 8항에 따라 큐레이션 요약은 근거로 쓰지 않고 1차 출처를 따라갔다. GeekNews 페이지에는 소스 링크가 노출되지 않아 웹 검색으로 원문을 특정했다.

## 2. "80% 감축" 주장의 실제 범위 (범주 확인)

원문의 근거는 이 한 문장이 전부다.

> We removed over 80% of **Claude Code's system prompt** for models like Claude Opus 5 and Claude Fable 5 with no measurable loss on our coding evaluations.

원문이 삭제 전 실물로 인용한 대상은 다음과 같은 **모델 행동 미시 제어 규칙**이다.

> *In code: default to writing no comments. Never write multi-paragraph docstrings or multi-line comment blocks — one short line max. Don't create planning, decision, or analysis documents unless the user asks for them.*

즉 감축 대상은 **제품 시스템 프롬프트의 행동 제약**이지, 라우팅·가드레일·조직 규약이 아니다. 이 하네스의 AGENTS.md 22,370B는 대부분 후자다(§7 라우팅 2,409B, §3 가드레일 1,858B, §5 git 규약 2,126B 등). **80%를 이 하네스의 목표 수치로 옮기는 것은 범주 오적용이며, 근거가 없다.**

## 3. 상시 로드 실측 (2026-07-26)

| 구성 | 바이트 | 비고 |
|---|---|---|
| AGENTS.md | 22,370 | R14 예산 32,768B의 68% |
| CLAUDE.md | 4,031 | |
| 스킬 description 17개 | 6,236 | R19 예산 9,000B의 69%, 평균 367B |
| **상시 로드 합계** | **32,637** | |
| SKILL.md 본문(지연 로드) | 197,590 | 상시 대비 **6.1배** |

상시 : 지연 = 1 : 6.1. 원문이 권고하는 점진적 공개는 이미 강하게 적용되어 있다.

## 4. 원문 권고 8축 대조

| # | 원문 권고 | 하네스 현황 | 판정 |
|---|---|---|---|
| ① | 규칙보다 판단 | §3은 원문도 인정하는 worst-case 가드레일. §13·§16은 원문이 유지 권장하는 영역(*"skills encode particular opinions, knowledge, or best practices that are particular to you"*) | 기수렴 |
| ② | 예시보다 인터페이스 | ADR 026이 이미 positive·pointed allowances 채택. 에이전트 frontmatter(`tier`, `tools`)가 열거형 인터페이스 | 기수렴 |
| ③ | 점진적 공개 | ADR 021(이력 분리)·032(delta packet), 스킬 본문 197KB 지연 로드 | 기수렴 |
| ④ | **반복 지침 삭제** | CLAUDE.md 앵커에 재기술 존재 — 5절에서 분해 | **부분 여지** |
| ⑤ | 자동 메모리 | §8이 이미 `memory/` 사용 | 기수렴 |
| ⑥ | 단순 도구 설명 | 스킬 description 평균 367B, 예산 내 | 기수렴 |
| ⑦ | **풍부한 참조 자료** | §13-1 스펙이 markdown 전용. rubric·테스트 스위트·HTML 아티팩트 형태 미도입 | **신규 착안** |
| ⑧ | CLAUDE.md 경량화 + 스킬 분산 | 구조적 제약으로 채택 불가 — 6절 | **기각** |

## 5. ④ 축 분해 — CLAUDE.md 앵커 7개 실측

ADR 021은 앵커의 근거를 **두 가지**로 명시했다.

1. **관측된 실패 방어** — 2026-07-16 사용자 대면 요약이 영어로 새는 사건. §15가 AGENTS.md에만 있어 항상-온이 아니었던 것이 원인.
2. **긴 문서 내 주목도 희석 방어** — *"`@import`(항상-온)와 앵커(요약, 최상단)의 이중 보장"*.

원문이 무효화하는 것은 **근거 2의 일반론**이다(*"Earlier Claude models ... more likely to listen to instructions at the end of their context window than at the start. We found we could delete these repeat examples"*). **근거 1은 이 하네스에서 실제로 관측된 사건이므로 원문이 무효화하지 않는다.** 원문 자신도 *"Avoid making them overconstrained, **except in highly important areas**"*로 중요 영역의 예외를 남긴다.

| 앵커 | 바이트 | AGENTS.md·스킬과의 관계 | 판정 |
|---|---|---|---|
| Output language (§15) | 279 | §15 요약이나 **관측된 실패 방어**(ADR 021 직접 동기) | **유지** |
| Routing (§7) | 1,066 | 17개 스킬 description의 역방향 색인. 대부분 재기술이나 조합 규칙(`troubleshooter`→`implementer`, `/watch` 한정 등)은 고유 | 혼합 — 부분 축소 |
| Orchestration invariants | 726 | §7 3·5·6항 재기술 + ADR 028·032 고유분(3파일 임계, Agent 예산, background 기본값) | 혼합 — 부분 축소 |
| Skill priority (§7) | 311 | §7 7항 재기술. 추가분은 미설치 도구명뿐 | **순수 중복** |
| Interview-first (§13-0) | 385 | §13-0 요약 | **순수 중복** |
| User comprehension (§13) | 343 | §13 서두 요약 | **순수 중복** |
| Context/output economy | 669 | ADR 032 — AGENTS.md에 없음 | **유지(고유)** |

**순수 중복 합계 1,039B = CLAUDE.md의 26%, 상시 로드의 3.2%.** 혼합 앵커 1,792B는 고유분을 남겨야 하므로 부분 축소만 가능하다.

### 부수 발견 — 미설치 도구명 상시 로드

`Skill priority` 앵커가 `SuperClaude`와 `gstack`을 상시 로드로 지목하는데, 실측 결과 **둘 다 미설치**다.

- SuperClaude: 2026-07-18 tool-audit이 51,331 메시지 전량 0건 실측 후 제거(세션당 ~36k 토큰). 사용자 전역 CLAUDE.md에 제거 사실 기재됨
- gstack: `~/.claude/skills/`·`~/.claude/plugins/installed_plugins.json` 어디에도 없음(설치 플러그인은 `document-skills`, `codex` 2종뿐)

바이트는 작지만, **존재하지 않는 도구에 대한 우선순위 규칙이 매 세션 라우팅 판단에 노이즈로 남는다**. harness-review 신호 ④(참조되지 않는 규칙)에 해당한다.

## 6. 기각 — 상시 로드 구조 개편(원문 ⑧)

원문의 *"CLAUDE.md를 가볍게, 나머지는 스킬 파일 트리로 점진 공개"*는 **스킬 자동 로드가 보장될 때만** 성립한다.

§12가 "문서가 규칙의 운반체"라고 못 박은 이유가 정확히 그 반대 사정이다 — 스킬·훅은 세션 cwd 상대로만 로드되며, §11이 지원하는 Codex 쪽에서 동일 보장이 없다. AGENTS.md의 §3 가드레일·§5 git 규약을 스킬로 옮기면 **Codex 세션에서 가드레일이 소실된다.**

원문은 Claude Code 단일 CLI를 전제하므로 이 제약을 다루지 않는다. 멀티 CLI 하네스에서는 채택할 수 없다.

## 7. 채택 설계

### Layer 1 — 미설치 도구명 제거 (즉시, 위험 0)

`Skill priority` 앵커에서 `SuperClaude`·`gstack` 삭제. 두 도구의 실측 부재가 근거이며, 재설치 시 harness-review 신호로 재등록된다.

### Layer 2 — 순수 중복 앵커 3개 축소 (1,039B)

`Skill priority`·`Interview-first`·`User comprehension`은 AGENTS.md 원본의 요약일 뿐이고 관측된 실패 이력이 없다. 원문 ④에 따라 삭제하거나, 유지한다면 **한 줄 포인터**(§ 번호만)로 축소한다.

**단, 이 3개는 §13(사용자 이해=완료)·§7(스킬 우선순위)처럼 우회 시 손실이 큰 규칙이다.** 삭제 후 우회가 관측되면 ADR 021 근거 1(관측된 실패)이 성립하므로 즉시 복원한다 — 복원 조건을 ADR에 명시하는 것이 이 Layer의 전제다.

### Layer 3 — 신규 착안 관찰 보류 (원문 ⑦)

rubric 기반 검증 에이전트와 비-markdown 스펙(테스트 스위트·HTML 아티팩트)은 순수 신규 역량이다. 다만 현재 레지스트리에 등록 프로젝트가 0건이라 적용 대상이 없다. **프로젝트 등록 시 team-review·§13-1에 대해 재평가**한다(Impeccable 항목과 동일한 보류 사유).

## 8. 채택하지 않는 것 (명시적 비목표)

| 비목표 | 사유 |
|---|---|
| 80% 감축 목표 수치 | 범주 오적용 — 대상이 제품 시스템 프롬프트이지 조직 규약이 아니다(2절) |
| AGENTS.md의 스킬 분산 | §11·§12 멀티 CLI 제약 — Codex 가드레일 소실(6절) |
| §3·§13·§16의 "판단 위임" 전환 | 원문이 worst-case 가드레일과 팀 고유 opinion은 유지 권장(4절 ①) |
| `Output language` 앵커 삭제 | 관측된 실패 방어 — ADR 021 근거 1(5절) |
| `Context/output economy` 앵커 삭제 | AGENTS.md에 없는 고유 정보 |

## 9. 정직한 평가

**이 하네스는 원문 권고 8축 중 6축에 이미 수렴해 있다.** 남은 여지는 상시 로드의 3.2%이며, 그마저도 주목도 방어 가치와 맞바꾸는 것이라 순수 이득이 아니다. ADR 032가 수행한 압축이 실질적으로 수렴점에 도달했다는 것이 이번 대조의 결론이다.

실질 개선은 **미설치 도구명 정리(Layer 1)** 하나이며, 이는 원문 검토가 아니라 부수적으로 발견된 것이다.

## 10. 거버넌스

- Layer 1·2는 하네스 규칙 변경 → **metaskill + 독립 reviewer 검증** 후 ADR 021 개정(앵커 계층 규율 + 복원 조건 명시)
- Layer 3는 프로젝트 등록 시까지 보류, 이슈 #41에 기록
- 이 문서는 결정이 아니라 제안이다. 채택 시 ADR로 확정한다(§6)
