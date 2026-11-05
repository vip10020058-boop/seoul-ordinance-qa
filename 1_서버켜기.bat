@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   서울 자취 조례 Q&A - API 서버 시작 (포트 8000)
echo   이 창은 채점이 끝날 때까지 끄지 마세요.
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [오류] 가상환경이 없습니다. 먼저 아래를 실행하세요:
  echo        py -3 -m venv .venv
  echo        .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
if not exist ".env" (
  echo [오류] .env 파일이 없습니다. UPSTAGE_API_KEY를 넣은 .env가 필요합니다.
  pause
  exit /b 1
)

echo 서버를 시작합니다. 잠시 후 "Application startup complete" 가 보이면 정상입니다.
echo.
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000

echo.
echo (서버가 종료되었습니다)
pause
