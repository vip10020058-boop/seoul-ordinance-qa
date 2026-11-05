# ============================================================
#  서울 자취 조례 Q&A — 채점용 서버 + 공개 주소 한 번에 켜기
#  사용법: 이 파일을 우클릭 → "PowerShell에서 실행"
#          또는 PowerShell에서  .\채점서버_켜기.ps1
#  종료:   열린 두 개의 창을 각각 닫으면 됩니다.
# ============================================================

$root = $PSScriptRoot
$py   = Join-Path $root ".venv\Scripts\python.exe"
$cf   = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

Write-Host "`n[1/3] 사전 점검..." -ForegroundColor Cyan

if (-not (Test-Path $py)) {
    Write-Host "  ✗ 가상환경을 찾지 못했습니다: $py" -ForegroundColor Red
    Write-Host "    먼저 'py -3 -m venv .venv' 로 가상환경을 만들고 패키지를 설치하세요." -ForegroundColor Yellow
    Read-Host "`n엔터를 누르면 종료"; exit 1
}
if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host "  ✗ .env 파일이 없습니다. UPSTAGE_API_KEY를 넣은 .env가 필요합니다." -ForegroundColor Red
    Read-Host "`n엔터를 누르면 종료"; exit 1
}
if (-not (Test-Path $cf)) {
    Write-Host "  ✗ cloudflared를 찾지 못했습니다: $cf" -ForegroundColor Red
    Write-Host "    'winget install Cloudflare.cloudflared' 로 설치하세요." -ForegroundColor Yellow
    Read-Host "`n엔터를 누르면 종료"; exit 1
}
Write-Host "  ✓ 가상환경 / .env / cloudflared 확인 완료" -ForegroundColor Green

# 혹시 이전에 8000 포트를 쓰던 서버가 남아 있으면 정리
$old = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($old) {
    Write-Host "  · 포트 8000을 쓰던 이전 프로세스를 정리합니다." -ForegroundColor Yellow
    $old.OwningProcess | Sort-Object -Unique | ForEach-Object { try { Stop-Process -Id $_ -Force } catch {} }
    Start-Sleep -Seconds 2
}

Write-Host "`n[2/3] API 서버를 새 창에서 시작합니다 (포트 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit","-Command",
    "cd '$root'; & '$py' -m uvicorn app:app --host 0.0.0.0 --port 8000"
)
Start-Sleep -Seconds 8

Write-Host "`n[3/3] 공개 주소 터널을 새 창에서 시작합니다..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit","-Command",
    "& '$cf' tunnel --url http://127.0.0.1:8000"
)

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " 두 개의 새 창이 열렸습니다. 둘 다 끄지 마세요." -ForegroundColor Green
Write-Host ""
Write-Host " · 서버 창: 'Application startup complete' 가 보이면 정상" -ForegroundColor White
Write-Host " · 터널 창: https://OOOO.trycloudflare.com 주소가 나옵니다" -ForegroundColor White
Write-Host ""
Write-Host " 제출할 채점 주소 =  그 주소 뒤에 /ask 를 붙인 것" -ForegroundColor Yellow
Write-Host "   예) https://OOOO.trycloudflare.com/ask" -ForegroundColor Yellow
Write-Host ""
Write-Host " 시민용 화면을 보려면 브라우저에서 그 주소(/ask 없이)를 열면 됩니다." -ForegroundColor White
Write-Host "============================================================`n" -ForegroundColor Green
Read-Host "확인했으면 엔터 (이 창은 닫아도 됩니다. 서버/터널 두 창은 유지)"
