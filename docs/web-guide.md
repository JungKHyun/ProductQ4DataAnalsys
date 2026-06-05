# 웹 실행 가이드

## 1) 의존성 설치

```powershell
pip install -r requirements.txt
```

## 2) Gemini API 키 설정

```powershell
set GEMINI_API_KEY=여기에_키입력
```

## 3) 웹 앱 실행

방법 A:

```powershell
streamlit run app.py
```

방법 B(윈도우 배치 파일):

```powershell
run_web.bat
```

실행 후 브라우저에서 Streamlit 주소(기본 http://localhost:8501)로 접속하면 됩니다.
