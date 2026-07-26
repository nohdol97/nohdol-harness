# 하네스 설계 자료 5건 1차 출처 대조 (이슈 #41 우선순위 A-2 ~ A-6)

> 상태: **대부분 기각 — 규칙 변경 후보 1건(승인 대기)**
> 날짜: 2026-07-26
> 선행: [2026-07-26-context-engineering-rules-review](2026-07-26-context-engineering-rules-review.md) (A-1)

## 0. 이 문서가 하는 일

이슈 #41은 지식 소스(§7 8항, ADR 033)를 통해 발굴한 하네스 관련 항목 10건의 검토 목록이다. A-1은 별도 문서로 끝났고, 이 문서가 **우선순위 A의 나머지 5건**을 다룬다. 도구 후보(B 4건)는 [2026-07-26-harness-tool-candidates-review](2026-07-26-harness-tool-candidates-review.md)로 분리했다.

§7 8항의 근거 등급 규칙대로, **큐레이션 한 줄 요약은 근거로 쓰지 않았다.** 항목마다 큐레이션 페이지에서 1차 출처 URL을 뽑아 원문을 열었고, 인용 가능한 것은 따라간 1차 출처뿐이다.

## 1. 판정 요약

| 항목 | 1차 출처 | 판정 | 한 줄 사유 |
|---|---|---|---|
| A-2 OpenAI 하네스 엔지니어링 | `openai.com/index/harness-engineering/` | **기각** | §11 Codex 축을 실제로 안 건드림. 핵심 관행이 §5·§13과 정면 충돌하며 원문 스스로 고처리량 한정 |
| A-3 장기 실행 앱 하네스 | `anthropic.com/engineering/harness-design-long-running-apps` | **부분 채택** | generate-verify 불변식 보강. 새 축 1건(모델 업그레이드 시 우회 장치 재검토) |
| A-4 Meta HyperAgents | `arxiv.org/abs/2603.19461` | **기각** | 큐레이션 전제 붕괴 — 논문에 "harness" 0회. 범주·규모 불일치 |
| A-5 Managed Agents | `anthropic.com/engineering/managed-agents` | **기각(원 목적)** | "두뇌/손"이 모델 분리가 아니라 하네스/샌드박스 분리. §9 근거로 못 씀 |
| A-6 동적 워크플로우 | `claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code` | **기각(규칙 무변경)** | 실축이 §9가 아니라 §7이고 orchestrate와 기수렴 |

**전체 5건에서 나온 규칙 변경 후보는 1건뿐이다** — 4절 참조.

## 2. A-2 — "Harness engineering: leveraging Codex in an agent-first world"

- **1차 출처**: `https://openai.com/index/harness-engineering/` (OpenAI, 2026-02-11)
- **성격**: 1차 당사자이나 **자사 홍보** — OpenAI가 OpenAI 팀의 Codex 사용을 서술하고 Codex CTA로 끝난다. 저자 명시 없음
- **수집 경로 주의**: Cloudflare 403으로 `defuddle` 3회 실패. 리더 프록시로 본문을 받고 **Wayback 독립 스냅샷과 7/7 특징 문자열 대조**해 진위를 확인했다. 본문은 진짜지만 경로가 비표준이었다는 점을 기록해 둔다

### 근거 등급 — 낮음

측정 연구가 아니라 **단일 팀 내부 사례**다. 원문 전체에서 `measur*` 0회, `benchmark` 0회, `security` 0회, `TDD` 0회.

- 간판 수치 "약 1/10 시간"은 `We estimate`로 헤지된 **반사실 추정**이며 비교 대상 프로젝트가 없다
- "엔지니어당 하루 3.5 PR"은 1,500 ÷ 3으로 유도한 값인데, 같은 기간 팀이 3→7명으로 늘었음에도 **시작 인원**을 분모로 썼다
- 결함률·장애 건수·롤백 건수는 아예 없다
- 원문 자기 제한: *"should not be assumed to generalize without similar investment."*

### 기각 사유

**① 이슈가 기대한 축(§11 Codex 병행)을 실제로 안 건드린다.** 원문에 `hook` 0회, `Claude` 0회, `multi-CLI` 0회, `config.toml` 0회, `sandbox` 0회. 단일 CLI·그린필드·단일 제품 환경이라 ADR 027(어댑터)·029(훅 패리티)·031(런타임 계약)과 무관하다.

