# CS_Study_SY

Cursor IDE 학습 워크스페이스 설정 저장소.

## 구조

```
CS_Study/
├── CS_Study_SY.code-workspace   # 워크스페이스 설정 파일
├── Algorithm_Drill/              # [별도 repo] 백준 알고리즘 학습 (C++)
└── GitMini/                      # [별도 repo] Git 클라이언트 프로젝트 (Java)
```

## 사용법 (새 PC / 노트북에서)

1. 이 repo를 클론
2. 하위 프로젝트들을 각각 클론 (같은 폴더 안에)
3. `CS_Study_SY.code-workspace` 파일로 Cursor 열기

```bash
git clone <이 repo URL> CS_Study
cd CS_Study
git clone https://github.com/bapuri-commits/Drilling_Algorithm.git Algorithm_Drill
git clone <GitMini repo URL> GitMini
```

## 프로젝트별 Git Remote

| 프로젝트 | Remote URL |
|----------|-----------|
| Algorithm_Drill | `https://github.com/bapuri-commits/Drilling_Algorithm.git` |
| GitMini | (GitHub repo 생성 후 기록) |
