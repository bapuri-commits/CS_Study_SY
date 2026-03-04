<#
.SYNOPSIS
    CS_Study 워크스페이스 부트스트랩 — 새 컴퓨터 원클릭 세팅

.DESCRIPTION
    새 컴퓨터에서 이 스크립트 하나만 실행하면:
    1. Git / Python 설치 확인 (없으면 winget 자동 설치 시도)
    2. G:\CS_Study 폴더 및 .workspace 생성
    3. config.json + sync.py 자동 생성
    4. 모든 GitHub 레포 클론
    5. 완료 안내

.USAGE
    1. 이 파일을 아무 곳에나 저장 (예: 바탕화면)
    2. PowerShell 관리자 모드로 실행:  .\bootstrap.ps1
    3. 이후 Cursor에서 CS_Study_SY.code-workspace 열기
#>

$ErrorActionPreference = "Continue"

# ─── 설정 ───────────────────────────────────────────────
$WORKSPACE = "G:\CS_Study"
$GITHUB_USER = "bapuri-commits"
$REPOS = @(
    @{L="Algorithm_Drill";        R="Drilling_Algorithm";            B="main"},
    @{L="BotTycoon";              R="BotTycoon-Study";               B="main"},
    @{L="eclass_crawler";         R="eclass_crawler";                B="main"},
    @{L="GitMini";                R="GitMini";                       B="main"},
    @{L="llm-mcp-agent";          R="llm-mcp-agent";                B="master"},
    @{L="News_Agent";             R="News_Agent";                    B="main"},
    @{L="Obsidian_Daily_Calendar"; R="Obsidian_Daily_Calendar_Plugin"; B="master"},
    @{L="PixelmonServer";         R="PixelmonServer";                B="main"},
    @{L="tax_agent";              R="tax_agent";                     B="main"},
    @{L="The Record";             R="The_Record";                    B="main"},
    @{L="The_Agent";              R="The_Agent";                     B="main"},
    @{L="xrun";                   R="xrun";                          B="master"},
    @{L="lesson-assist";          R="lesson-assist";                 B="main"}
)

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  CS_Study Workspace Bootstrap" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# ─── 1. 필수 도구 확인 ──────────────────────────────────
Write-Host "`n[ 1/4 ] 필수 도구 확인" -ForegroundColor Cyan

$gitOk = $null -ne (Get-Command git -ErrorAction SilentlyContinue)
$pyOk  = $null -ne (Get-Command python -ErrorAction SilentlyContinue)

if ($gitOk) {
    Write-Host "  ✓ Git: $(git --version)" -ForegroundColor Green
} else {
    Write-Host "  ✗ Git 미설치 — 자동 설치 시도 중..." -ForegroundColor Yellow
    try {
        winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
        Write-Host "  ✓ Git 설치 완료 (터미널 재시작 필요할 수 있음)" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Git 자동 설치 실패" -ForegroundColor Red
        Write-Host "    → https://git-scm.com/downloads 에서 수동 설치" -ForegroundColor Yellow
    }
}

if ($pyOk) {
    Write-Host "  ✓ Python: $(python --version)" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python 미설치 — 자동 설치 시도 중..." -ForegroundColor Yellow
    try {
        winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
        Write-Host "  ✓ Python 설치 완료 (터미널 재시작 필요할 수 있음)" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ Python 자동 설치 실패" -ForegroundColor Red
        Write-Host "    → https://python.org/downloads 에서 수동 설치" -ForegroundColor Yellow
    }
}

$gitOk = $null -ne (Get-Command git -ErrorAction SilentlyContinue)
$pyOk  = $null -ne (Get-Command python -ErrorAction SilentlyContinue)

if (-not $gitOk) {
    Write-Host "`n  Git을 설치한 후 터미널을 재시작하고 다시 실행하세요." -ForegroundColor Red
    exit 1
}

# ─── 2. 폴더 준비 ───────────────────────────────────────
Write-Host "`n[ 2/4 ] 폴더 준비" -ForegroundColor Cyan

