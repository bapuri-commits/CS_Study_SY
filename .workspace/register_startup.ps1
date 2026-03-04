<#
.SYNOPSIS
    CS_Study Startup Sync를 Windows Task Scheduler에 등록/해제

.USAGE
    등록:  powershell -ExecutionPolicy Bypass -File register_startup.ps1
    해제:  powershell -ExecutionPolicy Bypass -File register_startup.ps1 -Remove
#>

param(
    [switch]$Remove
)

$TASK_NAME = "CS_Study Startup Sync"
$PYTHONW = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
$SCRIPT_PATH = Join-Path $PSScriptRoot "startup_sync.pyw"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  CS_Study Startup Sync — Task Scheduler 등록" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# ─── 해제 모드 ───
if ($Remove) {
    $removed = $false

    $exists = schtasks /query /tn $TASK_NAME 2>$null
    if ($LASTEXITCODE -eq 0) {
        schtasks /delete /tn $TASK_NAME /f >$null
        Write-Host "`n  ✓ Task Scheduler에서 제거됨" -ForegroundColor Green
        $removed = $true
    }

    $startupVbs = Join-Path ([Environment]::GetFolderPath("Startup")) "CS_Study_Sync.vbs"
    if (Test-Path $startupVbs) {
        Remove-Item $startupVbs -Force
        Write-Host "`n  ✓ Startup 폴더에서 제거됨" -ForegroundColor Green
        $removed = $true
    }

    if (-not $removed) {
        Write-Host "`n  등록된 작업이 없습니다." -ForegroundColor Yellow
    }
    Write-Host ""
    exit 0
}

# ─── 사전 확인 ───
if (-not $PYTHONW) {
    $pyPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($pyPath) {
        $PYTHONW = Join-Path (Split-Path $pyPath) "pythonw.exe"
    }
}

if (-not $PYTHONW -or -not (Test-Path $PYTHONW)) {
    Write-Host "`n  ✗ pythonw.exe를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "    Python이 설치되어 있고 PATH에 등록되어 있는지 확인하세요." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $SCRIPT_PATH)) {
    Write-Host "`n  ✗ startup_sync.pyw를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "    이 스크립트를 .workspace 폴더에서 실행하세요." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n  pythonw:  $PYTHONW" -ForegroundColor White
Write-Host "  script:   $SCRIPT_PATH" -ForegroundColor White

# ─── 기존 작업 확인 ───
$exists = schtasks /query /tn $TASK_NAME 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n  기존 작업을 덮어씁니다..." -ForegroundColor Yellow
    schtasks /delete /tn $TASK_NAME /f >$null
}

# ─── Task Scheduler 등록 시도 ───
$registered = $false

schtasks /create `
    /tn $TASK_NAME `
    /tr "`"$PYTHONW`" `"$SCRIPT_PATH`"" `
    /sc onlogon `
    /delay 0000:30 `
    /rl limited `
    /f 2>$null >$null

if ($LASTEXITCODE -eq 0) {
    $registered = $true
    Write-Host "`n  ✓ Task Scheduler에 등록 완료!" -ForegroundColor Green
} else {
    Write-Host "`n  Task Scheduler 등록 실패 (관리자 권한 필요)" -ForegroundColor Yellow
    Write-Host "  → Startup 폴더 방식으로 대체합니다..." -ForegroundColor Yellow

    # Startup 폴더에 VBS 래퍼 생성 (콘솔 안 뜨게)
    $startupDir = [Environment]::GetFolderPath("Startup")
    $vbsPath = Join-Path $startupDir "CS_Study_Sync.vbs"

    $vbsContent = @"
Set ws = CreateObject("WScript.Shell")
ws.Run """{0}"" ""{1}""", 0, False
"@ -f $PYTHONW, $SCRIPT_PATH

    Set-Content -Path $vbsPath -Value $vbsContent -Encoding ASCII
    $registered = $true
    Write-Host "`n  ✓ Startup 폴더에 등록 완료!" -ForegroundColor Green
    Write-Host "    $vbsPath" -ForegroundColor DarkGray
}

if ($registered) {
    Write-Host ""
    Write-Host "  동작 방식:" -ForegroundColor Cyan
    Write-Host "    · Windows 로그인 시 자동 실행" -ForegroundColor White
    Write-Host "    · 네트워크 연결 대기 → 전체 레포 pull" -ForegroundColor White
    Write-Host "    · 결과를 Windows 토스트 알림으로 표시" -ForegroundColor White
    Write-Host "    · 로그: .workspace\sync.log" -ForegroundColor White
    Write-Host ""
    Write-Host "  관리:" -ForegroundColor Cyan
    Write-Host "    · 해제: .\register_startup.ps1 -Remove" -ForegroundColor White
    Write-Host "    · 수동 실행: pythonw startup_sync.pyw" -ForegroundColor White
}

Write-Host ""
