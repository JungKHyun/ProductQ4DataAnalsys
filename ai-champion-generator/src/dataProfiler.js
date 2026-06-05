/**
 * dataProfiler.js
 * CSV 데이터를 분석하여 컬럼 유형, 통계, 분석 추천 대상을 반환한다.
 */

const DATE_PATTERNS = [
  /^\d{4}-\d{2}-\d{2}$/,
  /^\d{4}\/\d{2}\/\d{2}$/,
  /^\d{4}\.\d{2}\.\d{2}$/,
  /^\d{4}년\s*\d{1,2}월/,
];

const YEAR_PATTERN = /^(19|20)\d{2}$/;

/** 컬럼 유형 감지 */
export function detectColumnTypes(rows, headers) {
  const types = {};

  headers.forEach(col => {
    const sample = rows
      .slice(0, Math.min(80, rows.length))
      .map(r => r[col])
      .filter(v => v !== null && v !== undefined && String(v).trim() !== '');

    if (sample.length === 0) { types[col] = 'unknown'; return; }

    // 날짜 패턴
    if (sample.every(v => DATE_PATTERNS.some(p => p.test(String(v).trim())))) {
      types[col] = 'date'; return;
    }

    // 연도 패턴 → year (범주/수치 경계; 수치로도 집계 가능)
    if (sample.every(v => YEAR_PATTERN.test(String(v).trim()))) {
      types[col] = 'year'; return;
    }

    // 수치형 (80% 이상이 숫자면 수치형)
    const numericCount = sample.filter(v => {
      const n = parseFloat(String(v).replace(/,/g, ''));
      return !isNaN(n) && isFinite(n);
    }).length;

    if (numericCount / sample.length >= 0.8) {
      types[col] = 'numeric'; return;
    }

    types[col] = 'category';
  });

  return types;
}

export function getNumericColumns(types) {
  return Object.entries(types).filter(([, t]) => t === 'numeric').map(([c]) => c);
}

export function getCategoryColumns(types) {
  return Object.entries(types).filter(([, t]) => t === 'category').map(([c]) => c);
}

export function getDateColumns(types) {
  return Object.entries(types).filter(([, t]) => t === 'date' || t === 'year').map(([c]) => c);
}

/** 분석 추천 대상 결정 */
export function recommendAnalysisTarget(types, rows) {
  const numerics = getNumericColumns(types);
  const cats = getCategoryColumns(types);

  // 합계가 가장 큰 수치형 컬럼을 지표로 추천
  let recommendedMetric = numerics[0] || null;
  if (numerics.length > 1) {
    let maxSum = -Infinity;
    numerics.forEach(col => {
      const s = rows.reduce((acc, r) => {
        const v = parseFloat(String(r[col]).replace(/,/g, ''));
        return acc + (isNaN(v) ? 0 : v);
      }, 0);
      if (s > maxSum) { maxSum = s; recommendedMetric = col; }
    });
  }

  // 고유값 2~30개인 범주형 컬럼 우선 선택
  let recommendedGroup = cats[0] || null;
  let recommendedCategory = cats.length > 1 ? cats[1] : (cats[0] || null);

  if (cats.length >= 1) {
    const scored = cats
      .map(col => ({ col, count: new Set(rows.map(r => r[col])).size }))
      .filter(u => u.count >= 2 && u.count <= 30)
      .sort((a, b) => a.count - b.count);

    if (scored.length > 0) {
      recommendedGroup = scored[0].col;
      recommendedCategory = scored.length > 1 ? scored[1].col : scored[0].col;
    }
  }

  return { recommendedMetric, recommendedGroup, recommendedCategory };
}

/** 컬럼별 통계 계산 */
function computeColumnStats(rows, col, type) {
  const values = rows.map(r => r[col]).filter(v => v !== null && v !== undefined && String(v).trim() !== '');
  const missing = rows.length - values.length;
  const unique = new Set(values).size;

  if (type === 'numeric') {
    const nums = values.map(v => parseFloat(String(v).replace(/,/g, ''))).filter(v => !isNaN(v));
    const sum = nums.reduce((a, b) => a + b, 0);
    const avg = nums.length > 0 ? sum / nums.length : 0;
    const min = nums.length > 0 ? Math.min(...nums) : 0;
    const max = nums.length > 0 ? Math.max(...nums) : 0;
    return { type, missing, unique, sum, avg, min, max };
  }

  return { type, missing, unique };
}

/** 메인 프로파일링 함수 */
export function profileData(rows) {
  if (!rows || rows.length === 0) throw new Error('데이터가 비어 있습니다.');

  const headers = Object.keys(rows[0]);
  if (headers.length === 0) throw new Error('헤더를 찾을 수 없습니다.');

  const types = detectColumnTypes(rows, headers);
  const numericColumns = getNumericColumns(types);
  const categoryColumns = getCategoryColumns(types);
  const dateColumns = getDateColumns(types);

  if (numericColumns.length === 0) {
    throw new Error('수치형 컬럼이 없어 합계 분석을 수행할 수 없습니다.');
  }
  if (categoryColumns.length === 0) {
    throw new Error('범주형 컬럼이 없어 그룹 분석을 수행할 수 없습니다.');
  }

  const stats = {};
  headers.forEach(col => { stats[col] = computeColumnStats(rows, col, types[col]); });

  const { recommendedMetric, recommendedGroup, recommendedCategory } = recommendAnalysisTarget(types, rows);

  return {
    rowCount: rows.length,
    columns: headers,
    columnTypes: types,
    numericColumns,
    categoryColumns,
    dateColumns,
    stats,
    recommendedMetric,
    recommendedGroup,
    recommendedCategory,
  };
}
