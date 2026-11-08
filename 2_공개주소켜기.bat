@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   Seoul Ordinance QA - Public URL (Cloudflare Tunnel)
echo   Run "1_server.bat" first so the server is up.
echo ============================================================
echo.

rem  find cloudflared: project folder -> Program Files -> PATH -> auto download
set "CF="
if exist "%~dp0cloudflared.exe" set "CF=%~dp0cloudflared.exe"
if not defined CF if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" set "CF=C:\Program Files (x86)\cloudflared\cloudflared.exe"
if not defined CF if exist "C:\Program Files\cloudflared\cloudflared.exe" set "CF=C:\Program Files\cloudflared\cloudflared.exe"
if not defined CF for /f "delims=" %%P in ('where cloudflared 2^>nul') do if not defined CF set "CF=%%P"
if not defined CF (
  echo [SETUP] cloudflared not found. Downloading to this folder ^(~60MB, first run only^)...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0cloudflared.exe'"
  if exist "%~dp0cloudflared.exe" set "CF=%~dp0cloudflared.exe"
  echo.
)
if not defined CF goto NOCF

echo [1/2] Closing any old tunnels (to avoid address conflicts)...
taskkill /F /IM cloudflared.exe >nul 2>&1
timeout /t 2 >nul

echo [2/2] Starting a new tunnel and reading the public URL...
echo       (please wait ~10 seconds)
echo.

if exist tunnel_url.txt del tunnel_url.txt
start "" /b "%CF%" tunnel --url http://127.0.0.1:8000 --no-autoupdate > "%~dp0_tunnel_raw.log" 2>&1

rem  wait for the URL to appear in the log
set "URL="
for /l %%i in (1,1,30) do (
  timeout /t 1 >nul
  for /f "tokens=*" %%L in ('findstr /c:"trycloudflare.com" "%~dp0_tunnel_raw.log" 2^>nul') do (
    for %%W in (%%L) do (
      echo %%W | findstr /c:"https://" >nul && set "URL=%%W"
    )
  )
  if defined URL goto GOTURL
)

:GOTURL
echo.
echo ============================================================
if defined URL (
  echo   PUBLIC URL ^(share / open in browser^):
  echo       %URL%
  echo.
  echo   GRADING SUBMIT URL ^(add /ask^):
  echo       %URL%/ask
  echo   %URL% > "%~dp0tunnel_url.txt"
) else (
  echo   Could not read URL automatically.
  echo   Look for "https://....trycloudflare.com" in _tunnel_raw.log
)
echo ============================================================
echo.
echo   Keep this window OPEN until grading finishes. (Do NOT close)
echo.
echo   Press Ctrl+C to stop the tunnel.
echo ============================================================
echo.

rem  keep showing live tunnel log so the window stays open
powershell -NoProfile -Command "Get-Content -Path '%~dp0_tunnel_raw.log' -Wait -Tail 5"
goto END

:NOCF
echo [ERROR] cloudflared download failed. Check internet, or install with:
echo   winget install Cloudflare.cloudflared
echo   or put cloudflared.exe in this folder.
pause

:END
