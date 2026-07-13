# .agents/projects/ — 하위 프로젝트 하네스 원본

하위 프로젝트 하네스(AGENTS.md, CLAUDE.md, adr/)의 **원본이자 유일본** 디렉토리.

- 구조: `.agents/projects/<이름>/` — `<이름>`은 REGISTRY.md 레지스트리 행과 일치해야 한다.
- REGISTRY.md처럼 **설치처별 데이터라 git 미추적**이다(이 README만 추적) — 컴퓨터마다 두는 프로젝트가 다르다.
- `project/<이름>/`에는 하네스 파일을 두지 않는다(심링크·복사본 포함). 라우팅(REGISTRY.md → 이 디렉토리의 AGENTS.md 읽기)이 연결한다.
- 상세 규칙: 루트 AGENTS.md 12절, docs/adr/006.
