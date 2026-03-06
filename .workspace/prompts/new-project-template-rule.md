# 프롬프트: 새 프로젝트 생성 템플릿 Cursor Rule 만들기

## 목적

이 워크스페이스에서 새 프로젝트를 만들 때마다 반복되는 세팅 작업을 Cursor rule로 자동화한다.
사용자가 "새 프로젝트 만들어줘" 또는 "프로젝트 초기화해줘" 같은 요청을 하면, AI가 이 rule을 따라 일관된 구조로 프로젝트를 생성한다.

## 배경: 현재 워크스페이스 구조

- **경로**: `G:\CS_Study`
- **구조**: 하위 폴더마다 독립 git repo (BotTycoon, xrun, The_Agent, News_Agent, PrivateLLM 등)
- **워크스페이스 루트 `.gitignore`**: 각 하위 프로젝트 폴더명을 나열해서 루트 repo에서 제외
- **The Record**: `G:\CS_Study\The Record` — 옵시디언 볼트. 프로젝트 메타 정보는 `2_Projects/[프로젝트명]/_index.md`에 관리
- **세션 핸드오프**: 모든 프로젝트에 `docs/handoff/` 디렉토리 존재 (`.gitkeep`으로 유지)

## 새 프로젝트 생성 시 반드시 수행해야 하는 7단계

### 1단계: 프로젝트 디렉토리 생성 + git init

```
G:\CS_Study\[프로젝트명]\
```

- `git init` 실행
- `git branch -M main` (기본 브랜치 이름 통일)

### 2단계: .gitignore 생성

**공통 패턴** (모든 프로젝트에 들어가는 것):

```gitignore
# IDE/에디터
.vscode/
.idea/
*.swp
*.swo
*~
.cursor/*
!.cursor/rules/

# 환경 변수
.env
.env.local
.env.*.local

# OS
.DS_Store
Thumbs.db
Desktop.ini

# 로그
*.log
logs/
```

**프로젝트 언어/도메인별 추가 패턴** (AI가 프로젝트 성격에 따라 판단):

| 도메인 | 추가할 패턴 |
|--------|-----------|
| Python | `__pycache__/`, `*.py[cod]`, `.venv/`, `venv/`, `.pytest_cache/`, `htmlcov/`, `.coverage` |
| Node.js | `node_modules/`, `dist/`, `*.tsbuildinfo` |
| Java/Gradle | `build/`, `.gradle/`, `out/`, `target/`, `*.class`, `*.jar` |
| C++ | `build/`, `cmake-build-*/`, `*.exe`, `*.obj`, `*.o`, `*.dll` |
| ML/LLM | `models/`, `*.safetensors`, `*.gguf`, `*.bin`, `*.pt`, `output/`, `wandb/`, `.ipynb_checkpoints/` |
| Docker | `docker-compose.override.yml`, `pgdata/` |

### 3단계: README.md 작성

기존 프로젝트들의 공통 형식:

```markdown
# [프로젝트명] — 한 줄 설명

> 한 줄 요약 (인용 블록)

## What is this?

프로젝트 설명 + 핵심 정보 테이블

| 항목 | 내용 |
|------|------|
| 목표 | ... |
| 기술 | ... |

## Tech Stack

| 분류 | 기술 |
|------|------|
| ... | ... |

## Project Structure

디렉토리 트리 (코드블록)

## Quick Start

설치/실행 단계 (코드블록)

## 문서 규칙

- 설계/기술 결정의 진실 기준 = 이 레포의 `docs/`
- 학습/성찰 기록 = The Record (`2_Projects/[프로젝트명]/_index.md`)
- 세션 핸드오프는 `docs/handoff/YYYY-MM-DD.md`에 기록
```

### 4단계: 프로젝트 디렉토리 구조 생성

**공통 (모든 프로젝트)**:
- `docs/handoff/.gitkeep`

**프로젝트 성격에 따라 추가**:
- Python 프로젝트: `src/` 또는 적절한 소스 디렉토리, `requirements.txt` 또는 `pyproject.toml`
- Node.js 프로젝트: `src/`, `package.json`
- 설계 문서가 있으면: `docs/`에 배치
- 설정 파일이 필요하면: `configs/`

빈 디렉토리는 `.gitkeep` 파일로 유지.

### 5단계: 워크스페이스 루트 .gitignore에 추가

`G:\CS_Study\.gitignore`의 하위 프로젝트 목록에 새 프로젝트 폴더명 추가:

```gitignore
# === 하위 프로젝트 (각자 독립 git repo로 관리) ===
...기존 목록...
[새프로젝트명]/
```

### 6단계: The Record _index.md 생성

경로: `G:\CS_Study\The Record\2_Projects\[프로젝트명]\_index.md`

```markdown
---
status: "active"
tech: [사용 기술 배열]
repo: "[프로젝트명]"
phase: "Phase 0 — 초기 세팅"
portfolio: false
---

# [프로젝트명]

> 한 줄 설명

## 현재 상태

- [x] 레포 생성 및 기본 세팅
- [ ] 다음 작업들...

## 핵심 결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| YYYY-MM-DD | 프로젝트 시작 | ... |

## 배운 것

- 

## 관련 링크

- [[프로젝트명]] 레포: `G:\CS_Study\[프로젝트명]`
```

portfolio 값은 사용자에게 확인. 기본값 false.

### 7단계: 초기 커밋 + 리모트 연결

```
git add -A
git commit -m "init: [프로젝트명] project initial setup"
```

사용자가 리모트 URL을 제공하면:
```
git remote add origin [URL]
git push -u origin main
```

## Rule 설정

- **파일 위치**: `G:\CS_Study\.cursor\rules\new-project-setup.mdc`
- **트리거**: 사용자가 "새 프로젝트", "프로젝트 초기화", "레포 생성" 등을 요청할 때
- **AI에게 요구하는 것**:
  1. 프로젝트 이름과 성격(언어, 도메인)을 확인
  2. 위 7단계를 순서대로 실행
  3. 각 단계 완료 시 사용자에게 진행 상황 알림
  4. 리모트 URL은 사용자에게 확인 후 처리
  5. portfolio 여부도 사용자에게 확인

## 참고: 실제 생성 사례

PrivateLLM 프로젝트 생성 시 위 7단계를 모두 적용함. 해당 대화 참고 가능.
