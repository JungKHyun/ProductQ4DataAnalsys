/**
 * problemsTemplate.js
 * 문제지 HTML 생성
 */

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

export function problemsTemplate(problems, profile) {
  const today = new Date().toLocaleDateString('ko-KR');
  const { rowCount, recommendedMetric, recommendedGroup } = profile;

  const problemCards = problems.map(p => `
    <div class="problem-card">
      <div class="problem-header">
        <span class="problem-num">문제 ${p.id}</span>
        <span class="problem-title">${escHtml(p.title)}</span>
        <span class="problem-file">📄 ${escHtml(p.file)}</span>
      </div>
      <div class="problem-body">
        <p class="problem-desc">${escHtml(p.description)}</p>
        <h4>필수 구현 요건</h4>
        <ul>
          ${p.requirements.map(r => `<li>${escHtml(r)}</li>`).join('\n          ')}
        </ul>
        <div class="rubric-inline">
          <h4>채점 기준</h4>
          <table>
            <thead><tr><th>채점 항목</th><th>배점</th></tr></thead>
            <tbody>
              ${p.rubric.map(rb => `<tr><td>${escHtml(rb.item)}</td><td>${rb.score}점</td></tr>`).join('\n              ')}
              <tr class="total-row"><td><strong>합계</strong></td><td><strong>${p.rubric.reduce((s,r)=>s+r.score,0)}점</strong></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `).join('\n');

  return `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI챔피언 데이터분석 실습 문제지</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Malgun Gothic','맑은 고딕',sans-serif; background: #f8fafc; color: #1e293b; }
  header { background: linear-gradient(135deg,#1e40af,#3b82f6); color: white; padding: 32px; text-align: center; }
  header h1 { font-size: 1.8rem; margin-bottom: 8px; }
  header p { opacity: .85; font-size: .9rem; }
  .info-bar { max-width: 860px; margin: 20px auto; background: white; border-radius: 10px;
    padding: 16px 24px; display: flex; gap: 32px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
  .info-bar dt { font-size: .78rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em; }
  .info-bar dd { font-weight: 700; color: #1e40af; font-size: 1rem; }
  main { max-width: 860px; margin: 0 auto 40px; padding: 0 20px; }
  .instructions { background: #eff6ff; border-left: 4px solid #3b82f6;
    padding: 16px 20px; border-radius: 0 8px 8px 0; margin-bottom: 28px; font-size: .9rem; line-height: 1.7; color: #1e40af; }
  .problem-card { background: white; border-radius: 12px; margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,.07); overflow: hidden; border: 1px solid #e2e8f0; }
  .problem-header { background: #1e40af; color: white; padding: 16px 24px;
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .problem-num { background: rgba(255,255,255,.2); padding: 4px 12px; border-radius: 20px;
    font-size: .8rem; font-weight: 700; letter-spacing: .05em; }
  .problem-title { font-size: 1.1rem; font-weight: 700; flex: 1; }
  .problem-file { font-size: .82rem; opacity: .85; font-family: monospace; background: rgba(255,255,255,.15);
    padding: 3px 10px; border-radius: 4px; }
  .problem-body { padding: 24px; }
  .problem-desc { color: #334155; line-height: 1.7; margin-bottom: 18px;
    padding: 12px 16px; background: #f8fafc; border-radius: 8px; }
  h4 { font-size: .9rem; color: #64748b; text-transform: uppercase; letter-spacing: .05em;
    margin-bottom: 10px; margin-top: 0; }
  ul { list-style: none; margin-bottom: 20px; }
  ul li { padding: 6px 0 6px 20px; position: relative; border-bottom: 1px dashed #f1f5f9; font-size: .9rem; }
  ul li::before { content: '☑'; position: absolute; left: 0; color: #3b82f6; }
  .rubric-inline table { width: 100%; border-collapse: collapse; font-size: .88rem; }
  .rubric-inline th { background: #f1f5f9; padding: 8px 12px; text-align: left;
    font-weight: 600; color: #475569; border-bottom: 2px solid #e2e8f0; }
  .rubric-inline td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; }
  .rubric-inline td:last-child { text-align: center; font-weight: 600; color: #1e40af; }
  .total-row td { background: #eff6ff !important; border-top: 2px solid #bfdbfe; }
  footer { text-align: center; padding: 20px; font-size: .82rem; color: #94a3b8; border-top: 1px solid #e2e8f0; }
  @media print { body { background: white; } .problem-card { page-break-inside: avoid; } }
</style>
</head>
<body>
<header>
  <h1>🏆 AI챔피언 데이터분석 실습 문제지</h1>
  <p>데이터를 분석하고 산출물을 제출하는 실습형 문제입니다</p>
</header>

<div class="info-bar">
  <div><dt>출제일</dt><dd>${today}</dd></div>
  <div><dt>데이터 건수</dt><dd>${rowCount.toLocaleString()}건</dd></div>
  <div><dt>핵심 지표</dt><dd>${escHtml(recommendedMetric)}</dd></div>
  <div><dt>주요 그룹</dt><dd>${escHtml(recommendedGroup)}</dd></div>
  <div><dt>총 문항</dt><dd>5문항 · 각 100점</dd></div>
</div>

<main>
  <div class="instructions">
    📌 <strong>시험 안내:</strong> 아래 5개 문제를 모두 풀고, 각 문제에서 요구하는 파일을 제출하세요.
    제출 파일명은 문제에 명시된 파일명과 동일하게 작성해야 합니다.
    모든 결과물은 업로드한 데이터를 직접 활용하여 제작해야 합니다.
  </div>

  ${problemCards}
</main>

<footer>
  AI챔피언 데이터분석 문제 자동 생성기 · ${today} 자동 생성
</footer>
</body>
</html>`;
}
