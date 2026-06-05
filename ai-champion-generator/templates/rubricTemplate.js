/**
 * rubricTemplate.js
 * 채점표 CSV 생성
 */

export function rubricTemplate(problems) {
  const rows = [];
  rows.push(['문제번호', '문제제목', '제출파일', '채점항목', '배점', '점수', '비고']);

  problems.forEach(p => {
    p.rubric.forEach((rb, idx) => {
      rows.push([
        idx === 0 ? `문제 ${p.id}` : '',
        idx === 0 ? p.title : '',
        idx === 0 ? p.file : '',
        rb.item,
        rb.score,
        '',
        '',
      ]);
    });
    // 소계 행
    rows.push([
      '',
      '',
      '',
      '소계',
      p.rubric.reduce((s, r) => s + r.score, 0),
      '',
      '',
    ]);
    rows.push(Array(7).fill('')); // 빈 행
  });

  // 합계 행
  const totalScore = problems.reduce((s, p) => s + p.rubric.reduce((ss, r) => ss + r.score, 0), 0);
  rows.push(['총점', '', '', '', totalScore, '', '']);

  return rows.map(r => r.map(cell => {
    const s = String(cell);
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"` : s;
  }).join(',')).join('\r\n');
}
