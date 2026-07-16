"""훅 공통 부트스트랩 — 훅 4종이 공유하는 로직의 단일 원본.

같은 수정을 훅마다 반복 적용하는 fix 연쇄(2026-07-14 cp949 장애가 3개 파일
동시 수정을 요구)를 없애기 위해 공통 로직을 이 파일 한 곳에만 둔다.
훅이 아니므로 .claude/settings.json에 등록하지 않는다. import 경로는 위치에
따라 다르다: 같은 디렉토리의 세션 훅 3종(agentsview-daemon·harness-review-
reminder·worklog-reminder)은 스크립트 직접 실행이라 sys.path[0]만으로
`from _common import ...`가 되지만, 다른 디렉토리의 git 훅
(.agents/githooks/tdd-gate.py)과 각 테스트 스위트는 이 파일이 있는 hooks/
경로를 sys.path에 명시 삽입한 뒤 import한다.
유실 시에도 훅이 죽지 않도록 각 importer는 no-op 폴백을 갖는다.

스펙: docs/specs/2026-07-15-hooks-common-bootstrap.md
회귀 테스트: .agents/hooks/_common_test.py (수정 시 반드시 통과)
"""
import sys


def utf8_stdio():
    """stdout/stderr를 UTF-8(errors=replace)로 재구성한다 — 한글 Windows 콘솔의
    기본 인코딩(cp949)은 em dash(U+2014) 등을 못 담아 print/write가 예외를 던지고,
    fail-open이 그것을 삼켜 훅이 무출력으로 죽거나(리마인더) 차단해야 할 커밋을
    통과시킨다(tdd-gate) — 2026-07-14 장애. 훅 출력의 소비자는 콘솔이 아니라
    Claude Code(UTF-8)다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # 재구성 불가 스트림(테스트 StringIO 등)은 그대로 둔다
