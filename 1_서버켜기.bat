@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Seoul Ordinance QA - API Server (port 8000)
echo   Keep this window OPEN until grading finishes.
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" goto NOVENV
if not exist ".env" goto NOENV

echo Starting server... "Application startup complete" means OK.
echo.
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000
echo.
echo (server stopped)
pause
exit /b 0

:NOVENV
echo [ERROR] venv not found. Run first:
echo   py -3 -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1

:NOENV
echo [ERROR] .env not found. Need .env with UPSTAGE_API_KEY.
pause
exit /b 1
