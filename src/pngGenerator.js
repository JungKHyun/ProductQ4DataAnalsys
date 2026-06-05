/**
 * pngGenerator.js
 * 숨겨진 HTML 카드를 html2canvas로 캡처하여 PNG Blob을 반환한다.
 */

/** 그룹별 합계 계산 유틸 */
function calcGroupSums(rows, group, metric) {
  const sums = {};
  rows.forEach(r => {
    const g = String(r[group] || '(기타)');
    const v = parseFloat(String(r[metric] || '0').replace(/,/g, '')) || 0;
    sums[g] = (sums[g] || 0) + v;
  });
  return Object.entries(sums).sort((a, b) => b[1] - a[1]);
}

/** 인포그래픽 HTML 카드 생성 */
function buildInfographicElement(rows, profile) {
  const { recommendedMetric: metric, recommendedGroup: group } = profile;
  const sorted = calcGroupSums(rows, group, metric);
  const top5 = sorted.slice(0, 5);
  const total = sorted.reduce((s, [, v]) => s + v, 0);
  const avg = total / (sorted.length || 1);
  const maxGroup = sorted[0] ? sorted[0][0] : '-';
  const maxVal = sorted[0] ? sorted[0][1] : 0;
  const today = new Date().toLocaleDateString('ko-KR');

  const el = document.createElement('div');
  el.id = '__infographic_target__';
  el.style.cssText = `
    position: fixed; top: -9999px; left: -9999px;
    width: 800px; background: #1e1b4b; color: white;
    font-family: 'Malgun Gothic','맑은 고딕',sans-serif;
    padding: 40px; border-radius: 16px;
  `;

  el.innerHTML = `
    <div style="text-align:center;margin-bottom:32px">
      <div style="font-size:13px;letter-spacing:3px;color:#a5b4fc;margin-bottom:8px">DATA INSIGHT REPORT</div>
      <h1 style="font-size:26px;font-weight:800;margin-bottom:6px">${esc(group)} 기준 ${esc(metric)} 분석 현황</h1>
      <div style="font-size:12px;color:#818cf8">${today} 기준 · AI챔피언 데이터분석 문제 자동 생성기</div>
    </div>

    <!-- KPI 3개 -->
    <div style="display:flex;gap:16px;margin-bottom:28px">
      ${kpiCard('전체 합계', Math.round(total).toLocaleString(), metric, '#6366f1')}
      ${kpiCard('그룹 평균', Math.round(avg).toLocaleString(), `${group}별 평균`, '#8b5cf6')}
      ${kpiCard('최고 ' + group, maxGroup, Math.round(maxVal).toLocaleString(), '#ec4899')}
    </div>

    <!-- 상위 5개 바 차트 -->
    <div style="background:rgba(255,255,255,0.07);border-radius:12px;padding:20px;margin-bottom:24px">
      <div style="font-size:13px;font-weight:700;color:#c7d2fe;margin-bottom:14px">
        🏆 상위 5개 ${esc(group)} (${esc(metric)} 기준)
      </div>
      ${top5.map(([name, val], i) => {
        const pct = maxVal > 0 ? Math.round((val / maxVal) * 100) : 0;
        const colors = ['#6366f1','#8b5cf6','#a78bfa','#c4b5fd','#ddd6fe'];
        return `
          <div style="display:flex;align-items:center;margin-bottom:10px;gap:10px">
            <span style="font-size:16px;font-weight:800;color:${colors[i]};width:24px">${i+1}</span>
            <span style="width:80px;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(name)}</span>
            <div style="flex:1;background:rgba(255,255,255,0.1);border-radius:4px;height:14px;overflow:hidden">
              <div style="width:${pct}%;height:100%;background:${colors[i]};border-radius:4px"></div>
            </div>
            <span style="font-size:12px;font-weight:700;color:${colors[i]};min-width:60px;text-align:right">
              ${Math.round(val).toLocaleString()}
            </span>
          </div>`;
      }).join('')}
    </div>

    <!-- 해석 문장 -->
    <div style="background:rgba(255,255,255,0.06);border-left:3px solid #6366f1;padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:16px">
      <p style="font-size:13px;line-height:1.8;color:#e0e7ff">
        📌 전체 ${esc(metric)} 합계는 <strong>${Math.round(total).toLocaleString()}</strong>이며,
        가장 높은 ${esc(group)}은 <strong>${esc(maxGroup)}</strong>(${Math.round(maxVal).toLocaleString()})으로
        전체 평균 대비 <strong>${avg > 0 ? Math.round(((maxVal - avg) / avg) * 100) : 0}%</strong> 높게 나타났습니다.
      </p>
      <p style="font-size:13px;line-height:1.8;color:#e0e7ff;margin-top:8px">
        📌 상위 5개 ${esc(group)}의 ${esc(metric)} 합계는 전체의
        <strong>${total > 0 ? Math.round((top5.reduce((s,[,v])=>s+v,0)/total)*100) : 0}%</strong>를 차지하며,
        집중도 관리가 필요합니다.
      </p>
    </div>

    <!-- 출처 -->
    <div style="text-align:right;font-size:11px;color:#6366f1;opacity:0.7">
      출처: 업로드 데이터(${rows.length.toLocaleString()}건) · AI챔피언 데이터분석 문제 자동 생성기
    </div>
  `;

  return el;
}

function kpiCard(label, value, sub, color) {
  return `
    <div style="flex:1;background:rgba(255,255,255,0.08);border-radius:10px;padding:16px 14px;border-top:3px solid ${color}">
      <div style="font-size:11px;color:#a5b4fc;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">${esc(label)}</div>
      <div style="font-size:22px;font-weight:800;color:${color};margin-bottom:4px">${esc(String(value))}</div>
      <div style="font-size:11px;color:#94a3b8">${esc(String(sub))}</div>
    </div>
  `;
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/** PNG Blob 생성 (비동기) */
export async function generateInfographicPng(rows, profile) {
  const el = buildInfographicElement(rows, profile);
  document.body.appendChild(el);

  try {
    const canvas = await window.html2canvas(el, {
      backgroundColor: '#1e1b4b',
      scale: 2,
      useCORS: true,
      logging: false,
    });

    return await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
  } finally {
    document.body.removeChild(el);
  }
}
