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
import os
import re
import sys

# 설치처 프로필(§5·ADR 012)의 단일 출처는 REGISTRY.md다. 미추적 파일이라
# 사내 설치처에서도 이 판정 입력만은 그 기계가 쥔다. 판독기가 여기 있는 이유는
# 소비자가 둘이기 때문이다 — harness-review-reminder(일일 점검 억제)와
# review-gate(검증 발행 차단). 사본을 두면 아래 두 주석이 기록한 독립 검증
# 수정(코드 펜스·제목 레벨)을 양쪽에 따로 반영해야 한다(이 파일의 존재 이유).
REGISTRY = "REGISTRY.md"
PROFILE_HEADING = "## 설치처 프로필"
CORPORATE = "사내"
_PROFILE_ITEM = re.compile(r"^\s*[-*]\s*\*\*(개인|사내)\*\*")
_HEADING = re.compile(r"^#{1,6}\s")


def read_profile(base):
    """REGISTRY.md 「설치처 프로필」 절의 값('개인'/'사내'). 미상은 None.

    절 안의 굵은 라벨 목록 항목만 읽는다 — 다른 절의 산문도 두 단어를 쓰므로
    전체 검색은 엉뚱한 절을 프로필로 읽는다. 어떤 실패도 None이며, 두 소비자
    모두 None을 '억제하지 않음'(일일 점검은 실행, 검증 발행은 통과)으로 받는다.
    """
    try:
        with open(os.path.join(base, REGISTRY), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:
        # 부재·권한·손상 모두 미상. 여기서 예외가 새면 호출자의 fail-open이
        # 삼켜 훅이 통째로 침묵한다(마커 읽기의 HOOK-F6과 같은 실패 형태).
        return None
    in_section = False
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            # 코드 펜스 안의 예시는 절이 아니다 — REGISTRY.md 형식을 보여주는
            # 예시가 들어갈 수 있고, 그것을 프로필로 읽으면 그 설치처가 아닌
            # 값으로 판정이 뒤집힌다.
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _HEADING.match(line):
            # 어느 레벨의 제목이든 절을 닫는다. `## `만 닫으면 `#`·`###` 뒤의
            # 굵은 라벨이 프로필로 읽힌다(독립 검증 2026-08-03 B3).
            in_section = line.strip() == PROFILE_HEADING
            continue
        if in_section:
            m = _PROFILE_ITEM.match(line)
            if m:
                return m.group(1)
    return None


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
