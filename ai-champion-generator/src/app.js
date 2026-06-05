/**
 * app.js
 * 메인 애플리케이션 — 파일 업로드, 프로파일링, 문제/정답 생성, ZIP 다운로드 오케스트레이션
 */

import { profileData } from './dataProfiler.js';
import {
  generateProblems, generateProblemHtml,
  generateRubricCsv, generateAnswerKey,
} from './problemGenerator.js';
import {
  generateDashboardHtml, generateFilterServiceHtml,
  generateVbaCode, generateExcelInstruction, generatePolicyReportHtml,
} from './answerGenerator.js';
import { generateInfographicPng } from './pngGenerator.js';
import { buildExamZip } from './zipBuilder.js';

// ── 상태 ──────────────────────────────────────────────
let parsedRows = null;
let currentProfile = null;
let currentProblems = null;  // 단계 1에서 생성된 문제 저장
let zipBlob = null;

// ── DOM 참조 ──────────────────────────────────────────
const fileInput       = document.getElementById('file-input');
const selectFileBtn   = document.getElementById('select-file-btn');
const loadSampleBtn   = document.getElementById('load-sample-btn');
const uploadBox       = document.getElementById('upload-box');
const fileInfo        = document.getElementById('file-info');
const previewSection  = document.getElementById('preview-section');
const previewContainer = document.getElementById('preview-container');
const profileSection  = document.getElementById('profile-section');
const profileContainer = document.getElementById('profile-container');
const generateSection        = document.getElementById('generate-section');
const generateBtn            = document.getElementById('generate-btn');
const problemPreviewSection  = document.getElementById('problem-preview-section');
const problemPreviewContainer = document.getElementById('problem-preview-container');
const confirmBtn             = document.getElementById('confirm-btn');
const regenerateBtn          = document.getElementById('regenerate-btn');
const logSection             = document.getElementById('log-section');
const logContainer           = document.getElementById('log-container');
const downloadSection        = document.getElementById('download-section');
const downloadBtn            = document.getElementById('download-btn');

// ── 이벤트 리스너 ─────────────────────────────────────
selectFileBtn.addEventListener('click', () => fileInput.click());

uploadBox.addEventListener('dragover', e => { e.preventDefault(); uploadBox.classList.add('dragover'); });
uploadBox.addEventListener('dragleave', () => uploadBox.classList.remove('dragover'));
uploadBox.addEventListener('drop', e => {
  e.preventDefault();
  uploadBox.classList.remove('dragover');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (file) handleFile(file);
});

loadSampleBtn.addEventListener('click', async () => {
  try {
    const res = await fetch('./samples/sample_crime.csv');
    if (!res.ok) throw new Error('샘플 파일을 찾을 수 없습니다.');
    const text = await res.text();
    processCSVText(text, 'sample_crime.csv');
  } catch (err) {
    showFileError('샘플 데이터를 불러오는 중 오류가 발생했습니다: ' + err.message);
  }
});

generateBtn.addEventListener('click', handlePreviewProblems);
confirmBtn.addEventListener('click', handleBuildArtifacts);
regenerateBtn.addEventListener('click', handlePreviewProblems);
downloadBtn.addEventListener('click', () => { if (zipBlob) window.saveAs(zipBlob, 'exam_package.zip'); });

// ── 파일 처리 ─────────────────────────────────────────
function handleFile(file) {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    showFileError('CSV 파일만 업로드할 수 있습니다.');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showFileError('파일 크기가 10MB를 초과합니다.');
    return;
  }

  const reader = new FileReader();
  reader.onload = e => processCSVText(e.target.result, file.name);
  reader.onerror = () => showFileError('파일을 읽는 중 오류가 발생했습니다.');
  reader.readAsText(file, 'UTF-8');
}

function processCSVText(text, filename) {
  // BOM 제거
  const clean = text.replace(/^\uFEFF/, '');

  const result = window.Papa.parse(clean, {
    header: true,
    skipEmptyLines: true,
    transformHeader: h => h.trim(),
  });

  if (!result.data || result.data.length === 0) {
    showFileError('데이터가 비어 있습니다.');
    return;
  }

  parsedRows = result.data;

  // 파일 정보 표시
  fileInfo.innerHTML = `<strong>${escHtml(filename)}</strong> · ${parsedRows.length.toLocaleString()}행 · ${result.meta.fields.length}열 로드 완료`;
  fileInfo.classList.remove('hidden');
  fileInfo.style.color = '';

  // 섹션 리셋
  hideSection(previewSection);
  hideSection(profileSection);
  hideSection(generateSection);
  hideSection(problemPreviewSection);
  hideSection(logSection);
  hideSection(downloadSection);

  // 미리보기
  renderPreview(parsedRows);

  // 프로파일링
  try {
    currentProfile = profileData(parsedRows);
    renderProfile(currentProfile);
    showSection(generateSection);
  } catch (err) {
    showFileError(err.message);
  }
}