**② 실제로 닿는 유일한 축이 A-1과 중복이다.** "AGENTS.md ~100줄 목차화"는 상시 문서 크기 축인데, A-1에서 이미 상시 32,637B : 지연 197,590B = 1:6.1로 기수렴 판정을 냈다. 새 정보가 없다.

**③ 핵심 관행이 이 하네스 규칙과 정면 충돌한다.**

| 원문 관행 | 충돌 규칙 |
|---|---|
| 에이전트가 자기 PR을 squash 머지 | §5 "머지는 사용자만" |
| 블로킹 머지 게이트 최소화 | §13-4 tdd-gate 실행 게이트 |
| flaky 테스트는 재실행으로 넘김 | §13-2 신선한 최종 검증 |
| 자동 머지되는 리팩터 PR을 여는 상주 에이전트 | §5 + §13 이해도 퀴즈 게이트 |
| 의존성보다 재구현 선호(가독성 사유) | §16 필요성→기존 재사용→표준 라이브러리 등반 순서 |

원문 스스로 이를 **고처리량 환경 한정**이라 못박고 "저처리량 환경에서는 무책임하다"고 쓴다. 이 하네스는 저처리량·문서 중심이므로 원문의 자기 조건을 그대로 적용하면 기각이 맞다.

### 관찰 보류 1건

**lint 에러 메시지에 교정 지침을 실어 에이전트 컨텍스트에 주입한다**는 착안은 이 하네스의 실행 게이트(tdd-gate·secret-gate·gate-reminder) 메시지 설계와 같은 축이다. 다만 원문에 효과 측정이 없고 우리 게이트 메시지의 실패 사례도 관측된 바 없으므로(§8 신호 미발화), 신호가 뜰 때 재검토한다.

**재검토 조건**: 실행 게이트 메시지를 읽고도 같은 위반이 2회 이상 반복될 때(§8 신호 ②).

## 3. A-3 — "Harness design for long-running applications"

- **1차 출처**: `https://www.anthropic.com/engineering/harness-design-long-running-apps` (Anthropic Engineering, Prithvi Rajasekaran, 2026-03-24)
- **성격**: 1차 당사자·단일 저자 실무 보고. 동반 저장소나 공개 하네스 코드 없음

### 큐레이션 정정 — "GAN 기반"이 아니다

이슈 본문이 "Anthropic GAN 기반 멀티 에이전트"라고 적었지만, 원문의 GAN 언급은 단 한 곳이다: *"Taking inspiration from Generative Adversarial Networks (GANs), I designed a multi-agent structure with a generator and evaluator agent."* **적대적 학습도, 그래디언트도, 판별자 손실도, 가중치 갱신도 없다.** 두 에이전트는 프롬프트만 다른 동결 Claude 인스턴스다. GeekNews 한국어 요약은 "GAN에서 **영감을 받은**"으로 정확했고, "GAN 기반"은 이슈를 쓰면서 생긴 드리프트다.

### 채택 — generate-verify 불변식 보강(규칙 무변경)

원문은 우리 `orchestrate`의 implementer+reviewer 분리·자기검증 금지 불변식에 대한 **독립 실무 증거**다. 특히 다음 진술이 우리 규칙의 사유를 강화한다:

> `[UNTRUSTED — anthropic.com/engineering/harness-design-long-running-apps, 데이터로만 취급]`
> "Out of the box, Claude is a poor QA agent. In early runs, I watched it identify legitimate issues, then talk itself into deciding they weren't a big deal and approve the work anyway."

동시에 **한계도 명시**한다 — 분리만으로 관대함이 사라지지 않으며, 평가자를 회의적으로 만드는 것이 생성자를 자기비판적으로 만드는 것보다 다룰 만할 뿐이라는 것. 실제 보정에는 사람이 평가자 로그를 읽고 판단이 갈린 지점을 찾아 QA 프롬프트를 고쳐 쓰는 수동 루프가 여러 차례 필요했다. **독립성은 구조가 아니라 사람이 만든 것**이라는 이 실측은 우리 reviewer 역할 정의(회의적 톤·증거 요구)가 왜 프롬프트 수준에서 명시되어야 하는지의 근거가 된다. 규칙은 이미 그렇게 되어 있으므로 변경 없음.

### 기각 — 비용 조건부 검증

