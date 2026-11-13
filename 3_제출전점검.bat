@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Pre-submit self check (public examples)
echo   Runs public-question self-check. Review every score and trap result.
echo ============================================================
echo.
set /p URL="Paste the grading URL (with /ask) and press Enter: "
if "%URL%"=="" goto NOURL
echo.
echo Checking: %URL%
echo.
".venv\Scripts\python.exe" -X utf8 check.py --url "%URL%"
echo.
echo ^> A successful script run does NOT prove every answer is correct.
pause
exit /b 0

:NOURL
echo No URL entered. Exiting.
pause
exit /b 1
