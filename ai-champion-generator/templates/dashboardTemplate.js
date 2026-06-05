/**
 * dashboardTemplate.js
 * 문제 1 — HTML 대시보드 예시 정답 생성
 */

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function calcGroupSums(rows, group, metric) {
  const sums = {};
  rows.forEach(r => {
    const g = String(r[group] || '(기타)');
    const v = parseFloat(String(r[metric] || '0').replace(/,/g, '')) || 0;
    sums[g] = (sums[g] || 0) + v;
  });
  return Object.entries(sums).sort((a, b) => b[1] - a[1]);
}

export function dashboardTemplate(rows, profile) {
  const { recommendedMetric: metric, recommendedGroup: group } = profile;
  const sorted = calcGroupSums(rows, group, metric);
  const top5 = sorted.slice(0, 5);
  const total = sorted.reduce((s, [, v]) => s + v, 0);
  const avg = sorted.length > 0 ? total / sorted.length : 0;
  const maxGroup = sorted[0]?.[0] ?? '-';
  const maxVal = sorted[0]?.[1] ?? 0;
  const today = new Date().toLocaleDateString('ko-KR');

  const chartLabels = JSON.stringify(top5.map(([k]) => k));
  const chartData = JSON.stringify(top5.map(([, v]) => Math.round(v)));

  const headers = Object.keys(rows[0]);
  const previewRows = rows.slice(0, 10);
  const tableHead = headers.map(h => `<th>${esc(h)}</th>`).join('');
  const tableBody = previewRows.map(row =>
    `<tr>${headers.map(h => `<td>${esc(String(row[h] ?? ''))}</td>`).join('')}</tr>`
  ).join('');

  const top5Html = top5.map(([name, val], i) => {
    const pct = maxVal > 0 ? Math.round((val / maxVal) * 100) : 0;
    return `
      <div class="top5-item">
        <span class="top5-rank">${i + 1}</span>
        <span class="top5-name">${esc(name)}</span>
        <div class="top5-bar-wrap"><div class="top5-bar">
          <div class="top5-fill" style="width:${pct}%"></div>
        </div></div>
        <span class="top5-val">${Math.round(val).toLocaleString()}</span>
      </div>`;
  }).join('');

  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>데이터 현황 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;background:#f0f4f8;color:#1a202c}
  header{background:linear-gradient(135deg,#1e40af,#3b82f6);color:white;padding:24px 32px}
  header h1{font-size:1.8rem;margin-bottom:6px}
  header p{opacity:.85;font-size:.9rem}
  .wrap{max-width:1200px;margin:0 auto;padding:24px}
  .summary{background:#eff6ff;border-left:4px solid #3b82f6;padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:24px;color:#1e40af;font-size:.92rem;line-height:1.7}
  .kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:24px}
  .kpi{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.07)}
  .kpi-lbl{font-size:.78rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
  .kpi-val{font-size:1.8rem;font-weight:800;color:#1e40af}
  .kpi-sub{font-size:.78rem;color:#94a3b8;margin-top:3px}
  .card{background:white;border-radius:12px;padding:22px;margin-bottom:22px;box-shadow:0 2px 8px rgba(0,0,0,.07)}
  .card h2{font-size:1.1rem;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #e2e8f0}
  .chart-wrap{position:relative;height:300px}
  .top5-item{display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #f1f5f9}
  .top5-rank{font-size:1.1rem;font-weight:800;color:#3b82f6;width:24px;text-align:center}
  .top5-name{width:90px;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .top5-bar-wrap{flex:1}.top5-bar{height:12px;background:#dbeafe;border-radius:6px;overflow:hidden}
  .top5-fill{height:100%;background:#3b82f6;border-radius:6px}
  .top5-val{font-weight:700;color:#1e40af;min-width:70px;text-align:right;font-size:.9rem}
  table{width:100%;border-collapse:collapse;font-size:.83rem}
  th{background:#f8fafc;padding:9px 11px;text-align:left;font-weight:600;color:#475569;border-bottom:2px solid #e2e8f0;white-space:nowrap}
  td{padding:8px 11px;border-bottom:1px solid #f1f5f9;white-space:nowrap}
  tr:hover td{background:#f8fafc}
  footer{text-align:center;padding:18px;color:#94a3b8;font-size:.8rem;border-top:1px solid #e2e8f0}
  @media(max-width:600px){header h1{font-size:1.3rem}.kpi-val{font-size:1.4rem}}
</style>
</head>
<body>
<header>
  <h1>📊 데이터 현황 대시보드</h1>
  <p>${today} 기준 · AI챔피언 데이터분석 실습 — 예시 정답 (문제 1)</p>
</header>
<div class="wrap">
  <div class="summary">
    📌 전체 데이터 <strong>${rows.length.toLocaleString()}건</strong> 분석 결과,
    <strong>${esc(group)}</strong> 기준 총 <strong>${esc(metric)}</strong>은
    <strong>${Math.round(total).toLocaleString()}</strong>이며,
    가장 높은 항목은 <strong>${esc(maxGroup)}</strong>(${Math.round(maxVal).toLocaleString()})입니다.
  </div>
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-lbl">전체 합계</div>
      <div class="kpi-val">${Math.round(total).toLocaleString()}</div>
      <div class="kpi-sub">${esc(metric)} 총합</div></div>
    <div class="kpi"><div class="kpi-lbl">그룹 평균</div>
      <div class="kpi-val">${Math.round(avg).toLocaleString()}</div>
      <div class="kpi-sub">${esc(group)}별 평균</div></div>
    <div class="kpi"><div class="kpi-lbl">최고 ${esc(group)}</div>
      <div class="kpi-val" style="font-size:1.3rem">${esc(maxGroup)}</div>
      <div class="kpi-sub">${Math.round(maxVal).toLocaleString()} ${esc(metric)}</div></div>
    <div class="kpi"><div class="kpi-lbl">총 데이터</div>
      <div class="kpi-val">${rows.length.toLocaleString()}</div>
      <div class="kpi-sub">건</div></div>
  </div>
  <div class="card">
    <h2>📊 ${esc(group)}별 ${esc(metric)} 막대차트 (상위 5개)</h2>
    <div class="chart-wrap"><canvas id="chart1"></canvas></div>
  </div>
  <div class="card">
    <h2>🏆 상위 5개 ${esc(group)}</h2>
    ${top5Html}
  </div>
  <div class="card">
    <h2>📋 데이터 표 (상위 10건)</h2>
    <div style="overflow-x:auto"><table>
      <thead><tr>${tableHead}</tr></thead>
      <tbody>${tableBody}</tbody>
    </table></div>
  </div>
</div>
<footer>AI챔피언 데이터분석 문제 자동 생성기 · 예시 정답 산출물 (문제 1)</footer>
<script>
new Chart(document.getElementById('chart1'), {
  type: 'bar',
  data: {
    labels: ${chartLabels},
    datasets: [{
      label: '${esc(metric)}',
      data: ${chartData},
      backgroundColor: ['#3b82f6','#60a5fa','#93c5fd','#bfdbfe','#dbeafe'],
      borderRadius: 6,
    }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
      x: { grid: { display: false } }
    }
  }
});
</script>
</body></html>`;
}
