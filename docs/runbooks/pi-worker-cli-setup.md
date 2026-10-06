# 런북: 사내 Pi 작업자 CLI 확인과 단발 위임 검증

- 목적: 설치된 CLI 계약을 확인하고 기존 인증 설정으로 읽기 전용 위임을 검증한다. / 소요: CLI·서버 접근 상태에 따라 다름. / 위험도: 로컬 테스트 파일 생성과 모델 호출. 배포·인증 변경은 포함하지 않는다.

## 사전 조건

개발 기계에서는 사용자 요청으로 사내 CLI 직접 확인을 생략했다. AX 어댑터의 지원 계약은 `turn_start` 이후 `turn_end.message`의 `role=assistant`, `stopReason=stop`, `content` text 블록이다. 회귀는 합성 이벤트로 검증하며 이 문서는 사내 연결 성공 기록이 아니다. 설치된 CLI의 계약이 다르면 정상 후보로 판정되지 않으므로 해당 구조를 확인해 어댑터와 회귀를 함께 수정한다.

하네스 루트에서 시작한다. `REGISTRY.md`의 설치처 프로필이 사내이며, CLI의 기존 설정이 승인된 내부 모델을 가리키는지 로컬에서 확인한다. 프로필을 임시로 사내로 바꿔 개인 기계에서 호출하지 않는다. 인증파일을 출력·복사하거나 작업자 JSON에 키를 넣지 않는다.

```bash
command -v pi
```

실제 실행 파일 이름이 다르면 그 이름을 사용한다. 이후 명령의 `/absolute/path/to/pi`는 확인한 실행 경로로 바꾼다. Node로 직접 실행해야 하면 기존 설치 명령의 실행 파일과 스크립트 경로를 인자 배열로 사용한다.

## 절차

1. **설치 계약을 확인한다.** 실제 실행 경로로 도움말을 연다.

   ```bash
   /absolute/path/to/pi --help
   ```

   설치 버전은 해당 CLI가 지원하는 버전 표시나 설치 패키지 메타데이터로 확인한다. 0.7.0 사용자 보고에서 확인된 내용은 값이 필요한 `-p/--prompt`, `--append-system-prompt @파일`, `--provider`·`--list-models` 미지원이다. `--mode json`, `--tools`, 선택적인 `--model`의 실제 지원 여부도 도움말·인자 파서에서 확인한다. 지원하지 않으면 호출하지 않고 어댑터 계약을 수정한다. 모델 목록 명령을 다른 CLI에서 가져와 실행하지 않는다.

   AX 호출 형태는 `pi -p "<프롬프트 전체>" --mode json --tools <도구목록> --append-system-prompt @<시스템파일>`이다. 실행기는 프롬프트를 `-p` 바로 다음 **단일 인자**로 전달한다. 마지막 `-- <프롬프트>`는 AX에 붙이지 않으며, upstream Pi만 기존 위치 인자 형식을 유지한다. `argument -p/--prompt: expected one argument`가 나오면 `-p --mode ... -- <프롬프트>`를 만드는 이전 하네스 실행기인지 확인한다. 설치된 AX 패키지나 인증 설정을 고치지 않고 실행기를 갱신한 뒤 새 출력 디렉터리로 재시도한다.

2. **정확한 도구·이벤트 구조를 확인한다.** 도움말에 도구 이름이 없으면 설치 패키지의 도구 등록 코드와 JSON 출력 코드를 읽는다. 인증·settings 파일 전체를 검색하거나 출력하지 않는다. 다음 항목을 민감정보 없이 기록한다.

   - 읽기·검색·셸·수정·쓰기 도구의 정확한 이름과 대소문자.
   - explorer에는 읽기 도구와 읽기 전용 명령용 셸만, implementer에는 필요한 수정·쓰기 도구를 추가한 목록.
   - `turn_end`의 응답 본문 위치, 정상 완료 표지, 오류 필드와 오류 이벤트.
   - 본문 없는 종료와 모델 오류에서 프로세스 exit code가 무엇인지.

   `session → turn_start → turn_end`라는 이벤트 이름 목록만으로 응답 스키마가 확인된 것은 아니다. 아래는 지원 계약의 **합성 예시**다. 실제 설치처 출력이라고 해석하지 않는다.

   ```json
   {"type":"turn_end","message":{"role":"assistant","stopReason":"stop","content":[{"type":"text","text":"candidate report"}]}}
   ```

   `stopReason=error` 또는 오류 이벤트는 `model_error`, 정상 종료지만 text가 공백이면 `empty_response`, assistant message가 없으면 `missing_response`로 실패한다. 다른 위치에 본문이 있거나 종료 사유가 없는 구조도 성공으로 추측하지 않는다. 기존 실호출 예시를 근거로 사용할 때에는 내부 주소·모델 식별값·인증정보를 제거한다. 원본을 공개 저장소·이슈에 올리지 않는다.