if (-not (Test-Path $WORKSPACE)) {
    New-Item -ItemType Directory -Path $WORKSPACE -Force | Out-Null
    Write-Host "  ✓ $WORKSPACE 생성" -ForegroundColor Green
} else {
    Write-Host "  ● $WORKSPACE 이미 존재" -ForegroundColor Green
}

$wsDir = Join-Path $WORKSPACE ".workspace"
if (-not (Test-Path $wsDir)) {
    New-Item -ItemType Directory -Path $wsDir -Force | Out-Null
}

# config.json 생성
$configContent = @'
{
    "github_user": "bapuri-commits",
    "workspace_file": "CS_Study_SY.code-workspace",
    "repos": [
        {"local": "Algorithm_Drill",        "remote": "Drilling_Algorithm",            "branch": "main"},
        {"local": "BotTycoon",              "remote": "BotTycoon-Study",               "branch": "main"},
        {"local": "eclass_crawler",         "remote": "eclass_crawler",                "branch": "main"},
        {"local": "GitMini",                "remote": "GitMini",                       "branch": "main"},
        {"local": "llm-mcp-agent",          "remote": "llm-mcp-agent",                "branch": "master"},
        {"local": "News_Agent",             "remote": "News_Agent",                    "branch": "main"},
        {"local": "Obsidian_Daily_Calendar","remote": "Obsidian_Daily_Calendar_Plugin","branch": "master"},
        {"local": "PixelmonServer",         "remote": "PixelmonServer",                "branch": "main"},
        {"local": "tax_agent",              "remote": "tax_agent",                     "branch": "main"},
        {"local": "The Record",             "remote": "The_Record",                    "branch": "main"},
        {"local": "The_Agent",              "remote": "The_Agent",                     "branch": "main"},
        {"local": "xrun",                   "remote": "xrun",                          "branch": "master"},
        {"local": "lesson-assist",          "remote": "lesson-assist",                 "branch": "main"}
    ]
}
'@
Set-Content -Path (Join-Path $wsDir "config.json") -Value $configContent -Encoding UTF8
Write-Host "  ✓ config.json 생성" -ForegroundColor Green

# ─── 3. 레포 클론 ───────────────────────────────────────
Write-Host "`n[ 3/4 ] 레포 클론" -ForegroundColor Cyan

$cloned = 0; $existed = 0; $failed = 0

foreach ($repo in $REPOS) {
    $localPath = Join-Path $WORKSPACE $repo.L
    $remoteUrl = "https://github.com/$GITHUB_USER/$($repo.R).git"

    if (Test-Path (Join-Path $localPath ".git")) {
        Write-Host "  ● $($repo.L) — 이미 존재" -ForegroundColor Green
        $existed++
        continue
    }

    Write-Host "  ↓ $($repo.L) 클론 중..." -ForegroundColor Cyan -NoNewline
    $result = git clone -b $repo.B $remoteUrl $localPath 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "`r  ✓ $($repo.L) — 완료            " -ForegroundColor Green
        $cloned++
    } else {
        Write-Host "`r  ✗ $($repo.L) — 실패            " -ForegroundColor Red
        $failed++
    }
}

Write-Host "`n  클론: $cloned | 기존: $existed | 실패: $failed"

# ─── 4. 완료 ────────────────────────────────────────────
Write-Host "`n[ 4/4 ] 세팅 완료" -ForegroundColor Green
Write-Host ""
Write-Host "  워크스페이스:  $WORKSPACE" -ForegroundColor White
Write-Host "  레포 수:       $($REPOS.Count)개" -ForegroundColor White
Write-Host ""
Write-Host "  다음 단계:" -ForegroundColor Cyan
Write-Host "  1. Cursor 설치  → https://cursor.sh" -ForegroundColor White
Write-Host "  2. Cursor에서   → CS_Study_SY.code-workspace 열기" -ForegroundColor White

if ($pyOk) {
    Write-Host "  3. 상태 확인    → python .workspace\sync.py" -ForegroundColor White
    Write-Host "  4. 업데이트     → python .workspace\sync.py pull" -ForegroundColor White
} else {
    Write-Host "  3. Python 설치 후 → python .workspace\sync.py" -ForegroundColor Yellow
}

Write-Host ""
