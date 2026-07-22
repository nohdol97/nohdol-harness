#!/usr/bin/env python3
"""gate-reminder — 진단→구현 전환점의 orchestrate 게이트 상기 (PostToolUse/PreToolUse).

같은 세션에서 읽기 전용 진단(kubectl·로그·원인 추적)이 코드 수정으로 조용히
미끄러지며 orchestrate Phase 0-1 게이트를 건너뛴 재발(신호 ② — 자가 정정
선언 후에도 재발)을 기계적으로 막는다. 프롬프트 문구(CLAUDE.md 앵커·AGENTS.md
7절 3항)는 상기 빈도만 높일 뿐 전환 시점 자체를 붙잡지 못했음이 실측됐다.

동작: --record(PostToolUse Bash)가 진단 명령을 관찰하면 세션 상태를 무장하고,
--check(PreToolUse Edit|Write|MultiEdit|NotebookEdit)가 제품 코드 첫 수정
직전에 해당 호출을 1회 차단하며 게이트 판정 선언을 지시한다(stderr → 모델).
재시도는 통과 — 차단은 세션당 최대 1회다. 판정 내용의 품질은 검증하지
않는다(orchestrate·리뷰 몫). 모든 오류는 통과(fail-open).

Codex: .codex/hooks.json에도 선제 등록한다(ADR 029 파리티 기본값). 단
검증된 Codex 훅 이벤트는 SessionStart뿐이라 PreToolUse 상당 이벤트·차단
시맨틱스·stdin 계약은 미확인 — fail-open이라 미지원이면 무해하게 무시되고,
실검증 전 Codex의 확실한 방어선은 AGENTS.md 7절 3항 문구다(이 훅은 커밋
산출물이 아닌 세션 중 라우팅 행동 교정이라 git 계층으로도 못 옮긴다).

스펙: docs/specs/2026-07-22-gate-reminder-hook.md
회귀 테스트: .agents/hooks/gate-reminder_test.py (수정 시 반드시 통과)
"""
import json
import os
import re
import sys
import time

try:
    # stdio UTF-8 재구성의 단일 원본(스펙 2026-07-15-hooks-common-bootstrap).
    from _common import utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    def utf8_stdio():
        pass

BLOCK_EXIT = 2  # PreToolUse: 도구 호출 차단 + stderr를 모델에게 전달
STATE_DIRNAME = os.path.join("_workspace", ".gate-reminder")
STALE_SECONDS = 7 * 24 * 3600  # R5: 7일 지난 세션 상태는 기회적으로 정리

# 진단 패턴은 실측된 우회(kubectl·ArgoCD·로그) 중심의 보수 목록 — 과잉 매칭은
# 오탐 차단으로 규율을 노이즈화한다(루트 16절). 재발 관찰 시 확장.
DIAG_RE = re.compile(
    r"\b(kubectl|argocd|stern|journalctl)\b"
    r"|\bdocker\s+logs\b"
    r"|\bhelm\s+(status|get)\b"
    r"|\baws\s+logs\b"
)

# 제품 코드가 아닌 쓰기 대상 — 상태를 소모하지 않고 통과한다(R3).
EXCLUDE_PARTS = ("_workspace",)
EXCLUDE_PREFIXES = ("/tmp/", "/var/tmp/", "/private/tmp/")

REMINDER = """[gate-reminder] 이 세션은 조사·진단(kubectl/로그 등)으로 시작해 지금 첫 파일 수정에 진입했다 — 진단→구현 전환점은 orchestrate Phase 0-1 게이트의 재판정 대상이다(루트 AGENTS.md 7절 3항, 명시적 '구현해줘'가 없어도 트리거). 이 수정을 진행하기 전에:
1. 게이트 판정(직접 수행/단독 서브에이전트/생성-검증 쌍/팀)과 근거를 한 줄로 사용자에게 선언하라.
2. 3+파일 구현이면 implementer, k8s·인프라 매니페스트면 infra-specialist를 발행하라(메인 루프 직접 구현은 ≤2파일·저위험 + 독립 reviewer일 때만).
이미 이 세션에서 판정을 선언했거나 네가 발행된 서브에이전트라면, 그 사실을 확인하고 같은 호출을 재시도하라 — 이 알림은 세션당 1회만 차단한다."""


def project_dir():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def state_file(sid):
    return os.path.join(project_dir(), STATE_DIRNAME, sid)


def read_event():
    """stdin JSON → (session_id, tool_input dict). 파싱 불가는 예외 → fail-open."""
    data = json.load(sys.stdin)
    sid = data.get("session_id")
    if not sid or os.sep in sid or "/" in sid:  # 경로 조작 방지 겸 무결성 확인
        raise ValueError("no usable session_id")
    return sid, data.get("tool_input") or {}


def cleanup_stale(state_dir):
    """R5: 7일 초과 상태 파일 삭제 — 실패는 전부 무시(정리는 부업이다)."""
    try:
        cutoff = time.time() - STALE_SECONDS
        for name in os.listdir(state_dir):
            path = os.path.join(state_dir, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                pass
    except OSError:
        pass


def record():
    """PostToolUse(Bash): 진단 명령 관찰 시 세션 상태를 'diag'로 무장(R1)."""
    sid, tool_input = read_event()
    if not DIAG_RE.search(tool_input.get("command") or ""):
        return 0
    path = state_file(sid)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cleanup_stale(os.path.dirname(path))
    if os.path.exists(path):  # diag든 reminded든 유지 — 세션당 1회 원칙
        return 0
    with open(path, "w", encoding="utf-8") as f:
        f.write("diag")
    return 0


def is_excluded(file_path):
    norm = (file_path or "").replace("\\", "/")
    if any(part in norm.split("/") for part in EXCLUDE_PARTS):
        return True
    return norm.startswith(EXCLUDE_PREFIXES)


def check():
    """PreToolUse(Edit|Write 계열): diag 상태의 제품 코드 첫 수정을 1회 차단(R2·R3)."""
    sid, tool_input = read_event()
    path = state_file(sid)
    try:
        with open(path, encoding="utf-8") as f:
            state = f.read().strip()
    except OSError:
        return 0  # 진단 이력 없는 세션
    if state != "diag":
        return 0  # 이미 상기했다 — 세션당 1회
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if is_excluded(target):
        return 0  # 리포트·스크래치 쓰기는 제품 코드 수정이 아니다 — 상태 유지
    with open(path, "w", encoding="utf-8") as f:
        f.write("reminded")
    print(REMINDER, file=sys.stderr)
    return BLOCK_EXIT


def main():
    utf8_stdio()
    try:
        mode = sys.argv[1] if len(sys.argv) > 1 else ""
        if mode == "--record":
            return record()
        if mode == "--check":
            return check()
        return 0
    except Exception:
        return 0  # fail-open: 훅의 어떤 실패도 세션을 막지 않는다(R4)


if __name__ == "__main__":
    sys.exit(main())
