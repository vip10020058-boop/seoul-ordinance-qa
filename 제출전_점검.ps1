# ============================================================
#  제출 전 자가 점검: 공개 주소로 공개 예시 문항을 돌려
#  오류 0건 · 90초 이내인지 확인합니다.
#  사용법: .\제출전_점검.ps1 https://OOOO.trycloudflare.com/ask
# ============================================================
param([string]$Url)

$root = $PSScriptRoot
$py   = Join-Path $root ".venv\Scripts\python.exe"

if (-not $Url) {
    Write-Host "사용법: .\제출전_점검.ps1 https://OOOO.trycloudflare.com/ask" -ForegroundColor Yellow
    $Url = Read-Host "채점 주소(/ask 포함)를 붙여넣고 엔터"
}
if (-not $Url) { Write-Host "주소가 없습니다. 종료합니다." -ForegroundColor Red; exit 1 }

Write-Host "`n점검 시작: $Url`n" -ForegroundColor Cyan
& $py -X utf8 (Join-Path $root "check.py") --url $Url

Write-Host "`n→ '오류 0건'이고 모든 문항이 90초 이내면 제출 OK." -ForegroundColor Green
Read-Host "`n엔터를 누르면 종료"
