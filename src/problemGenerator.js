/**
 * problemGenerator.js
 * 데이터 프로파일을 기반으로 문제 5개를 정의하고 문제지 HTML, 채점표 CSV, 정답 JSON을 생성한다.
 */

import { problemsTemplate } from '../templates/problemsTemplate.js';
import { rubricTemplate } from '../templates/rubricTemplate.js';

/** 5개 문제 정의 생성 */
export function generateProblems(profile) {
  const { recommendedMetric, recommendedGroup, recommendedCategory, dateColumns, rowCount } = profile;
  const metric = recommendedMetric;
  const group = recommendedGroup;
  const category = recommendedCategory || group;
  const hasDate = dateColumns.length > 0;

  return [
    {
      id: 1,
      title: 'HTML 대시보드 제작',
      file: 'problem_01_dashboard.html',
      description: `업로드한 데이터(${rowCount.toLocaleString()}건)를 활용하여 주요 현황을 한눈에 볼 수 있는 HTML 대시보드를 제작하시오.`,
      requirements: [
        `전체 ${metric} 합계(KPI) 표시`,
        `${group}별 ${metric} 합계 막대차트 표시`,
        `${metric} 기준 상위 5개 ${group} 목록 표시`,
        '원본 데이터 표(10행 이상) 표시',
        '분석 결과 요약 문장 자동 표시',
      ],
      rubric: [
        { item: 'KPI 표시', score: 20 },
        { item: '차트 표시', score: 20 },
        { item: '상위 5개 표시', score: 20 },
        { item: '데이터 표 표시', score: 20 },
        { item: '가독성 및 디자인', score: 20 },
      ],
    },
    {
      id: 2,
      title: 'HTML 검색/필터 서비스 제작',
      file: 'problem_02_filter_service.html',
      description: `업로드한 데이터를 기반으로 사용자가 원하는 조건으로 데이터를 검색·필터링할 수 있는 HTML 서비스를 제작하시오.`,
      requirements: [
        `${category} 기준 드롭다운 필터 기능`,
        '검색창(텍스트 검색) 기능',
        '선택 조건의 합계 및 건수 실시간 표시',
        '필터링된 데이터 표 표시',
        '선택 항목 요약 문장 자동 생성',
      ],
      rubric: [
        { item: '필터 기능 동작', score: 25 },
        { item: '검색 기능 동작', score: 20 },
        { item: '합계/건수 계산 정확성', score: 20 },
        { item: '표시 정확성', score: 20 },
        { item: '화면 구성 및 UX', score: 15 },
      ],
    },
    {
      id: 3,
      title: 'Excel VBA 자동화 코드 작성',
      file: 'problem_03_vba_code.bas / problem_03_excel_instruction.md',
      description: `CSV 데이터를 엑셀로 불러와 자동으로 분석 보고서를 생성하는 VBA 코드를 작성하시오.`,
      requirements: [
        'CSV 데이터를 엑셀 시트로 불러오기',
        '분석결과 시트 자동 생성',
        `${group}별 ${metric} 집계표 생성`,
        '집계 결과 차트 자동 생성',
        '보고서 제목 및 작성일 표시, 주석 포함',
      ],
      rubric: [
        { item: 'VBA 코드 실행 가능성', score: 30 },
        { item: '집계표 생성', score: 25 },
        { item: '차트 생성', score: 20 },
        { item: '보고서 시트 구성', score: 15 },
        { item: '주석 포함 여부', score: 10 },
      ],
    },
    {
      id: 4,
      title: 'PNG 인포그래픽 제작',
      file: 'problem_04_infographic.png',
      description: `데이터 분석 결과를 시각적으로 표현한 인포그래픽 이미지(PNG)를 제작하시오.`,
      requirements: [
        `제목 및 분석 주제 표시`,
        `핵심 KPI 3개 이상(전체 합계, 평균, 최고 ${group}) 포함`,
        `${metric} 기준 상위 5개 항목 시각화`,
        '해석 문장 2개 이상 포함',
        '출처·작성자 문구 표시',
      ],
      rubric: [
        { item: 'KPI 표현', score: 25 },
        { item: '상위 항목 시각화', score: 25 },
        { item: '해석 문장', score: 20 },
        { item: '시각적 가독성', score: 20 },
        { item: '출처 표시', score: 10 },
      ],
    },
    {
      id: 5,
      title: 'HTML 정책 제안 리포트 작성',
      file: 'problem_05_policy_report.html',
      description: `데이터 분석 결과를 바탕으로 정책 제안을 담은 HTML 리포트를 제작하시오.`,
      requirements: [
        '데이터 요약(전체 현황, 주요 통계) 서술',
        `주요 발견 사항 3개 이상(${hasDate ? '시계열 변화 포함' : '그룹 간 비교 포함'})`,
        '데이터 근거를 갖춘 정책 제안 3개 이상',
        '근거 데이터 표 포함',
        '차트 1개 이상 포함',
      ],
      rubric: [
        { item: '데이터 요약 완성도', score: 20 },
        { item: '주요 발견 사항', score: 25 },
        { item: '정책 제안 구체성', score: 25 },
        { item: '근거 표 포함', score: 15 },
        { item: '차트 포함', score: 15 },
      ],
    },
  ];
}

/** 문제지 HTML 생성 */
export function generateProblemHtml(problems, profile) {
  return problemsTemplate(problems, profile);
}

/** 채점표 CSV 생성 */
export function generateRubricCsv(problems) {
  return rubricTemplate(problems);
}

/** 정답 메타 JSON 생성 */
export function generateAnswerKey(profile, results) {
  return {
    generatedAt: new Date().toISOString(),
    dataProfile: {
      rowCount: profile.rowCount,
      columns: profile.columns,
      numericColumns: profile.numericColumns,
      categoryColumns: profile.categoryColumns,
      dateColumns: profile.dateColumns,
      recommendedMetric: profile.recommendedMetric,
      recommendedGroup: profile.recommendedGroup,
      recommendedCategory: profile.recommendedCategory,
    },
    answers: [
      { problemId: 1, file: 'answers/problem_01_dashboard.html', type: 'HTML' },
      { problemId: 2, file: 'answers/problem_02_filter_service.html', type: 'HTML' },
      { problemId: 3, files: ['answers/problem_03_vba_code.bas', 'answers/problem_03_excel_instruction.md'], type: 'VBA+MD' },
      { problemId: 4, file: 'answers/problem_04_infographic.png', type: 'PNG' },
      { problemId: 5, file: 'answers/problem_05_policy_report.html', type: 'HTML' },
    ],
    note: '이 파일은 자동 생성된 예시 정답 메타데이터입니다. 실제 평가 시 채점자가 rubric 기준에 따라 직접 평가하십시오.',
  };
}