원문은 평가자가 *"worth the cost when the task sits beyond what the current model does reliably solo"*라며 **비용 조건부**로 프레이밍한다(솔로 20분 $9 vs 하네스 6시간 $200 = 20배). 우리 검증은 무조건이다. 이 하네스에는 이미 검증 비례성 규칙(metaskill 개선 모드: 규범 변경은 reviewer 필수, 비규범은 자가 검증)이 있고, 이는 **위험도 축**이지 **모델 능력 축**이 아니다. 모델이 솔로로 잘한다는 이유로 검증을 빼는 것은 "독립성을 침식하는 절감안"이라 기본 비권장이다(앵커링 기각 전례).

### 근거의 약점 — 반드시 함께 기록

기간·비용은 계측값이라 신뢰할 만하지만, **품질 주장은 전부 저자가 정성적으로 판단한 단일 미반복 실행**이다. 벤치마크·홀드아웃·반복 시행·신뢰구간·블라인드 채점이 전무하다. 저자가 서술한 "한 번에 한 구성요소씩 제거하는" 절제 실험은 **결과표가 공개되지 않았다** — 스프린트 제거 결정의 근거는 서술적 판단뿐이다. 저자 자신도 점수 순서가 불안정했다고 적는다("중간 반복본을 마지막 것보다 선호한 경우가 자주 있었다"). 이 문서의 채택분은 서술된 메커니즘의 개념적 정합성에 한정하며, 수치를 근거로 삼지 않는다.

### 새 축 1건 → 4절

## 4. 규칙 변경 후보(승인 대기) — 모델 업그레이드 시 우회 장치 재검토

**5건 전체에서 나온 유일한 규칙 변경 후보이며, 두 개의 독립된 1차 출처가 같은 결론에 도달했다는 점이 근거의 핵심이다.**

### 근거

**A-3 (2026-03-24)**: 이전 하네스는 컨텍스트 리셋(창을 비우고 구조화된 인수인계 산출물로 새 에이전트 시작)을 썼는데, 이유는 Sonnet 4.5의 "context anxiety"(한계에 가깝다고 믿으면 조기에 마무리하는 행동)였다. Opus 4.5가 그 행동을 대부분 없애자 **리셋 장치를 통째로 제거**하고 SDK 자동 압축에 맡겼다.

**A-5 (2026-04-08)**: 같은 사례를 같은 논지로 든다 — 하네스는 모델 결함에 대한 우회를 인코딩하며, 모델이 나아지면 그 우회는 *"dead weight"*가 된다.

두 출처는 다른 저자·다른 글이고 서로를 인용하지 않는다. **하네스 장치의 수명은 모델 버전에 묶여 있으며, 모델이 올라가면 일부 장치는 이득이 아니라 순비용이 된다**는 명제에 독립 도달한 것이다.

### 이 하네스의 공백

§8 진화 트리거 4신호 중 축소·효율은 신호 ④뿐이고, 그 판정 기준은 **사용 횟수**(3주 이상 미호출)와 **토큰 비용**이다. 즉 "모델이 좋아져서 존재 이유가 사라진 장치"는 **여전히 호출되고 있으면 영원히 걸리지 않는다.** 실제로 이 하네스에는 모델 행동을 보정하려고 만든 장치가 여럿 있다(gate-reminder 훅, 앵커의 재판정 문구, 델타 패킷 규율 등). 이것들이 언제 죽은 코드가 되는지 판정할 절차가 없다.

### 제안 형태 — 신호 신설이 아니라 ④ 내부 확장

§8은 **"Keep the signal set fixed"**를 명시한다. 따라서 5번째 신호를 만들지 않는다. 대신 `harness-review` **주간** 점검(신호 ④ 담당)에 발화 조건 한 줄을 추가한다:

> 세션 모델의 메이저 버전이 직전 주간 점검 이후 바뀌었다면, 그 주 ④ 점검에 **모델 결함 보정 목적으로 만든 장치의 재검토**를 포함한다. 대상은 "무엇을 막으려고 만들었는가"가 특정 모델의 관측된 행동인 규칙·훅·앵커. 판정은 그 행동이 현재 모델에서 재현되는지 실측으로 확인한 뒤 유지/제거를 제안한다.

