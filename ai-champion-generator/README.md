# AI챔피언 데이터분석 문제 자동 생성기

CSV 파일을 업로드하면 **5개의 데이터분석 실습 문제**와 **예시 정답 산출물**을 자동으로 생성하고 ZIP으로 다운로드합니다.

## 🚀 실행 방법

```bash
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

## 📦 빌드 (GitHub Pages 배포)

1. `vite.config.js`의 `base`를 레포지토리 이름으로 변경  
   예) `base: '/ai-champion-generator/'`
2. `npm run build`
3. `dist/` 폴더를 GitHub Pages에 배포 (CI/CD 자동화: `.github/workflows/pages.yml`)

## 📁 생성되는 ZIP 구조

```
exam_package.zip
├─ problems.html          # 문제지
├─ grading_rubric.csv     # 채점표
├─ answer_key.json        # 정답 메타 JSON
├─ README.md              # 안내문
└─ answers/
   ├─ problem_01_dashboard.html        # 1번: HTML 대시보드
   ├─ problem_02_filter_service.html   # 2번: 필터 서비스
   ├─ problem_03_vba_code.bas          # 3번: VBA 코드
   ├─ problem_03_excel_instruction.md  # 3번: 엑셀 작업 지시서
   ├─ problem_04_infographic.png       # 4번: PNG 인포그래픽
   └─ problem_05_policy_report.html    # 5번: 정책 제안 리포트
```

## 🛠 사용 기술

- **PapaParse** – CSV 파싱
- **JSZip** – ZIP 생성
- **FileSaver.js** – 파일 다운로드
- **Chart.js** – 차트
- **html2canvas** – PNG 캡처
- **Vite** – 개발 서버 / 빌드

## 📋 요구사항

- Node.js 18 이상
- 브라우저: Chrome / Edge / Firefox 최신 버전
- CSV 파일: UTF-8 인코딩, 첫 행 헤더, 최대 10MB
- 수치형 컬럼 1개 이상, 범주형 컬럼 1개 이상 필요

## 🔒 개인정보 보호

업로드한 CSV 파일은 **서버로 전송되지 않습니다.** 모든 처리는 브라우저 내에서 수행됩니다.
