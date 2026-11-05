@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Seoul Ordinance QA - Public URL (Cloudflare Tunnel)
echo   Run "1_server.bat" first so the server is up.
echo   Keep this window OPEN until grading finishes.
echo ============================================================
echo.
echo A public URL will appear below:
echo     https://OOOO.trycloudflare.com
echo Submit URL = that URL + /ask
echo     e.g.  https://OOOO.trycloudflare.com/ask
echo.

set "CF=C:\Program Files (x86)\cloudflared\cloudflared.exe"
if not exist "%CF%" goto NOCF

"%CF%" tunnel --url http://127.0.0.1:8000
echo.
echo (tunnel stopped)
pause
exit /b 0

:NOCF
echo [ERROR] cloudflared not found. Install with:
echo   winget install Cloudflare.cloudflared
pause
exit /b 1
