# ADR 066: Paperclip 연동 폐기

> 번호 변경: 2026-11-27 [ADR 061](061-knowledge-notes-explicit-request.md)과 번호가 겹쳐 061에서 066으로 바꿨다. 2026-11-24~27 사이의 기록에 나오는 「ADR 061(Paperclip)」은 이 문서다.

- 날짜: 2026-11-24
- 상태: 활성
- 대체 대상: ADR 057·058·059·060

## 배경
2026-10-14~15에 Paperclip 연동(역할·스킬 동기화, 레지스트리 연결, 협업 예외 규칙, Paseo 패널)을 넣었다. 사용자가 Paperclip을 쓰지 않으며 남아 있는 내용이 혼동을 준다고 알렸다. 2026-11-24 확인 시 이 기기에 Paperclip 실행 파일·프로세스·홈 디렉터리가 없었고, Paseo에 등록된 플러그인도 없었다(`paseo plugin ls --json` 결과 `[]`).

## 결정
1. `.agents/integrations/paperclip/` 전체(동기화 스크립트, runtime 계약, Paseo 패널 플러그인 원본과 시험)를 삭제한다.
2. 루트 `AGENTS.md` §11의 Paperclip 협업 예외 문단과 한글 뷰의 같은 절, 루트 `README.md`의 사용 안내 절을 삭제한다.
3. ADR 057~060과 관련 스펙 6건은 이력으로 남기고 폐기 표시를 붙인다. 변경 이력의 과거 행은 고치지 않는다.

## 영향
- 세션이 Paperclip 실행 문맥인지 판정하는 규칙이 없어진다. CLI·Pi 세션의 동작은 그대로다.
- 다시 쓰려면 이 커밋 이전의 git 이력에서 `.agents/integrations/paperclip/`을 복원하고 ADR 059의 규칙 문단을 되살린다.
- 대상: `.agents/integrations/paperclip/**`, `AGENTS.md`, `AGENTS.ko.md`, `README.md`, `docs/README.md`, `docs/adr/057~060`, `docs/specs/2026-10-14-paperclip-harness-sync.md`, `docs/specs/2026-10-15-paperclip-*.md`, `docs/specs/2026-10-15-paseo-paperclip-*.md`, `docs/harness-changelog.md`
