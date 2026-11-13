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
if errorlevel 1 goto CHECK_FAILED
echo.
echo [PASS] All committed sample questions passed the configured checks.
echo ^> This does not validate answer wording beyond citation/format checks.
pause
exit /b 0

:CHECK_FAILED
echo.
echo [FAIL] One or more sample questions failed. Review the output above.
pause
exit /b 1

:NOURL
echo No URL entered. Exiting.
pause
exit /b 1
