---
name: autoloop
description: "Launch, monitor, and stop an unattended multi-session loop that repeatedly runs headless claude -p against one spec until its completion criteria pass - each iteration gets a fresh context (new process = auto clear) with state handed over via a local carryover note, edits run unattended while destructive ops halt the loop (never bypassPermissions), and done claims must survive a driver-run test plus a read-only reviewer verdict. Three verbs: start (preflight then nohup driver), status (digest note+log), stop (STOP file, graceful). Use when the user wants work to continue autonomously across context limits - 자율 루프, 무인 실행, 밤새 돌려줘, autoloop, autonomous loop, 루프 돌려줘, 무인 개발. Do NOT use for a recurring prompt on an interval (→ /loop, Claude Code built-in), scheduled cloud agents (→ schedule, Claude Code built-in), manual same-machine handoff (→ carryover), cross-session epic tracking (→ work-tracker), or infra/deploy specs (destructive ops halt it). Re-run keywords - autoloop, 자율 루프, 무인 실행, 루프 상태, 루프 정지."
---

# autoloop — 자율 멀티세션 루프 (발사대)

## 왜 이 스킬인가

한 세션 컨텍스트를 넘는 작업을 무인으로 완주하려면 "wrapup → clear → 재개"가 자동이어야 하는데, `/clear`는 CLI 명령이라 세션 안의 모델이 스스로 부를 수 없다. 해법은 세션 **바깥**의 드라이버 프로세스가 `claude -p`(headless)를 반복 기동하는 것 — **새 프로세스 = 새 컨텍스트**라 clear가 구조적으로 해결되고, 반복 간 상태는 carryover 노트로 넘어간다. 이 스킬은 그 드라이버(`scripts/driver.py`)의 **발사대**다: 루프 본체는 세션 밖에서 돌고, 스킬은 기동·조회·정지만 담당한다.

대화형 세션의 소프트 게이트(리뷰·신선한 증거)는 무인 모드에서 침식되기 쉬우므로, 드라이버가 구조로 강제한다(스펙: `docs/specs/2026-07-19-autoloop-driver.md`):

- **안전 게이트(§3 준수)**: `acceptEdits` + 협소 화이트리스트/블랙리스트 — 읽기·편집·고정 테스트 러너만 무인, 파괴적 작업(배포·삭제·force push·DB 마이그레이션)은 세션이 `blocked`를 보고하고 루프가 멈춘다. **`bypassPermissions`는 어떤 경로로도 금지.** bare 인터프리터 그랜트(`python3:*`·`npx:*` 등)도 금지 — 블랙리스트를 감싸는 우회로가 된다. 프로젝트별 러너가 더 필요하면 `--allow-extra`로 사용자가 명시 그랜트한다. **정직한 한계**: 테스트 실행은 곧 저장소 코드 실행이라 완전 봉쇄는 아니다 — 그래서 인프라·배포가 걸린 스펙에는 이 도구를 쓰지 않는다(아래 주의).
- **검증 게이트(§13 준수)**: 테스트는 드라이버가 독립 실행한 결과만 증거(모델 자가보고 불신). `done` 주장은 읽기 전용 reviewer 검증 반복의 PASS를 받아야 확정.
- **정지 게이트**: done / blocked / stalled(연속 무진전) / exhausted(반복 상한) / stopped(STOP 파일) / cost(비용 상한) / error(프로세스 연속 실패) — 반드시 하나로 끝난다. 무한 루프 불가.

## 동사 분기 (첫 판단)

호출 인자에서 동사를 정한다: `status`·`상태` → **status**, `stop`·`정지`·`멈춰` → **stop**, 그 외(스펙 경로 포함) → **start**.

## start — 기동

1. **사전 검사 (오라클 없는 루프 금지)**:
   - 대상 스펙 파일이 존재하고 "완료 기준" 절이 있는지 확인한다(없으면 기동 거부 — 먼저 doc-writer 스펙 템플릿으로 작성하도록 안내). 드라이버도 같은 검사를 하지만(R9), 스킬 단계에서 잡아야 사용자에게 이유를 대화로 설명할 수 있다.
   - `--test-cmd`를 사용자에게 확인한다(스펙 완료 기준을 검증하는 실제 명령). 없으면 "독립 증거가 약해진다"를 경고하고 진행 여부를 묻는다.
   - 파괴적 작업이 예상되는 스펙(배포·인프라 변경 포함)이면 **기동을 권하지 않는다** — 그 지점에서 루프가 blocked로 멈춰 무인의 의미가 없고, 안전 게이트의 한계(위) 때문에 애초에 이 도구의 대상이 아니다. 사용자가 그래도 원하면 blocked 이월 동작을 설명하고 진행한다.
   - `_workspace/autoloop/<슬러그>/STOP`이 남아 있으면 드라이버가 기동을 거부한다(R10) — 사용자에게 STOP 삭제 여부를 확인한 뒤 진행한다.
   - 표준 러너(pytest·npm test·go/cargo test) 밖의 테스트 명령이 필요하면 `--allow-extra 'Bash(<러너>:*)'`를 사용자 확인 후 붙인다(명시 그랜트 — 임의로 넓히지 않는다).
