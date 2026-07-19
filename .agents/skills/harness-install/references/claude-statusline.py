#!/usr/bin/env python3
"""Claude Code statusline — 컨텍스트 상시 표시 (harness-install 3d 설정의 단일 원본).

Claude Code가 stdin으로 넘기는 세션 JSON(model.display_name·context_window.*)에서
컨텍스트 사용률을 읽어 한 줄로 출력한다. 새 의존성 없이 표준 라이브러리(json)만
쓴다 — jq 미설치 환경 대비. 어떤 입력에도 크래시하지 않고 "[claude]"로 폴백한다
(statusLine 실패의 최악 결과는 장식 한 줄이 안 뜨는 것이므로 조용히 폴백).
설치: 이 파일을 ~/.claude/statusline.py 로 복사하고, settings.json의 statusLine.command를
"python3 ~/.claude/statusline.py" 로 지정한다(harness-install 3d).
"""
import json
import sys


def render(data):
    cw = data.get("context_window") or {}
    model = (data.get("model") or {}).get("display_name") or "claude"

    pct = cw.get("used_percentage")
    pct = int(pct) if isinstance(pct, (int, float)) else 0  # 세션 초기엔 null
    used_k = int((cw.get("total_input_tokens") or 0) / 1000)
    size_k = int((cw.get("context_window_size") or 0) / 1000)

    width = 10
    filled = min(width, pct * width // 100)
    bar = "▓" * filled + "░" * (width - filled)  # ▓ 채움 / ░ 빈칸
    warn = " ⚠" if pct >= 80 else ""  # ⚠ 80% 이상 경고
    return f"[{model}] {bar} {pct}%{warn} · {used_k}k/{size_k}k ctx"


try:
    print(render(json.load(sys.stdin)))
except Exception:
    print("[claude]")  # 파싱 불가·예상 밖 모양 모두 폴백
