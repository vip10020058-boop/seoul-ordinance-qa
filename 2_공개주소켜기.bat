@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   서울 자취 조례 Q&A - 공개 주소(터널) 시작
echo   먼저 "1_서버켜기.bat" 을 실행해 서버가 켜져 있어야 합니다.
echo   이 창은 채점이 끝날 때까지 끄지 마세요.
echo ============================================================
echo.
echo 잠시 후 아래와 같은 공개 주소가 나옵니다:
echo     https://OOOO.trycloudflare.com
echo 제출할 채점 주소 = 그 주소 뒤에 /ask 를 붙인 것
echo     예) https://OOOO.trycloudflare.com/ask
echo.

set "CF=C:\Program Files (x86)\cloudflared\cloudflared.exe"
if not exist "%CF%" (
  echo [오류] cloudflared 가 없습니다. 아래로 설치하세요:
  echo        winget install Cloudflare.cloudflared
  pause
  exit /b 1
)

"%CF%" tunnel --url http://127.0.0.1:8000

echo.
echo (터널이 종료되었습니다)
pause