2. **기동** (하네스 루트에서 — headless 세션이 하네스를 항상-온 로드해야 하므로 §12):
   ```bash
   mkdir -p _workspace/autoloop/<슬러그>
   nohup python3 .agents/skills/autoloop/scripts/driver.py \
     --spec <스펙 경로> --project <대상 디렉토리> \
     --test-cmd '<테스트 명령>' --max-iterations 10 --stall-limit 3 \
     --work-name <슬러그> > _workspace/autoloop/<슬러그>/launch.log 2>&1 &
   ```
   기본값: max-iterations 10, stall-limit 3. 밤새 돌리는 큰 작업이면 max-iterations를 올리되 반드시 유한하게.
3. **기동 확인 후 보고**: 2~3초 뒤 `launch.log`를 읽는다 — "기동 거부"가 있으면 그 이유를 사용자에게 전하고 종료한다(조용한 no-op 금지). 정상이면 산출 경로(`_workspace/autoloop/<슬러그>/`)와 "다른 세션에서 `/autoloop status`로 확인, `/autoloop stop`으로 정지"를 안내한다.

## status — 조회

`_workspace/autoloop/<슬러그>/`의 `driver.log`(반복별 상태·EXIT 사유)와 `carryover.md`(한 일/다음/막힘/사용자 확인 필요)를 읽어 **한국어로 소화해** 보고한다(§15): 몇 반복째, 테스트 green/red, open 항목 수, 종료됐으면 사유. 슬러그를 모르면 `ls _workspace/autoloop/`로 나열해 고르게 한다. `blocked`로 끝났으면 "사용자 확인 필요" 항목을 최우선으로 보여준다 — 그것이 루프가 사용자에게 이월한 결정이다.

### 튜닝 신호 포착 (리뷰 시점 — 루프는 자기 개선점을 진단하지 않는다)

드라이버는 헤드리스라 자신의 튜닝 필요를 판단하지 못한다. `status`로 끝난 런을 검토할 때, `driver.log`에서 아래 **하네스 튜닝 신호**를 함께 훑어 리뷰 시점의 대화형 세션이 §8 진화 흐름으로 라우팅한다(이것이 raw 로그를 개선으로 잇는 유일한 연결이다):

- **EXIT 사유가 `done`이 아님**(stalled·exhausted·error·cost) → 완주 실패. 스펙 문제인지 드라이버 결함인지 판단한다.
- **권한 거부·자가 검증 불가**가 carryover/로그에 반복 → 안전 게이트가 정상 작업을 막는지(allow 목록 조정 후보).
- **무진전 반복·낭비 반복**(open 미감소인데 반복 소비) → 프롬프트·완료 판정 튜닝 후보.
- **reviewer BLOCK 반복** → 완료 기준이 모호하거나 검증 프롬프트가 과도한지.

판단(하네스 버그 ↔ 작업 특성)은 헤드리스 드라이버가 못 하므로 이 리뷰 세션이 맡는다. 신호가 잡히면 **프로필 게이트**(REGISTRY.md, §5·ADR 012)로 갈린다:
- **개인 프로필** → 튜닝을 **사용자에게 제안**하고, 승인 시 `metaskill`로 직접 적용(무단 수정 금지 — §8).
- **사내 프로필** → 추적 하네스 파일을 못 고치므로 **`_workspace/harness-updates.md` 대기 큐에 기록**한다(개인 머신에서 그대로 적용 가능한 수준으로 — 대상 파일·변경 내용·근거). `harness-ops-log.md`는 적용 이력이지 대기 큐가 아니다 — 혼동 금지.

## stop — 정지

```bash
touch _workspace/autoloop/<슬러그>/STOP
```

프로세스를 kill하지 않는다 — 드라이버가 **다음 반복 경계**에서 carryover를 보존한 채 곱게 내려간다(진행 중 반복은 마저 끝난다). STOP 파일은 드라이버가 지우지 않으므로, 재기동하려면 사용자가 STOP을 지웠음을 확인한 뒤 start를 다시 밟는다(같은 `--work-name`이면 기존 노트를 이어받는다 — R10).

## 주의

- **파괴적 작업 무인 실행 금지(§3 완화 불가)**: bypass 모드 추가, bare 인터프리터 그랜트 복원, 파괴 패턴의 `--allow-extra` 그랜트(kubectl·terraform·배포 명령 등) 요청은 거절하고 이유를 설명한다 — 이 게이트가 이 도구의 존재 조건이다. `--allow-extra`는 테스트·빌드 러너 수준까지만.
- **인프라·배포 스펙에 사용 금지**: k8s·AWS·릴리스가 걸린 작업은 orchestrate(infra-specialist 경유)·release로 — 무인 루프의 대상이 아니다.
- **드라이버 수정 시** `python3 .agents/skills/autoloop/scripts/driver_test.py` 통과 필수(C1~C12, tdd-gate와 같은 규율).
- 완주 후 정식 기록이 필요한 작업이면 work-tracker로 승격한다(`_workspace/`는 미보존 — §4).

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 컨텍스트 한계 | 세션 소진 시 수동 wrapup·clear·재개 | 새 프로세스 반복으로 자동 롤오버 |
| 무인 안전 | 전면 bypass 유혹 → §3 위반 | 편집만 무인, 파괴적 작업은 blocked 이월 |
| 결함 누적 | 자가보고 "통과"가 다음 반복에 전파 | 드라이버 실측 + reviewer PASS만 완료 인정 |
| 종료 보장 | 자율 루프가 목표 없이 토큰 소각 | 7종 정지 조건으로 반드시 유한 종료 |
