@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   제출 전 자가 점검
echo   공개 예시 문항을 돌려 오류 0건, 90초 이내인지 확인합니다.
echo ============================================================
echo.
set /p URL="채점 주소(/ask 포함)를 붙여넣고 엔터: "
if "%URL%"=="" (
  echo 주소가 없습니다. 종료합니다.
  pause
  exit /b 1
)
echo.
echo 점검 시작: %URL%
echo.
".venv\Scripts\python.exe" -X utf8 check.py --url "%URL%"
echo.
echo → '오류 0건'이고 모든 문항이 90초 이내면 제출 OK.
pause
