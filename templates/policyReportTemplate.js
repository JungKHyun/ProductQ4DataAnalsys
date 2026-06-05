/**
 * policyReportTemplate.js
 * 문제 5 — HTML 정책 제안 리포트 예시 정답 생성
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

export function policyReportTemplate(rows, profile) {
  const { recommendedMetric: metric, recommendedGroup: group, dateColumns, rowCount } = profile;
  const today = new Date().toLocaleDateString('ko-KR');
  const sorted = calcGroupSums(rows, group, metric);
  const top5 = sorted.slice(0, 5);
  const bottom3 = sorted.slice(-3).reverse();
  const total = sorted.reduce((s, [, v]) => s + v, 0);
  const avg = sorted.length > 0 ? total / sorted.length : 0;
  const maxGroup = sorted[0]?.[0] ?? '-';
  const maxVal = sorted[0]?.[1] ?? 0;
  const minGroup = sorted[sorted.length - 1]?.[0] ?? '-';
  const minVal = sorted[sorted.length - 1]?.[1] ?? 0;
  const hasDate = dateColumns.length > 0;

  const chartLabels = JSON.stringify(top5.map(([k]) => k));
  const chartData = JSON.stringify(top5.map(([, v]) => Math.round(v)));
  const avgLine = Math.round(avg);

  const headers = Object.keys(rows[0]);
  const tableRows = sorted.slice(0, 10).map(([g, v]) => {
    const pct = total > 0 ? ((v / total) * 100).toFixed(1) : '0.0';
    return `<tr><td>${esc(g)}</td><td>${Math.round(v).toLocaleString()}</td><td>${pct}%</td></tr>`;
  }).join('');

  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>정책 제안 리포트</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Malgun Gothic','맑은 고딕',sans-serif;background:#f8fafc;color:#1e293b}
  header{background:linear-gradient(135deg,#7c3aed,#a855f7);color:white;padding:28px 36px}
  header .tag{background:rgba(255,255,255,.2);padding:3px 12px;border-radius:20px;font-size:.78rem;margin-bottom:10px;display:inline-block}
  header h1{font-size:1.8rem;font-weight:800;margin-bottom:6px}
  header p{opacity:.85;font-size:.88rem}
  .wrap{max-width:900px;margin:0 auto;padding:28px 20px}
  .section{background:white;border-radius:14px;padding:26px;margin-bottom:24px;box-shadow:0 2px 8px rgba(0,0,0,.07)}
  .section-title{display:flex;align-items:center;gap:10px;margin-bottom:20px;padding-bottom:12px;border-bottom:2px solid #f1f5f9}
  .section-icon{width:34px;height:34px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.1rem}
  .section-title h2{font-size:1.1rem;font-weight:700}
  .summary-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:16px}
  .stat-card{background:#faf5ff;border-radius:10px;padding:14px 16px;border-top:3px solid #7c3aed}
  .stat-lbl{font-size:.75rem;color:#7c3aed;text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px}
  .stat-val{font-size:1.5rem;font-weight:800;color:#6d28d9}
  .stat-sub{font-size:.75rem;color:#94a3b8;margin-top:2px}
  .finding-item{padding:14px 16px;background:#faf5ff;border-left:4px solid #7c3aed;border-radius:0 8px 8px 0;margin-bottom:12px;line-height:1.7;font-size:.9rem}
  .finding-item .num{font-weight:800;color:#7c3aed;margin-right:8px}
  .policy-item{padding:16px 20px;background:#fff;border:1.5px solid #e9d5ff;border-radius:10px;margin-bottom:12px}
  .policy-item h3{font-size:.95rem;font-weight:700;color:#6d28d9;margin-bottom:8px}
  .policy-item p{font-size:.88rem;color:#475569;line-height:1.7}
  .policy-item .basis{font-size:.82rem;color:#7c3aed;margin-top:8px;padding-top:8px;border-top:1px solid #e9d5ff}
  table{width:100%;border-collapse:collapse;font-size:.87rem}
  th{background:#faf5ff;padding:10px 12px;text-align:left;font-weight:600;color:#6d28d9;border-bottom:2px solid #e9d5ff}
  td{padding:9px 12px;border-bottom:1px solid #f3e8ff}
  tr:hover td{background:#fdf4ff}
  td:nth-child(2),td:nth-child(3){text-align:right;font-variant-numeric:tabular-nums}
  .chart-wrap{position:relative;height:300px}
  footer{text-align:center;padding:20px;color:#94a3b8;font-size:.8rem;border-top:1px solid #e2e8f0;margin-top:8px}
</style>
</head>
<body>
<header>
  <div class="tag">📋 정책 제안 리포트</div>
  <h1>${esc(metric)} 현황 분석 및 정책 제안</h1>
  <p>작성일: ${today} &nbsp;·&nbsp; 분석 데이터: ${rowCount.toLocaleString()}건 &nbsp;·&nbsp; AI챔피언 데이터분석 실습 — 예시 정답 (문제 5)</p>
</header>
<div class="wrap">

  <!-- ① 데이터 요약 -->
  <div class="section">
    <div class="section-title">
      <div class="section-icon" style="background:#f3e8ff">📊</div>
      <h2>1. 데이터 요약</h2>
    </div>
    <div class="summary-stats">
      <div class="stat-card"><div class="stat-lbl">전체 합계</div>
        <div class="stat-val">${Math.round(total).toLocaleString()}</div>
        <div class="stat-sub">${esc(metric)}</div></div>
      <div class="stat-card"><div class="stat-lbl">그룹 평균</div>
        <div class="stat-val">${Math.round(avg).toLocaleString()}</div>
        <div class="stat-sub">${esc(group)}별</div></div>
      <div class="stat-card"><div class="stat-lbl">최고 ${esc(group)}</div>
        <div class="stat-val" style="font-size:1.1rem">${esc(maxGroup)}</div>
        <div class="stat-sub">${Math.round(maxVal).toLocaleString()}</div></div>
      <div class="stat-card"><div class="stat-lbl">최저 ${esc(group)}</div>
        <div class="stat-val" style="font-size:1.1rem">${esc(minGroup)}</div>
        <div class="stat-sub">${Math.round(minVal).toLocaleString()}</div></div>
      <div class="stat-card"><div class="stat-lbl">분석 건수</div>
        <div class="stat-val">${rowCount.toLocaleString()}</div>
        <div class="stat-sub">건</div></div>
    </div>
    <p style="font-size:.9rem;color:#475569;line-height:1.7;padding:12px 16px;background:#faf5ff;border-radius:8px">
      본 분석은 총 <strong>${rowCount.toLocaleString()}건</strong>의 데이터를 대상으로 수행되었습니다.
      <strong>${esc(group)}</strong> 기준으로 <strong>${esc(metric)}</strong>을 집계한 결과,
      전체 합계는 <strong>${Math.round(total).toLocaleString()}</strong>이며 그룹별 평균은 <strong>${Math.round(avg).toLocaleString()}</strong>입니다.
      ${hasDate ? '시계열 데이터가 포함되어 있어 추세 분석이 가능합니다.' : ''}
    </p>
  </div>

  <!-- ② 주요 발견 -->
  <div class="section">
    <div class="section-title">
      <div class="section-icon" style="background:#f3e8ff">🔎</div>
      <h2>2. 주요 발견 사항</h2>
    </div>
    <div class="finding-item">
      <span class="num">발견 1</span>
      <strong>${esc(maxGroup)}</strong>의 ${esc(metric)}이 <strong>${Math.round(maxVal).toLocaleString()}</strong>으로
      전체 그룹 중 가장 높으며, 평균(${Math.round(avg).toLocaleString()}) 대비
      <strong>${avg > 0 ? Math.round(((maxVal - avg) / avg) * 100) : 0}%</strong> 높습니다.
      집중 관리 및 원인 분석이 필요합니다.
    </div>
    <div class="finding-item">
      <span class="num">발견 2</span>
      상위 5개 ${esc(group)}(${top5.map(([g]) => g).join(', ')})의 합계는
      <strong>${Math.round(top5.reduce((s,[,v])=>s+v,0)).toLocaleString()}</strong>으로
      전체의 <strong>${total > 0 ? Math.round((top5.reduce((s,[,v])=>s+v,0) / total) * 100) : 0}%</strong>를
      차지하여 특정 그룹에 집중되어 있습니다.
    </div>
    <div class="finding-item">
      <span class="num">발견 3</span>
      <strong>${esc(minGroup)}</strong>의 ${esc(metric)}은 <strong>${Math.round(minVal).toLocaleString()}</strong>으로
      가장 낮으며, 최고 그룹 대비 <strong>${maxVal > 0 ? Math.round(((maxVal - minVal) / maxVal) * 100) : 0}%</strong>
      차이가 있습니다. 하위 그룹 지원 정책 검토가 필요합니다.
    </div>
  </div>

  <!-- ③ 정책 제안 -->
  <div class="section">
    <div class="section-title">
      <div class="section-icon" style="background:#f3e8ff">💡</div>
      <h2>3. 정책 제안</h2>
    </div>
    <div class="policy-item">
      <h3>제안 1. 상위 집중 그룹 집중 관리 체계 구축</h3>
      <p>
        ${esc(metric)} 상위 그룹(${top5.slice(0,3).map(([g])=>g).join(', ')})에 대한 현황을 주기적으로 모니터링하고,
        원인 요인을 분석하여 선제적 대응 계획을 수립해야 합니다.
      </p>
      <div class="basis">📌 근거: 상위 3개 ${esc(group)}이 전체 ${esc(metric)}의 ${total > 0 ? Math.round((sorted.slice(0,3).reduce((s,[,v])=>s+v,0)/total)*100) : 0}% 차지</div>
    </div>
    <div class="policy-item">
      <h3>제안 2. 하위 그룹 역량 강화 및 지원 프로그램 도입</h3>
      <p>
        ${esc(metric)}이 낮은 하위 그룹(${bottom3.map(([g])=>g).join(', ')})에 대해
        전문 인력 배치, 예산 지원, 교육 프로그램 등 맞춤형 지원 방안을 마련해야 합니다.
      </p>
      <div class="basis">📌 근거: 최저 ${esc(group)} ${esc(minGroup)}의 수치가 평균 대비 ${avg > 0 ? Math.round(((avg - minVal) / avg) * 100) : 0}% 낮음</div>
    </div>
    <div class="policy-item">
      <h3>제안 3. 그룹 간 편차 완화를 위한 자원 재배분 검토</h3>
      <p>
        최고·최저 그룹 간 ${esc(metric)} 편차가 크므로, 자원 배분의 불균형을 검토하고
        형평성 있는 분배 기준을 마련하여 전체적인 수준 향상을 도모해야 합니다.
      </p>
      <div class="basis">📌 근거: 최고-최저 ${esc(group)} 간 ${esc(metric)} 차이 ${(maxVal - minVal).toLocaleString()} (${maxVal > 0 ? Math.round(((maxVal-minVal)/maxVal)*100) : 0}%)</div>
    </div>
  </div>

  <!-- ④ 근거 데이터 표 -->
  <div class="section">
    <div class="section-title">
      <div class="section-icon" style="background:#f3e8ff">📋</div>
      <h2>4. 근거 데이터 표</h2>
    </div>
    <div style="overflow-x:auto"><table>
      <thead><tr><th>${esc(group)}</th><th>${esc(metric)} 합계</th><th>비율(%)</th></tr></thead>
      <tbody>${tableRows}</tbody>
    </table></div>
  </div>

  <!-- ⑤ 차트 -->
  <div class="section">
    <div class="section-title">
      <div class="section-icon" style="background:#f3e8ff">📊</div>
      <h2>5. 데이터 시각화</h2>
    </div>
    <div class="chart-wrap"><canvas id="policyChart"></canvas></div>
  </div>

</div>
<footer>AI챔피언 데이터분석 문제 자동 생성기 · 예시 정답 산출물 (문제 5)</footer>
<script>
new Chart(document.getElementById('policyChart'), {
  type: 'bar',
  data: {
    labels: ${chartLabels},
    datasets: [
      {
        label: '${esc(metric)}',
        data: ${chartData},
        backgroundColor: ['#7c3aed','#8b5cf6','#a78bfa','#c4b5fd','#ddd6fe'],
        borderRadius: 6,
      },
      {
        type: 'line',
        label: '평균',
        data: Array(${top5.length}).fill(${avgLine}),
        borderColor: '#f59e0b',
        borderDash: [6,3],
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
      }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: '상위 5개 ${esc(group)} ${esc(metric)} 현황 및 평균선', color: '#6d28d9' }
    },
    scales: {
      y: { beginAtZero: true, grid: { color: '#f3e8ff' } },
      x: { grid: { display: false } }
    }
  }
});
</script>
</body></html>`;
}