**발화 조건**: 주간 점검 시점에 모델 메이저 버전 변경이 있었을 때만. 없으면 발화하지 않는다(매주 비용이 붙지 않는다).
**충족**: 대상 장치 목록과 각각의 재현 실측 결과가 제안에 포함됨. **위반**: 버전이 바뀌었는데 ④ 점검이 사용량만 보고 끝남.

### 미적용 사유

이슈 #41의 제약대로 하네스 규칙 변경은 metaskill + 독립 reviewer를 거쳐야 하고, 사용자 승인이 선행이다. **이 문서는 제안까지이며 적용하지 않았다.**

## 5. A-4 — Meta HyperAgents

### 큐레이션 전제가 붕괴한다

이슈가 "에이전트가 스스로 하네스를 설계"로 적은 근거는 큐레이션이 원문으로 지목한 Medium 글이다. 그런데 그 글은 **1차 출처가 아니다.**

| 계층 | URL | 성격 |
|---|---|---|
| 큐레이션 | `news.hada.io/topic?id=28430` | GN+ 요약 |
| 큐레이션이 지목한 "원문" | `cobusgreyling.medium.com/hyperagents-by-meta-892580e14f5b` | **2차 논평.** Cobus Greyling(Kore.ai), 논문 저자 아님 |
| **진짜 1차 출처(논문)** | `https://arxiv.org/abs/2603.19461` | arXiv 프리프린트 v1, 2026-03-19, **동료 심사 없음** |
| **진짜 1차 출처(코드)** | `https://github.com/facebookresearch/HyperAgents` | Python, CC BY-NC-SA 4.0 |

논문 LaTeX 원본 전문에서:

```
$ grep -ic "harness" paper.tex
0
```

**논문에 "harness"라는 단어가 한 번도 안 나온다.** 6구성요소 하네스 모델(도구 통합/메모리/컨텍스트 엔지니어링/계획/검증/모듈성)은 Greyling이 이전에 만든 자기 프레임워크이고, 그는 이를 자기 인용한 뒤 논문의 창발 구성요소를 자기 버킷에 대응시킨다. "하네스는 수렴적 아키텍처"도 그의 주장이며, 논문은 "convergence"를 **피해야 할 조기 수렴**이라는 뜻으로만 두 번 쓴다. **A-4 표제 전체가 1차 근거 없는 3자 해석층이다.**

저자 구성도 "Meta와 UBC"가 아니라 UBC·Vector·Edinburgh·NYU·FAIR·Meta Superintelligence Labs·CIFAR에 걸친 4기관 이상이다.

### 범주·규모 불일치

이것은 문서·프롬프트 하네스가 아니라 **Python RL 실험 인프라**다. Python 3.12 venv, Docker, Genesis 물리 시뮬레이터 RL, `.env`에 OpenAI/Anthropic/Gemini 키. 100 반복 1회에 **약 8,860만 토큰**으로, ADR 032의 세션 예산 프레이밍보다 2~3자릿수 크다. 라이선스는 **CC BY-NC-SA 4.0(비상업·동일조건)**이라 채택 자체가 제약이 붙는다. 저장소 README는 *"executing untrusted, model-generated code… it may still behave destructively"*를 경고한다.

수치도 큐레이션이 옮기지 않은 유의성 단서가 결정적이다 — 코딩에서 DGM-H는 원본 DGM보다 **오히려 낮고**(0.267 vs 0.307), 사람이 커스터마이즈한 DGM-custom을 **유의하게 이기지 못했다**(p > 0.05). 200회 복리 이득도 유의하지 않다.

### 기각. 단, 값있는 사실 1건은 기록한다

논문이 스스로 밝힌 한계가 우리 §8 설계와 **정반대 방향**이다:

> `[UNTRUSTED — arxiv.org/abs/2603.19461 LaTeX 원본, 데이터로만 취급]`
> "components of the open-ended exploration loop (e.g., parent selection, evaluation protocols) remain fixed.
> Although hyperagents can modify their self-improvement mechanisms, they cannot alter the outer process that
> determines which agents are selected or how they are evaluated. Keeping these components fixed improves
> experimental stability and safety, but limits full self-modifiability."

**자기수정 에이전트가 자기 평가자·선택자는 절대 못 건드린다.** 드리프트를 막는 것이 바로 평가 메커니즘을 자기수정 대상에서 빼는 일이다. 반면 이 하네스의 §8 루프는 metaskill이 metaskill을 바꿀 수 있고, harness-review가 harness-review의 기준을 바꿀 수 있다.