3. **worker 설정을 새 파일로 생성한다.** 아래 코드는 CLI 명령, 검증한 도구 목록, 측정한 동시 실행 수만 입력받는다. AX는 provider를 넣지 않고 모델도 기존 CLI 설정을 사용한다. 입력값에 인증 옵션이나 셸 연산자를 넣지 않는다.

   ```bash
   python3 -c '
   import json
   from pathlib import Path
   target = Path("_workspace/pi-workers/config.json")
   command = json.loads(input("실행 명령 JSON 배열: "))
   explorer = json.loads(input("검증한 explorer 도구 JSON 배열: "))
   implementer = json.loads(input("검증한 implementer 도구 JSON 배열: "))
   capacity = int(input("검증한 서버 동시 실행 수: "))
   assert isinstance(command, list) and command and all(isinstance(x, str) and x for x in command)
   assert capacity > 0
   for names in (explorer, implementer):
       assert isinstance(names, list) and names and all(isinstance(x, str) and x for x in names)
   target.parent.mkdir(parents=True, exist_ok=True)
   with target.open("x", encoding="utf-8") as stream:
       json.dump({"cli": "ax", "command": command,
                  "tools": {"explorer": explorer, "implementer": implementer},
                  "max_parallel": capacity, "timeout_seconds": 1800}, stream, indent=2)
   print("worker 설정 생성 완료; 인증 설정은 변경하지 않았습니다.")
   '
   ```

   기존 파일이 있으면 덮어쓰지 않고 실패한다. 기존 내용을 로컬에서 검토하고 별도 이름으로 생성해 비교한다. 기존 Pi CLI는 `cli` 생략 또는 `pi`를 사용하고 기존 provider/model 설정을 유지한다.

4. **읽기 전용 smoke 배치를 만든다.** 프롬프트에는 확인할 파일 경로만 넣고 임의값 자체는 넣지 않는다. 따라서 최종 응답과 파일 내용이 같으면 실제 파일 접근 근거가 된다.

   ```bash
   python3 - <<'PY'
   import json, uuid
   from pathlib import Path
   root = Path.cwd()
   job = root / '_workspace/pi-workers/smoke'
   job.mkdir(parents=True, exist_ok=False)
   (job / 'expected.txt').write_text('PI_WORKER_SMOKE_' + uuid.uuid4().hex, encoding='utf-8')
   (job / 'prompt.md').write_text(
       f'Read {job / "expected.txt"} using your read tool. Return only its exact text. '
       'Do not modify files or run shell commands.', encoding='utf-8')
   (job / 'batch.json').write_text(json.dumps([{
       'id': 'smoke', 'role': 'explorer', 'target': str(job),
       'project_harness': 'AGENTS.md', 'prompt_file': str(job / 'prompt.md')
   }]), encoding='utf-8')
   print('읽기 전용 smoke 배치 생성 완료')
   PY
   ```

5. **실제 위임을 한 번 실행한다.** CLI 옵션·도구 설정을 확인한 뒤 실행한다. 회귀는 `python3 .agents/skills/orchestrate/scripts/pi_workers_test.py`로 먼저 확인할 수 있다.

   ```bash
   python3 .agents/skills/orchestrate/scripts/pi_workers.py \
     --root "$PWD" \
     --config _workspace/pi-workers/config.json \
     --batch _workspace/pi-workers/smoke/batch.json \
     --output _workspace/pi-workers/smoke/run-01
   ```

   기대값은 exit 0과 `candidate: 1, total: 1`이다. CLI 인증은 기존 설치 설정에서 읽는다. 실패하면 출력 폴더를 보존하고 `failure_kind`, exit code, 원본 이벤트를 로컬에서 확인한다. 인증 오류를 해결하려고 인증파일을 하네스 안에 복사하지 않는다.

## 검증

```bash
python3 - <<'PY'
import json
from pathlib import Path
job = Path('_workspace/pi-workers/smoke')
result = json.loads((job / 'run-01/results.json').read_text())[0]
assert result['status'] == 'candidate', result.get('failure_kind')
assert result['exit_code'] == 0
assert (job / 'run-01/smoke/report.md').read_text().strip() == (job / 'expected.txt').read_text()
print('PASS: 실제 위임 응답과 읽기 대상 일치')
PY
```

이 검증은 모델 호출·대상 파일 접근·최종 응답 판정의 smoke 근거다. 회귀 fixture는 사용자 보고의 값 필수 `-p/--prompt` 계약을 argparse로 재현하고, 이전 호출의 값 누락 오류와 AX 후행 위치 인자 거부를 확인한다. 공백·개행·따옴표·한국어 프롬프트 보존과 upstream의 기존 전체 인자 목록도 검사한다. 설치된 AX 파서 소스 자체를 사용한 테스트는 아니다. 시스템 프롬프트 인자와 파일 내용은 합성 회귀에서 확인하지만, 이 smoke만으로 실제 CLI가 시스템 지침을 읽고 따랐는지는 증명하지 않는다. 수정 도구와 최대 병렬 용량도 별도 검증 대상이다. 구현 역할은 승인된 전용 feature worktree에서 확인한다. 오류·빈 응답 회귀는 가짜 인증정보로 운영 모델을 호출하지 않고 저장된 민감정보 제거 fixture로 수행한다.

## 롤백

실패한 worker 설정을 더 이상 사용하지 않고 기존 Pi 설정 경로를 명시해 사용한다. AX 바이너리에 `cli: pi`를 붙이는 방식으로 우회하지 않는다. 인증 설정은 변경하지 않았으므로 복구 대상이 없다. 실패한 결과·부분 diff는 보존하고 원인을 확인한 뒤 새 출력 디렉터리로 재시도한다. 실행 중 프로세스는 호출 런타임의 취소/SIGINT를 사용한다.

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-10-06 | AX의 -p 값 위치와 후행 위치 인자 제거, 파서 오류 진단·회귀 범위 보완 | 절차·검증 | 사용자 실측의 expected one argument 오류를 하네스 인자 생성에서 해결 |
| 2026-10-06 | 설치 계약 확인·미추적 설정 생성·실위임 smoke 절차 작성, 개발 시 직접 확인 생략과 합성 테스트 범위 명시 | 본문 | 설치처 CLI와 지원 계약의 일치를 배포처에서 검증하기 위함 |