// ── UI 렌더링 ─────────────────────────────────────────
function renderPreview(rows) {
  const headers = Object.keys(rows[0]);
  const preview = rows.slice(0, 10);

  let html = '<div class="table-wrapper"><table class="data-table"><thead><tr>';
  headers.forEach(h => { html += `<th>${escHtml(h)}</th>`; });
  html += '</tr></thead><tbody>';
  preview.forEach(row => {
    html += '<tr>';
    headers.forEach(h => { html += `<td>${escHtml(String(row[h] ?? ''))}</td>`; });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  if (rows.length > 10) {
    html += `<p style="font-size:.82rem;color:#94a3b8;margin-top:8px">... 외 ${(rows.length - 10).toLocaleString()}행 생략</p>`;
  }

  previewContainer.innerHTML = html;
  showSection(previewSection);
}

function renderProfile(profile) {
  const { numericColumns, categoryColumns, dateColumns, rowCount, columns,
    recommendedMetric, recommendedGroup, stats } = profile;

  const totalMissing = Object.values(stats).reduce((s, st) => s + (st.missing || 0), 0);

  let html = `
    <div class="profile-grid">
      ${statCard('총 행 수', rowCount.toLocaleString(), '건')}
      ${statCard('총 열 수', columns.length, '개')}
      ${statCard('수치형', numericColumns.length, '개')}
      ${statCard('범주형', categoryColumns.length, '개')}
      ${statCard('날짜/연도', dateColumns.length, '개')}
      ${statCard('결측치', totalMissing.toLocaleString(), '개')}
    </div>
    <div class="profile-tags">
      <strong>수치형:</strong>
      ${numericColumns.map(c => `<span class="tag tag-numeric">${escHtml(c)}</span>`).join('') || '<em style="color:#94a3b8">없음</em>'}
    </div>
    <div class="profile-tags">
      <strong>범주형:</strong>
      ${categoryColumns.map(c => `<span class="tag tag-category">${escHtml(c)}</span>`).join('') || '<em style="color:#94a3b8">없음</em>'}
    </div>
    ${dateColumns.length > 0 ? `
    <div class="profile-tags">
      <strong>날짜/연도:</strong>
      ${dateColumns.map(c => `<span class="tag tag-date">${escHtml(c)}</span>`).join('')}
    </div>` : ''}
    <div class="profile-recommend">
      <strong>분석 추천</strong> &nbsp;→&nbsp;
      지표: <code>${escHtml(recommendedMetric)}</code> &nbsp;&nbsp;
      그룹: <code>${escHtml(recommendedGroup)}</code>
    </div>
  `;

  profileContainer.innerHTML = html;
  showSection(profileSection);
}

function statCard(label, value, unit) {
  return `
    <div class="profile-item">
      <span class="profile-label">${label}</span>
      <span class="profile-value">${value}<small style="font-size:.8rem;font-weight:400"> ${unit}</small></span>
    </div>`;
}

// ── 단계 1: 문제 생성 후 미리보기 표시 ─────────────────────────────
function handlePreviewProblems() {
  generateBtn.disabled = true;
  generateBtn.textContent = '⏳ 분석 중...';

  // 블로킹 해제를 위해 짧은 timeout 후 실행
  setTimeout(() => {
    try {
      currentProblems = generateProblems(currentProfile);
      renderProblemPreview(currentProblems);
      hideSection(logSection);
      hideSection(downloadSection);
      showSection(problemPreviewSection);
      problemPreviewSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      logError('문제 생성 오류: ' + err.message);
      console.error(err);
    }
    generateBtn.disabled = false;
    generateBtn.textContent = '🔍 문제 미리보기';
  }, 30);
}

/** 문제 5개를 인라인 카드로 렌더링 */
function renderProblemPreview(problems) {
  const cards = problems.map(p => `
    <div class="pp-card">
      <div class="pp-header">
        <span class="pp-num">문제 ${p.id}</span>
        <span class="pp-title">${escHtml(p.title)}</span>
        <span class="pp-file">📄 ${escHtml(p.file)}</span>
      </div>
      <div class="pp-body">
        <div class="pp-desc">${escHtml(p.description)}</div>
        <p style="font-size:.8rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">필수 구현 요건</p>
        <ul class="pp-req-list">
          ${p.requirements.map(r => `<li>${escHtml(r)}</li>`).join('')}
        </ul>
        <p style="font-size:.8rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px">채점 기준</p>
        <div class="pp-rubric">
          ${p.rubric.map(rb => `<div class="pp-rubric-item">${escHtml(rb.item)}<strong>${rb.score}점</strong></div>`).join('')}
        </div>
      </div>
    </div>
  `);
  problemPreviewContainer.innerHTML = cards.join('');
}

// ── 단계 2: 확인 후 산출물 생성 ───────────────────────────────────
async function handleBuildArtifacts() {
  confirmBtn.disabled = true;
  regenerateBtn.disabled = true;
  confirmBtn.textContent = '⏳ 산출물 생성 중...';
  logContainer.innerHTML = '';
  showSection(logSection);
  hideSection(downloadSection);
  zipBlob = null;
  logSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  try {
    const problems = currentProblems;

    log('문제지 HTML 생성 중...');
    const problemsHtml = generateProblemHtml(problems, currentProfile);
    log('문제지 HTML 생성 완료');

    log('채점표 CSV 생성 완료');
    const rubricCsv = generateRubricCsv(problems);

    log('대시보드 HTML(문제 1) 생성 중...');
    const dashboardHtml = generateDashboardHtml(parsedRows, currentProfile);
    log('대시보드 HTML 생성 완료');

    log('필터 서비스 HTML(문제 2) 생성 중...');
    const filterHtml = generateFilterServiceHtml(parsedRows, currentProfile);
    log('필터 서비스 HTML 생성 완료');

    log('VBA 코드(문제 3) 생성 중...');
    const vbaCode = generateVbaCode(currentProfile);
    const excelInstruction = generateExcelInstruction(currentProfile);
    log('VBA 코드 및 엑셀 지시서 생성 완료');

    log('PNG 인포그래픽(문제 4) 생성 중...');
    let pngBlob = null;
    try {
      pngBlob = await generateInfographicPng(parsedRows, currentProfile);
      log('PNG 인포그래픽 생성 완료');
    } catch (e) {
      logWarn('PNG 생성 오류 (건너뜀): ' + e.message);
    }

    log('정책 제안 리포트 HTML(문제 5) 생성 중...');
    const policyHtml = generatePolicyReportHtml(parsedRows, currentProfile);
    log('정책 제안 리포트 HTML 생성 완료');

    log('정답 메타 JSON 생성 중...');
    const answerKey = generateAnswerKey(currentProfile, {});
    log('정답 JSON 생성 완료');

    log('ZIP 파일 조립 중...');
    zipBlob = await buildExamZip({
      problemsHtml,
      rubricCsv,
      answerKey: JSON.stringify(answerKey, null, 2),
      dashboardHtml,
      filterHtml,
      vbaCode,
      excelInstruction,
      pngBlob,
      policyHtml,
    });
    log('✨ exam_package.zip 생성 완료!');

    showSection(downloadSection);
    downloadSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    logError('파일 생성 중 오류가 발생했습니다: ' + err.message);
    console.error(err);
  }

  confirmBtn.disabled = false;
  regenerateBtn.disabled = false;
  confirmBtn.textContent = '✅ 확인 — 산출물 생성 시작';
}

// ── 유틸 ──────────────────────────────────────────────
function log(msg) {
  const div = document.createElement('div');
  div.className = 'log-item';
  div.textContent = '✅ ' + msg;
  logContainer.appendChild(div);
}

function logWarn(msg) {
  const div = document.createElement('div');
  div.className = 'log-item log-warn';
  div.textContent = '⚠️ ' + msg;
  logContainer.appendChild(div);
}

function logError(msg) {
  const div = document.createElement('div');
  div.className = 'log-item log-error';
  div.textContent = '❌ ' + msg;
  logContainer.appendChild(div);
}

function showSection(el) { el.classList.remove('hidden'); }
function hideSection(el) { el.classList.add('hidden'); }

function showFileError(msg) {
  fileInfo.innerHTML = `<span style="color:#dc2626">⚠️ ${escHtml(msg)}</span>`;
  fileInfo.style.background = '#fee2e2';
  fileInfo.style.borderLeftColor = '#dc2626';
  fileInfo.classList.remove('hidden');
}

export function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
