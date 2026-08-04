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

# 설치처 판정 입력(§5·ADR 012·ADR 040)의 단일 출처는 REGISTRY.md다. 미추적
# 파일이라 사내 설치처에서도 이 입력만은 그 기계가 쥔다. 판독기가 여기 있는
# 이유는 소비자가 셋이기 때문이다 — harness-review-reminder(일일 점검 억제)와
# dispatch-gate(발행 차단)가 프로필을, tier-gate(경량 발행 차단)가 경량
# 목록을 읽는다. 사본을 두면 아래 주석이 기록한 독립 검증 수정(코드 펜스·제목
# 레벨)을 그만큼 따로 반영해야 한다(이 파일의 존재 이유).
REGISTRY = "REGISTRY.md"
CORPORATE = "사내"
_PROFILE_VALUES = ("개인", CORPORATE)
# 굵은 라벨이 목록 항목의 **첫 내용**일 때만 잡는다 — `- 프로필: **사내**`처럼
# 라벨 앞에 글자가 붙은 형태는 미상이어야 한다(harness-install이 형식을 고정한
# 이유, 독립 검증 2026-08-03 B1에서 다섯 형태 실측).
_BOLD_ITEM = re.compile(r"^\s*[-*]\s*\*\*(.+?)\*\*")
_HEADING = re.compile(r"^#{1,6}\s")
# 「경량 모델」 절은 제목 뒤에 괄호 설명을 단다. 프로필 절처럼 정확 일치를
# 요구하면 설명을 붙인 순간 조용히 미상이 되므로(harness-install이 그 함정을
# 문서로 막아야 했던 이유) 제목 접두만 보되, 낱말 경계를 요구해 다른 절을
# 삼키지 않게 한다.
_LIGHTWEIGHT_HEADING = re.compile(r"^#{1,6}\s+경량 모델(\s|$)")
# 프로필 절도 같은 함정을 가진다. 정확 일치를 요구하던 동안 `## 설치처 프로필
# (ADR 012)`처럼 괄호 설명을 단 것만으로 절이 조용히 미상이 됐고, ADR 042
# 이후로는 그 미상이 곧 **발행 차단 해제**다(reviewer 하나가 아니라 전 역할).
# 그래서 경량 절과 같은 접두+낱말경계 판정으로 맞춘다(독립 검증 C-04 실측).
_PROFILE_HEADING_RE = re.compile(r"^#{1,6}\s+설치처 프로필(\s|$)")


def _section_items(base, matches_heading):
    """REGISTRY.md에서 `matches_heading`이 참인 절의 굵은 라벨 목록을 순서대로.

    절 밖은 읽지 않는다 — 다른 절의 산문도 같은 낱말을 쓰므로 전체 검색은
    엉뚱한 절을 판정 입력으로 읽는다. 어떤 실패도 빈 리스트이며, 소비자는
    전부 그것을 '억제하지 않음'(점검 실행·검증 통과·발행 통과)으로 받는다.
    """
    try:
        with open(os.path.join(base, REGISTRY), encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:
        # 부재·권한·손상 모두 미상. 여기서 예외가 새면 호출자의 fail-open이
        # 삼켜 훅이 통째로 침묵한다(마커 읽기의 HOOK-F6과 같은 실패 형태).
        return []
    items = []
    in_section = False
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            # 코드 펜스 안의 예시는 절이 아니다 — REGISTRY.md 형식을 보여주는
            # 예시가 들어갈 수 있고, 그것을 판정 입력으로 읽으면 그 설치처가
            # 아닌 값으로 판정이 뒤집힌다.
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _HEADING.match(line):
            # 어느 레벨의 제목이든 절을 닫는다. `## `만 닫으면 `#`·`###` 뒤의
            # 굵은 라벨이 절의 내용으로 읽힌다(독립 검증 2026-08-03 B3).
            in_section = matches_heading(line.strip())
            continue
        if in_section:
            m = _BOLD_ITEM.match(line)
            if m:
                items.append(m.group(1))
    return items


def read_profile(base):
    """REGISTRY.md 「설치처 프로필」 절의 값('개인'/'사내'). 미상은 None.

    굵은 라벨이 두 값 중 하나일 때만 인정한다 — 절 안의 다른 굵은 항목
    (기계 대수 등)이 프로필로 읽히면 안 된다.
    """
    for item in _section_items(base, lambda h: bool(_PROFILE_HEADING_RE.match(h))):
        if item in _PROFILE_VALUES:
            return item
    return None


def read_lightweight_models(base):
    """REGISTRY.md 「경량 모델」 절이 나열한 등급 이름의 소문자 집합.

    절이 없거나 비었으면 빈 집합이고, tier-gate는 그것을 '차단 대상 없음'으로
    받는다(fail-open) — 비용·품질 규칙이지 3절 가드레일이 아니다. 모델명이
    코드가 아니라 이 데이터에 있는 이유는 ADR 005다: 라인업은 설치처와 시간에
    따라 바뀌지만 훅은 바뀌지 않아야 한다.

    **빈 항목은 반드시 걸러낸다.** 빈 문자열이 집합에 들어가면 어떤 모델
    문자열에도 매칭돼 `model`을 지정한 발행이 전부 막힌다 — fail-open 설계가
    한 항목 때문에 fail-closed로 뒤집힌다(독립 검증 2026-08-04 F5, 변이로 재현).
    """
    names = set()
    for item in _section_items(base, _LIGHTWEIGHT_HEADING.match):
        name = item.strip().lower()
        if name:
            names.add(name)
    return names


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
