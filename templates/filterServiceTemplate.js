/**
 * filterServiceTemplate.js
 * 문제 2 — HTML 검색/필터 서비스 예시 정답 생성
 */

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

export function filterServiceTemplate(rows, profile) {
  const { recommendedMetric: metric, recommendedGroup: group, recommendedCategory: cat } = profile;
  const filterCol = cat || group;

  const uniqueCategories = [...new Set(rows.map(r => String(r[filterCol] || '')))].filter(Boolean).sort();
  const headers = Object.keys(rows[0]);
  const today = new Date().toLocaleDateString('ko-KR');

  // 데이터 인라인 임베딩 (최대 2000행)
  const dataJson = JSON.stringify(rows.slice(0, 2000));
  const headersJson = JSON.stringify(headers);
  const metricJson = JSON.stringify(metric);
  const groupJson = JSON.stringify(group);
  const filterColJson = JSON.stringify(filterCol);

  const options = uniqueCategories.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('\n        ');

  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>데이터 검색/필터 서비스</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;background:#f0f4f8;color:#1a202c}
  header{background:linear-gradient(135deg,#0f766e,#14b8a6);color:white;padding:22px 32px}
  header h1{font-size:1.6rem;margin-bottom:4px}
  header p{opacity:.85;font-size:.88rem}
  .wrap{max-width:1100px;margin:0 auto;padding:22px}
  .controls{background:white;border-radius:12px;padding:22px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,.07);display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end}
  .ctrl-group{display:flex;flex-direction:column;gap:6px;flex:1;min-width:180px}
  label{font-size:.8rem;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:.04em}
  select,input{padding:9px 12px;border:1.5px solid #e2e8f0;border-radius:8px;font-size:.9rem;font-family:inherit;color:#1e293b;background:white}
  select:focus,input:focus{outline:none;border-color:#14b8a6}
  .btn-reset{padding:9px 18px;background:#0f766e;color:white;border:none;border-radius:8px;font-size:.9rem;font-weight:600;cursor:pointer;font-family:inherit}
  .btn-reset:hover{background:#0d6360}
  .summary-bar{background:#ccfbf1;border-left:4px solid #14b8a6;padding:12px 18px;border-radius:0 8px 8px 0;margin-bottom:20px;color:#0f766e;font-size:.9rem}
  .card{background:white;border-radius:12px;padding:22px;box-shadow:0 2px 8px rgba(0,0,0,.07)}
  .card h2{font-size:1rem;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #e2e8f0;color:#1e293b}
  table{width:100%;border-collapse:collapse;font-size:.83rem}
  th{background:#f8fafc;padding:9px 11px;text-align:left;font-weight:600;color:#475569;border-bottom:2px solid #e2e8f0;white-space:nowrap}
  td{padding:8px 11px;border-bottom:1px solid #f1f5f9;white-space:nowrap}
  tr:hover td{background:#f0fdfa}
  .no-data{text-align:center;padding:40px;color:#94a3b8;font-size:.95rem}
  .badge{display:inline-block;background:#ccfbf1;color:#0f766e;padding:2px 10px;border-radius:12px;font-size:.8rem;font-weight:700;margin-left:6px}
  footer{text-align:center;padding:18px;color:#94a3b8;font-size:.8rem;border-top:1px solid #e2e8f0;margin-top:20px}
  @media(max-width:600px){.controls{flex-direction:column}}
</style>
</head>
<body>
<header>
  <h1>🔍 데이터 검색/필터 서비스</h1>
  <p>${today} · AI챔피언 데이터분석 실습 — 예시 정답 (문제 2)</p>
</header>
<div class="wrap">
  <div class="controls">
    <div class="ctrl-group">
      <label for="sel-filter">${esc(filterCol)} 필터</label>
      <select id="sel-filter">
        <option value="">전체</option>
        ${options}
      </select>
    </div>
    <div class="ctrl-group">
      <label for="txt-search">텍스트 검색</label>
      <input type="text" id="txt-search" placeholder="검색어 입력...">
    </div>
    <button class="btn-reset" id="btn-reset">초기화</button>
  </div>
  <div class="summary-bar" id="summary-bar">전체 데이터를 표시 중입니다.</div>
  <div class="card">
    <h2>📋 필터링 결과 <span class="badge" id="result-count">0건</span></h2>
    <div style="overflow-x:auto"><table id="data-table">
      <thead id="table-head"></thead>
      <tbody id="table-body"></tbody>
    </table></div>
    <div class="no-data hidden" id="no-data">조건에 맞는 데이터가 없습니다.</div>
  </div>
</div>
<footer>AI챔피언 데이터분석 문제 자동 생성기 · 예시 정답 산출물 (문제 2)</footer>
<script>
const DATA = ${dataJson};
const HEADERS = ${headersJson};
const METRIC = ${metricJson};
const FILTER_COL = ${filterColJson};

// 헤더 렌더링
const thead = document.getElementById('table-head');
thead.innerHTML = '<tr>' + HEADERS.map(h => \`<th>\${h}</th>\`).join('') + '</tr>';

// 필터/검색 상태
let selVal = '', searchVal = '';

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function render() {
  const tbody = document.getElementById('table-body');
  const noData = document.getElementById('no-data');
  const countBadge = document.getElementById('result-count');
  const summaryBar = document.getElementById('summary-bar');

  const filtered = DATA.filter(row => {
    const matchFilter = !selVal || String(row[FILTER_COL] || '') === selVal;
    const matchSearch = !searchVal || HEADERS.some(h => String(row[h] || '').toLowerCase().includes(searchVal));
    return matchFilter && matchSearch;
  });

  const total = filtered.reduce((s, r) => {
    const v = parseFloat(String(r[METRIC] || '0').replace(/,/g,''));
    return s + (isNaN(v) ? 0 : v);
  }, 0);

  countBadge.textContent = filtered.length.toLocaleString() + '건';

  const conditions = [];
  if (selVal) conditions.push(\`<strong>\${esc(FILTER_COL)}</strong>: \${esc(selVal)}\`);
  if (searchVal) conditions.push(\`검색어: \${esc(searchVal)}\`);

  summaryBar.innerHTML = conditions.length
    ? \`📌 조건 [\${conditions.join(' / ')}] → 총 <strong>\${filtered.length.toLocaleString()}건</strong>, \${esc(METRIC)} 합계 <strong>\${Math.round(total).toLocaleString()}</strong>\`
    : \`📌 전체 <strong>\${filtered.length.toLocaleString()}건</strong> 표시 중, \${esc(METRIC)} 합계 <strong>\${Math.round(total).toLocaleString()}</strong>\`;

  if (filtered.length === 0) {
    tbody.innerHTML = '';
    noData.classList.remove('hidden');
    return;
  }
  noData.classList.add('hidden');

  tbody.innerHTML = filtered.slice(0, 200).map(row =>
    '<tr>' + HEADERS.map(h => \`<td>\${esc(String(row[h] ?? ''))}</td>\`).join('') + '</tr>'
  ).join('');
}

document.getElementById('sel-filter').addEventListener('change', e => { selVal = e.target.value; render(); });
document.getElementById('txt-search').addEventListener('input', e => { searchVal = e.target.value.trim().toLowerCase(); render(); });
document.getElementById('btn-reset').addEventListener('click', () => {
  selVal = ''; searchVal = '';
  document.getElementById('sel-filter').value = '';
  document.getElementById('txt-search').value = '';
  render();
});

render();
</script>
</body></html>`;
}
