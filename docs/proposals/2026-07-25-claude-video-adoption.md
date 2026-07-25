# claude-video (`/watch`) 채택 — 직접 호출 전용

- 날짜: 2026-07-25 / 상태: **채택** (사용자 결정 2026-07-25)
- 대상: https://github.com/bradautomates/claude-video (MIT, Claude Code 플러그인 + 다중 CLI, npm agentskills)
- 관련: 루트 AGENTS.md §3·§7·§11, harness-install 3g, docs/proposals/2026-07-25-understand-anything-adoption.md(같은 직접 호출 전용 패턴)

## 대상 요약

`/watch <URL 또는 로컬경로> <질문>` — Claude가 영상을 실제로 보게 하는 스킬. yt-dlp가 자막 우선 확보(없으면 다운로드), ffmpeg가 장면 전환 인식 프레임을 추출(중복 제거 패스 + 길이 비례 프레임 예산), Claude가 프레임을 이미지로 Read + 타임스탬프 트랜스크립트. 소스: yt-dlp 지원 URL(YouTube·Loom·TikTok·X 등) + 로컬 `.mp4/.mov/.mkv/.webm`. 트랜스크립트: 무료 자막 우선, 없으면 Whisper 폴백(Groq `whisper-large-v3` 선호 / OpenAI `whisper-1`). detail 모드(transcript/efficient/balanced/token-burner)로 속도·토큰 조절, `--start/--end` 집중 모드. 의존성 yt-dlp·ffmpeg는 첫 실행 시 자동 설치. Whisper 키는 자막 없는 영상에서만 필요.

## 왜 채택 (기각한 것들과 다른 점)

1. **순수 신규 역량·중복 0**: 하네스에 영상을 볼 수 있는 자산이 전무하다(defuddle=웹 텍스트, context7=문서, WebFetch=URL). graphify·agentmemory 기각의 핵심이던 "니치 기충족·중복"이 여기선 성립하지 않는다.
2. **opt-in-per-use·상시 비용 0**: `/watch` 직접 호출이라 상시 서버·백그라운드 훅이 없다(agentmemory와 정반대). 토큰 비용(프레임=이미지)은 쓸 때만 발생하고 도구가 프레임 예산·중복 제거로 자체 관리(실측 표 제공).
3. **명확한 실사용처**: 버그 재현 화면 녹화 진단, 경쟁사·튜토리얼·업데이트 영상 요약.

## 채택 범위·경계

- **채택**: 영상 이해가 필요할 때의 직접 호출(`/watch …`) 역량.
- **직접 호출 전용(사용자 결정)**: 자동 라우팅하지 않는다(직접 호출 전용) — 영상 URL을 붙여 요약을 요청해도 `/watch`가 자동 발동하지 않고, 사용자의 명시적 `/watch`에만 돈다. 강제는 문서화된 라우팅 정책(CLAUDE.md 스킬맵 + §7 + harness-install 3g)이며 외부 플러그인 프론트매터는 고치지 않는다(§11). 이유: 프레임=이미지 토큰이 커질 수 있어 깜짝 소비를 막는다.
- **사내 마켓플레이스 차단 대체 경로**: 사내는 `/plugin marketplace`가 흔히 막히나, claude-video는 우회 경로가 있다 — `npx skills add bradautomates/claude-video -g`(agentskills CLI, Claude Code의 `~/.claude/skills`도 대상) 또는 수동 clone+심링크(`ln -s <repo>/skills/watch ~/.claude/skills/watch`). npm·GitHub까지 막히면 사유와 함께 스킵. 사용자 결정: 사내도 강제 유지·차단은 자연 스킵.

## §3 유출 처리

- **핵심 유출 지점 = Whisper 폴백**: 자막이 없는 영상(로컬 파일·TikTok 등)은 **오디오를 제3자(Groq/OpenAI)로 전송**해 받아쓴다. 사내 내부 앱 화면 녹화에 음성이 있으면 그 내용이 나간다.
- **완화(실행 문서 3g에 실림)**: 사내 프로필·민감/내부 녹화는 `--no-whisper`(프레임만) 또는 자막 있는 공개 영상만. 개인 프로필의 공개·본인 콘텐츠는 Whisper 허용.
- **프레임→Claude는 기본 동작**(스크린샷 보여주는 것과 동일)이라 §3 추가 유출이 아니다. API 키는 `~/.config/watch/.env`(0600) — 대리 복사 금지(§3).

## 재검토 조건

- 직접 호출 전용 정책이 실제로 안 지켜져 자동 발동·토큰 깜짝 소비가 신호 ②로 관찰되면 강제 방식 재설계.
- 3주 실측 게이트는 두지 않음(직접 호출 전용이라 안 쓰면 자연 방치, 상시 리스크 낮음 — Understand-Anything과 동일 논리).

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-25 | 채택 설계 기록(직접 호출 전용·Whisper §3 완화) + harness-install 3g·CLAUDE.md 라우팅 반영 | 신규, harness-install, CLAUDE.md | 사용자 검토 요청 → 채택+직접 호출 전용 결정. 순수 신규 역량이라 중복 우려 없고, 유일 유출 지점(Whisper 오디오)은 사내 `--no-whisper` 전제로 차단 |
