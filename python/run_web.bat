@echo off
setlocal
cd /d "%~dp0"

if "%GEMINI_API_KEY%"=="" (
  echo [경고] GEMINI_API_KEY가 설정되어 있지 않습니다.
  echo .env 파일 또는 환경변수를 확인하세요.
)

python -m streamlit run app.py
if errorlevel 1 (
  py -m streamlit run app.py
)