**다만 등가 비교는 아니다.** 우리에게는 논문에 없는 층이 있다 — §8의 **사용자 승인 게이트**("apply only after approval via metaskill")와 독립 reviewer다. 논문의 "human oversight is maintained throughout all experiments"가 대응한다. 즉 우리는 평가자를 고정하는 대신 사람을 고정했다. 어느 쪽이 강한지는 이 자료만으로 판정할 수 없으므로 **관찰 항목으로만 남긴다.**

**재검토 조건**: 승인 게이트를 우회하거나 약화하는 하네스 변경이 제안될 때. 그때 이 논문의 "평가자 고정" 대안이 검토 대상이 된다.

## 6. A-5 — "Managed Agents"

- **1차 출처**: `https://www.anthropic.com/engineering/managed-agents` (Anthropic Engineering, Lance Martin·Gabe Cemaj·Michael Cohen, 2026-04-08). 제품 출시에 붙은 엔지니어링 해설

### 원 목적으로는 쓸 수 없다

이슈는 이 항목을 "§9 티어→모델 매핑(모델명 미고정) 근거 보강"으로 분류했다. **전제가 틀렸다.**

"두뇌와 손"은 **모델 대 모델**이 아니라 **하네스 대 샌드박스** 분리다. 두뇌 = "Claude와 그 하네스"(루프 전체), 손 = 샌드박스와 도구이며 각각 `execute(name, input) → string`으로 축약된다. **Claude는 하나뿐이고 모델-역할 배정이라는 개념이 없다.** 그래서 원문에는 모델 선택 기준이 아예 없다 — 하네스는 *"샌드박스가 컨테이너인지 휴대폰인지 포켓몬 에뮬레이터인지 알지 못한다"*. §9에 대한 근거로 인용할 수 없다.

큐레이션은 두뇌를 "하네스"로만 옮기며 Claude를 빠뜨렸는데, 이 누락이 바로 모델 분리라는 오독을 만든다.

### §9의 결론은 지지하지만 전제가 다르다

§9의 사유는 **모델명·라인업이 바뀐다**는 것이다. A-5의 사유는 **가정이 노후화한다**는 것이다 — 4절의 채택 후보가 여기서 나온다. 결론이 같다고 근거를 바꿔 붙이면 규칙의 적용 범위가 조용히 달라지므로, §9 사유는 그대로 두고 4절을 별건으로 다룬다.

### 수치는 인용 불가

p50 TTFT −60%, p95 −90%. **측정 방법이 전무하다** — 표본 수, 워크로드 구성, 측정 창, 베이스라인 어느 것도 없다. 게으른 컨테이너 프로비저닝에서 나온 아키텍처 지연 결과이며 비용·정확도·모델 선택에 대해 아무 말도 하지 않는다.

### 부수 관찰 — §3 쪽이 더 강하게 닿는다

원문이 서술하는 자격증명 격리(클론 시점에 git remote를 미리 배선, MCP OAuth를 프록시 뒤 볼트에 보관)는 구조적 프롬프트 인젝션 방어다. §3의 봉투 규칙과 같은 축이지만, 이 하네스는 등록 인프라 프로젝트가 0건이라 적용 대상이 없다. **재검토 조건**: REGISTRY.md에 인프라·배포 대상 프로젝트가 등록될 때.

## 7. A-6 — "A harness for every task: dynamic workflows in Claude Code"

- **1차 출처**: `https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code` (claude.com, Thariq Shihipar·Sid Bidasaria, 2026-06-02). 출시 공지가 아니라 **1차 당사자 실무 포스트**

### 실체 정정

동적 워크플로우는 스킬도, 런타임 생성 프롬프트 문자열도 아니다. **Claude가 직접 작성해 서브에이전트를 스폰·조율하는 JavaScript 파일**이다. 스킬은 배포 경로일 뿐이며, 원문은 스킬로 묶인 워크플로를 *"그대로 실행할 스크립트가 아니라 템플릿으로"* 다루라고 권한다. 동기는 단일 컨텍스트 작업의 세 실패 모드다 — agentic laziness, self-preferential bias, goal drift.

### 기각 — 실축이 §9가 아니라 §7이고, 그 §7은 기수렴이다

