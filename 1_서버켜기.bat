@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
echo ============================================================
echo   Seoul Ordinance QA - API Server (port 8000)
echo   Keep this window OPEN until grading finishes.
echo ============================================================
echo.

rem ------------------------------------------------------------
rem  1) .env check (copy from .env.example on first run)
rem ------------------------------------------------------------
if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  echo [SETUP] .env created. Put your UPSTAGE_API_KEY in it, save, then run this file again.
  start "" notepad ".env"
  pause
  exit /b 1
)
findstr /r /c:"^UPSTAGE_API_KEY=..*" ".env" >nul
if errorlevel 1 (
  echo [SETUP] UPSTAGE_API_KEY is empty in .env. Fill it in, save, then run this file again.
  start "" notepad ".env"
  pause
  exit /b 1
)

rem ------------------------------------------------------------
rem  2) Python virtual env (auto install on first run)
rem ------------------------------------------------------------
if exist ".venv\Scripts\python.exe" goto HAVEVENV

echo [SETUP] First run: creating Python environment. This takes a few minutes.
set "PY="
for %%V in (312 313 311 310) do (
  if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
  if not defined PY if exist "%ProgramFiles%\Python%%V\python.exe" set "PY=%ProgramFiles%\Python%%V\python.exe"
)
if not defined PY (
  where py >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  echo [SETUP] Python not found. Installing Python 3.12 with winget...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PY (
  echo [ERROR] Python install failed. Install Python 3.12 from https://www.python.org/downloads/ and run again.
  pause
  exit /b 1
)

echo [SETUP] Using Python: !PY!
if "!PY!"=="py -3" (
  py -3 -m venv .venv
) else (
  "!PY!" -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Failed to create .venv
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  rmdir /s /q .venv
  echo [ERROR] pip install failed. Check your internet connection and run again.
  pause
  exit /b 1
)
echo [SETUP] Python environment ready.
echo.

:HAVEVENV
rem ------------------------------------------------------------
rem  3) Embedding index (build once if missing)
rem ------------------------------------------------------------
if not exist "data\vectors_paragraph.npy" (
  echo [SETUP] Building embedding index - data\vectors_paragraph.npy ...
  ".venv\Scripts\python.exe" -X utf8 build_index.py
  echo.
)

rem ------------------------------------------------------------
rem  4) Start server
rem ------------------------------------------------------------
echo Starting server... "Application startup complete" means OK.
echo.
".venv\Scripts\python.exe" -m uvicorn app:app --host 0.0.0.0 --port 8000
echo.
echo (server stopped)
pause
exit /b 0
