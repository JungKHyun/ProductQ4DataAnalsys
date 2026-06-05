/**
 * answerGenerator.js
 * 각 문제에 대한 예시 정답 산출물을 생성한다.
 */

import { dashboardTemplate } from '../templates/dashboardTemplate.js';
import { filterServiceTemplate } from '../templates/filterServiceTemplate.js';
import { policyReportTemplate } from '../templates/policyReportTemplate.js';
import { vbaTemplate } from '../templates/vbaTemplate.js';

/** 문제 1: HTML 대시보드 */
export function generateDashboardHtml(rows, profile) {
  return dashboardTemplate(rows, profile);
}

/** 문제 2: HTML 필터 서비스 */
export function generateFilterServiceHtml(rows, profile) {
  return filterServiceTemplate(rows, profile);
}

/** 문제 3: VBA 코드 */
export function generateVbaCode(profile) {
  return vbaTemplate(profile);
}

/** 문제 3: 엑셀 작업 지시서 */
export function generateExcelInstruction(profile) {
  const { recommendedMetric, recommendedGroup, columns } = profile;
  const today = new Date().toLocaleDateString('ko-KR');

  return `# 엑셀 작업 지시서 — VBA 자동화 보고서

작성일: ${today}

---

## 개요

이 지시서는 \`problem_03_vba_code.bas\` VBA 코드를 활용하여 엑셀 매크로 파일(\`.xlsm\`)을 구성하는 방법을 안내합니다.

---

## 준비 사항

1. Microsoft Excel 2016 이상 (또는 Microsoft 365)
2. 분석 대상 CSV 파일 (본 시험에서 업로드한 파일과 동일)
3. VBA 편집기 사용 권한 활성화

---

## 작업 순서

### Step 1 — 엑셀 파일 생성

1. Excel을 열고 **새 통합 문서** 생성
2. **파일 → 다른 이름으로 저장 → Excel 매크로 사용 통합 문서(\*.xlsm)** 로 저장

### Step 2 — VBA 코드 삽입

1. \`Alt + F11\` → Visual Basic Editor 열기
2. **삽입 → 모듈** 클릭
3. \`problem_03_vba_code.bas\` 파일 내용을 전체 복사하여 모듈에 붙여넣기
4. 코드 상단의 \`CSV_FILE_PATH\` 상수를 실제 CSV 파일 경로로 변경

   \`\`\`vba
   Const CSV_FILE_PATH As String = "C:\\경로\\데이터파일.csv"
   \`\`\`

### Step 3 — 매크로 실행

1. \`Alt + F8\` → 매크로 목록에서 \`CreateAnalysisReport\` 선택
2. **실행** 클릭
3. 완료 후 다음 시트가 자동 생성됩니다:
   - **원본데이터** 시트: CSV 데이터 전체
   - **분석결과** 시트: ${recommendedGroup}별 ${recommendedMetric} 집계표 + 차트

---

## 예상 시트 구조

### 원본데이터 시트

| ${columns.join(' | ')} |
|${columns.map(() => '---').join('|')}|
| (데이터 자동 채움) |

### 분석결과 시트

| ${recommendedGroup} | ${recommendedMetric} 합계 | 비율(%) |
|---|---|---|
| (그룹별 집계 자동 채움) | | |

차트: 막대형 차트 (${recommendedGroup} × ${recommendedMetric})

---

## 주의사항

- CSV 파일 인코딩이 **UTF-8-BOM** 또는 **ANSI**여야 엑셀에서 한글이 깨지지 않습니다.
- 파일 경로에 한글이 포함된 경우 오류가 발생할 수 있으니 영문 경로 사용을 권장합니다.
- 매크로 보안 설정에서 **"모든 매크로 사용"** 또는 **"디지털 서명된 매크로만 사용"** 으로 설정 필요

---

*이 지시서는 AI챔피언 데이터분석 문제 자동 생성기에서 생성된 예시 산출물입니다.*
`;
}

/** 문제 5: HTML 정책 제안 리포트 */
export function generatePolicyReportHtml(rows, profile) {
  return policyReportTemplate(rows, profile);
}
