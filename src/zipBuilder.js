/**
 * zipBuilder.js
 * JSZip을 이용해 exam_package.zip을 조립하고 Blob을 반환한다.
 */

const README_CONTENT = `# exam_package — 시험 패키지 안내

AI챔피언 데이터분석 문제 자동 생성기에 의해 자동 생성된 시험 패키지입니다.

## 파일 목록

| 파일 | 설명 |
|------|------|
| problems.html | 문제지 (수험자에게 배포) |
| grading_rubric.csv | 채점표 (채점자용) |
| answer_key.json | 정답 메타 JSON |
| answers/problem_01_dashboard.html | 문제 1 예시 정답 |
| answers/problem_02_filter_service.html | 문제 2 예시 정답 |
| answers/problem_03_vba_code.bas | 문제 3 예시 VBA 코드 |
| answers/problem_03_excel_instruction.md | 문제 3 엑셀 작업 지시서 |
| answers/problem_04_infographic.png | 문제 4 예시 인포그래픽 |
| answers/problem_05_policy_report.html | 문제 5 예시 정책 리포트 |

## 사용 방법

1. \`problems.html\`을 열어 문제 내용을 확인합니다.
2. \`grading_rubric.csv\`를 채점 시 참고합니다.
3. \`answers/\` 폴더 내 예시 정답을 참고하여 평가 기준을 수립합니다.

---
생성 일시: ${new Date().toLocaleString('ko-KR')}  
생성 도구: AI챔피언 데이터분석 문제 자동 생성기
`;

/**
 * @param {Object} files
 *   problemsHtml, rubricCsv, answerKey,
 *   dashboardHtml, filterHtml, vbaCode, excelInstruction,
 *   pngBlob (nullable), policyHtml
 * @returns {Promise<Blob>}
 */
export async function buildExamZip(files) {
  const zip = new window.JSZip();

  zip.file('problems.html', files.problemsHtml);
  zip.file('grading_rubric.csv', '\uFEFF' + files.rubricCsv); // BOM for Excel
  zip.file('answer_key.json', files.answerKey);
  zip.file('README.md', README_CONTENT);

  const answers = zip.folder('answers');
  answers.file('problem_01_dashboard.html', files.dashboardHtml);
  answers.file('problem_02_filter_service.html', files.filterHtml);
  answers.file('problem_03_vba_code.bas', files.vbaCode);
  answers.file('problem_03_excel_instruction.md', files.excelInstruction);

  if (files.pngBlob) {
    answers.file('problem_04_infographic.png', files.pngBlob, { binary: true });
  } else {
    answers.file('problem_04_infographic.txt', 'PNG 생성에 실패하였습니다. 브라우저 콘솔을 확인하세요.');
  }

  answers.file('problem_05_policy_report.html', files.policyHtml);

  return zip.generateAsync({ type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } });
}

/** Blob을 파일로 다운로드 */
export function downloadZip(zipBlob) {
  window.saveAs(zipBlob, 'exam_package.zip');
}