원문이 다루는 문제(누가 계획을 쥐는가, 언제 팬아웃하는가, 검증을 어떻게 독립시키는가)는 `orchestrate`가 이미 다루는 문제다. Phase 0-1 게이트, 역할별 발행(explorer/troubleshooter/reviewer), 팀 모드, `_workspace/` 파일 기반 핸드오프가 모두 대응한다. 원문에 측정 수치는 **하나도 없고**("35 of 50"은 예시, 에이전트 상한은 제품 제한), 큐레이션은 이를 "20개만"으로 잘못 옮겼다.

### §9와의 긴장 — 충돌이 아니라 층위 차이(명확화만 기록)

원문은 *"a classifier agent can do this research and then route to Sonnet or Opus based on the expected complexity"*라며 런타임 모델 선택을 예로 든다. §9는 에이전트 프론트매터에 모델명을 고정하지 말라고 한다. **둘은 충돌하지 않는다** — §9가 금지하는 것은 **정의 시점**에 모델명을 박제하는 것이고, 원문이 말하는 것은 **실행 시점**의 선택이다. 실행 시점 선택은 §9의 "사용 중인 CLI의 현재 라인업에서 기준에 따라 고른다"와 오히려 같은 방향이다. 규칙 변경 불필요.

### 관찰 보류 1건 — 출처 기반 트리거 게이팅

원문의 `ultracode` 키워드는 입력 출처가 `{ kind: "human" }`으로 각인된 경우에만 발화하고 `-p`·웹훅·PR 코멘트·스케줄 실행에서는 차단된다. **외부에서 흘러든 텍스트가 트리거를 발화시키지 못하게 하는 실행 계층 장치**로, §3 봉투 규칙(주입 시 untrusted 표시)과 같은 문제를 다르게 푼다. 우리 §3은 모델이 따르는 문서 규율이고 이쪽은 런타임 강제다.

다만 **이 하네스가 지금 이 장치를 만들 근거가 없다**. autoloop 드라이버가 유일한 무인 경로이고 해당 스펙에 봉투 규칙이 이미 걸려 있으며, 봉투 무시로 인한 실패는 관측된 적이 없다(§8 신호 미발화).

**재검토 조건**: 외부 텍스트가 하네스 트리거를 발화시킨 사례가 1회라도 관측될 때(§8 신호 ③, 관측 즉시 1회차 기록 규율 대상).

## 8. 이 검토가 남기는 것

- **적용된 규칙 변경**: 없음(A-1 Layer 1은 별건으로 이미 적용)
- **승인 대기 규칙 변경**: 1건 — 4절, 모델 업그레이드 시 우회 장치 재검토를 신호 ④ 주간 점검 안에 편입
- **재검토 조건이 달린 관찰**: 4건 — A-2 게이트 메시지(신호 ②), A-4 승인 게이트 약화 제안 시, A-5 인프라 프로젝트 등록 시, A-6 외부 텍스트 트리거 발화 관측 시(신호 ③)
- **큐레이션 오류 정정 3건**: A-3 "GAN 기반"(영감받음), A-4 "에이전트가 스스로 하네스 설계"(논문에 harness 0회), A-5 "두뇌와 손 = 모델 분리"(하네스/샌드박스 분리)

마지막 항목이 이번 검토의 부수 소득이다. §7 8항이 "한 줄 요약은 근거가 아니다"라고 못박은 이유가 5건 중 3건에서 실제로 확인됐다 — **원문을 열지 않았다면 세 건 모두 틀린 전제 위에서 설계 판단을 했을 것이다.**

## 9. 검증되지 않은 범위

- A-4 논문 그림 파일(`results_task.pdf` 등) 미판독 — 그림에만 있는 값은 미검증
- A-4 부록 5개 표본 추출만 수행, 전수 열거 아님. 라이선스는 README 배지 주장이며 LICENSE 본문 미확보
- A-3 절제 실험 결과는 원문이 공개하지 않아 외부 검증 불가
- A-3의 선행 글 `anthropic.com/engineering/effective-harnesses-for-long-running-agents` 미조회 — 컨텍스트 리셋 메커니즘의 원 근거가 그쪽에 있다
- A-2는 1차 출처가 403이라 리더 프록시 경유. Wayback 대조로 진위는 확인했으나 직접 조회는 아님
- A-6의 실행 계층 통제(입력 출처 각인, 승인 프롬프트)는 블로그 본문이 아니라 연결된 문서에서 나온 것이며, 이 하네스에서 재현 실측하지 않았다
