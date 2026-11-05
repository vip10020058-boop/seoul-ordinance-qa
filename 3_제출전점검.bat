@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Pre-submit self check (public examples)
echo   Confirms 0 errors and under 90s per question.
echo ============================================================
echo.
set /p URL="Paste the grading URL (with /ask) and press Enter: "
if "%URL%"=="" goto NOURL
echo.
echo Checking: %URL%
echo.
".venv\Scripts\python.exe" -X utf8 check.py --url "%URL%"
echo.
echo ^> If "0 errors" and all under 90s, you are good to submit.
pause
exit /b 0

:NOURL
echo No URL entered. Exiting.
pause
exit /b 1
